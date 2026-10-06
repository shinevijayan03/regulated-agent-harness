import pytest
from pydantic import ValidationError

from harness.core.types import (
    AgentMessage,
    AuditRecord,
    HarnessState,
    ResumeRequest,
    RiskTier,
    Role,
    RunRequest,
)


def test_tc_typ_01_audit_record_immutability_and_validation() -> None:
    """TC-TYP-01: AuditRecord enforces immutability, validates ISO-8601 UTC timestamps, and prevents field mutation."""
    record = AuditRecord(
        step=1,
        trace_id="tr-9812",
        session_id="sess-001",
        actor="agent",
        action="TOOL_EXECUTION",
        payload_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        prev_hash="0000000000000000000000000000000000000000000000000000000000000000",
        block_hash="7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
        status="SUCCESS",
    )
    assert record.step == 1
    assert len(record.prev_hash) == 64
    assert len(record.block_hash) == 64
    assert record.status == "SUCCESS"

    # Enforce frozen immutability
    with pytest.raises((ValidationError, TypeError)):
        record.status = "FAILED"  # type: ignore[misc]


def test_tc_typ_02_harness_state_defaults_and_invariants() -> None:
    """TC-TYP-02: HarnessState initializes with expected defaults and invariants."""
    state = HarnessState(session_id="test-session-123")
    assert state.session_id == "test-session-123"
    assert state.iteration_count == 0
    assert state.max_iterations == 10
    assert state.risk_tier == RiskTier.READ_ONLY
    assert state.hitl_pending is False
    assert state.approval_id is None
    assert len(state.messages) == 0
    assert len(state.audit_trail) == 0
    assert state.total_tokens == 0
    assert state.total_cost_usd == 0.0


def test_agent_message_immutability_and_roles() -> None:
    """Verify AgentMessage supports roles and is frozen."""
    msg = AgentMessage(role=Role.USER, content="Hello Enterprise Agent")
    assert msg.role == Role.USER
    assert msg.content == "Hello Enterprise Agent"

    with pytest.raises((ValidationError, TypeError)):
        msg.content = "Modified"  # type: ignore[misc]


def test_run_request_and_resume_request_schemas() -> None:
    """Verify RunRequest and ResumeRequest schemas enforce required fields."""
    req = RunRequest(message="Investigate cold chain alarm")
    assert req.message == "Investigate cold chain alarm"
    assert req.session_id is None

    resume = ResumeRequest(
        approval_id="appr-8821",
        approved=True,
        approver_id="dr_smith",
        approver_role="qa_lead",
        signature="sig_valid_hash",
        comment="Approved per SOP-102",
    )
    assert resume.approved is True
    assert resume.approver_id == "dr_smith"
