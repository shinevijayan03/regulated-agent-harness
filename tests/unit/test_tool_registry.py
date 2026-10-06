import pytest
from pydantic import BaseModel, Field

from harness.core.exceptions import SchemaValidationError
from harness.core.types import RiskTier
from harness.registry.mcp import MCPClientAdapter
from harness.registry.tools import ToolRegistry, harness_tool


class PatientLookupInput(BaseModel):
    patient_id: str = Field(..., description="Unique alphanumeric patient ID")
    include_records: bool = Field(default=False, description="Flag for medical records")


@pytest.mark.asyncio
async def test_tc_reg_01_harness_tool_decorator_and_execution() -> None:
    """TC-REG-01: Decorator parses schema, assigns risk tier, and executes async function."""
    registry = ToolRegistry()

    @harness_tool(name="lookup_patient", risk_tier=RiskTier.READ_ONLY, registry=registry)
    async def lookup_patient(patient_id: str, include_records: bool = False) -> dict:
        """Retrieves patient profile information from EHR."""
        return {"id": patient_id, "include_records": include_records, "status": "active"}

    definition = registry.get_tool("lookup_patient")
    assert definition.name == "lookup_patient"
    assert definition.risk_tier == RiskTier.READ_ONLY
    assert "patient_id" in definition.parameters_schema["properties"]

    # Execute with valid parameters
    result = await registry.execute(
        "lookup_patient", {"patient_id": "P-9092", "include_records": True}
    )
    assert result == {"id": "P-9092", "include_records": True, "status": "active"}


@pytest.mark.asyncio
async def test_tc_reg_02_tool_input_validation_rejection() -> None:
    """TC-REG-02: Executing tool with invalid arguments raises SchemaValidationError."""
    registry = ToolRegistry()

    @harness_tool(name="validate_lot", risk_tier=RiskTier.READ_ONLY, registry=registry)
    async def validate_lot(lot_number: str, count: int) -> dict:
        """Validates lot inventory count."""
        return {"lot": lot_number, "count": count}

    # Missing required argument 'count'
    with pytest.raises(SchemaValidationError):
        await registry.execute("validate_lot", {"lot_number": "LT-100"})


@pytest.mark.asyncio
async def test_tc_mcp_01_mcp_client_tool_registration_and_execution() -> None:
    """TC-MCP-01: MCP adapter registers remote tools and executes calls."""
    adapter = MCPClientAdapter(server_name="erp_server")

    # Mock remote tools discovery
    remote_tool_def = {
        "name": "query_erp_po",
        "description": "Fetches purchase order status from ERP system",
        "inputSchema": {
            "type": "object",
            "properties": {"po_number": {"type": "string"}},
            "required": ["po_number"],
        },
    }

    adapter.register_remote_tool(remote_tool_def, risk_tier=RiskTier.READ_ONLY)
    tool_def = adapter.get_tool("erp_server__query_erp_po")
    assert tool_def.name == "erp_server__query_erp_po"
    assert tool_def.risk_tier == RiskTier.READ_ONLY

    # Mock remote execution handler
    adapter.set_remote_executor(
        "erp_server__query_erp_po",
        lambda args: {"po_number": args["po_number"], "status": "APPROVED", "amount": 12500.0},
    )

    result = await adapter.execute("erp_server__query_erp_po", {"po_number": "PO-9921"})
    assert result["status"] == "APPROVED"
    assert result["po_number"] == "PO-9921"
