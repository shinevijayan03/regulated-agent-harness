import pytest

from harness.compliance.audit import CryptographicAuditTrail
from harness.core.exceptions import AuditIntegrityException
from harness.core.types import AuditRecord


def test_tc_aud_01_genesis_block_creation_and_chaining() -> None:
    """TC-AUD-01: Genesis block created with zero prev_hash and blocks chain deterministically."""
    trail = CryptographicAuditTrail(session_id="sess-audit-01")

    # Genesis block
    genesis = trail.record_step(
        actor="system",
        action="SESSION_INITIALIZED",
        payload={"session_id": "sess-audit-01", "policy": "strict"},
        trace_id="tr-000",
    )

    assert genesis.step == 0
    assert genesis.prev_hash == "0" * 64
    assert len(genesis.block_hash) == 64
    assert len(genesis.payload_hash) == 64

    # Step 1 block
    step1 = trail.record_step(
        actor="agent",
        action="TOOL_EXECUTION",
        payload={"tool": "lookup_sensor", "result": {"temp": 4.2}},
        trace_id="tr-001",
    )

    assert step1.step == 1
    assert step1.prev_hash == genesis.block_hash
    assert trail.validate() is True


def test_tc_aud_02_tamper_detection_in_merkle_chain() -> None:
    """TC-AUD-02: Tampering with any historical block breaks cryptographic validation."""
    trail = CryptographicAuditTrail(session_id="sess-tamper-01")

    for i in range(5):
        trail.record_step(
            actor="agent",
            action=f"ACTION_{i}",
            payload={"iteration": i, "data": f"content_{i}"},
            trace_id=f"tr-{i}",
        )

    # Valid chain passes
    assert trail.validate() is True

    # Tamper with step 2 by modifying an attribute or creating a modified copy
    original_step_2 = trail.records[2]
    # Create an altered record with modified payload_hash
    tampered_step_2 = AuditRecord(
        step=original_step_2.step,
        timestamp=original_step_2.timestamp,
        trace_id=original_step_2.trace_id,
        session_id=original_step_2.session_id,
        actor=original_step_2.actor,
        action="UNAUTHORIZED_MUTATION",  # Mutated action
        payload_hash="0000000000000000000000000000000000000000000000000000000000000000",
        prev_hash=original_step_2.prev_hash,
        block_hash=original_step_2.block_hash,
        status="SUCCESS",
    )
    trail.records[2] = tampered_step_2

    # Validation must raise AuditIntegrityException identifying tampered step 2
    with pytest.raises(AuditIntegrityException) as exc_info:
        trail.validate()

    assert exc_info.value.step_index == 2
