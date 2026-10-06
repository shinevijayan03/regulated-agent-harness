import asyncio
import json
import logging
from typing import Any

import litellm

from harness.core.exceptions import ProviderException, ProviderUnavailableException
from harness.core.types import AgentMessage, Role, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class BaseModelGateway:
    async def generate_response(
        self,
        messages: list[AgentMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
    ) -> AgentMessage:
        raise NotImplementedError


class LiteLLMModelGateway(BaseModelGateway):
    def __init__(
        self,
        primary_model: str,
        fallback_models: list[str] | None = None,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        timeout: float = 60.0,
    ) -> None:
        self.primary_model = primary_model
        self.fallback_models = fallback_models or []
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout

    def _format_messages_for_litellm(self, messages: list[AgentMessage]) -> list[dict[str, Any]]:
        formatted: list[dict[str, Any]] = []
        for msg in messages:
            item: dict[str, Any] = {"role": msg.role.value, "content": msg.content or ""}
            if msg.name:
                item["name"] = msg.name
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            formatted.append(item)
        return formatted

    def _format_tools_for_litellm(
        self, tools: list[ToolDefinition] | None
    ) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        formatted_tools: list[dict[str, Any]] = []
        for tool in tools:
            formatted_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters_schema,
                    },
                }
            )
        return formatted_tools

    async def _invoke_model_with_retry(
        self,
        model: str,
        formatted_messages: list[dict[str, Any]],
        formatted_tools: list[dict[str, Any]] | None,
        temperature: float,
    ) -> Any:
        last_exception: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "messages": formatted_messages,
                    "temperature": temperature,
                    "timeout": self.timeout,
                }
                if formatted_tools:
                    kwargs["tools"] = formatted_tools

                response = await litellm.acompletion(**kwargs)
                return response
            except Exception as exc:
                last_exception = exc
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_factor * (2**attempt)
                    await asyncio.sleep(sleep_time)

        if last_exception:
            raise last_exception
        raise ProviderException(f"Failed to generate completion from {model}")

    async def generate_response(
        self,
        messages: list[AgentMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
    ) -> AgentMessage:
        formatted_messages = self._format_messages_for_litellm(messages)
        formatted_tools = self._format_tools_for_litellm(tools)

        models_to_try = [self.primary_model] + self.fallback_models
        raw_response: Any | None = None
        last_error: Exception | None = None

        for model in models_to_try:
            try:
                raw_response = await self._invoke_model_with_retry(
                    model, formatted_messages, formatted_tools, temperature
                )
                break
            except Exception as exc:
                logger.warning("Model %s failed: %s", model, exc)
                last_error = exc

        if raw_response is None:
            raise ProviderUnavailableException(f"All models failed. Last error: {last_error}")

        # Parse LiteLLM / OpenAI response format
        choices = (
            raw_response.get("choices", [])
            if isinstance(raw_response, dict)
            else getattr(raw_response, "choices", [])
        )
        if not choices:
            return AgentMessage(role=Role.ASSISTANT, content="")

        choice_msg = (
            choices[0].get("message", {})
            if isinstance(choices[0], dict)
            else getattr(choices[0], "message", {})
        )
        content = (
            choice_msg.get("content") or ""
            if isinstance(choice_msg, dict)
            else getattr(choice_msg, "content", "") or ""
        )
        raw_tool_calls = (
            choice_msg.get("tool_calls")
            if isinstance(choice_msg, dict)
            else getattr(choice_msg, "tool_calls", None)
        )

        parsed_tool_calls: list[ToolCall] | None = None
        if raw_tool_calls:
            parsed_tool_calls = []
            for tc in raw_tool_calls:
                tc_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
                func_data = (
                    tc.get("function", {}) if isinstance(tc, dict) else getattr(tc, "function", {})
                )
                tc_name = (
                    func_data.get("name", "")
                    if isinstance(func_data, dict)
                    else getattr(func_data, "name", "")
                )
                tc_args_raw = (
                    func_data.get("arguments", "{}")
                    if isinstance(func_data, dict)
                    else getattr(func_data, "arguments", "{}")
                )
                if isinstance(tc_args_raw, str):
                    try:
                        tc_args = json.loads(tc_args_raw)
                    except json.JSONDecodeError:
                        tc_args = {}
                else:
                    tc_args = tc_args_raw or {}

                parsed_tool_calls.append(ToolCall(id=tc_id, name=tc_name, arguments=tc_args))

        return AgentMessage(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=parsed_tool_calls,
        )
