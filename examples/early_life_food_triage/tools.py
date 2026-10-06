"""Early Life Nutrition & Infant Food Supply Chain Triage Tools.

Governed tools adhering to FDA Infant Formula Act (21 CFR Part 106 & 107),
FSMA (21 CFR Part 117), and ISO 22000 / FSSC 22000.
"""

from typing import Any, Dict
from pydantic import BaseModel, Field

from harness.core.types import RiskTier
from harness.registry.tools import ToolRegistry, harness_tool

# Central domain tool registry
early_life_registry = ToolRegistry()


class PathogenScreenResult(BaseModel):
    batch_id: str
    cronobacter_sakazakii_detected: bool = Field(..., description="Target: Zero tolerance (Absence in 30x10g)")
    salmonella_detected: bool = Field(..., description="Target: Zero tolerance (Absence in 30x25g)")
    aerobic_plate_count_cfu_g: int = Field(..., description="Standard Plate Count (CFU/g)")
    lims_tested_at: str


class ThermalHistory(BaseModel):
    batch_id: str
    pasteurizer_id: str
    target_temp_celsius: float
    actual_temp_celsius: float
    hold_time_seconds: float
    excursion_breach: bool


# ------------------------------------------------------------------------------
# 1. READ_ONLY TOOLS: No mutating side effects
# ------------------------------------------------------------------------------


@harness_tool(
    name="get_batch_pathogen_screening",
    risk_tier=RiskTier.READ_ONLY,
    timeout_seconds=10.0,
    registry=early_life_registry,
)
async def get_batch_pathogen_screening(batch_id: str) -> Dict[str, Any]:
    """Retrieves certified microbiological screening from LIMS for an infant formula lot.

    Checks critical pathogens (Cronobacter sakazakii and Salmonella).
    """
    # Simulated enterprise LIMS database records
    sample_records: Dict[str, Dict[str, Any]] = {
        "LOT-INF-8812": {
            "batch_id": "LOT-INF-8812",
            "cronobacter_sakazakii_detected": True,  # PRESUMPTIVE POSITIVE
            "salmonella_detected": False,
            "aerobic_plate_count_cfu_g": 420,
            "lims_tested_at": "2026-10-06T18:15:00Z",
            "lab_analyst": "analyst_mcneil",
        },
        "LOT-INF-9901": {
            "batch_id": "LOT-INF-9901",
            "cronobacter_sakazakii_detected": False,
            "salmonella_detected": False,
            "aerobic_plate_count_cfu_g": 35,
            "lims_tested_at": "2026-10-06T19:00:00Z",
            "lab_analyst": "analyst_park",
        },
    }

    if batch_id in sample_records:
        return sample_records[batch_id]

    return {
        "batch_id": batch_id,
        "cronobacter_sakazakii_detected": False,
        "salmonella_detected": False,
        "aerobic_plate_count_cfu_g": 10,
        "lims_tested_at": "2026-10-06T12:00:00Z",
        "lab_analyst": "analyst_default",
    }


@harness_tool(
    name="get_thermal_telemetry",
    risk_tier=RiskTier.READ_ONLY,
    timeout_seconds=10.0,
    registry=early_life_registry,
)
async def get_thermal_telemetry(batch_id: str) -> Dict[str, Any]:
    """Retrieves high-temperature short-time (HTST) pasteurizer telemetry from SCADA historians."""
    sample_scada: Dict[str, Dict[str, Any]] = {
        "LOT-INF-8812": {
            "batch_id": "LOT-INF-8812",
            "pasteurizer_id": "HTST-UNIT-04",
            "target_temp_celsius": 72.0,
            "actual_temp_celsius": 68.2,  # SUB-LETHAL EXCURSION
            "hold_time_seconds": 11.5,  # SHORT OF 15 SEC MANDATE
            "excursion_breach": True,
            "flow_diversion_valve_tripped": False,
        },
        "LOT-INF-9901": {
            "batch_id": "LOT-INF-9901",
            "pasteurizer_id": "HTST-UNIT-02",
            "target_temp_celsius": 72.0,
            "actual_temp_celsius": 72.8,
            "hold_time_seconds": 16.2,
            "excursion_breach": False,
            "flow_diversion_valve_tripped": False,
        },
    }

    if batch_id in sample_scada:
        return sample_scada[batch_id]

    return {
        "batch_id": batch_id,
        "pasteurizer_id": "HTST-DEFAULT",
        "target_temp_celsius": 72.0,
        "actual_temp_celsius": 72.5,
        "hold_time_seconds": 15.5,
        "excursion_breach": False,
        "flow_diversion_valve_tripped": False,
    }


# ------------------------------------------------------------------------------
# 2. MUTATING_HIGH_RISK TOOLS: Enforces Human-In-The-Loop (HITL) Gate
# ------------------------------------------------------------------------------


@harness_tool(
    name="quarantine_infant_formula_lot",
    risk_tier=RiskTier.MUTATING_HIGH_RISK,
    timeout_seconds=15.0,
    registry=early_life_registry,
)
async def quarantine_infant_formula_lot(
    lot_id: str,
    reason: str,
    quarantine_type: str = "FULL_LOCKDOWN",
    regulatory_statute: str = "FDA_21_CFR_106_100",
) -> Dict[str, Any]:
    """QUARANTINES an infant formula production lot across ERP (SAP S/4HANA / WMS).

    Applies immediate shipment blocks, seals warehouse bins, and flags product release holds.
    MUTATING OPERATION: Requires Quality Assurance Director digital signature.
    """
    return {
        "status": "QUARANTINED",
        "lot_id": lot_id,
        "quarantine_type": quarantine_type,
        "regulatory_statute": regulatory_statute,
        "action_timestamp": "2026-10-06T20:50:00Z",
        "erp_lock_id": f"SAP-LOCK-{lot_id}-QMS",
        "reason": reason,
        "containment": "Warehouse pallets flagged. Outbound shipping docks halted.",
    }


@harness_tool(
    name="escalate_fda_incident_report",
    risk_tier=RiskTier.MUTATING_HIGH_RISK,
    timeout_seconds=15.0,
    registry=early_life_registry,
)
async def escalate_fda_incident_report(
    lot_id: str,
    pathogen: str,
    root_cause_preliminary: str,
) -> Dict[str, Any]:
    """Generates and submits a preliminary 24-hour FDA Notification of Contamination draft.

    MUTATING OPERATION: Critical regulatory notification. Requires Regulatory Affairs sign-off.
    """
    return {
        "status": "DRAFT_COMMITTED_TO_REGULATORY_QUEUE",
        "lot_id": lot_id,
        "pathogen": pathogen,
        "root_cause_preliminary": root_cause_preliminary,
        "qms_ticket_id": f"CAPA-FDA-2026-{lot_id}",
    }
