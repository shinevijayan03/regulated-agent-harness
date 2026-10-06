import json
import uuid
from typing import Any

from harness.core.exceptions import HITLInterruptException
from harness.core.types import (
    AgentMessage,
    HarnessState,
    ResumeRequest,
    RiskTier,
    Role,
)
from harness.gateway.model import BaseModelGateway
from harness.middleware.pipeline import MiddlewarePipeline
from harness.registry.tools import ToolRegistry


class HarnessOrchestrator:
    def __init__(
        self,
        gateway: BaseModelGateway,
        tools: ToolRegistry,
        middleware: MiddlewarePipeline | None = None,
        checkpointer: Any | None = None,
    ) -> None:
        self.gateway = gateway
        self.tools = tools
        self.middleware = middleware
        self.checkpointer = checkpointer
        self._sessions: dict[str, HarnessState] = {}

    async def run(self, initial_state: HarnessState) -> HarnessState:
        state = initial_state
        self._sessions[state.session_id] = state

        # Ingress middleware
        if self.middleware:
            state = await self.middleware.run_pre(state, "ingress")

        while state.iteration_count < state.max_iterations:
            # Invoke model gateway
            response = await self.gateway.generate_response(
                messages=state.messages,
                tools=self.tools.list_tools(),
            )

            # Check if model requested tool execution
            if response.tool_calls:
                # Add assistant message with tool calls
                state.messages.append(response)
                state.iteration_count += 1

                for tc in response.tool_calls:
                    state.pending_tool_call = tc

                    # Pre-tool middleware / HITL gate
                    if self.middleware:
                        try:
                            state = await self.middleware.run_pre(state, "tool_executor")
                        except HITLInterruptException as exc:
                            state.hitl_pending = True
                            state.approval_id = exc.approval_id
                            state.risk_tier = RiskTier.MUTATING_HIGH_RISK
                            self._sessions[state.session_id] = state
                            return state

                    # Fallback direct HITL check if middleware didn't trigger
                    if tc.name in self.tools._tools:
                        tool_def = self.tools.get_tool(tc.name)
                        if (
                            tool_def.risk_tier == RiskTier.MUTATING_HIGH_RISK
                            and not state.hitl_pending
                        ):
                            approval_id = f"appr-{uuid.uuid4().hex[:8]}"
                            state.hitl_pending = True
                            state.approval_id = approval_id
                            state.risk_tier = RiskTier.MUTATING_HIGH_RISK
                            self._sessions[state.session_id] = state
                            return state

                    # Execute tool
                    try:
                        tool_output = await self.tools.execute(tc.name, tc.arguments)
                    except Exception as err:
                        tool_output = {"error": str(err)}

                    # Append tool response
                    state.messages.append(
                        AgentMessage(
                            role=Role.TOOL,
                            content=json.dumps(tool_output)
                            if not isinstance(tool_output, str)
                            else tool_output,
                            tool_call_id=tc.id,
                            name=tc.name,
                        )
                    )
                    state.pending_tool_call = None

                # Continue loop to allow reasoner to process tool output
                continue

            # Assistant emitted a text response (final answer)
            state.messages.append(response)
            state.iteration_count += 1
            self._sessions[state.session_id] = state
            return state

        # Exceeded max_iterations - graceful degradation
        state.messages.append(
            AgentMessage(
                role=Role.ASSISTANT,
                content="Execution terminated: Maximum allowed iterations reached.",
            )
        )
        self._sessions[state.session_id] = state
        return state

    async def resume(self, session_id: str, resume_payload: ResumeRequest) -> HarnessState:
        if session_id not in self._sessions:
            raise KeyError(f"Session {session_id} not found.")

        state = self._sessions[session_id]

        if not state.hitl_pending or not state.pending_tool_call:
            return state

        pending_tc = state.pending_tool_call

        if not resume_payload.approved:
            state.hitl_pending = False
            state.approval_id = None
            state.pending_tool_call = None
            rejection_text = (
                f"Action rejected: {resume_payload.comment or 'Execution cancelled by reviewer.'}"
            )
            state.messages.append(AgentMessage(role=Role.ASSISTANT, content=rejection_text))
            self._sessions[session_id] = state
            return state

        # Approved: execute pending mutating tool
        try:
            tool_output = await self.tools.execute(pending_tc.name, pending_tc.arguments)
        except Exception as err:
            tool_output = {"error": str(err)}

        state.hitl_pending = False
        state.approval_id = None
        state.pending_tool_call = None

        state.messages.append(
            AgentMessage(
                role=Role.TOOL,
                content=json.dumps(tool_output)
                if not isinstance(tool_output, str)
                else tool_output,
                tool_call_id=pending_tc.id,
                name=pending_tc.name,
            )
        )

        # Generate final response
        final_response = await self.gateway.generate_response(
            messages=state.messages,
            tools=self.tools.list_tools(),
        )
        state.messages.append(final_response)
        state.iteration_count += 1
        self._sessions[session_id] = state
        return state
