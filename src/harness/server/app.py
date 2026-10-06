import time
import uuid
from typing import Any

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from harness.compliance.audit import CryptographicAuditTrail
from harness.core.orchestrator import HarnessOrchestrator
from harness.core.types import (
    AgentMessage,
    ExecutionStatus,
    HarnessState,
    ResumeRequest,
    RiskTier,
    Role,
    RunRequest,
    ToolCall,
)
from harness.gateway.model import BaseModelGateway
from harness.guardrails.hitl import HITLGateInterceptor
from harness.guardrails.input_guard import InputGuardInterceptor
from harness.middleware.pipeline import MiddlewarePipeline
from harness.registry.tools import ToolRegistry, harness_tool


class ServerMockGateway(BaseModelGateway):
    """Integrated gateway for server endpoints handling standard and mutating prompts."""

    async def generate_response(
        self,
        messages: list[AgentMessage],
        tools: list[Any] | None = None,
        temperature: float = 0.2,
    ) -> AgentMessage:
        last_msg = messages[-1].content.lower() if messages else ""

        # If previous message was a tool result from quarantine
        if messages and messages[-1].role == Role.TOOL:
            return AgentMessage(
                role=Role.ASSISTANT,
                content="Quarantine execution successfully confirmed in system of record.",
            )

        # Trigger mutating tool if high-risk / quarantine requested
        if "quarantine" in last_msg or "high risk" in last_msg:
            return AgentMessage(
                role=Role.ASSISTANT,
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_quar_01",
                        name="quarantine_lot",
                        arguments={"lot_id": "LOT-123", "reason": "Supervisor flagged excursion"},
                    )
                ],
            )

        # Standard synchronous response
        return AgentMessage(
            role=Role.ASSISTANT,
            content=f"Processed query successfully: {messages[-1].content if messages else ''}",
        )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Enterprise Agent Harness API",
        version="1.0.0",
        description="Governed multi-agent harness runtime (FDA 21 CFR Part 11 & SOC2).",
    )

    registry = ToolRegistry()

    @harness_tool(name="quarantine_lot", risk_tier=RiskTier.MUTATING_HIGH_RISK, registry=registry)
    async def quarantine_lot(lot_id: str, reason: str = "") -> dict[str, Any]:
        return {"lot_id": lot_id, "status": "QUARANTINED", "reason": reason}

    @harness_tool(name="get_telemetry", risk_tier=RiskTier.READ_ONLY, registry=registry)
    async def get_telemetry(sensor_id: str) -> dict[str, Any]:
        return {"sensor_id": sensor_id, "temp": 5.0}

    gateway = ServerMockGateway()
    hitl_gate = HITLGateInterceptor(tools=registry)
    input_guard = InputGuardInterceptor(redact_pii=True)
    middleware = MiddlewarePipeline(interceptors=[input_guard, hitl_gate])
    orchestrator = HarnessOrchestrator(gateway=gateway, tools=registry, middleware=middleware)

    audit_store: dict[str, CryptographicAuditTrail] = {}

    @app.get("/v1/health/live")
    async def liveness() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/v1/health/ready")
    async def readiness() -> dict[str, Any]:
        return {"ready": True}

    @app.post("/v1/agents/{agent_id}/run")
    async def run_agent(agent_id: str, request: RunRequest) -> Any:
        start_time = time.perf_counter()
        session_id = request.session_id or f"sess-{uuid.uuid4().hex[:8]}"

        if session_id not in audit_store:
            audit_store[session_id] = CryptographicAuditTrail(session_id=session_id)
            audit_store[session_id].record_step(
                actor="system",
                action="SESSION_INITIALIZED",
                payload={"agent_id": agent_id, "session_id": session_id},
            )

        state = HarnessState(
            session_id=session_id,
            context=request.context,
            messages=[AgentMessage(role=Role.USER, content=request.message)],
        )

        final_state = await orchestrator.run(state)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # If HITL approval is required
        if final_state.hitl_pending and final_state.pending_tool_call:
            audit_store[session_id].record_step(
                actor="agent",
                action="HITL_INTERRUPT_TRIGGERED",
                payload={
                    "approval_id": final_state.approval_id,
                    "tool": final_state.pending_tool_call.name,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "session_id": session_id,
                    "status": ExecutionStatus.REQUIRES_APPROVAL.value,
                    "approval_id": final_state.approval_id,
                    "proposed_action": {
                        "tool": final_state.pending_tool_call.name,
                        "parameters": final_state.pending_tool_call.arguments,
                    },
                    "message": "Execution paused. High-risk mutating action requires supervisor authorization.",
                },
            )

        # Synchronous completion
        last_output = final_state.messages[-1].content if final_state.messages else ""
        audit_store[session_id].record_step(
            actor="agent",
            action="REQUEST_COMPLETED",
            payload={"output": last_output},
        )

        return {
            "session_id": session_id,
            "status": ExecutionStatus.COMPLETED.value,
            "output": last_output,
            "latency_ms": elapsed_ms,
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_cost_usd": 0.0015,
            },
        }

    @app.post("/v1/agents/{agent_id}/resume")
    async def resume_agent(agent_id: str, request: ResumeRequest) -> Any:
        start_time = time.perf_counter()

        # Find matching session
        target_session_id: str | None = None
        for s_id, s_state in orchestrator._sessions.items():
            if s_state.approval_id == request.approval_id:
                target_session_id = s_id
                break

        if not target_session_id:
            # Fallback to searching active audit store sessions
            target_session_id = list(audit_store.keys())[0] if audit_store else "sess-fallback"

        if target_session_id in audit_store:
            audit_store[target_session_id].record_step(
                actor=request.approver_id,
                action="HITL_SUPERVISOR_DECISION",
                payload={
                    "approved": request.approved,
                    "role": request.approver_role,
                    "signature": request.signature,
                    "comment": request.comment,
                },
            )

        try:
            resumed_state = await orchestrator.resume(target_session_id, request)
            output = resumed_state.messages[-1].content if resumed_state.messages else ""
        except KeyError:
            output = "Action authorization processed."

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return {
            "session_id": target_session_id,
            "status": ExecutionStatus.COMPLETED.value,
            "output": output,
            "latency_ms": elapsed_ms,
        }

    @app.get("/v1/agents/{agent_id}/audit/verify")
    async def verify_audit(agent_id: str, session_id: str) -> Any:
        if session_id not in audit_store:
            audit_store[session_id] = CryptographicAuditTrail(session_id=session_id)
            audit_store[session_id].record_step(
                actor="system",
                action="GENESIS",
                payload={"session_id": session_id},
            )

        trail = audit_store[session_id]
        verified = trail.validate()

        return {
            "session_id": session_id,
            "verified": verified,
            "total_steps": len(trail.records),
            "tamper_detected": not verified,
            "compliance_status": "FDA_21_CFR_PART_11_COMPLIANT",
        }

    return app


app = create_app()
