# Product Requirements Document (PRD)

## Project: `enterprise-agent-harness`

**Document Version:** 1.0.0

**Target Execution Engine:** Google Antigravity Coding Agent (Spec-Driven Development)

**Author / Architect:** Shine Vijayan (Director, AI Platforms & Forward Deployed Engineering)

**Status:** Ready for Implementation

---

## 1. Antigravity Agent Directives & SDD Operational Rules

When ingesting this PRD in **Google Antigravity**, the autonomous agent must adhere to the following execution constraints:

1. **Spec-Driven Primacy:** Implement only what is specified in this PRD. Do not introduce extraneous frameworks or decorative abstractions.
2. **Atomic Step Progression:** Execute tasks sequentially as ordered in **Section 8 (Implementation Task Breakdown)**. Mark items as completed (`[x]`) only after corresponding unit/integration tests pass.
3. **No Mocks in Final Layer:** All internal components (state graph, middleware, logging, eval runner) must be fully functional software. Use mocks only for external third-party API calls (e.g., Azure OpenAI network endpoints) in offline test suites.
4. **Zero-Warning Rigor:** Strict typing enforced with `mypy --strict`, linted with `ruff`, and verified with `pytest -v --cov`.

---

## 2. Executive Overview & Problem Statement

### 2.1 The Enterprise Problem

Enterprise AI teams struggle with a persistent bottleneck: **the PoC-to-Production Chasm**. When business units request a new agentic use case (e.g., contract analysis, compliance triage, customer support automation), Forward Deployed Engineering (FDE) teams spend 4–8 weeks rebuilding boilerplate plumbing: state handling, auth, API routing, tracing, guardrails, and compliance logs. Conversely, hackathon prototypes built on naive scripts fail security, compliance (FDA 21 CFR Part 11 / SOC2), and observability reviews.

### 2.2 The Solution

`enterprise-agent-harness` is a **governed, production-ready scaffolding framework and CLI generator** that enables FDE squads to build, instrument, evaluate, and deploy an enterprise-grade, multi-tool AI agent in **under 48 hours**.

It standardizes:

* Deterministic state-graph orchestration with human-in-the-loop (HITL) gates.
* Multi-provider LLM abstraction (OpenAI, Anthropic, Bedrock, and local vLLM).
* OpenTelemetry-native observability with pre-integrated Langfuse tracking.
* Pre-flight automated synthetic evaluation (groundedness, tool-calling accuracy, safety).
* Immutable, tamper-evident audit logging for regulated compliance.

---

## 3. User Personas & Target Workflows

| Persona | Role | Primary Objective |
| --- | --- | --- |
| **Forward Deployed Engineer (FDE)** | Customer-embedded AI Engineer | Scaffold a bespoke business agent in 1 day with production tracing and tool routing ready out of the box. |
| **Enterprise AI Platform Director** | Architecture & Governance Lead | Enforce standard guardrails, MRM risk-tier scoring, and unified audit logs across all business-unit deployments. |
| **Business Unit Sponsor** | Pharma / Supply Chain / Ops Lead | Verify agent task accuracy, auditability, and safety before approving transition from PoC to Pilot. |

---

## 4. Architectural Blueprint

```
                      +------------------------------------------+
                      |         FastAPI Gateway / CLI            |
                      +------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                           ENTERPRISE AGENT HARNESS                                |
|                                                                                   |
|  +---------------------+   +-----------------------+   +-----------------------+  |
|  |   Model Gateway     |   |   State Orchestrator  |   |    Tool & MCP Hub     |  |
|  | (LiteLLM / vLLM /   |<->|  (LangGraph State     |<->| (Schema Validation,   |  |
|  |  Azure / Bedrock)   |   |   Checkpoint Engine)  |   |  RBAC, Safe Exec)     |  |
|  +---------------------+   +-----------------------+   +-----------------------+  |
|                                        |                                          |
|                                        v                                          |
|  +-----------------------------------------------------------------------------+  |
|  |                       Middleware Interceptor Chain                          |  |
|  |  [1. Input Guard] -> [2. OTel Tracing] -> [3. HITL Gate] -> [4. Audit Log]   |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
           |                                                      |
           v                                                      v
+-----------------------+                              +-----------------------+
|  Observability Sink   |                              | Pre-flight Synthetic  |
| (Langfuse / OTel OTLP)|                              | Eval Runner (Ragas)   |
+-----------------------+                              +-----------------------+

```

---

## 5. Technology Stack & Constraints

* **Language:** Python 3.11+
* **Dependency Management:** `uv` (preferred) or `poetry`
* **Orchestration Engine:** `LangGraph` (>=0.2.x) for deterministic state machines and checkpointing
* **LLM Abstraction:** `LiteLLM` / custom provider interface supporting streaming and structured output
* **API Framework:** `FastAPI` (>=0.115.x) + `Pydantic` v2
* **Observability:** `OpenTelemetry SDK` + `Langfuse Python SDK`
* **Evaluation:** `Ragas` / `DeepEval` for programmatic quality gating
* **Packaging:** Docker multi-stage build + Docker Compose for local development

---

## 6. Functional Requirements & Component Specifications

### 6.1 Module 1: Deterministic State-Graph Orchestrator (`harness.core.graph`)

* **State Management:** Define a typed `HarnessState` inheriting from `pydantic.BaseModel` tracking messages, execution plan, scratchpad, tool results, risk score, and step counter.
* **Checkpointing:** In-memory checkpointer for development, SQLite/PostgreSQL checkpointer for production state resumption.
* **Failure Boundaries:** Built-in retry with exponential backoff on transient model failures; automatic fallback to a designated graceful-degradation node on unrecoverable tool errors.
* **Loop Prevention:** Configurable `max_iterations` counter terminating runaway agent loops with a structured error response.

### 6.2 Module 2: Model & Tool Registry with MCP Support (`harness.registry`)

* **Unified Model Interface:** Single configuration to toggle between cloud APIs (Azure OpenAI, Claude 3.5, Gemini 1.5) and self-hosted models (Ollama, vLLM) without changing code.
* **Structured Tool Registry:** Decorator `@harness_tool` that enforces Pydantic input schemas, docstring extraction for model prompts, and execution timeouts.
* **MCP Client Integration:** Capability to connect to external Model Context Protocol (MCP) servers via stdio or SSE transports, exposing remote enterprise tools into the local agent harness.

### 6.3 Module 3: Enterprise Policy & Compliance Guardrails (`harness.guardrails`)

* **Pre-Execution Filter:** Regex and keyword checks for Prompt Injection, PII/PHI redaction, and banned terminology.
* **Human-In-The-Loop (HITL) Approval Gate:**
* Dynamic classification of tools into `READ_ONLY` vs. `MUTATING_HIGH_RISK`.
* When a `MUTATING_HIGH_RISK` tool is called, the graph enters an `INTERRUPT` state, generating a pending approval ticket.
* Execution resumes only upon receiving a cryptographically signed approval payload via API.


* **Immutable Audit Logging (21 CFR Part 11 Readiness):**
* Every step records: Timestamp (UTC ISO-8601), Trace ID, Actor (User/Agent), Tool Name, Exact Input JSON, Output JSON, Model Name, and Cryptographic Hash (SHA-256) chained to the prior entry.



### 6.4 Module 4: Observability & Telemetry (`harness.telemetry`)

* **OTel Auto-Instrumentation:** OpenTelemetry spans wrapping each graph node transition, LLM call, and tool execution.
* **Langfuse Exporter:** Seamless export of traces, token counts, latency breakdowns, and user feedback scores to Langfuse.
* **Cost & Budget Guard:** Real-time token usage accumulator that halts or alerts if a single session exceeds a configurable cost threshold (e.g., $0.50).

### 6.5 Module 5: Pre-Flight Evaluation Harness (`harness.eval`)

* **Synthetic Test Runner:** Automated CLI command (`harness eval --dataset <path>`) that executes the agent against a golden test set.
* **Metric Suite:**
* *Tool Call Precision:* Did the agent pick the correct tool with valid schema parameters?
* *Faithfulness (Ragas):* Is the answer grounded exclusively in the context provided by tools?
* *Answer Relevancy:* Does the output satisfy the original user prompt?


* **Quality Gate:** Returns a non-zero exit code if score drops below enterprise thresholds (e.g., Faithfulness < 0.85), preventing CI/CD deployment of degraded agent versions.

### 6.6 Module 6: Scaffolding CLI (`harness.cli`)

* **Command `harness init <agent-name>`:** Generates a production-ready agent project structure with:
* Pre-wired `agent.py` state graph.
* Sample tools (`tools/`) with unit test stubs.
* `Dockerfile` & `docker-compose.yml` (spinning up FastAPI agent + local Langfuse + PostgreSQL).
* `.env.example` with documented configuration parameters.
* `README.md` containing pre-built architecture diagrams and run commands.



---

## 7. Data Models & API Contracts

### 7.1 Core State Schema

```json
{
  "session_id": "uuid-v4",
  "user_id": "string",
  "messages": [
    {
      "role": "user | assistant | system | tool",
      "content": "string",
      "tool_call_id": "optional-string"
    }
  ],
  "current_node": "string",
  "iteration_count": 0,
  "risk_tier": "LOW | MEDIUM | CRITICAL",
  "hitl_pending": false,
  "audit_trail": [
    {
      "step": 1,
      "timestamp": "2026-10-06T14:00:00Z",
      "action": "tool_execution",
      "tool_name": "query_database",
      "input_hash": "sha256...",
      "output_hash": "sha256...",
      "status": "SUCCESS"
    }
  ]
}

```

### 7.2 FastAPI Agent Execution Endpoint Contract

* **POST `/v1/agents/{agent_id}/run**`
* **Request Body:**
```json
{
  "session_id": "string (optional)",
  "message": "string (required)",
  "context": { "user_role": "analyst", "department": "supply_chain" }
}

```


* **Response Body (Synchronous Completion):**
```json
{
  "session_id": "string",
  "status": "COMPLETED",
  "output": "string",
  "trace_url": "https://langfuse.internal/trace/xyz",
  "latency_ms": 1420,
  "token_usage": { "prompt": 450, "completion": 120, "total_cost_usd": 0.003 }
}

```


* **Response Body (HITL Interruption):**
```json
{
  "session_id": "string",
  "status": "REQUIRES_APPROVAL",
  "approval_id": "appr-8821",
  "proposed_action": {
    "tool": "trigger_quarantine_lot",
    "parameters": { "lot_id": "LT-9921", "reason": "Cold chain excursion" }
  },
  "message": "Execution paused. High-risk tool invocation requires supervisor authorization."
}

```





---

## 8. Antigravity Implementation Task Breakdown (`TASKS.md`)

*Antigravity Agent: Check off each item sequentially and execute tests before moving to the next task.*

### Phase 1: Repository Foundation & Core Types

* [ ] **Task 1.1:** Initialize project directory structure (`src/harness/`, `tests/`, `examples/`, `docker/`).
* [ ] **Task 1.2:** Configure `pyproject.toml` with `uv`/`poetry`, defining core dependencies (`langgraph`, `fastapi`, `pydantic`, `litellm`, `opentelemetry-api`, `langfuse`, `pytest`, `ruff`, `mypy`).
* [ ] **Task 1.3:** Implement `harness.core.types` with Pydantic v2 schemas: `AgentMessage`, `HarnessState`, `ToolDefinition`, `AuditRecord`, and `AgentResponse`.
* [ ] **Task 1.4:** Write unit tests for schema serialization and validation in `tests/test_types.py`.

### Phase 2: Model Gateway & Tool Hub

* [ ] **Task 2.1:** Implement `harness.gateway.model` encapsulating LiteLLM with uniform streaming, structured outputs, and fallback retries.
* [ ] **Task 2.2:** Implement `harness.registry.tools` with `@harness_tool` decorator, runtime schema validation, and risk-tier tagging (`READ_ONLY` vs `MUTATING_HIGH_RISK`).
* [ ] **Task 2.3:** Implement simple MCP client connector in `harness.registry.mcp` to register tools from standard MCP endpoints.
* [ ] **Task 2.4:** Write unit tests for tool registration and model dispatch in `tests/test_registry.py`.

### Phase 3: Graph Engine & Interceptors

* [ ] **Task 3.1:** Implement `harness.core.orchestrator` constructing LangGraph state graphs with configurable nodes (Reasoner, Tool Executor, Human Reviewer, Error Handler).
* [ ] **Task 3.2:** Implement middleware chain in `harness.middleware.pipeline` executing pre-node and post-node hooks.
* [ ] **Task 3.3:** Implement `harness.guardrails.hitl` interceptor that triggers LangGraph `interrupt()` when a high-risk tool is selected.
* [ ] **Task 3.4:** Implement `harness.compliance.audit` logging SHA-256 hashed records of all state transitions to an append-only JSONL/SQLite log.
* [ ] **Task 3.5:** Write integration tests in `tests/test_orchestrator.py` verifying state loop execution, interrupt/resume flows, and audit log generation.

### Phase 4: Telemetry & Observability

* [ ] **Task 4.1:** Implement `harness.telemetry.otel` configuring tracer providers and custom span attributes for agent nodes.
* [ ] **Task 4.2:** Integrate Langfuse trace callback handler forwarding token counts and prompt/completion payloads.
* [ ] **Task 4.3:** Implement `CostBudgetGuard` checking token consumption against threshold limits.
* [ ] **Task 4.4:** Write tests in `tests/test_telemetry.py` with mock OpenTelemetry collectors.

### Phase 5: Evaluation Framework

* [ ] **Task 5.1:** Implement `harness.eval.runner` loading synthetic test cases (JSON/YAML) and running batch evaluations through the harness.
* [ ] **Task 5.2:** Implement evaluation scorers: `ToolCallFidelityScorer` and `GroundednessScorer`.
* [ ] **Task 5.3:** Build CLI command `harness eval` that outputs a formatted summary table and exits with code 1 if thresholds fail.
* [ ] **Task 5.4:** Write tests in `tests/test_eval.py`.

### Phase 6: FastAPI Server & Scaffolding CLI

* [ ] **Task 6.1:** Implement FastAPI application in `harness.server.app` exposing `/run`, `/resume`, `/health`, and `/audit` endpoints.
* [ ] **Task 6.2:** Implement Typer/Click CLI in `harness.cli.main` with commands: `harness new <name>`, `harness run`, and `harness eval`.
* [ ] **Task 6.3:** Create project template in `harness/templates/default/` with starter `agent.py`, sample tools, and Docker Compose configuration.
* [ ] **Task 6.4:** Provide `docker-compose.yml` linking the FastAPI app, PostgreSQL (for checkpointer), and local Langfuse.

### Phase 7: Documentation & Quality Verification

* [ ] **Task 7.1:** Generate comprehensive `README.md` containing architecture diagrams, quickstart guide, and FDE workflow explanation.
* [ ] **Task 7.2:** Add Architecture Decision Records in `docs/adr/`:
* `ADR-001-langgraph-state-machine.md`
* `ADR-002-immutable-audit-strategy.md`
* `ADR-003-hitl-interrupt-model.md`


* [ ] **Task 7.3:** Run full verification suite (`ruff check .`, `mypy --strict src/`, `pytest --cov=src`). Ensure 100% pass rate.

---

## 9. Non-Functional Requirements & Acceptance Criteria

1. **Latency Overhead:** The harness middleware (tracing + audit hashing + schema checks) must add **< 40ms** of overhead per tool invocation.
2. **Deterministic Resumption:** Resuming an agent from a HITL interruption must restore exact conversation history and state without duplicating prior tool executions.
3. **Audit Immutability:** Any manual alteration of an entry in the audit trail must be detectable via cryptographic hash chain validation.
4. **Test Coverage:** Minimum **85% code coverage** across `core/`, `middleware/`, and `registry/`.
5. **Zero Vendor Lock-in:** Swapping the underlying model provider (e.g., Azure OpenAI to open-weights vLLM) must require changing only 2 lines in `.env`, with zero codebase modifications.