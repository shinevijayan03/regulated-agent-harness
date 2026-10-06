import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="harness",
    help="Enterprise Agent Harness CLI - Scaffolding, Evaluation & Runtime.",
    add_completion=False,
)
console = Console()


@app.command("init")
def init_agent(
    name: str = typer.Argument(..., help="Name of the new agent to scaffold"),
    directory: str | None = typer.Option(None, "--dir", "-d", help="Target output directory"),
) -> None:
    """Scaffold a production-grade, governed enterprise agent project in seconds."""
    target_dir = Path(directory or f"./{name}")
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "tools").mkdir(exist_ok=True)
    (target_dir / "tests").mkdir(exist_ok=True)

    agent_py = f"""\"\"\"Governed Enterprise Agent: {name}\"\"\"
import asyncio
from harness.core.types import HarnessState, AgentMessage, Role, RiskTier
from harness.core.orchestrator import HarnessOrchestrator
from harness.gateway.model import LiteLLMModelGateway
from harness.registry.tools import ToolRegistry, harness_tool
from harness.guardrails.hitl import HITLGateInterceptor
from harness.guardrails.input_guard import InputGuardInterceptor
from harness.middleware.pipeline import MiddlewarePipeline

registry = ToolRegistry()

@harness_tool(name="health_query", risk_tier=RiskTier.READ_ONLY, registry=registry)
async def health_query(param: str) -> dict:
    return {{"status": "ok", "param": param}}

gateway = LiteLLMModelGateway(primary_model="azure/gpt-4o")
middleware = MiddlewarePipeline([InputGuardInterceptor(), HITLGateInterceptor(registry)])
orchestrator = HarnessOrchestrator(gateway=gateway, tools=registry, middleware=middleware)

async def main():
    state = HarnessState(session_id="session-001", messages=[AgentMessage(role=Role.USER, content="Hello")])
    final_state = await orchestrator.run(state)
    print(final_state.messages[-1].content)

if __name__ == "__main__":
    asyncio.run(main())
"""
    with open(target_dir / "agent.py", "w", encoding="utf-8") as f:
        f.write(agent_py)

    env_content = """# Enterprise Agent Harness Environment Variables
PRIMARY_MODEL=azure/gpt-4o
FALLBACK_MODELS=bedrock/anthropic.claude-3-5-sonnet
CHECKPOINTER_TYPE=sqlite
DATABASE_URL=sqlite+aiosqlite:///./.harness_checkpoints.db
LANGFUSE_HOST=http://localhost:3000
MAX_SESSION_COST_USD=0.50
MAX_ITERATIONS=10
"""
    with open(target_dir / ".env.example", "w", encoding="utf-8") as f:
        f.write(env_content)

    console.print(
        f"[bold green]✓[/bold green] Agent [bold cyan]{name}[/bold cyan] scaffolded successfully at [underline]{target_dir}[/underline]!"
    )
    console.print("Next steps:")
    console.print(f"  cd {target_dir}")
    console.print("  cp .env.example .env")
    console.print("  harness run")


@app.command("run")
def run_server(
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Server host"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Auto reload"),
) -> None:
    """Launch the FastAPI Agent Harness runtime server."""
    import uvicorn

    console.print(
        f"[bold green]Starting Enterprise Agent Harness on http://{host}:{port}[/bold green]"
    )
    uvicorn.run("harness.server.app:app", host=host, port=port, reload=reload)


@app.command("eval")
def run_eval(
    dataset: str = typer.Option(
        "tests/fixtures/sample_dataset.json", "--dataset", help="Path to golden eval dataset"
    ),
    min_fidelity: float = typer.Option(
        0.95, "--min-fidelity", help="Minimum required tool fidelity score"
    ),
    min_faithfulness: float = typer.Option(
        0.85, "--min-faithfulness", help="Minimum required faithfulness score"
    ),
) -> None:
    """Execute pre-flight synthetic evaluation quality gates."""
    from harness.eval.runner import SyntheticEvalRunner

    runner = SyntheticEvalRunner(
        dataset_path=dataset,
        min_fidelity=min_fidelity,
        min_faithfulness=min_faithfulness,
    )

    results = asyncio.run(runner.run_evaluation())

    table = Table(title="Pre-Flight Synthetic Evaluation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Score", style="magenta")
    table.add_column("Threshold", style="yellow")
    table.add_column("Status", style="bold")

    fidelity_status = (
        "[green]PASSED[/green]" if results["avg_fidelity"] >= min_fidelity else "[red]FAILED[/red]"
    )
    faithfulness_status = (
        "[green]PASSED[/green]"
        if results["avg_faithfulness"] >= min_faithfulness
        else "[red]FAILED[/red]"
    )

    table.add_row(
        "Tool Call Fidelity",
        f"{results['avg_fidelity']:.3f}",
        f"{min_fidelity:.3f}",
        fidelity_status,
    )
    table.add_row(
        "Faithfulness (Ragas)",
        f"{results['avg_faithfulness']:.3f}",
        f"{min_faithfulness:.3f}",
        faithfulness_status,
    )

    console.print(table)

    if results["passed_quality_gate"]:
        console.print(
            "[bold green]QUALITY GATE PASSED: Ready for production deployment.[/bold green]"
        )
    else:
        console.print(
            "[bold red]QUALITY GATE FAILED: Scores below enterprise thresholds.[/bold red]"
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
