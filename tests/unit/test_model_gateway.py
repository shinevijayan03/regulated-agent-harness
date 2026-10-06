from unittest.mock import AsyncMock, patch

import pytest

from harness.core.types import AgentMessage, RiskTier, Role, ToolDefinition
from harness.gateway.model import LiteLLMModelGateway


@pytest.mark.asyncio
async def test_tc_mod_01_successful_generation_with_tool_call() -> None:
    """TC-MOD-01: Gateway formats messages and parses assistant responses with tool calls."""
    gateway = LiteLLMModelGateway(primary_model="azure/gpt-4o")

    mock_llm_result = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "check_inventory",
                                "arguments": '{"sku": "SKU-409"}',
                            },
                        }
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 40, "completion_tokens": 20},
    }

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_llm_result

        messages = [AgentMessage(role=Role.USER, content="Check inventory for SKU-409")]
        tools = [
            ToolDefinition(
                name="check_inventory",
                description="Checks SKU inventory",
                parameters_schema={"type": "object", "properties": {"sku": {"type": "string"}}},
                risk_tier=RiskTier.READ_ONLY,
            )
        ]

        response = await gateway.generate_response(messages=messages, tools=tools)

        assert response.role == Role.ASSISTANT
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "check_inventory"
        assert response.tool_calls[0].arguments == {"sku": "SKU-409"}


@pytest.mark.asyncio
async def test_tc_mod_02_exponential_backoff_transient_retries() -> None:
    """TC-MOD-02: Gateway retries upon transient rate limit (HTTP 429) before succeeding."""
    gateway = LiteLLMModelGateway(primary_model="azure/gpt-4o", max_retries=3, backoff_factor=0.01)

    success_result = {
        "choices": [{"message": {"role": "assistant", "content": "Recovery response."}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    }

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        # Fail twice with RateLimitError, then succeed
        mock_acompletion.side_effect = [
            Exception("RateLimitError 429"),
            Exception("RateLimitError 429"),
            success_result,
        ]

        messages = [AgentMessage(role=Role.USER, content="Test retry")]
        response = await gateway.generate_response(messages=messages)

        assert response.content == "Recovery response."
        assert mock_acompletion.call_count == 3


@pytest.mark.asyncio
async def test_tc_mod_03_provider_failover_to_secondary_model() -> None:
    """TC-MOD-03: Gateway switches to fallback model when primary model fails permanently."""
    gateway = LiteLLMModelGateway(
        primary_model="azure/gpt-4o",
        fallback_models=["bedrock/anthropic.claude-3-5-sonnet"],
        max_retries=1,
        backoff_factor=0.01,
    )

    fallback_result = {
        "choices": [
            {"message": {"role": "assistant", "content": "Fallback model generated this."}}
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 15},
    }

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        # Primary fails, fallback succeeds
        mock_acompletion.side_effect = [
            Exception("Primary service 503 unavailable"),
            fallback_result,
        ]

        messages = [AgentMessage(role=Role.USER, content="Test failover")]
        response = await gateway.generate_response(messages=messages)

        assert response.content == "Fallback model generated this."
        assert mock_acompletion.call_count == 2
