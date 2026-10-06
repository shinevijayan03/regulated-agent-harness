from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class ToolCall(BaseModel):
    id: str = Field(..., description="Unique ID of tool call invocation")
    name: str = Field(..., description="Registered name of tool")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Parsed arguments")


class AgentMessage(BaseModel):
    role: Role = Field(..., description="Message author role")
    content: str = Field(..., description="Text content of message")
    tool_calls: list[ToolCall] | None = Field(default=None, description="Model tool calls")
    tool_call_id: str | None = Field(default=None, description="Tool response identifier")
    name: str | None = Field(default=None, description="Author identifier or tool name")

    model_config = ConfigDict(frozen=True)


class ToolDefinition(BaseModel):
    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Docstring description for LLM")
    parameters_schema: dict[str, Any] = Field(..., description="JSON Schema of parameters")
    risk_tier: RiskTier = Field(default=RiskTier.READ_ONLY, description="Risk classification")
    timeout_seconds: float = Field(default=30.0, description="Max execution duration")


class AuditRecord(BaseModel):
    step: int = Field(..., ge=0, description="Sequence index")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO-8601 UTC timestamp",
    )
    trace_id: str = Field(..., description="Trace identifier")
    session_id: str = Field(..., description="Session identifier")
    actor: str = Field(..., description="User or agent actor")
    action: str = Field(..., description="Action label")
    payload_hash: str = Field(..., description="SHA-256 payload hash")
    prev_hash: str = Field(..., description="SHA-256 prev block hash")
    block_hash: str = Field(..., description="SHA-256 block hash")
    status: str = Field(default="SUCCESS", description="Step status")

    model_config = ConfigDict(frozen=True)


class HarnessState(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(default="anonymous", description="User identifier")
    context: dict[str, Any] = Field(default_factory=dict, description="Context metadata")
    messages: list[AgentMessage] = Field(default_factory=list, description="Messages history")
    current_node: str = Field(default="ingress", description="Active graph node")
    iteration_count: int = Field(default=0, ge=0, description="Iteration count")
    max_iterations: int = Field(default=10, ge=1, description="Max iterations")
    risk_tier: RiskTier = Field(default=RiskTier.READ_ONLY, description="Current risk tier")
    hitl_pending: bool = Field(default=False, description="Flag for pending HITL")
    approval_id: str | None = Field(default=None, description="Approval ID")
    pending_tool_call: ToolCall | None = Field(default=None, description="Pending tool call")
    audit_trail: list[AuditRecord] = Field(default_factory=list, description="Audit chain")
    total_tokens: int = Field(default=0, ge=0, description="Token count")
    total_cost_usd: float = Field(default=0.0, ge=0.0, description="Cost in USD")


class RunRequest(BaseModel):
    session_id: str | None = Field(default=None, description="Session ID")
    message: str = Field(..., min_length=1, description="User instruction")
    context: dict[str, Any] = Field(default_factory=dict, description="Context")


class ResumeRequest(BaseModel):
    approval_id: str = Field(..., description="Approval ticket identifier")
    approved: bool = Field(..., description="True to approve, False to reject")
    approver_id: str = Field(..., description="Approver user ID")
    approver_role: str = Field(..., description="Approver role")
    signature: str = Field(..., description="Cryptographic signature")
    comment: str | None = Field(default=None, description="Audit comment")


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0


class RunResponse(BaseModel):
    session_id: str
    status: ExecutionStatus
    output: str | None = None
    approval_id: str | None = None
    proposed_action: dict[str, Any] | None = None
    trace_url: str | None = None
    latency_ms: float = 0.0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
