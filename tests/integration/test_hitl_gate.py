import pytest

from harness.core.orchestrator import HarnessOrchestrator
from harness.core.types import (
    AgentMessage,
    HarnessState,
    ResumeRequest,
    RiskTier,
    Role,
    ToolCall,
    ToolDefinition,
)
from harness.gateway.model import BaseModelGateway
from harness.guardrails.hitl import HITLGateInterceptor
from harness.middleware.pipeline import MiddlewarePipeline
from harness.registry.tools import ToolRegistry, harness_tool


class HitlMockGateway(BaseModelGateway):
    def __init__(self, step1_tool_call: ToolCall, step2_final_msg: str):
        self.step1_tool_call = step1_tool_call
        self.step2_final_msg = step2_final_msg
        self.turn = 0

    async def generate_response(
        self,
        messages: list[AgentMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
    ) -> AgentMessage:
        self.turn += 1
        if self.turn == 1:
            return AgentMessage(role=Role.ASSISTANT, content="", tool_calls=[self.step1_tool_call])
        return AgentMessage(role=Role.ASSISTANT, content=self.step2_final_msg)


@pytest.mark.asyncio
async def test_tc_htl_01_and_02_hitl_interrupt_and_resumption() -> None:
    """TC-HTL-01 & TC-HTL-02: Interruption on MUTATING tool and deterministic resumption."""
    registry = ToolRegistry()
    execution_counter = {"count": 0}

    @harness_tool(name="quarantine_batch", risk_tier=RiskTier.MUTATING_HIGH_RISK, registry=registry)
    async def quarantine_batch(batch_id: str, reason: str) -> dict:
        execution_counter["count"] += 1
        return {"batch_id": batch_id, "status": "QUARANTINED", "reason": reason}

    gateway = HitlMockGateway(
        step1_tool_call=ToolCall(
            id="call_quar",
            name="quarantine_batch",
            arguments={"batch_id": "LOT-991", "reason": "Cold chain excursion"},
        ),
        step2_final_msg="Lot LOT-991 was successfully quarantined following supervisor authorization.",
    )

    hitl_gate = HITLGateInterceptor(tools=registry)
    middleware = MiddlewarePipeline(interceptors=[hitl_gate])
    orchestrator = HarnessOrchestrator(gateway=gateway, tools=registry, middleware=middleware)

    initial_state = HarnessState(
        session_id="sess-hitl-01",
        messages=[AgentMessage(role=Role.USER, content="Quarantine lot LOT-991 immediately.")],
    )

    # 1. Run until interrupt
    interrupted_state = await orchestrator.run(initial_state)

    assert interrupted_state.hitl_pending is True
    assert interrupted_state.approval_id is not None
    assert interrupted_state.pending_tool_call is not None
    assert interrupted_state.pending_tool_call.name == "quarantine_batch"
    assert execution_counter["count"] == 0  # Mutating tool NOT executed yet!

    # 2. Submit signed approval and resume
    resume_req = ResumeRequest(
        approval_id=interrupted_state.approval_id,
        approved=True,
        approver_id="dr_smith_qa",
        approver_role="quality_director",
        signature="sig_valid_token_ed25519",
        comment="Confirmed excursion on physical datalogger.",
    )

    resumed_state = await orchestrator.resume(
        session_id=interrupted_state.session_id, resume_payload=resume_req
    )

    assert resumed_state.hitl_pending is False
    assert execution_counter["count"] == 1  # Executed exactly once
    assert "quarantined following supervisor authorization" in resumed_state.messages[-1].content


@pytest.mark.asyncio
async def test_tc_htl_03_hitl_rejection() -> None:
    """TC-HTL-03: Rejection by reviewer prevents execution and returns cancellation notice."""
    registry = ToolRegistry()
    execution_counter = {"count": 0}

    @harness_tool(name="delete_account", risk_tier=RiskTier.MUTATING_HIGH_RISK, registry=registry)
    async def delete_account(account_id: str) -> dict:
        execution_counter["count"] += 1
        return {"account_id": account_id, "deleted": True}

    gateway = HitlMockGateway(
        step1_tool_call=ToolCall(
            id="call_del", name="delete_account", arguments={"account_id": "ACC-1"}
        ),
        step2_final_msg="Account deletion cancelled.",
    )

    hitl_gate = HITLGateInterceptor(tools=registry)
    middleware = MiddlewarePipeline(interceptors=[hitl_gate])
    orchestrator = HarnessOrchestrator(gateway=gateway, tools=registry, middleware=middleware)

    state = await orchestrator.run(
        HarnessState(
            session_id="sess-reject-01",
            messages=[AgentMessage(role=Role.USER, content="Delete account ACC-1")],
        )
    )

    assert state.hitl_pending is True

    # Reject
    resume_req = ResumeRequest(
        approval_id=state.approval_id,
        approved=False,
        approver_id="compliance_officer",
        approver_role="auditor",
        signature="sig_reject",
        comment="Deletion denied: active retention hold in place.",
    )

    rejected_state = await orchestrator.resume(
        session_id=state.session_id, resume_payload=resume_req
    )

    assert execution_counter["count"] == 0  # Tool was NEVER called
    assert (
        "cancelled" in rejected_state.messages[-1].content.lower()
        or "rejected" in rejected_state.messages[-1].content.lower()
    )
