# ==============================================================================
# STAGE 1: Dependency Builder
# ==============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install uv for fast, deterministic dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /bin/uv

# Install system build dependencies for C-extensions
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
