# Implementation Plan: Regulated Agent Harness

**Project Name:** `regulated-agent-harness`  
**Document Version:** 1.0.0  
**Status:** Approved for Execution  
**Target Environment:** Python 3.11+ / uv / FastAPI / LangGraph / LiteLLM / OpenTelemetry / Langfuse  
**Compliance Target:** FDA 21 CFR Part 11, GxP, ISO 27001, SOC2 Type II  

---

## 1. Executive Summary & Purpose

The **Regulated Agent Harness** is a governed, production-grade orchestration and rapid prototyping framework designed for high-liability, heavily audited environments. It bridges the "PoC-to-Production Chasm" by standardizing state-graph execution, multi-provider model routing, human-in-the-loop (HITL) authorization gates, immutable cryptographic audit trails, and automated pre-flight synthetic evaluation.

This Implementation Plan defines the phased roadmap, critical path, dependency management, resource allocations, and risk mitigation strategies required to deliver the harness with zero architectural debt and strict conformance to the Product Requirements Document (PRD).

---

## 2. Project Lifecycle & Phased Execution Strategy

The project adheres to Google Antigravity's **4-Phase Spec-Driven Development Gateway**:

```
+-----------------------------------------------------------------------------------+
| PHASE 1: Elaborate Documentation & Architectural Blueprints                      |
| [Status: IN PROGRESS] -> Produces 7 Core Specifications & ADRs                    |
+-----------------------------------------------------------------------------------+
                                          |
                                    [GATE 1 APPROVAL]
                                          v
+-----------------------------------------------------------------------------------+
| PHASE 2: Test-Driven Development (Test Implementation & Verification)             |
| [Status: PENDING] -> Implements test fixtures, mocks, and full test suite          |
+-----------------------------------------------------------------------------------+
                                          |
                                    [GATE 2 APPROVAL]
                                          v
+-----------------------------------------------------------------------------------+
| PHASE 3: Prioritized Implementation Plan                                          |
| [Status: PENDING] -> Defines atomic build order and dependency graph              |
+-----------------------------------------------------------------------------------+
                                          |
                                    [GATE 3 APPROVAL]
                                          v
+-----------------------------------------------------------------------------------+
| PHASE 4: Functional Implementation & Green Test Cycle                             |
| [Status: PENDING] -> Implements production code until 100% test pass rate         |
+-----------------------------------------------------------------------------------+
```

---

## 3. Work Breakdown Structure (WBS) & Milestones

### Milestone 0: Architectural Clarity (Phase 1)
* **Deliverables:**
  - `IMPLEMENTATION_PLAN.md` (this document)
  - `ARCHITECTURE.md` (System topology, Mermaid diagrams, ADRs)
  - `SOFTWARE_DESIGN_DOCUMENT.md` (Pydantic schemas, class designs, error models)
  - `TEST_STRATEGY_AND_PLAN.md` (Testing philosophy, non-functional testing, mock contracts)
  - `TEST_CASES_SPECIFICATION.md` (Exhaustive test scenarios with exact assertions)
  - `DEPLOYMENT_PLAN.md` (Docker multi-stage, docker-compose, secrets, scaling)
  - `USAGE_GUIDE.md` (Quickstart, tool registration, CLI usage, Langfuse inspection)
* **Exit Criteria:** Review and formal approval at Gate 1.

### Milestone 1: Test Infrastructure & Test Suite (Phase 2)
* **Deliverables:**
  - Test runner configuration (`pytest.ini`, `pyproject.toml`, coverage settings).
  - Test suites in `tests/unit/`, `tests/integration/`, `tests/eval/`, `tests/fixtures/`:
    - `test_types.py`: Pydantic schema validation, serialization, immutability.
    - `test_model_gateway.py`: LiteLLM gateway, streaming, retries, model fallback.
    - `test_tool_registry.py`: `@harness_tool` decorator, Pydantic inputs, MCP adapter.
    - `test_orchestrator.py`: LangGraph state machine, cycles, checkpointing, error recovery.
    - `test_hitl_gate.py`: Interruption on `MUTATING_HIGH_RISK` tools, resume verification.
    - `test_audit_trail.py`: SHA-256 Merkle chain, tamper-evident log detection.
    - `test_telemetry.py`: OTel span propagation, Langfuse export, token cost caps.
    - `test_eval_runner.py`: Synthetic dataset runner, fidelity, and groundedness gates.
    - `test_server_api.py`: FastAPI endpoints (`/run`, `/resume`, `/health`, `/audit`).
* **Exit Criteria:** Execution of test suite producing expected test baselines at Gate 2.

### Milestone 2: Build Sequencing & Risk-Weighted Backlog (Phase 3)
* **Deliverables:**
  - `PRIORITIZED_BUILD_PLAN.md`: Component dependency graph and step-by-step implementation plan.
* **Exit Criteria:** Review and formal approval at Gate 3.

### Milestone 3: Production Core Implementation (Phase 4 - Part A)
* **Deliverables:**
  - Foundation: `harness.core.types`, `harness.core.config`, `harness.core.exceptions`.
  - Engine: `harness.gateway.model`, `harness.registry.tools`, `harness.registry.mcp`.
  - Orchestration: `harness.core.orchestrator`, `harness.core.checkpointer`.
* **Exit Criteria:** Unit tests in `test_types.py`, `test_model_gateway.py`, `test_tool_registry.py`, and `test_orchestrator.py` pass cleanly.

### Milestone 4: Governance, Observability & Evaluation (Phase 4 - Part B)
* **Deliverables:**
  - Interceptors & Guardrails: `harness.middleware.pipeline`, `harness.guardrails.input_guard`, `harness.guardrails.hitl`.
  - Audit Trail: `harness.compliance.audit` (SHA-256 Merkle hash chain).
  - Telemetry: `harness.telemetry.otel`, `harness.telemetry.langfuse`, `harness.telemetry.budget`.
  - Evaluation: `harness.eval.runner`, `harness.eval.metrics`.
* **Exit Criteria:** `test_hitl_gate.py`, `test_audit_trail.py`, `test_telemetry.py`, `test_eval_runner.py` pass.

### Milestone 5: Delivery, CLI & Integration Gating (Phase 4 - Part C)
* **Deliverables:**
  - FastAPI Server: `harness.server.app`, `harness.server.routes`.
  - Scaffolding CLI: `harness.cli.main`, `harness.cli.scaffold`, template directory.
  - Packaging: Multi-stage `Dockerfile`, `docker-compose.yml`, `.env.example`.
* **Exit Criteria:** 100% test pass rate, code coverage >=85%, latency overhead <40ms, `mypy --strict` passes with 0 warnings, `ruff` clean.

---

## 4. Component Dependencies & Critical Path Analysis

The critical path directly influences implementation order and must be strictly respected to avoid blocking circularities:

```
[Core Types & Exceptions] 
       |
       v
[Configuration Engine] 
       |
       +-----------------------+-----------------------+
       |                                               |
       v                                               v
[Model Gateway Abstraction]                    [Tool & MCP Registry]
       |                                               |
       +-----------------------+-----------------------+
                               |
                               v
               [LangGraph State Orchestrator]
                               |
                               v
             [Middleware Interceptor Pipeline]
             /        |               |        \
            v         v               v         v
     [Input Guard] [OTel Tracing] [HITL Gate] [Merkle Audit Trail]
            \         |               |         /
             +--------+-------+-------+--------+
                              |
                              v
                   [FastAPI Runtime Server]
                              |
                              v
                   [Scaffolding CLI & Eval]
```

### Critical Path Dependencies
1. **Types & Config:** Foundation for all modules. Zero external harness dependencies.
2. **Model Gateway & Tools:** Independent modules; depend only on Types.
3. **LangGraph Orchestrator:** Depends on Model Gateway and Tool Registry to define state transitions and node dispatchers.
4. **Middleware Interceptor Chain:** Wraps graph node execution; depends on State and Types.
5. **FastAPI & CLI:** Upper-tier presentation layers depending on Orchestrator, Middleware, and Configuration.

---

## 5. Technology Stack & Environment Setup

### 5.1 Python Runtime & Tooling
* **Python Version:** 3.11.8+ (ensures complete support for modern `asyncio`, typing self-referencing, and performance enhancements).
* **Dependency Manager:** `uv` (recommended for sub-second deterministic resolution) or `poetry`.
* **Static Analysis:** `mypy --strict` for zero-warning type rigor.
* **Linter & Formatter:** `ruff` (replaces flake8, black, isort).
* **Test Runner:** `pytest` (>=8.0.0), `pytest-asyncio`, `pytest-cov`, `pytest-mock`.

### 5.2 Core Libraries & Pinning Matrix

| Component | Library | Minimum Version | Rationale |
|---|---|---|---|
| **State Orchestration** | `langgraph` | `>=0.2.20` | Deterministic cyclical state graph, built-in checkpointing and interrupts |
| **State & Data Validation** | `pydantic` | `>=2.8.0` | High-performance v2 core, strict schema validation, JSON Schema export |
| **Model Gateway** | `litellm` | `>=1.44.0` | Multi-provider abstraction (OpenAI, Anthropic, Bedrock, Ollama, vLLM) |
| **Web Server** | `fastapi` | `>=0.115.0` | Asynchronous REST endpoints, native OpenAPI schema generation |
| **ASGI Server** | `uvicorn[standard]` | `>=0.30.0` | Production async server with HTTP/2 and WebSocket support |
| **Observability** | `opentelemetry-api` | `>=1.26.0` | OpenTelemetry standard instrumentation |
| **Observability SDK** | `opentelemetry-sdk` | `>=1.26.0` | Custom span exporter and trace context propagation |
| **Tracing Sink** | `langfuse` | `>=2.45.0` | Dedicated LLM tracing, token tracking, user feedback metrics |
| **CLI Framework** | `typer[all]` | `>=0.12.0` | Rich terminal formatting, type-hinted CLI subcommands |
| **Evaluation** | `ragas` / `deepeval` | `>=0.1.15` / `>=0.21.0` | Groundedness, answer relevancy, and tool call precision scoring |
| **HTTP Client** | `httpx` | `>=0.27.0` | Asynchronous HTTP client for MCP and REST communications |
| **Persistence (Dev)** | `aiosqlite` | `>=0.20.0` | Async SQLite checkpointer for local development |
| **Persistence (Prod)** | `asyncpg` | `>=0.29.0` | Async PostgreSQL driver for enterprise checkpointing |

---

## 6. Resource Requirements & Operational Constraints

### 6.1 Development Hardware & OS
* **Operating Systems:** Windows 11 / Linux (Ubuntu 22.04 LTS) / macOS Darwin.
* **Memory Requirement:** Minimum 16 GB RAM (32 GB recommended if hosting local Ollama/vLLM containers).
* **CPU:** 8+ vCPUs recommended for concurrent async test execution.

### 6.2 External Connectivity & Mock Strategy
* Development and unit testing must run **100% offline** using deterministic mock gateways.
* Integration and staging tests require external network connectivity or local Docker containers for:
  - Langfuse instance (served locally via `docker-compose.yml`).
  - PostgreSQL 16 (served locally via `docker-compose.yml`).
  - Mock LLM server or LiteLLM mock responses.

---

## 7. Governance, Regulatory & Compliance Plan

The harness is engineered specifically for regulated environments. Compliance features are foundational, not bolted on:

| Regulation / Standard | Requirement | Harness Architectural Mechanism |
|---|---|---|
| **FDA 21 CFR Part 11** | Audit trails must be secure, computer-generated, time-stamped, and tamper-evident. | Append-only SHA-256 Merkle hash chain linking each state transition, tool execution, and user decision. |
| **FDA 21 CFR Part 11** | Authority checks to ensure only authorized individuals can operate the system. | Cryptographically signed HITL approval tokens containing user identity, role, and approval timestamp. |
| **GxP (Good Practice)** | Traceability, reproducibility, and system validation. | Immutable session checkpoints; deterministic state replay; pre-flight synthetic evaluation quality gates. |
| **ISO 27001 / SOC2** | Data minimization, input sanitization, and access governance. | Pre-execution PII/PHI redaction regex filter; Prompt injection guard; Tool risk tiering (`READ_ONLY` vs `MUTATING_HIGH_RISK`). |

---

## 8. Risk Management Matrix

| Risk ID | Description | Severity | Likelihood | Mitigation Strategy |
|---|---|---|---|---|
| **RSK-01** | Middleware latency exceeds 40ms SLA due to cryptographic hashing or OTel overhead. | High | Medium | Implement zero-copy hashing with optimized SHA-256 C-bindings (`hashlib`); execute non-critical OTel exports in background async tasks. |
| **RSK-02** | Non-deterministic state recovery after HITL interrupt causes duplicate tool calls. | Critical | Low | Utilize LangGraph's persistent state checkpointing keyed by unique `checkpoint_id`; store exact tool call ID and prohibit duplicate execution. |
| **RSK-03** | Model provider outage stalls agent execution in production. | High | Medium | Configure LiteLLM fallback cascading (e.g., Azure OpenAI -> AWS Bedrock -> Claude 3.5 Sonnet) with exponential backoff and jitter. |
| **RSK-04** | Runaway LLM loops exhaust token budgets. | High | Medium | Implement a two-tier ceiling: strict `max_iterations` counter (e.g., 10) in `HarnessState` and `CostBudgetGuard` with cumulative dollar limits. |
| **RSK-05** | Remote MCP tool schemas fail runtime validation. | Medium | Medium | Validate all tool inputs against Pydantic v2 schemas prior to dispatch; route schema validation errors to the error-handling fallback node. |

---

## 9. Quality Gates & Acceptance Sign-Off

Progression between phases requires satisfying the following strict acceptance criteria:

* **Gate 1 (Documentation Sign-Off):** All 7 specification documents written, self-consistent, cross-referenced, and approved.
* **Gate 2 (Test Implementation Sign-Off):** 100% of test cases specified in `TEST_CASES_SPECIFICATION.md` implemented with deterministic fixtures.
* **Gate 3 (Build Plan Sign-Off):** Component sequencing reviewed and approved without circular dependencies.
* **Gate 4 (Production Code & Green Cycle Sign-Off):**
  - All tests passing (100% pass rate).
  - Code coverage `>= 85%` across `src/harness/core`, `src/harness/middleware`, and `src/harness/registry`.
  - Static type checking: 0 errors with `mypy --strict`.
  - Code style: 0 errors with `ruff check .` and `ruff format --check .`.
  - Middleware latency overhead verified `< 40ms`.
  - Final Verification Report generated and approved.
