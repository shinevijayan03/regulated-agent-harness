# Prioritized Implementation Plan: Regulated Agent Harness

**Document Version:** 1.0.0  
**Phase:** Phase 3 (Build Sequencing & Risk-Weighted Backlog)  
**Objective:** Sequence the implementation roadmap to turn the 20 failing tests green with zero circular dependencies, minimal rework, and strict architectural integrity.  

---

## 1. Dependency Analysis & Sequencing Rationale

To transition our test suite from Red to Green cleanly, components must be implemented strictly from leaf nodes (lowest-level foundation) to composite coordination layers (orchestrator, middleware) and finally presentation gateways (FastAPI, CLI).

### Component Dependency Graph:
```
[Priority 1: Foundation]
  - harness.core.types (Validated)
  - harness.core.exceptions (Complete)
  - harness.core.config (Settings & env vars)
         |
         v
[Priority 2: Engine & Protocols]
  - harness.gateway.model (LiteLLM, retry, fallback)
  - harness.registry.tools (@harness_tool, schema parser)
  - harness.registry.mcp (Remote MCP adapter)
         |
         v
[Priority 3: Orchestration Core]
  - harness.core.orchestrator (LangGraph state machine)
  - harness.core.checkpointer (aiosqlite / in-memory)
         |
         v
[Priority 4: Enterprise Governance & Compliance]
  - harness.guardrails.input_guard (Regex & PII/PHI redaction)
  - harness.guardrails.hitl (Risk tier interrupt gate)
  - harness.compliance.audit (SHA-256 Merkle chain)
  - harness.middleware.pipeline (Sequential runner)
         |
         v
[Priority 5: Observability & Quality Gates]
  - harness.telemetry.budget (CostBudgetGuard)
  - harness.telemetry.otel (Spans & attributes)
  - harness.eval.metrics (Fidelity, Groundedness)
  - harness.eval.runner (CLI synthetic runner)
         |
         v
[Priority 6: Delivery & Interfaces]
  - harness.server.app & routes (/run, /resume, /audit)
  - harness.cli.main & scaffold (harness init, harness eval)
  - Templates & Docker assets
```

---

## 2. Priority Breakdown & Test Transition Roadmap

### Priority 1: Foundation Layer
* **Target Modules:**
  - `src/harness/core/config.py`: `HarnessSettings` utilizing Pydantic `BaseSettings` reading `.env` (model providers, database URLs, Langfuse credentials, budget caps).
  - `src/harness/core/exceptions.py`: Refine any missing error message formatting and attributes.
* **Test Transition Target:**
  - `test_types.py`: 100% Green (4/4 passing).

---

### Priority 2: Engine Subsystems (Gateway & Registry)
* **Target Modules:**
  - `src/harness/gateway/model.py`: Implement `LiteLLMModelGateway` supporting:
    - Asynchronous chat completions via `litellm.acompletion`.
    - Automated exponential backoff with full jitter on transient rate limits (HTTP 429).
    - Sequential fallback cascading across `fallback_models` on provider unavailability (HTTP 503).
    - Tool call serialization into OpenAI-compatible format and response deserialization into `ToolCall` and `AgentMessage`.
  - `src/harness/registry/tools.py`: Implement `ToolRegistry` and `@harness_tool`:
    - Dynamic docstring and Python type hint inspection generating JSON Schema parameter specs.
    - Runtime argument validation against generated schemas (raising `SchemaValidationError` on mismatch).
    - Asynchronous tool execution wrapped in `asyncio.wait_for`.
  - `src/harness/registry/mcp.py`: Implement `MCPClientAdapter`:
    - Translation of remote MCP tool schemas into `ToolDefinition`.
    - Local namespace prefixing (`{server_name}__{tool_name}`).
    - Remote executor routing.
* **Test Transition Target:**
  - `tests/unit/test_model_gateway.py` (3 tests): RED $\rightarrow$ **GREEN**
  - `tests/unit/test_tool_registry.py` (3 tests): RED $\rightarrow$ **GREEN**

---

### Priority 3: State Orchestration Engine
* **Target Modules:**
  - `src/harness/core/orchestrator.py`: Implement `HarnessOrchestrator` using LangGraph:
    - Directed state graph with nodes: `ingress`, `reasoner`, `tool_router`, `tool_executor`, `hitl_gate`, `error_fallback`, `finalize`.
    - Loop prevention: strict tracking of `iteration_count`; clean degradation to `error_fallback` when `iteration_count >= max_iterations`.
    - Durable state checkpointing per `session_id`.
    - Multi-turn message state accumulation without message loss.
* **Test Transition Target:**
  - `tests/integration/test_orchestrator.py` (2 tests): RED $\rightarrow$ **GREEN**

---

### Priority 4: Enterprise Governance & Compliance
* **Target Modules:**
  - `src/harness/guardrails/input_guard.py`: Implement `InputGuardInterceptor`:
    - Pre-node regex pattern matching for prompt injection attempts (raising `PromptInjectionDetected`).
    - In-place sanitization and redaction for SSNs (`[REDACTED_SSN]`) and emails (`[REDACTED_EMAIL]`).
  - `src/harness/guardrails/hitl.py`: Implement `HITLGateInterceptor`:
    - Inspection of pending tool calls against registered risk tiers (`READ_ONLY` vs `MUTATING_HIGH_RISK`).
    - Interruption mechanism emitting UUIDv4 `approval_id` and setting `hitl_pending = True`.
    - Deterministic resumption in `orchestrator.resume()` accepting signed authorization tokens, preventing duplicate tool invocation.
  - `src/harness/compliance/audit.py`: Implement `CryptographicAuditTrail`:
    - Genesis block generation with `prev_hash = "0" * 64`.
    - Deterministic canonical JSON serialization and SHA-256 block hashing:
      $$\text{block\_hash} = \text{SHA256}(\text{prev\_hash} + \text{step} + \text{timestamp} + \text{actor} + \text{action} + \text{payload\_hash})$$
    - Full chain validation algorithm raising `AuditIntegrityException` indicating the exact corrupted index upon tamper detection.
* **Test Transition Target:**
  - `tests/integration/test_hitl_gate.py` (2 tests): RED $\rightarrow$ **GREEN**
  - `tests/unit/test_audit_trail.py` (2 tests): RED $\rightarrow$ **GREEN**
  - `tests/unit/test_telemetry.py` (Input guard tests): RED $\rightarrow$ **GREEN**

---

### Priority 5: Observability & Pre-Flight Quality Gates
* **Target Modules:**
  - `src/harness/telemetry/budget.py`: Implement `CostBudgetGuard` checking token costs against thresholds.
  - `src/harness/eval/metrics.py`: Implement `ToolCallFidelityScorer`, `GroundednessScorer`, and `AnswerRelevancyScorer`.
  - `src/harness/eval/runner.py`: Implement `SyntheticEvalRunner` executing batch evaluations against golden datasets, computing averages, and enforcing quality gate thresholds.
* **Test Transition Target:**
  - `tests/unit/test_telemetry.py` (CostBudgetGuard): RED $\rightarrow$ **GREEN**
  - `tests/eval/test_eval_runner.py` (2 tests): RED $\rightarrow$ **GREEN**

---

### Priority 6: Delivery, Interfaces & API Endpoints
* **Target Modules:**
  - `src/harness/server/routes.py`: Implement endpoints:
    - `POST /v1/agents/{id}/run`: Synchronous execution or HTTP 202 HITL interruption.
    - `POST /v1/agents/{id}/resume`: Signed resumption endpoint.
    - `GET /v1/agents/{id}/audit/verify`: Audit chain validation endpoint.
    - `GET /v1/health/live` & `GET /v1/health/ready`: System health probes.
  - `src/harness/cli/main.py`: Implement Typer CLI subcommands:
    - `harness init <agent-name>`: Scaffold new projects from templates.
    - `harness run`: Launch FastAPI development server.
    - `harness eval`: Run pre-flight evaluation suite with exit code gates.
  - Template scaffolding directory `src/harness/templates/default/`.
* **Test Transition Target:**
  - `tests/integration/test_server_api.py` (3 tests): RED $\rightarrow$ **GREEN**

---

## 3. Verification & Quality Gates

At the conclusion of Priority 6:
1. **Test Pass Rate:** 100% of the 25 test cases must pass (25 passed, 0 failed, 0 skipped).
2. **Code Coverage:** `>= 85%` line and branch coverage across `src/harness`.
3. **Static Analysis:** `mypy --strict src/` must pass with 0 errors.
4. **Style & Linting:** `ruff check src/ tests/` and `ruff format --check src/ tests/` clean.
5. **Latency Budget:** Middleware latency benchmark verified `< 40ms` per step.
