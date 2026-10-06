# Test Strategy and Plan: Regulated Agent Harness

**Document Version:** 1.0.0  
**Status:** Approved  
**Classification:** Quality Assurance & Testing Framework  
**Target Coverage:** Minimum 85% branch and line coverage across `core`, `middleware`, and `registry`  

---

## 1. Testing Philosophy & Test Pyramid

In heavily regulated software engineering (GxP, FDA 21 CFR Part 11, SOC2), testing is not merely a bug-detection mechanism—it is a formal **Validation Protocol**. The Regulated Agent Harness implements a multi-tiered test pyramid ensuring determinism, safety, and performance under strict failure conditions:

```
                  / \
                 /   \
                /     \
               /  EVAL \     Pre-flight Synthetic Eval (Ragas / DeepEval)
              /---------\    Tool Fidelity, Faithfulness, Answer Relevancy
             / CONTRACT  \   Pydantic & MCP Schema Contract Tests
            /-------------\
           /  INTEGRATION  \ LangGraph State Cycles, Checkpointing, HITL
          /-----------------\
         /    UNIT TESTS     \ Fast, isolated, deterministic unit tests
        /---------------------\ Mocked LLMs, Pure Python State Transitions
```

---

## 2. Test Directory Structure & Organization

The test suite is structured to separate unit isolation from system integration and pre-flight synthetic evaluation:

```
tests/
|-- __init__.py
|-- conftest.py                     # Global pytest fixtures, mock factories, event loops
|-- unit/                           # Isolated unit tests (<10ms per test)
|   |-- __init__.py
|   |-- test_types.py               # Pydantic v2 schemas, immutability, serialization
|   |-- test_config.py              # Configuration loading, environment overrides
|   |-- test_model_gateway.py       # LiteLLM gateway, retries, fallback cascading
|   |-- test_tool_registry.py       # @harness_tool, schema extraction, risk tiering
|   |-- test_mcp_client.py          # MCP tool adapter, transport protocol serialization
|   |-- test_input_guard.py         # Regex prompt injection, PII/PHI redaction
|   |-- test_audit_trail.py         # SHA-256 Merkle chain, genesis block, tamper checks
|   `-- test_budget_guard.py        # Token counting, dollar cost threshold trips
|-- integration/                    # Stateful multi-node integration tests
|   |-- __init__.py
|   |-- test_orchestrator.py        # LangGraph cyclic execution, max_iterations limit
|   |-- test_checkpointing.py       # Persistent state serialization to SQLite/Postgres
|   |-- test_hitl_gate.py           # Interrupt on MUTATING tool, cryptographic resume
|   |-- test_middleware_pipeline.py # End-to-end middleware pre/post pipeline
|   `-- test_server_api.py          # FastAPI HTTP endpoints (/run, /resume, /audit, /health)
|-- eval/                           # Pre-flight Synthetic Evaluation test harness
|   |-- __init__.py
|   |-- test_eval_runner.py         # Batch runner, metric calculation, threshold gating
|   `-- test_eval_metrics.py        # Groundedness, answer relevancy, tool fidelity
|-- non_functional/                 # Performance, SLA & Security tests
|   |-- __init__.py
|   |-- test_latency_sla.py         # Benchmarks enforcing <40ms middleware overhead
|   |-- test_concurrency.py         # Async load test simulating concurrent sessions
|   `-- test_audit_tamper_attack.py # Penetration test simulating malicious log mutation
`-- fixtures/                       # Deterministic data files
    |-- sample_datasets.json        # Golden evaluation question-answer pairs
    |-- sample_mcp_tools.json       # Mock MCP tool definitions
    `-- golden_audit_chains.json    # Pre-computed cryptographic audit chains
```

---

## 3. Mocking Strategy & Determinism Protocol

To guarantee tests run reliably in offline CI/CD pipelines without external API costs or non-deterministic drift:

### 3.1 Model Gateway Deterministic Mocking
- **`MockModelGateway`:** Replaces actual cloud LLM endpoints (OpenAI, Anthropic, Bedrock) with a state-aware mock engine.
- Supports pre-programmed scripted responses:
  - Text response generation.
  - Tool call emission with exact JSON arguments.
  - Sequential multi-turn dialogue simulation.
  - Simulated network failure / timeout exceptions to test retry and fallback logic.

### 3.2 OpenTelemetry & Langfuse Sinks
- OpenTelemetry is tested using `InMemorySpanExporter`. Spans emitted by nodes are captured and inspected for required enterprise attributes (`agent.session_id`, `agent.node`, `agent.risk_tier`).
- Langfuse calls are captured using mock callback handlers to assert token counts and payload forwarding without live network traffic.

### 3.3 Remote MCP Server Mocking
- An in-memory mock MCP server implements the JSON-RPC 2.0 protocol over asynchronous memory channels, emulating tools like enterprise ERP querying and customer database lookups.

---

## 4. Non-Functional Testing Strategy

### 4.1 Middleware Latency Benchmarking (<40ms SLA)
- **Objective:** Verify that the full middleware chain (Input Guard + OTel span injection + HITL risk tier check + SHA-256 Merkle block generation) consumes **< 40ms** of CPU wall-clock time per step.
- **Methodology:**
  - Execute 1,000 continuous iterations of the middleware pipeline across diverse payloads.
  - Measure 50th, 95th, and 99th percentile latencies using high-resolution monotonic clocks (`time.perf_counter_ns()`).
  - Automated assertion: $P_{99} < 40.0 \text{ ms}$.

### 4.2 State Tamper & Cryptographic Validation Attack Testing
- **Objective:** Verify mathematical tamper-detection conforming to FDA 21 CFR Part 11.
- **Methodology:**
  1. Generate an audit chain of 20 sequential state transitions.
  2. Verify the chain passes validation (`chain.validate() == True`).
  3. Surgically mutate a single bit in the 5th block (e.g., alter an input parameter or change the status from `REJECTED` to `SUCCESS`).
  4. Run validation and assert:
     - `chain.validate()` raises `AuditIntegrityException`.
     - The exception identifies the exact corrupted step index (`tampered_step == 5`).

### 4.3 Async Concurrency & Resource Leaks
- **Objective:** Ensure no memory leakage or cross-session state bleed during high-concurrency async workloads.
- **Methodology:**
  - Launch 50 concurrent agent sessions across the FastAPI test client (`httpx.AsyncClient`).
  - Monitor memory consumption across 500 completed executions using `tracemalloc`.
  - Assert zero state leakage between sessions: session $A$ context is completely inaccessible to session $B$.

---

## 5. Synthetic Evaluation Framework (Pre-Flight Quality Gate)

The harness features an integrated synthetic test runner implementing Ragas / DeepEval evaluation metrics before releasing agent versions:

### Metrics & Formulae:
1. **Tool Call Fidelity:**
   $$\text{Fidelity} = \frac{\text{Correct Tools Selected with Valid Schema}}{\text{Total Tool Opportunities}}$$
   *Threshold:* $\ge 0.95$

2. **Faithfulness (Groundedness):**
   $$\text{Faithfulness} = \frac{\text{Claims grounded in retrieved tool context}}{\text{Total claims in final response}}$$
   *Threshold:* $\ge 0.85$

3. **Answer Relevancy:**
   $$\text{Relevancy} = \text{CosineSimilarity}(\text{Embedding}(\text{Answer}), \text{Embedding}(\text{User Prompt}))$$
   *Threshold:* $\ge 0.85$

### CI/CD Quality Gate Rule:
If any metric falls below its configured threshold during `harness eval`, the CLI exits with return code `1`, halting the deployment pipeline.

---

## 6. Coverage Requirements & Tools

- **Coverage Enforcement:** `pytest --cov=src/harness --cov-report=term-missing --cov-fail-under=85`.
- **Target Areas:**
  - `src/harness/core/`: 95%+
  - `src/harness/middleware/`: 90%+
  - `src/harness/compliance/`: 100% (Zero tolerance for unverified audit code)
  - `src/harness/guardrails/`: 95%+
  - `src/harness/registry/`: 90%+
- **Static Type Checking:** `mypy --strict src/ tests/` (Zero errors allowed).
- **Code Linter:** `ruff check src/ tests/` and `ruff format --check src/ tests/`.
