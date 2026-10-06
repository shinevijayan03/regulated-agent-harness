from harness.core.exceptions import BudgetLimitExceededException
from harness.core.types import HarnessState


class CostBudgetGuard:
    def __init__(self, max_cost_usd: float = 0.50) -> None:
        self.max_cost_usd = max_cost_usd

    def check_budget(self, state: HarnessState) -> None:
        if state.total_cost_usd > self.max_cost_usd:
            raise BudgetLimitExceededException(
                f"Session {state.session_id} exceeded budget cap of ${self.max_cost_usd:.2f} (current: ${state.total_cost_usd:.4f})"
            )
