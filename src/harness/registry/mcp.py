import asyncio
from collections.abc import Callable
from typing import Any

from harness.core.types import RiskTier, ToolDefinition


class MCPClientAdapter:
    def __init__(self, server_name: str) -> None:
        self.server_name = server_name
        self._tools: dict[str, ToolDefinition] = {}
        self._executors: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register_remote_tool(
        self,
        tool_def: dict[str, Any],
        risk_tier: RiskTier = RiskTier.READ_ONLY,
        timeout_seconds: float = 30.0,
    ) -> ToolDefinition:
        base_name = tool_def.get("name", "remote_tool")
        namespaced_name = f"{self.server_name}__{base_name}"
        description = tool_def.get("description", f"Remote MCP tool {base_name}")
        schema = tool_def.get("inputSchema", {"type": "object", "properties": {}})

        definition = ToolDefinition(
            name=namespaced_name,
            description=description,
            parameters_schema=schema,
            risk_tier=risk_tier,
            timeout_seconds=timeout_seconds,
        )
        self._tools[namespaced_name] = definition
        return definition

    def get_tool(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise KeyError(f"Remote tool {name} not found in adapter for {self.server_name}")
        return self._tools[name]

    def set_remote_executor(self, name: str, executor: Callable[[dict[str, Any]], Any]) -> None:
        self._executors[name] = executor

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name not in self._executors:
            raise KeyError(f"No executor configured for remote tool {tool_name}")

        executor = self._executors[tool_name]
        if asyncio.iscoroutinefunction(executor):
            return await executor(arguments)
        return executor(arguments)
