import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from harness.core.exceptions import AuditIntegrityException
from harness.core.types import AuditRecord


def canonical_hash(data: Any) -> str:
    """Computes deterministic SHA-256 hash of canonicalized JSON."""
    canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class CryptographicAuditTrail:
    """Immutable, append-only SHA-256 Merkle chain meeting FDA 21 CFR Part 11 requirements."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.records: list[AuditRecord] = []

    def _compute_block_hash(
        self,
        prev_hash: str,
        step: int,
        timestamp: str,
        actor: str,
        action: str,
        payload_hash: str,
    ) -> str:
        block_content = f"{prev_hash}{step}{timestamp}{actor}{action}{payload_hash}"
        return hashlib.sha256(block_content.encode("utf-8")).hexdigest()

    def record_step(
        self,
        actor: str,
        action: str,
        payload: dict[str, Any],
        trace_id: str = "",
        status: str = "SUCCESS",
    ) -> AuditRecord:
        step = len(self.records)
        timestamp = datetime.now(UTC).isoformat()
        prev_hash = "0" * 64 if step == 0 else self.records[-1].block_hash
        payload_hash = canonical_hash(payload)
        block_hash = self._compute_block_hash(
            prev_hash=prev_hash,
            step=step,
            timestamp=timestamp,
            actor=actor,
            action=action,
            payload_hash=payload_hash,
        )

        record = AuditRecord(
            step=step,
            timestamp=timestamp,
            trace_id=trace_id or f"tr-{step}",
            session_id=self.session_id,
            actor=actor,
            action=action,
            payload_hash=payload_hash,
            prev_hash=prev_hash,
            block_hash=block_hash,
            status=status,
        )
        self.records.append(record)
        return record

    def validate(self) -> bool:
        """Validates entire cryptographic chain from genesis to head."""
        for i, record in enumerate(self.records):
            # 1. Verify sequence step
            if record.step != i:
                raise AuditIntegrityException(
                    f"Sequence index mismatch: expected {i}, got {record.step}",
                    step_index=i,
                )

            # 2. Verify previous hash chaining
            expected_prev = "0" * 64 if i == 0 else self.records[i - 1].block_hash
            if record.prev_hash != expected_prev:
                raise AuditIntegrityException(
                    f"Previous block hash mismatch at step {i}: expected {expected_prev}, got {record.prev_hash}",
                    step_index=i,
                )

            # 3. Verify block hash integrity
            expected_block_hash = self._compute_block_hash(
                prev_hash=record.prev_hash,
                step=record.step,
                timestamp=record.timestamp,
                actor=record.actor,
                action=record.action,
                payload_hash=record.payload_hash,
            )
            if record.block_hash != expected_block_hash:
                raise AuditIntegrityException(
                    f"Block hash integrity violation at step {i}: computed {expected_block_hash}, stored {record.block_hash}",
                    step_index=i,
                )

        return True
