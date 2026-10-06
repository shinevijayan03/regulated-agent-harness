from pathlib import Path

import pytest

from harness.eval.metrics import AnswerRelevancyScorer, GroundednessScorer, ToolCallFidelityScorer
from harness.eval.runner import SyntheticEvalRunner


def test_eval_metric_scorers() -> None:
    """Verify individual metric scorer calculations."""
    fidelity_scorer = ToolCallFidelityScorer()
    score = fidelity_scorer.score(
        selected_tool="get_sensor_telemetry",
        expected_tool="get_sensor_telemetry",
        actual_arguments={"sensor_id": "SENS-901"},
        expected_arguments={"sensor_id": "SENS-901"},
    )
    assert score == 1.0

    # Wrong tool
    score_wrong = fidelity_scorer.score(
        selected_tool="other_tool",
        expected_tool="get_sensor_telemetry",
        actual_arguments={},
        expected_arguments={"sensor_id": "SENS-901"},
    )
    assert score_wrong == 0.0

    # Empty expected arguments
    score_empty = fidelity_scorer.score(
        selected_tool="ping",
        expected_tool="ping",
        actual_arguments={},
        expected_arguments={},
    )
    assert score_empty == 1.0

    groundedness_scorer = GroundednessScorer()
    g_score = groundedness_scorer.score(
        context="Temperature was 8.5C with 45 minutes excursion.",
        answer="The temperature reached 8.5C and excursion lasted 45 minutes.",
    )
    assert g_score >= 0.80

    # Empty answer groundedness
    assert groundedness_scorer.score(context="Some context", answer="") == 0.0

    relevancy_scorer = AnswerRelevancyScorer()
    r_score = relevancy_scorer.score(
        question="Check cold chain status",
        answer="Status is nominal with cold chain verified.",
    )
    assert r_score >= 0.30
    assert relevancy_scorer.score(question="", answer="") == 0.0


@pytest.mark.asyncio
async def test_tc_evl_01_and_02_eval_runner_quality_gate() -> None:
    """TC-EVL-01 & TC-EVL-02: Runner runs dataset and verifies quality gate thresholds."""
    fixture_path = Path("tests/fixtures/sample_dataset.json")
    runner = SyntheticEvalRunner(
        dataset_path=str(fixture_path),
        min_fidelity=0.90,
        min_faithfulness=0.80,
    )

    # Run mock evaluation with passing scores
    result = await runner.run_evaluation(
        mock_evaluator=lambda case: {
            "fidelity": 1.0,
            "faithfulness": 0.95,
            "relevancy": 0.92,
        }
    )

    assert result["passed_quality_gate"] is True
    assert result["avg_fidelity"] >= 0.90
    assert result["avg_faithfulness"] >= 0.80

    # Run evaluation without mock_evaluator (exercises default scoring branch)
    default_result = await runner.run_evaluation()
    assert default_result["passed_quality_gate"] is True

    # Test gate failure when scores are below threshold
    failing_result = await runner.run_evaluation(
        mock_evaluator=lambda case: {
            "fidelity": 0.50,  # Below 0.90 threshold
            "faithfulness": 0.60,
            "relevancy": 0.65,
        }
    )
    assert failing_result["passed_quality_gate"] is False


def test_eval_runner_errors() -> None:
    """Verify FileNotFoundError on missing dataset path."""
    runner = SyntheticEvalRunner(dataset_path="nonexistent_dataset.json")
    with pytest.raises(FileNotFoundError):
        runner.load_dataset()
