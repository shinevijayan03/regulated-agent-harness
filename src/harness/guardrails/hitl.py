import uuid

from harness.core.exceptions import HITLInterruptException
from harness.core.types import HarnessState, RiskTier
from harness.middleware.pipeline import BaseInterceptor
from harness.registry.tools import ToolRegistry


class HITLGateInterceptor(BaseInterceptor):
    def __init__(self, tools: ToolRegistry | None = None) -> None:
        self.tools = tools

    async def pre_node(self, state: HarnessState, node_name: str) -> HarnessState:
        if node_name == "tool_executor" and state.pending_tool_call:
            tool_name = state.pending_tool_call.name
            if self.tools and tool_name in self.tools._tools:
                tool_def = self.tools.get_tool(tool_name)
                if tool_def.risk_tier == RiskTier.MUTATING_HIGH_RISK and not state.hitl_pending:
                    approval_id = f"appr-{uuid.uuid4().hex[:8]}"
                    state.hitl_pending = True
                    state.approval_id = approval_id
                    state.risk_tier = RiskTier.MUTATING_HIGH_RISK
                    raise HITLInterruptException(
                        approval_id=approval_id,
                        message=f"Tool {tool_name} requires supervisor authorization.",
                    )
        return state

    async def post_node(self, state: HarnessState, node_name: str) -> HarnessState:
        return state
