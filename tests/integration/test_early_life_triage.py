import pytest

from harness.core.types import (
    AgentMessage,
    HarnessState,
    ResumeRequest,
    Role,
)
from examples.early_life_food_triage.agent import build_early_life_triage_orchestrator


@pytest.mark.asyncio
async def test_early_life_food_compliant_lot_triage() -> None:
    """Verify compliant lot LOT-INF-9901 passes without triggering HITL."""
    orchestrator = build_early_life_triage_orchestrator()
    state = HarnessState(
        session_id="test-compliant-lot-01",
        messages=[
            AgentMessage(
                role=Role.USER,
                content="Investigate microbiological status for compliant lot LOT-INF-9901.",
            )
        ],
    )

    final_state = await orchestrator.run(state)

    assert final_state.hitl_pending is False
    assert "cleared for standard release" in final_state.messages[-1].content.lower()


@pytest.mark.asyncio
async def test_early_life_food_contaminated_lot_quarantine_lifecycle() -> None:
    """Verify suspect lot LOT-INF-8812 triggers HITL interrupt and resumes cleanly."""
    orchestrator = build_early_life_triage_orchestrator()
    session_id = "test-contam-lot-8812"

    state = HarnessState(
        session_id=session_id,
        messages=[
            AgentMessage(
                role=Role.USER,
                content="Urgent triage on suspect infant formula lot LOT-INF-8812.",
            )
        ],
    )

    # 1. Run until HITL interrupt
    interrupted_state = await orchestrator.run(state)

    assert interrupted_state.hitl_pending is True
    assert interrupted_state.approval_id is not None
    assert interrupted_state.pending_tool_call is not None
    assert interrupted_state.pending_tool_call.name == "quarantine_infant_formula_lot"

    # 2. QA Director digital signature resume
    resume_req = ResumeRequest(
        approval_id=interrupted_state.approval_id,
        approved=True,
        approver_id="dr_vance_qa",
        approver_role="Director of Quality Assurance",
        signature="ed25519_valid_signature_hash",
        comment="Excursion and Cronobacter positive confirmed. Lockdown authorized.",
    )

    resumed_state = await orchestrator.resume(session_id, resume_req)

    assert resumed_state.hitl_pending is False
    assert "quarantine lockdown" in resumed_state.messages[-1].content.lower()
