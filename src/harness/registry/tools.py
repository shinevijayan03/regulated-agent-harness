import asyncio
import inspect
from collections.abc import Callable, Coroutine
from typing import Any, get_type_hints

from harness.core.exceptions import SchemaValidationError
from harness.core.types import RiskTier, ToolDefinition


def _python_type_to_json_schema(py_type: Any) -> dict[str, Any]:
    if py_type is str:
        return {"type": "string"}
    elif py_type is int:
        return {"type": "integer"}
    elif py_type is float:
        return {"type": "number"}
    elif py_type is bool:
        return {"type": "boolean"}
    elif py_type is list or getattr(py_type, "__origin__", None) is list:
        return {"type": "array"}
    elif py_type is dict or getattr(py_type, "__origin__", None) is dict:
        return {"type": "object"}
    return {"type": "string"}


def _generate_json_schema_from_func(func: Callable[..., Any]) -> dict[str, Any]:
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue
        param_type = type_hints.get(param_name, str)
        properties[param_name] = _python_type_to_json_schema(param_type)

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._executors: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}

    def register(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        name: str | None = None,
        description: str | None = None,
        risk_tier: RiskTier = RiskTier.READ_ONLY,
        timeout_seconds: float = 30.0,
    ) -> ToolDefinition:
        tool_name = name or func.__name__
        tool_desc = description or inspect.getdoc(func) or f"Tool {tool_name}"
        schema = _generate_json_schema_from_func(func)

        definition = ToolDefinition(
            name=tool_name,
            description=tool_desc,
            parameters_schema=schema,
            risk_tier=risk_tier,
            timeout_seconds=timeout_seconds,
        )
        self._tools[tool_name] = definition
        self._executors[tool_name] = func
        return definition

    def get_tool(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise KeyError(f"Tool {name} not found in registry.")
        return self._tools[name]

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def validate_arguments(self, tool_def: ToolDefinition, arguments: dict[str, Any]) -> None:
        schema = tool_def.parameters_schema
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in arguments:
                raise SchemaValidationError(
                    f"Missing required parameter '{field}' for tool '{tool_def.name}'"
                )

        properties = schema.get("properties", {})
        for key, val in arguments.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type == "integer" and not isinstance(val, int):
                    raise SchemaValidationError(
                        f"Parameter '{key}' must be an integer, got {type(val).__name__}"
                    )
                elif expected_type == "boolean" and not isinstance(val, bool):
                    raise SchemaValidationError(
                        f"Parameter '{key}' must be a boolean, got {type(val).__name__}"
                    )
                elif expected_type == "string" and not isinstance(val, str):
                    raise SchemaValidationError(
                        f"Parameter '{key}' must be a string, got {type(val).__name__}"
                    )
                elif expected_type == "number" and not isinstance(val, (int, float)):
                    raise SchemaValidationError(
                        f"Parameter '{key}' must be a number, got {type(val).__name__}"
                    )

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        tool_def = self.get_tool(tool_name)
        self.validate_arguments(tool_def, arguments)

        executor = self._executors[tool_name]
        try:
            return await asyncio.wait_for(executor(**arguments), timeout=tool_def.timeout_seconds)
        except TimeoutError as err:
            raise TimeoutError(
                f"Tool {tool_name} execution timed out after {tool_def.timeout_seconds}s"
            ) from err


def harness_tool(
    name: str | None = None,
    risk_tier: RiskTier = RiskTier.READ_ONLY,
    timeout_seconds: float = 30.0,
    registry: ToolRegistry | None = None,
) -> Callable[..., Any]:
    def decorator(
        func: Callable[..., Coroutine[Any, Any, Any]],
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        target_registry = registry
        if target_registry is not None:
            target_registry.register(
                func=func,
                name=name,
                risk_tier=risk_tier,
                timeout_seconds=timeout_seconds,
            )
        return func

    return decorator
