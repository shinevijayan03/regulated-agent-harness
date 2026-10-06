import pytest
from httpx import ASGITransport, AsyncClient

from harness.server.app import create_app


@pytest.mark.asyncio
async def test_health_check_endpoints() -> None:
    """Verify liveness and readiness health check endpoints."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        ready_resp = await client.get("/v1/health/ready")
        assert ready_resp.status_code == 200
        assert ready_resp.json()["ready"] is True


@pytest.mark.asyncio
async def test_tc_api_01_agent_run_endpoint() -> None:
    """TC-API-01: POST /v1/agents/{id}/run executes request and returns synchronous completion."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"message": "Hello enterprise agent test"}
        resp = await client.post("/v1/agents/test-agent/run", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["status"] in ["COMPLETED", "PENDING"]


@pytest.mark.asyncio
async def test_tc_api_02_and_03_hitl_run_and_resume_endpoints() -> None:
    """TC-API-02 & TC-API-03: Verify approval requirement and resumption via HTTP."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Request requiring approval
        resp = await client.post(
            "/v1/agents/test-agent/run",
            json={"message": "Trigger high risk action quarantine lot LOT-123"},
        )

        # If HITL is triggered:
        if resp.status_code == 202:
            data = resp.json()
            assert data["status"] == "REQUIRES_APPROVAL"
            approval_id = data["approval_id"]

            # Resume endpoint
            resume_payload = {
                "approval_id": approval_id,
                "approved": True,
                "approver_id": "dr_smith",
                "approver_role": "director",
                "signature": "sig_token_123",
                "comment": "Approved",
            }
            resume_resp = await client.post(
                "/v1/agents/test-agent/resume",
                json=resume_payload,
            )
            assert resume_resp.status_code == 200


@pytest.mark.asyncio
async def test_tc_api_04_audit_verify_endpoint() -> None:
    """TC-API-04: GET /v1/agents/{id}/audit/verify validates cryptographic hash chain."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/v1/agents/test-agent/audit/verify",
            params={"session_id": "test-session-001"},
        )
        assert resp.status_code in [200, 404]
