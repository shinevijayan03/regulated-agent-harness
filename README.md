# Regulated Agent Harness

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![Compliance](https://img.shields.io/badge/compliance-FDA%2021%20CFR%20Part%2011%20%7C%20GxP-red.svg)]()
[![Code Coverage](https://img.shields.io/badge/coverage-88.45%25-brightgreen.svg)]()
[![Hardware Acceleration](https://img.shields.io/badge/CUDA-NVIDIA%20Ampere%20RTX%203060-76B900.svg?logo=nvidia)]()

A production-grade, highly governed, low-overhead rapid prototyping and validation framework for enterprise multi-agent systems. Engineered for high-liability, heavily audited environments (**FDA 21 CFR Part 11**, **GxP**, **ISO 27001**, **SOC2 Type II**).

---

## 1. Executive Summary & Problem Statement

Enterprise AI squads face a persistent challenge: **the PoC-to-Production Chasm**. When customers request a regulated agentic workflow (contract analysis, regulatory triage, supply chain quarantine), engineering teams spend 4–8 weeks building plumbing: state checkpointing, tracing, guardrails, and compliance logs. Conversely, naive prototypes fail regulatory audits and security reviews.

`regulated-agent-harness` solves this by standardizing enterprise governance out of the box:
* **Deterministic State-Graph Orchestration:** Cyclic state machines powered by `LangGraph` (>=0.2.x) with loop limits and fallback boundaries.
* **Model Gateway Abstraction:** Multi-provider interface powered by `LiteLLM` (Azure OpenAI, AWS Bedrock, Anthropic, and local vLLM/Ollama) with automated exponential backoff and failover cascading.
* **Human-In-The-Loop (HITL) Gate:** Automated risk-tiering (`READ_ONLY` vs. `MUTATING_HIGH_RISK`). Pauses execution on mutating actions and resumes only upon cryptographically signed supervisor authorization.
* **Tamper-Evident Merkle Audit Trail:** Append-only SHA-256 hash chains conforming to **FDA 21 CFR Part 11**.
* **Hardware GPU Acceleration:** Built-in NVIDIA CUDA tensor core acceleration (tested on NVIDIA RTX 3060 12GB) for real-time semantic evaluations and embeddings (57.8x speedup).
* **Pre-Flight Synthetic Evals:** Built-in CLI test runner executing golden test datasets via `Ragas` measuring Tool Call Fidelity, Faithfulness, and Relevancy.
* **Low Middleware Overhead:** Sub-millisecond latency overhead ($P_{99} = 0.196\text{ ms}$), far outperforming the $<40\text{ ms}$ SLA requirement.

---

## 2. Architectural Blueprint

```
                      +------------------------------------------+
                      |         FastAPI Gateway / CLI            |
                      +------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                            REGULATED AGENT HARNESS                                |
|                                                                                   |
|  +---------------------+   +-----------------------+   +-----------------------+  |
|  |   Model Gateway     |   |   State Orchestrator  |   |    Tool & MCP Hub     |  |
|  | (LiteLLM / vLLM /   |<->|  (LangGraph State     |<->| (Schema Validation,   |  |
|  |  Azure / Bedrock)   |   |   Checkpoint Engine)  |   |  Risk Tiering, Exec)  |  |
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

## 3. Reference Implementation: Early Life Food Supply Chain Triage

Included in [`examples/early_life_food_triage/`](examples/early_life_food_triage):
* **Domain:** Infant Nutrition & Baby Food Supply Chain Governance (**FDA Infant Formula Act, 21 CFR Part 106/107**).
* **Pathogen Zero-Tolerance:** Autonomous LIMS screening for *Cronobacter sakazakii* and *Salmonella*.
* **Thermal Pasteurization Monitoring:** HTST pasteurizer telemetry tracking.
* **Governed Quarantine Action:** Mutating ERP lockdown (`quarantine_infant_formula_lot`) halts execution, persists a checkpoint, and requires QA Director electronic signature before resumption.
* **Audit Trail:** Append-only SHA-256 Merkle chain recording the initial report, pause, signature, and ERP lock.

Run the interactive live demo:
```bash
python examples/early_life_food_triage/demo.py
```

---

## 4. Quickstart (< 15 Minutes)

### Prerequisites
* Python 3.11+
* `uv` (recommended) or `pip`
* NVIDIA GPU with CUDA drivers (optional, automatic fallback to CPU)

### Installation
```bash
# Clone the repository
git clone https://github.com/shinevijayan03/regulated-agent-harness.git
cd regulated-agent-harness

# Create virtual environment and install with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Scaffolding a New Agent
```bash
# Scaffold a new production agent layout
harness init my-enterprise-agent
cd my-enterprise-agent
```

### Running the API Server
```bash
harness run --port 8000
```

### Running Synthetic Evaluations
```bash
harness eval --dataset examples/early_life_food_triage/eval_dataset.json --min-fidelity 0.90 --min-faithfulness 0.80
```

---

## 5. Verification & Test Metrics

* **Test Suite:** **33 passed** (0 failed, 0 skipped in 18.19s).
* **Code Coverage:** **`88.45%`** branch & line coverage.
* **Type Rigor:** `mypy --strict src/` passes with 0 issues.
* **Code Quality:** `ruff check` and `ruff format` pass cleanly.
* **Middleware Overhead:** $P_{99} = 0.196\text{ ms}$ (budget: $<40.0\text{ ms}$).
* **GPU Speedup:** RTX 3060 CUDA Tensor throughput: **57.8x faster** than CPU baseline.

---

## 6. Project Specifications & Architectural Artifacts

1. [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): WBS, critical path, and risk management.
2. [`ARCHITECTURE.md`](ARCHITECTURE.md): System topology, Mermaid diagrams, and Architecture Decision Records (ADRs).
3. [`SOFTWARE_DESIGN_DOCUMENT.md`](SOFTWARE_DESIGN_DOCUMENT.md): Pydantic schemas, class hierarchies, and error models.
4. [`TEST_STRATEGY_AND_PLAN.md`](TEST_STRATEGY_AND_PLAN.md): Testing pyramid, contract mocks, and non-functional tests.
5. [`TEST_CASES_SPECIFICATION.md`](TEST_CASES_SPECIFICATION.md): Exhaustive catalog of test scenarios with assertions.
6. [`DEPLOYMENT_PLAN.md`](DEPLOYMENT_PLAN.md): Hardened multi-stage Dockerfile and docker-compose topology.
7. [`USAGE_GUIDE.md`](USAGE_GUIDE.md): Developer quickstart, tool registration, and CLI instructions.

---

## 7. License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
