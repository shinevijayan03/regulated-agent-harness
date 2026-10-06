import asyncio
from typing import Any

import pytest


# Global event loop fixture
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Deterministic Mock Provider response objects
class MockLLMResponse:
    def __init__(
        self,
        content: str = "",
        tool_calls: list[dict[str, Any]] | None = None,
        prompt_tokens: int = 50,
        completion_tokens: int = 25,
        cost_usd: float = 0.001,
    ):
        self.content = content
        self.tool_calls = tool_calls or []
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost_usd = cost_usd


@pytest.fixture
def sample_audit_genesis_payload() -> dict[str, Any]:
    return {
        "step": 0,
        "trace_id": "tr-test-genesis-000",
        "session_id": "sess-test-001",
        "actor": "system",
        "action": "SESSION_INITIALIZED",
        "payload": {"environment": "test", "max_iterations": 10},
    }


@pytest.fixture
def sample_user_message_payload() -> dict[str, Any]:
    return {
        "session_id": "sess-test-001",
        "message": "Query temperature telemetry for sensor SENS-901.",
        "context": {"user_id": "usr-test-01", "role": "analyst"},
    }
