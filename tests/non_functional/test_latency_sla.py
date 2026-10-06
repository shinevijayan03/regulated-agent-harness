import time

import pytest

from harness.compliance.audit import CryptographicAuditTrail
from harness.core.types import AgentMessage, HarnessState, RiskTier, Role
from harness.guardrails.hitl import HITLGateInterceptor
from harness.guardrails.input_guard import InputGuardInterceptor
from harness.middleware.pipeline import MiddlewarePipeline
from harness.registry.tools import ToolRegistry, harness_tool


@pytest.mark.asyncio
async def test_middleware_latency_sla_under_40ms() -> None:
    """Non-functional test: Middleware stack latency overhead must be strictly < 40ms."""
    registry = ToolRegistry()

    @harness_tool(name="read_sensor", risk_tier=RiskTier.READ_ONLY, registry=registry)
    async def read_sensor(sensor_id: str) -> dict:
        return {"sensor_id": sensor_id, "val": 22.5}

    input_guard = InputGuardInterceptor(redact_pii=True)
    hitl_gate = HITLGateInterceptor(tools=registry)
    pipeline = MiddlewarePipeline([input_guard, hitl_gate])
    trail = CryptographicAuditTrail(session_id="benchmark-sess-01")

    iterations = 200
    latencies_ms = []

    for i in range(iterations):
        state = HarnessState(
            session_id=f"sess-bench-{i}",
            messages=[
                AgentMessage(
                    role=Role.USER,
                    content=f"Telemetry query {i} for patient SSN 000-11-2222 on sensor SENS-001",
                )
            ],
        )

        t0 = time.perf_counter_ns()

        # 1. Pipeline pre-node (Input Sanitization + HITL check)
        state = await pipeline.run_pre(state, "ingress")

        # 2. Cryptographic audit hashing
        trail.record_step(
            actor="agent",
            action="BENCHMARK_STEP",
            payload={"step": i, "content": state.messages[0].content},
        )

        t1 = time.perf_counter_ns()
        elapsed_ms = (t1 - t0) / 1_000_000.0
        latencies_ms.append(elapsed_ms)

    latencies_ms.sort()
    p50 = latencies_ms[int(iterations * 0.50)]
    p95 = latencies_ms[int(iterations * 0.95)]
    p99 = latencies_ms[int(iterations * 0.99)]

    print(
        f"\n[LATENCY BENCHMARK] P50: {p50:.3f}ms | P95: {p95:.3f}ms | P99: {p99:.3f}ms (SLA: <40.0ms)"
    )

    assert p99 < 40.0, f"P99 latency {p99:.2f}ms exceeded 40ms SLA limit"
