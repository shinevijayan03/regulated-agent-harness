# Deployment Plan: Regulated Agent Harness

**Document Version:** 1.0.0  
**Status:** Approved  
**Classification:** DevOps & Infrastructure Engineering Specification  
**Target Environments:** Local Docker Compose / Kubernetes (EKS / GKE / AKS)  
**Security Baseline:** CIS Docker Benchmark, Non-Root Execution, Distroless/Slim Base  

---

## 1. Containerization Specification (Multi-Stage Dockerfile)

To ensure minimal attack surface, rapid build caching, and compliance with enterprise container security policies, the harness utilizes a **multi-stage Python 3.11 Docker build**.

### 1.1 Dockerfile Architecture
- **Stage 1: Builder:** Uses `python:3.11-slim` with `uv` for ultra-fast, deterministic compilation of wheel dependencies into a isolated virtual environment (`/opt/venv`).
- **Stage 2: Runtime:** Uses a clean `python:3.11-slim` base image, copies only the prepared virtual environment and application code, creates a non-root system user (`harness:harness`), and drops all root privileges.

### 1.2 Production `Dockerfile` Specification
```dockerfile
# ==============================================================================
# STAGE 1: Dependency Builder
# ==============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install uv for fast, deterministic dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /bin/uv

# Install system build dependencies for C-extensions (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definitions
COPY pyproject.toml README.md ./

# Create virtualenv and install dependencies
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
RUN uv venv /opt/venv && \
    uv pip install --no-cache -e .

# ==============================================================================
# STAGE 2: Hardened Production Runtime
# ==============================================================================
FROM python:3.11-slim AS runtime

LABEL maintainer="AI Platforms & Forward Deployed Engineering" \
      version="1.0.0" \
      compliance="FDA 21 CFR Part 11 / SOC2 Type II"

WORKDIR /app

# Install minimal runtime dependencies (libpq for postgres client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user and group
RUN groupadd -r harness --gid 10001 && \
    useradd -r -g harness --uid 10001 --shell /sbin/nologin --home-dir /app harness

# Copy pre-built virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source code
COPY --chown=harness:harness src/ /app/src/
COPY --chown=harness:harness pyproject.toml /app/

# Switch to unprivileged non-root user
USER harness:harness

# Expose FastAPI HTTP port
EXPOSE 8000

# Healthcheck probe
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health/live || exit 1

# Launch ASGI server with production tuning
ENTRYPOINT ["uvicorn", "harness.server.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info"]
```

---

## 2. Docker Compose Infrastructure Topology

For local development and on-premise PoC deployments, `docker-compose.yml` orchestrates the complete harness ecosystem including persistent PostgreSQL checkpointing and Langfuse full-stack observability.

```mermaid
flowchart TD
    subgraph Host["Host Network / Ingress"]
        ClientPort["HTTP :8000 (Agent API)"]
        LangfusePort["HTTP :3000 (Langfuse UI)"]
    end

    subgraph ComposeNetwork["Docker Network: harness-net"]
        AgentApp["fastapi-agent-harness\n(Python 3.11 Runtime)"]
        PostgresDB["postgres-checkpointer\n(PostgreSQL 16)"]
        LangfuseServer["langfuse-server\n(Web & Tracing API)"]
        LangfuseWorker["langfuse-worker\n(Background Async Queue)"]
        ClickHouseDB["clickhouse\n(Analytics Sink for Langfuse)"]
        RedisQueue["redis\n(Queue for Langfuse Tasks)"]
        MinioStore["minio\n(S3 Object Store for Traces)"]
    end

    ClientPort --> AgentApp
    LangfusePort --> LangfuseServer

    AgentApp -->|State Checkpoints & Audit Logs| PostgresDB
    AgentApp -->|OTel Tracing & LLM Spans| LangfuseServer

    LangfuseServer --> PostgresDB
    LangfuseServer --> ClickHouseDB
    LangfuseServer --> RedisQueue
    LangfuseServer --> MinioStore

    LangfuseWorker --> RedisQueue
    LangfuseWorker --> PostgresDB
    LangfuseWorker --> ClickHouseDB
```

### 2.1 Complete `docker-compose.yml` Specification
```yaml
version: '3.8'

networks:
  harness-net:
    driver: bridge

volumes:
  pgdata:
  clickhousedata:
  miniodata:
  langfusedata:

services:
  # ============================================================================
  # 1. Regulated Agent Harness FastAPI Service
  # ============================================================================
  agent-harness:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: regulated-agent-harness
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - PRIMARY_MODEL=azure/gpt-4o
      - FALLBACK_MODELS=bedrock/anthropic.claude-3-5-sonnet
      - CHECKPOINTER_TYPE=postgres
      - DATABASE_URL=postgresql://harness_user:harness_secure_pw@postgres:5432/harness_db
      - LANGFUSE_HOST=http://langfuse-server:3000
      - LANGFUSE_PUBLIC_KEY=pk-lf-enterprise-harness
      - LANGFUSE_SECRET_KEY=sk-lf-enterprise-secret
      - MAX_SESSION_COST_USD=1.00
      - MAX_ITERATIONS=10
    depends_on:
      postgres:
        condition: service_healthy
      langfuse-server:
        condition: service_started
    networks:
      - harness-net

  # ============================================================================
  # 2. PostgreSQL 16 (LangGraph Checkpoints & Audit Store)
  # ============================================================================
  postgres:
    image: postgres:16-alpine
    container_name: harness-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: harness_user
      POSTGRES_PASSWORD: harness_secure_pw
      POSTGRES_DB: harness_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U harness_user -d harness_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - harness-net

  # ============================================================================
  # 3. Langfuse Server (Enterprise LLM Observability Sink)
  # ============================================================================
  langfuse-server:
    image: langfuse/langfuse:2
    container_name: harness-langfuse-server
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://harness_user:harness_secure_pw@postgres:5432/harness_db
      - NEXTAUTH_URL=http://localhost:3000
      - NEXTAUTH_SECRET=changeme-in-production-auth-secret
      - SALT=changeme-in-production-salt
      - TELEMETRY_ENABLED=false
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - harness-net
```

---

## 3. Environment Variables & Secret Configuration

Configuration is managed via Pydantic v2 `BaseSettings` reading from `.env` or system environment variables:

| Variable Name | Required | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `production` | Deployment environment: `development`, `staging`, `production`. |
| `PRIMARY_MODEL` | Yes | `azure/gpt-4o` | Primary model identifier passed to LiteLLM. |
| `FALLBACK_MODELS` | No | `""` | Comma-separated list of secondary models for failover. |
| `AZURE_API_KEY` | Conditional | `None` | API key if using Azure OpenAI provider. |
| `AZURE_API_BASE` | Conditional | `None` | Endpoint URL for Azure OpenAI deployment. |
| `ANTHROPIC_API_KEY`| Conditional | `None` | API key if using Anthropic Claude models. |
| `AWS_REGION_NAME` | Conditional | `us-east-1` | AWS region if using Bedrock models. |
| `DATABASE_URL` | Yes | - | Connection string for checkpointer and audit logs. |
| `CHECKPOINTER_TYPE`| Yes | `postgres` | Storage type: `sqlite` (dev) or `postgres` (prod). |
| `LANGFUSE_HOST` | Yes | `http://localhost:3000` | Host endpoint for Langfuse OTLP ingest. |
| `LANGFUSE_PUBLIC_KEY`| Yes | - | Langfuse project public credential. |
| `LANGFUSE_SECRET_KEY`| Yes | - | Langfuse project secret credential. |
| `MAX_SESSION_COST_USD`| No | `0.50` | Maximum allowable spend per session before tripping guard. |
| `MAX_ITERATIONS` | No | `10` | Hard loop ceiling preventing infinite execution cycles. |
| `PII_MASKING_STRICT`| No | `false` | If true, aborts execution on PII; if false, redacts in-place. |

---

## 4. Production Readiness, Health Checks & Scaling

### 4.1 Kubernetes Probes
- **Liveness Probe (`/v1/health/live`):** Returns 200 if the FastAPI event loop is responsive.
- **Readiness Probe (`/v1/health/ready`):** Returns 200 only if:
  1. PostgreSQL checkpointer connection pool is healthy.
  2. Primary or fallback model gateway endpoints respond to ping.
  3. Disk and memory utilization remain within safe operational thresholds.

### 4.2 Graceful Shutdown Procedure
Upon receiving `SIGTERM` or `SIGINT`:
1. The server stops accepting new incoming HTTP connections (Kubernetes removes pod from Service endpoints).
2. Active state-graph sessions in flight are allowed up to 30 seconds to finish or persist a durable checkpoint.
3. The cryptographic audit trail flushes all in-memory buffers to disk.
4. Database connection pools close cleanly.
