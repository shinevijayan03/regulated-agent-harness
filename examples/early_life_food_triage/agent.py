"""Early Life Food Supply Chain Triage Agent.

Autonomous multi-agent orchestration for infant formula safety, pathogen containment,
and regulatory compliance under FDA 21 CFR Part 106 and GxP.
"""

from typing import Any, List, Optional
import json

from harness.core.types import (
    AgentMessage,
    HarnessState,
    RiskTier,
    Role,
    ToolCall,
    ToolDefinition,
)
from harness.core.orchestrator import HarnessOrchestrator
from harness.gateway.model import BaseModelGateway
from harness.guardrails.hitl import HITLGateInterceptor
from harness.guardrails.input_guard import InputGuardInterceptor
from harness.compliance.audit import CryptographicAuditTrail
from harness.middleware.pipeline import MiddlewarePipeline
from examples.early_life_food_triage.tools import early_life_registry


class InfantFormulaSafetyReasoner(BaseModelGateway):
    """Domain reasoner evaluating infant formula safety under FDA 21 CFR 106.100."""

    async def generate_response(
        self,
        messages: List[AgentMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.2,
    ) -> AgentMessage:
        last_msg = messages[-1]

        # Case 1: Initial user prompt requesting investigation of lot LOT-INF-8812
        if last_msg.role == Role.USER:
            prompt = last_msg.content
            if "LOT-INF-8812" in prompt:
                return AgentMessage(
                    role=Role.ASSISTANT,
                    content="Initiating critical microbiological and pasteurization telemetry triage for lot LOT-INF-8812.",
                    tool_calls=[
                        ToolCall(
                            id="tc_pathogen_01",
                            name="get_batch_pathogen_screening",
                            arguments={"batch_id": "LOT-INF-8812"},
                        )
                    ],
                )
            elif "LOT-INF-9901" in prompt:
                return AgentMessage(
                    role=Role.ASSISTANT,
                    content="Checking safety profile for compliant lot LOT-INF-9901.",
                    tool_calls=[
                        ToolCall(
                            id="tc_pathogen_02",
                            name="get_batch_pathogen_screening",
                            arguments={"batch_id": "LOT-INF-9901"},
                        )
                    ],
                )
            return AgentMessage(
                role=Role.ASSISTANT,
                content="Please specify a valid infant formula production lot ID (e.g. LOT-INF-8812) to triage.",
            )

        # Case 2: Inspecting tool result from pathogen screening
        if last_msg.role == Role.TOOL and last_msg.name == "get_batch_pathogen_screening":
            try:
                data = json.loads(last_msg.content)
            except Exception:
                data = {}

            if data.get("cronobacter_sakazakii_detected") or data.get("batch_id") == "LOT-INF-8812":
                # Contamination detected! Immediately request high-risk quarantine action
                return AgentMessage(
                    role=Role.ASSISTANT,
                    content=(
                        "CRITICAL CONTAMINATION ALERT: LIMS confirms PRESUMPTIVE POSITIVE for "
                        "Cronobacter sakazakii in lot LOT-INF-8812. In accordance with FDA 21 CFR "
                        "Part 106.100 zero-tolerance mandates, immediate quarantine lockdown is required."
                    ),
                    tool_calls=[
                        ToolCall(
                            id="tc_quar_01",
                            name="quarantine_infant_formula_lot",
                            arguments={
                                "lot_id": "LOT-INF-8812",
                                "reason": (
                                    "Presumptive positive Cronobacter sakazakii detected in finished "
                                    "powder screening (LIMS 2026-10-06). Sub-lethal pasteurizer excursion."
                                ),
                                "quarantine_type": "FULL_LOCKDOWN",
                                "regulatory_statute": "FDA_21_CFR_106_100",
                            },
                        )
                    ],
                )
            else:
                return AgentMessage(
                    role=Role.ASSISTANT,
                    content=(
                        f"Lot {data.get('batch_id')} passed all microbiological screening requirements. "
                        "Zero pathogens detected (Cronobacter sakazakii negative, Salmonella negative). "
                        "Standard Plate Count nominal. Lot cleared for standard release workflow."
                    ),
                )

        # Case 3: Post-quarantine resumption synthesis
        if last_msg.role == Role.TOOL and last_msg.name == "quarantine_infant_formula_lot":
            return AgentMessage(
                role=Role.ASSISTANT,
                content=(
                    "INCIDENT CONTAINMENT CONFIRMED: Lot LOT-INF-8812 is now in FULL QUARANTINE LOCKDOWN "
                    "across enterprise ERP (SAP Lock ID: SAP-LOCK-LOT-INF-8812-QMS). Outbound shipping "
                    "docks have been halted. QA Director digital signature has been verified and committed "
                    "to the immutable FDA 21 CFR Part 11 audit log chain."
                ),
            )

        return AgentMessage(
            role=Role.ASSISTANT,
            content="Triage step completed.",
        )


def build_early_life_triage_orchestrator() -> HarnessOrchestrator:
    """Builds and returns the configured Early Life Triage Orchestrator."""
    gateway = InfantFormulaSafetyReasoner()
    input_guard = InputGuardInterceptor(redact_pii=True)
    hitl_gate = HITLGateInterceptor(tools=early_life_registry)
    middleware = MiddlewarePipeline(interceptors=[input_guard, hitl_gate])

    orchestrator = HarnessOrchestrator(
        gateway=gateway,
        tools=early_life_registry,
        middleware=middleware,
    )
    return orchestrator
