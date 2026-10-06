import pytest

from harness.core.orchestrator import HarnessOrchestrator
from harness.core.types import (
    AgentMessage,
    HarnessState,
    RiskTier,
    Role,
    ToolCall,
    ToolDefinition,
)
from harness.gateway.model import BaseModelGateway
from harness.middleware.pipeline import MiddlewarePipeline
from harness.registry.tools import ToolRegistry, harness_tool


class ScriptedMockGateway(BaseModelGateway):
    """Deterministic mock gateway providing sequential predefined responses."""

    def __init__(self, responses: list[AgentMessage]):
        self.responses = list(responses)
        self.call_count = 0

    async def generate_response(
        self,
        messages: list[AgentMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
    ) -> AgentMessage:
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return AgentMessage(role=Role.ASSISTANT, content="Default fallback answer.")


@pytest.mark.asyncio
async def test_tc_orc_01_multi_turn_graph_execution() -> None:
    """TC-ORC-01: Multi-turn graph execution: User -> Reasoner -> Read Tool -> Reasoner -> Final."""
    registry = ToolRegistry()

    @harness_tool(name="get_sensor_telemetry", risk_tier=RiskTier.READ_ONLY, registry=registry)
    async def get_sensor_telemetry(sensor_id: str) -> dict:
        return {"sensor_id": sensor_id, "temperature": 8.5, "excursion_mins": 45}

    gateway = ScriptedMockGateway(
        responses=[
            # Step 1: Model requests tool call
            AgentMessage(
                role=Role.ASSISTANT,
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_01",
                        name="get_sensor_telemetry",
                        arguments={"sensor_id": "SENS-901"},
                    )
                ],
            ),
            # Step 2: Model emits final answer after inspecting tool result
            AgentMessage(
                role=Role.ASSISTANT,
                content="Sensor SENS-901 is at 8.5°C with a 45-minute temperature excursion.",
            ),
        ]
    )

    middleware = MiddlewarePipeline(interceptors=[])
    orchestrator = HarnessOrchestrator(gateway=gateway, tools=registry, middleware=middleware)

    initial_state = HarnessState(
        session_id="sess-turn-01",
        messages=[
            AgentMessage(role=Role.USER, content="Check cold chain status for sensor SENS-901.")
        ],
    )

    final_state = await orchestrator.run(initial_state)

    assert final_state.iteration_count == 2
    assert len(final_state.messages) >= 3
    last_message = final_state.messages[-1]
    assert last_message.role == Role.ASSISTANT
    assert "8.5°C" in last_message.content


@pytest.mark.asyncio
async def test_tc_orc_02_loop_prevention_max_iterations() -> None:
    """TC-ORC-02: Graph exits cleanly and routes to fallback when max_iterations is reached."""
    registry = ToolRegistry()

    @harness_tool(name="ping_server", risk_tier=RiskTier.READ_ONLY, registry=registry)
    async def ping_server(target: str) -> dict:
        return {"ping": "pong"}

    # Mock gateway endlessly calls tool in a loop
    loop_call = AgentMessage(
        role=Role.ASSISTANT,
        content="",
        tool_calls=[ToolCall(id="call_loop", name="ping_server", arguments={"target": "api"})],
    )
    gateway = ScriptedMockGateway(responses=[loop_call, loop_call, loop_call, loop_call])

    middleware = MiddlewarePipeline(interceptors=[])
    orchestrator = HarnessOrchestrator(gateway=gateway, tools=registry, middleware=middleware)

    initial_state = HarnessState(
        session_id="sess-loop-01",
        max_iterations=3,
        messages=[AgentMessage(role=Role.USER, content="Loop infinitely")],
    )

    final_state = await orchestrator.run(initial_state)

    assert final_state.iteration_count == 3
    last_message = final_state.messages[-1]
    assert "maximum allowed iterations" in last_message.content.lower()
