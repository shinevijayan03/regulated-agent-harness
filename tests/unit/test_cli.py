from pathlib import Path

from typer.testing import CliRunner

from harness.cli.main import app

runner = CliRunner()


def test_cli_init_command(tmp_path: Path) -> None:
    """Verify harness init scaffolds project layout and files."""
    agent_dir = tmp_path / "test-agent"
    result = runner.invoke(app, ["init", "test-agent", "--dir", str(agent_dir)])
    assert result.exit_code == 0
    assert "scaffolded successfully" in result.output
    assert (agent_dir / "agent.py").exists()
    assert (agent_dir / ".env.example").exists()
    assert (agent_dir / "tools").is_dir()
    assert (agent_dir / "tests").is_dir()


def test_cli_eval_command() -> None:
    """Verify harness eval runs against sample dataset."""
    result = runner.invoke(
        app,
        [
            "eval",
            "--dataset",
            "tests/fixtures/sample_dataset.json",
            "--min-fidelity",
            "0.90",
            "--min-faithfulness",
            "0.80",
        ],
    )
    assert result.exit_code == 0
    assert "QUALITY GATE PASSED" in result.output
