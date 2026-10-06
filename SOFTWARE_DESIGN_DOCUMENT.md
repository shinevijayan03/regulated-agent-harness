# Software Design Document (SDD): Regulated Agent Harness

**Document Version:** 1.0.0  
**Package Name:** `regulated-agent-harness`  
**Namespace:** `src/harness`  
**Target Runtime:** Python 3.11+ / Pydantic v2 / LangGraph >=0.2.20 / FastAPI >=0.115.0  

---

## 1. Package Structure & Modular Responsibilities

The codebase follows strict separation of concerns, organized under `src/harness`:

```
src/harness/
|-- __init__.py                     # Package entry point and version metadata
|-- core/                           # Foundation and State Orchestration
|   |-- __init__.py
|   |-- types.py                    # Core Pydantic v2 schemas and models
|   |-- config.py                   # Centralized configuration management
|   |-- exceptions.py               # Custom hierarchical domain exceptions
|   |-- checkpointer.py             # Persistent state checkpointing engine
|   `-- orchestrator.py             # LangGraph state machine constructor
|-- gateway/                        # Multi-Provider Model Abstraction
|   |-- __init__.py
|   |-- model.py                    # LiteLLM client abstraction, retries, fallbacks
|   `-- streaming.py                # Asynchronous token streaming adapter
|-- registry/                       # Tool Hub and Protocols
|   |-- __init__.py
|   |-- tools.py                    # @harness_tool decorator and registry
|   `-- mcp.py                      # Anthropic Model Context Protocol client
|-- middleware/                     # Interceptor Pipeline
|   |-- __init__.py
|   |-- pipeline.py                 # Sequential pre-node and post-node runner
|   `-- base.py                     # Interceptor abstract base class
|-- guardrails/                     # Security, Sanitization & HITL
|   |-- __init__.py
|   |-- input_guard.py              # Regex prompt injection & PII/PHI redaction
|   `-- hitl.py                     # Risk tiering evaluation & interrupt gate
|-- compliance/                     # Audit & Regulatory Logging
|   |-- __init__.py
|   |-- audit.py                    # SHA-256 Merkle chain generator and verifier
|   `-- storage.py                  # Append-only audit store (JSONL / SQLite / PG)
|-- telemetry/                      # Observability & Budgets
|   |-- __init__.py
|   |-- otel.py                     # OpenTelemetry SDK tracer and span management
|   |-- langfuse.py                 # Langfuse trace and score callback handler
|   `-- budget.py                   # CostBudgetGuard real-time token tracking
|-- eval/                           # Pre-Flight Synthetic Evaluation
|   |-- __init__.py
|   |-- runner.py                   # CLI evaluation test runner
|   |-- metrics.py                  # Faithfulness, Fidelity, Relevancy scorers
|   `-- dataset.py                  # Golden test dataset loader and validator
|-- server/                         # FastAPI Production Runtime
|   |-- __init__.py
|   |-- app.py                      # FastAPI application factory and lifecycle
|   `-- routes.py                   # /run, /resume, /health, /audit endpoints
|-- cli/                            # Scaffolding & CLI Utilities
|   |-- __init__.py
|   |-- main.py                     # Typer CLI application
|   `-- scaffold.py                 # Project generator from templates
`-- templates/                      # Agent Scaffolding Templates
    `-- default/                    # Standard production-ready template
        |-- agent.py
        |-- tools/
        |-- Dockerfile
        |-- docker-compose.yml
        |-- .env.example
        `-- README.md
```

---

## 2. Pydantic v2 Schemas & Data Contracts (`harness.core.types`)

All data transferred across boundaries is strictly validated using Pydantic v2 models with immutability flags where appropriate.

### 2.1 Enumerations
```python
from enum import Enum

class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class RiskTier(str, Enum):
    READ_ONLY = "READ_ONLY"
    MUTATING_HIGH_RISK = "MUTATING_HIGH_RISK"

class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
```

### 2.2 Core Message & Tool Schemas
```python
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

class ToolCall(BaseModel):
    id: str = Field(..., description="Unique ID of tool call invocation")
    name: str = Field(..., description="Registered name of tool")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Parsed arguments")

class AgentMessage(BaseModel):
    role: Role = Field(..., description="Message author role")
    content: str = Field(..., description="Text content of message")
    tool_calls: Optional[List[ToolCall]] = Field(default=None, description="Model tool calls")
    tool_call_id: Optional[str] = Field(default=None, description="Tool response identifier")
    name: Optional[str] = Field(default=None, description="Author identifier or tool name")

    model_config = ConfigDict(frozen=True)

class ToolDefinition(BaseModel):
    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Docstring description for LLM")
    parameters_schema: Dict[str, Any] = Field(..., description="JSON Schema of parameters")
    risk_tier: RiskTier = Field(default=RiskTier.READ_ONLY, description="Risk classification")
    timeout_seconds: float = Field(default=30.0, description="Max execution duration")
```

### 2.3 Cryptographic Audit Record Schema
```python
from datetime import datetime, timezone

class AuditRecord(BaseModel):
    step: int = Field(..., ge=0, description="Monotonically increasing sequence index")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp"
    )
    trace_id: str = Field(..., description="OTel / Langfuse trace identifier")
    session_id: str = Field(..., description="Unique execution session ID")
    actor: str = Field(..., description="User ID, Agent ID, or System Process")
    action: str = Field(..., description="Semantic action label, e.g. TOOL_EXECUTION")
    payload_hash: str = Field(..., description="SHA-256 hash of canonicalized step payload")
    prev_hash: str = Field(..., description="SHA-256 block_hash of step - 1")
    block_hash: str = Field(..., description="SHA-256 hash of entire block including prev_hash")
    status: str = Field(default="SUCCESS", description="Step status: SUCCESS / FAILED / REJECTED")

    model_config = ConfigDict(frozen=True)
```

### 2.4 State Model (`HarnessState`)
```python
class HarnessState(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(default="anonymous", description="Requesting user identifier")
    context: Dict[str, Any] = Field(default_factory=dict, description="Enterprise context")
    messages: List[AgentMessage] = Field(default_factory=list, description="Chat history")
    current_node: str = Field(default="ingress", description="Currently active node")
    iteration_count: int = Field(default=0, ge=0, description="Loop counter")
    max_iterations: int = Field(default=10, ge=1, description="Loop threshold limit")
    risk_tier: RiskTier = Field(default=RiskTier.READ_ONLY, description="Highest current risk")
    hitl_pending: bool = Field(default=False, description="Flag indicating pending approval")
    approval_id: Optional[str] = Field(default=None, description="Pending approval ID")
    pending_tool_call: Optional[ToolCall] = Field(default=None, description="Tool awaiting auth")
    audit_trail: List[AuditRecord] = Field(default_factory=list, description="Merkle hash chain")
    total_tokens: int = Field(default=0, ge=0, description="Accumulated token count")
    total_cost_usd: float = Field(default=0.0, ge=0.0, description="Accumulated cost in USD")
```

### 2.5 API Request & Response Contracts
```python
class RunRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Optional existing session ID")
    message: str = Field(..., min_length=1, description="User instruction / prompt")
    context: Dict[str, Any] = Field(default_factory=dict, description="Metadata / user role")

class ResumeRequest(BaseModel):
    approval_id: str = Field(..., description="Approval ticket identifier")
    approved: bool = Field(..., description="True to approve and proceed, False to reject")
    approver_id: str = Field(..., description="Authorized reviewer user ID")
    approver_role: str = Field(..., description="Role of reviewer, e.g. compliance_officer")
    signature: str = Field(..., description="Cryptographic digital signature or auth token")
    comment: Optional[str] = Field(default=None, description="Audit justification rationale")

class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0

class RunResponse(BaseModel):
    session_id: str
    status: ExecutionStatus
    output: Optional[str] = None
    approval_id: Optional[str] = None
    proposed_action: Optional[Dict[str, Any]] = None
    trace_url: Optional[str] = None
    latency_ms: float = 0.0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
```

---

## 3. Core Class Interfaces & Hierarchies

### 3.1 Model Gateway (`harness.gateway.model`)
```python
from abc import ABC, abstractmethod

class BaseModelGateway(ABC):
    @abstractmethod
    async def generate_response(
        self,
        messages: List[AgentMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.2
    ) -> AgentMessage:
        """Invokes underlying LLM with retry, backoff, and fallback."""
        pass

class LiteLLMModelGateway(BaseModelGateway):
    def __init__(
        self,
        primary_model: str,
        fallback_models: Optional[List[str]] = None,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        timeout: float = 60.0
    ) -> None: ...
```

### 3.2 Tool Registry & Decorator (`harness.registry.tools`)
```python
from typing import Callable, Coroutine

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        self._executors: Dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}

    def register(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        name: Optional[str] = None,
        description: Optional[str] = None,
        risk_tier: RiskTier = RiskTier.READ_ONLY,
        timeout_seconds: float = 30.0
    ) -> ToolDefinition: ...

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any: ...

    def get_definitions(self) -> List[ToolDefinition]: ...

def harness_tool(
    name: Optional[str] = None,
    risk_tier: RiskTier = RiskTier.READ_ONLY,
    timeout_seconds: float = 30.0
) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorator to register an async function as a governed harness tool."""
    ...
```

### 3.3 Middleware Pipeline (`harness.middleware.pipeline`)
```python
class BaseInterceptor(ABC):
    @abstractmethod
    async def pre_node(self, state: HarnessState, node_name: str) -> HarnessState:
        """Executes before a graph node transition."""
        pass

    @abstractmethod
    async def post_node(self, state: HarnessState, node_name: str) -> HarnessState:
        """Executes after a graph node transition."""
        pass

class MiddlewarePipeline:
    def __init__(self, interceptors: List[BaseInterceptor]) -> None:
        self.interceptors = interceptors

    async def run_pre(self, state: HarnessState, node_name: str) -> HarnessState:
        for interceptor in self.interceptors:
            state = await interceptor.pre_node(state, node_name)
        return state

    async def run_post(self, state: HarnessState, node_name: str) -> HarnessState:
        for interceptor in reversed(self.interceptors):
            state = await interceptor.post_node(state, node_name)
        return state
```

### 3.4 State Orchestrator (`harness.core.orchestrator`)
```python
from langgraph.graph import StateGraph

class HarnessOrchestrator:
    def __init__(
        self,
        gateway: BaseModelGateway,
        tools: ToolRegistry,
        middleware: MiddlewarePipeline,
        checkpointer: Any
    ) -> None:
        self.gateway = gateway
        self.tools = tools
        self.middleware = middleware
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Constructs LangGraph with reasoner, tool_executor, hitl_gate, error_fallback."""
        ...

    async def run(self, initial_state: HarnessState) -> HarnessState: ...

    async def resume(self, session_id: str, resume_payload: ResumeRequest) -> HarnessState: ...
```

---

## 4. Error-Handling Matrix, Retry Policies & Circuit Breakers

### 4.1 Domain Exception Hierarchy (`harness.core.exceptions`)
```
HarnessException (Base)
|-- ConfigurationError
|-- SchemaValidationError
|-- GuardrailViolationException
|   |-- PromptInjectionDetected
|   `-- PIIContentDetected
|-- HITLInterruptException
|-- BudgetLimitExceededException
|-- MaxIterationsReachedException
|-- AuditIntegrityException
`-- ProviderException
    |-- ProviderUnavailableException
    |-- ProviderTimeoutException
    `-- ProviderRateLimitException
```

### 4.2 Error Handling Matrix

| Exception Class | Handling Policy | Fallback / Recovery Action |
|---|---|---|
| `PromptInjectionDetected` | Terminal Reject | Halts execution immediately; writes security audit block; returns HTTP 400. |
| `PIIContentDetected` | Redaction / Masking | Mask matched tokens (`[REDACTED_SSN]`) and proceeds if soft-mode, or aborts if strict. |
| `ProviderRateLimitException` | Transient Retry | Exponential backoff with Full Jitter ($t = \min(t_{\max}, t_0 \cdot 2^{\text{attempt}}) \pm \text{jitter}$). |
| `ProviderUnavailableException` | Failover | Switch to configured secondary fallback model (e.g., Anthropic -> Bedrock). |
| `HITLInterruptException` | Graph Interruption | Checkpoint current state; generate approval ticket; return HTTP 202. |
| `MaxIterationsReachedException` | Graceful Degradation | Route to `error_fallback` node; synthesize best-effort response with warning flag. |
| `AuditIntegrityException` | Critical System Halt | Lock session from further mutation; trigger incident alert; return HTTP 500. |

---

## 5. Security & Concurrency Design

### 5.1 Async Concurrency Model
- The framework uses non-blocking Python `asyncio` for all I/O operations (model gateway calls, tool execution, database checkpointing, and HTTP communications).
- Tool execution is wrapped in `asyncio.wait_for(timeout=timeout_seconds)` to prevent stalled child coroutines.
- Fast, non-blocking crypto: JSON serialization utilizes sort-key UTF-8 encoding, hashed via `hashlib.sha256()`.

### 5.2 Zero-Trust State Checkpointing
- In development: `aiosqlite` maintains a local `.harness_checkpoints.db`.
- In production: `asyncpg` connects to PostgreSQL with TLS encryption and connection pooling (`min_size=5, max_size=20`).
- Checkpoints are cryptographically isolated per `session_id`.
