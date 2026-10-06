# Developer Usage Guide: Regulated Agent Harness

**Document Version:** 1.0.0  
**Target Audience:** Forward Deployed Engineers (FDEs), AI Platform Engineers, Compliance Reviewers  
**Target Time to Production:** Under 15 minutes for new agent scaffolding and deployment  

---

## 1. Quickstart: 15-Minute Agent Deployment

The Regulated Agent Harness accelerates PoC development into production deployment by eliminating plumbing: state management, compliance audit trails, OpenTelemetry tracing, and security guardrails are pre-wired.

### Prerequisites
- Python 3.11+
- `uv` (recommended) or `poetry` / `pip`
- Docker and Docker Compose (for local PostgreSQL & Langfuse)

### Step 1: Install the Harness CLI & Library
```bash
# Clone the repository
git clone https://github.com/shinevijayan03/regulated-agent-harness.git
cd regulated-agent-harness

# Install harness and CLI using uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

---

## 2. Scaffolding a New Regulated Agent (`harness init`)

To scaffold a new governed enterprise agent project in seconds:

```bash
harness init cold-chain-triage
cd cold-chain-triage
```

### Generated Project Layout:
```
cold-chain-triage/
|-- agent.py                  # Pre-wired LangGraph state orchestrator
|-- tools/                    # Tool definitions with risk tiers
|   |-- __init__.py
|   `-- inventory.py          # Sample tools
|-- tests/                    # Pre-configured test suite
|   `-- test_agent.py
|-- Dockerfile                # Production multi-stage container
|-- docker-compose.yml        # App + Postgres checkpointer + Langfuse
|-- .env.example              # Provider configurations
`-- README.md                 # Project documentation
```

---

## 3. Registering Custom Tools with Risk Tiering

Define tools by decorating Python async functions with `@harness_tool`. The decorator automatically extracts Pydantic JSON schemas, parses docstrings for LLM prompt context, and enforces risk governance.

### Example: Read-Only Tool vs. Mutating High-Risk Tool

Edit `tools/inventory.py`:

```python
from harness.registry.tools import harness_tool
from harness.core.types import RiskTier
from pydantic import BaseModel, Field

class TemperatureTelemetry(BaseModel):
    sensor_id: str = Field(..., description="Unique cold chain sensor ID")
    temperature_celsius: float = Field(..., description="Current temperature reading")
    excursion_duration_minutes: int = Field(..., description="Minutes above threshold")

# 1. READ_ONLY Tool: No human authorization required
@harness_tool(
    name="get_sensor_telemetry",
    risk_tier=RiskTier.READ_ONLY,
    timeout_seconds=10.0
)
async def get_sensor_telemetry(sensor_id: str) -> TemperatureTelemetry:
    """Retrieves real-time temperature telemetry for a cold chain pallet."""
    # Simulated database lookup
    return TemperatureTelemetry(
        sensor_id=sensor_id,
        temperature_celsius=8.5,
        excursion_duration_minutes=45
    )

# 2. MUTATING_HIGH_RISK Tool: Automatically triggers HITL interrupt gate
@harness_tool(
    name="quarantine_batch",
    risk_tier=RiskTier.MUTATING_HIGH_RISK,
    timeout_seconds=15.0
)
async def quarantine_batch(batch_id: str, reason: str) -> dict:
    """Quarantines a pharmaceutical lot in ERP, halting all outbound shipments."""
    # This mutating action executes ONLY after cryptographic supervisor approval
    return {
        "status": "QUARANTINED",
        "batch_id": batch_id,
        "action_taken": "ERP lock applied. Logistics alerted.",
        "reason": reason
    }
```

---

## 4. Multi-Provider Model Configuration

Switching between enterprise cloud LLMs and private on-premise models requires **zero code changes**—only two environment variables in your `.env`:

### Option A: Azure OpenAI
```ini
PRIMARY_MODEL=azure/gpt-4o
AZURE_API_KEY=your-azure-key
AZURE_API_BASE=https://your-corp-azure-openai.openai.azure.com/
AZURE_API_VERSION=2024-02-15-preview
```

### Option B: AWS Bedrock (Claude 3.5 Sonnet)
```ini
PRIMARY_MODEL=bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0
AWS_REGION_NAME=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
```

### Option C: Anthropic Direct
```ini
PRIMARY_MODEL=claude-3-5-sonnet-20240620
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Option D: Local Open-Weights (vLLM / Ollama)
```ini
PRIMARY_MODEL=openai/meta-llama/Meta-Llama-3.1-70B-Instruct
OPENAI_API_BASE=http://localhost:8000/v1
OPENAI_API_KEY=not-needed-for-local
```

### Dynamic Failover Configuration
Provide fallback models separated by commas:
```ini
FALLBACK_MODELS=bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0,claude-3-5-sonnet-20240620
```

---

## 5. Running the Agent Server & API Workflows

### 5.1 Launch Infrastructure & Server
```bash
# Start PostgreSQL and Langfuse observability sink
docker compose up -d postgres langfuse-server

# Launch FastAPI agent runtime
harness run --port 8000 --reload
```

### 5.2 Standard Execution (`POST /v1/agents/{id}/run`)
Execute a prompt that invokes read-only tools:
```bash
curl -X POST http://localhost:8000/v1/agents/cold-chain/run \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Check current temperature readings for sensor SENS-901."
  }'
```

**Response (HTTP 200 OK):**
```json
{
  "session_id": "4b684c37-9759-4d22-b437-083f2187bf3a",
  "status": "COMPLETED",
  "output": "Sensor SENS-901 currently reports a temperature of 8.5°C with an excursion duration of 45 minutes.",
  "trace_url": "http://localhost:3000/trace/tr-88910",
  "latency_ms": 1180,
  "token_usage": {
    "prompt_tokens": 340,
    "completion_tokens": 65,
    "total_cost_usd": 0.0021
  }
}
```

---

## 6. Human-In-The-Loop (HITL) Approval Workflow

When an agent decides to execute a tool marked `MUTATING_HIGH_RISK`, the state graph halts immediately.

### 6.1 Triggering a Mutating Action
```bash
curl -X POST http://localhost:8000/v1/agents/cold-chain/run \
  -H "Content-Type: application/json" \
  -d '{
    "message": "The temperature excursion exceeded 30 minutes! Immediately quarantine lot LOT-4029."
  }'
```

**Response (HTTP 202 Accepted):**
```json
{
  "session_id": "9d81ba23-1123-45ef-89a1-cb98129034aa",
  "status": "REQUIRES_APPROVAL",
  "approval_id": "appr-77218",
  "proposed_action": {
    "tool": "quarantine_batch",
    "parameters": {
      "batch_id": "LOT-4029",
      "reason": "Temperature excursion 8.5C exceeded 30-minute threshold."
    }
  },
  "message": "Execution paused. High-risk mutating action requires supervisor authorization."
}
```

### 6.2 Authorizing and Resuming Execution (`POST /v1/agents/{id}/resume`)
A compliance officer reviews the proposed action and submits a signed approval payload:
```bash
curl -X POST http://localhost:8000/v1/agents/cold-chain/resume \
  -H "Content-Type: application/json" \
  -d '{
    "approval_id": "appr-77218",
    "approved": true,
    "approver_id": "dr_sarah_connor",
    "approver_role": "quality_assurance_director",
    "signature": "sig_ed25519_fda_compliant_token",
    "comment": "Excursion verified on sensor logs. Quarantine approved per SOP-401."
  }'
```

**Response (HTTP 200 OK):**
```json
{
  "session_id": "9d81ba23-1123-45ef-89a1-cb98129034aa",
  "status": "COMPLETED",
  "output": "Lot LOT-4029 has been successfully quarantined in ERP. Logistics notified.",
  "latency_ms": 780
}
```

---

## 7. Verifying the Cryptographic Audit Trail (FDA 21 CFR Part 11)

Verify that the session history was not retroactively tampered with:

```bash
curl http://localhost:8000/v1/agents/cold-chain/audit/verify?session_id=9d81ba23-1123-45ef-89a1-cb98129034aa
```

**Response (HTTP 200 OK):**
```json
{
  "session_id": "9d81ba23-1123-45ef-89a1-cb98129034aa",
  "verified": true,
  "total_steps": 5,
  "chain_head_hash": "c4ca4238a0b923820dcc509a6f75849b6574f0c8e2354a8e",
  "tamper_detected": false,
  "compliance_status": "FDA_21_CFR_PART_11_COMPLIANT"
}
```

---

## 8. Running Pre-Flight Synthetic Evaluations

Before committing changes or deploying to staging, run the automated evaluation harness against your golden dataset:

```bash
harness eval --dataset tests/fixtures/golden_eval.json --min-faithfulness 0.85 --min-fidelity 0.95
```

### Sample CLI Output:
```
======================================================================
           REGULATED AGENT HARNESS PRE-FLIGHT EVALUATION
======================================================================
Evaluating dataset: tests/fixtures/golden_eval.json (10 test cases)

[OK] Case 1: Telemetry lookup ..................... Faithfulness: 0.96 | Fidelity: 1.00
[OK] Case 2: Out of bound parameter .............. Faithfulness: 1.00 | Fidelity: 1.00
[OK] Case 3: Mutating quarantine trigger ......... Faithfulness: 0.92 | Fidelity: 1.00
...
----------------------------------------------------------------------
EVALUATION SUMMARY:
  Total Test Cases:            10
  Passed Quality Gate:         10
  Failed Quality Gate:         0
  Average Faithfulness:        0.942 (Threshold: 0.850) [PASSED]
  Average Tool Call Fidelity:  0.980 (Threshold: 0.950) [PASSED]
  Average Answer Relevancy:    0.915 (Threshold: 0.850) [PASSED]
----------------------------------------------------------------------
Result: PASSED QUALITY GATE (Exit Code 0)
======================================================================
```

If any score drops below the threshold, the CLI prints a red failure breakdown and exits with return code `1`, preventing CI/CD deployment of degraded agents.

---

## 9. Inspecting Traces in Langfuse

1. Open your browser to `http://localhost:3000`.
2. Navigate to **Traces**.
3. Locate your `session_id`.
4. Inspect:
   - Full latency waterfall breakdown (Input Guard $\rightarrow$ Reasoner $\rightarrow$ Tool Execution $\rightarrow$ Audit).
   - Exact token consumption and cost calculated in real time.
   - Guardrail flags and HITL approval timestamps.
