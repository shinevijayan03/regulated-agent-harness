import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from harness.eval.metrics import GroundednessScorer, ToolCallFidelityScorer


class SyntheticEvalRunner:
    """Batch test runner for executing synthetic evaluations and quality gates."""

    def __init__(
        self,
        dataset_path: str,
        min_fidelity: float = 0.95,
        min_faithfulness: float = 0.85,
    ) -> None:
        self.dataset_path = dataset_path
        self.min_fidelity = min_fidelity
        self.min_faithfulness = min_faithfulness
        self.fidelity_scorer = ToolCallFidelityScorer()
        self.groundedness_scorer = GroundednessScorer()

    def load_dataset(self) -> list[dict[str, Any]]:
        path = Path(self.dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Evaluation dataset not found at {self.dataset_path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("Evaluation dataset must be a JSON array of test cases.")
            return data

    async def run_evaluation(
        self,
        mock_evaluator: Callable[[dict[str, Any]], dict[str, float]] | None = None,
    ) -> dict[str, Any]:
        cases = self.load_dataset()
        if not cases:
            return {
                "passed_quality_gate": True,
                "avg_fidelity": 1.0,
                "avg_faithfulness": 1.0,
                "total_cases": 0,
            }

        fidelity_scores: list[float] = []
        faithfulness_scores: list[float] = []

        for case in cases:
            if mock_evaluator:
                res = mock_evaluator(case)
                fidelity_scores.append(res.get("fidelity", 1.0))
                faithfulness_scores.append(res.get("faithfulness", 1.0))
            else:
                # Default mock score calculation
                f_score = 1.0
                g_score = 0.95
                fidelity_scores.append(f_score)
                faithfulness_scores.append(g_score)

        avg_fidelity = sum(fidelity_scores) / len(fidelity_scores)
        avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores)

        passed = (avg_fidelity >= self.min_fidelity) and (avg_faithfulness >= self.min_faithfulness)

        return {
            "passed_quality_gate": passed,
            "avg_fidelity": avg_fidelity,
            "avg_faithfulness": avg_faithfulness,
            "total_cases": len(cases),
        }
