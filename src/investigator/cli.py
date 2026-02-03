import typer
from investigator.store import EventStore
from investigator.agent import Investigator
from investigator.types import Budget
from investigator.tools.synthetic_oracle import SyntheticOracle

app = typer.Typer(add_completion=False)


@app.command("run")
def run_cmd(
    calls: int = typer.Option(20, help="Maximum number of tool calls."),
    seed: int = typer.Option(0, help="Random seed."),
    fail_prob: float = typer.Option(0.0, help="Per-candidate tool failure probability."),
    corrupt_prob: float = typer.Option(0.0, help="Per-candidate result corruption probability."),
    belief_decay: float = typer.Option(
        1.0,
        help="Exponential decay factor applied to beliefs each step (1.0 = no forgetting).",
    ),
    db: str = typer.Option("runs/events.db", help="SQLite event log path."),
):
    """
    Run a single closed-loop investigation.
    """
    store = EventStore(db)
    oracle = SyntheticOracle(
        seed=seed,
        fail_prob=fail_prob,
        corrupt_prob=corrupt_prob,
    )
    agent = Investigator(oracle=oracle, store=store)

    run_id = agent.run(
        budget=Budget(max_tool_calls=calls),
        constraints={
            "batch_size": 12,
            "top_k": 10,
            "stability_min": -1.2,
            "bandgap_min": 1.0,
            "bandgap_max": 2.0,
            "target_bandgap": 1.5,
            "belief_decay": belief_decay,
        },
        seed=seed,
    )

    typer.echo(f"run_id: {run_id}")


if __name__ == "__main__":
    app()


@app.command("show")
def show_cmd(
    run_id: str = typer.Argument(..., help="Run ID to display."),
    db: str = typer.Option("runs/events.db", help="SQLite event log path."),
):
    """
    Show the full event trace for a run.
    """
    store = EventStore(db)

    for ts, step, payload in store.load_run(run_id):
        typer.echo(f"{ts}  {step}")
        if step in ("HYPOTHESIS", "DESIGN"):
            typer.echo(f"  {str(payload)[:200]}...")
        elif step == "EXECUTE":
            results = payload.get("output", {}).get("results", {})
            ok = sum(1 for r in results.values() if r.get("ok"))
            bad = sum(1 for r in results.values() if not r.get("ok"))
            typer.echo(f"  tool={payload.get('tool')} ok={ok} bad={bad}")
        elif step == "INTERPRET":
            top = list(payload.get("updated_beliefs", {}).items())[:5]
            typer.echo(f"  top={top}")
        else:
            typer.echo(f"  {payload}")

@app.command("stats")
def stats_cmd(
    run_id: str = typer.Argument(..., help="Run ID to summarize."),
    db: str = typer.Option("runs/events.db", help="SQLite event log path."),
):
    """
    Print a concise quantitative summary of a run.
    """
    store = EventStore(db)
    events = list(store.load_run(run_id))

    # Count steps
    step_counts = {}
    for _, step, _ in events:
        step_counts[step] = step_counts.get(step, 0) + 1

    typer.echo("step counts:")
    for k, v in step_counts.items():
        typer.echo(f"  {k}: {v}")

    # Best scalar score seen
    best = None
    for _, step, payload in events:
        if step == "INTERPRET":
            beliefs = payload.get("updated_beliefs", {})
            if beliefs:
                local_best = max(float(v) for v in beliefs.values())
                best = local_best if best is None else max(best, local_best)

    typer.echo(f"best scalar score observed: {best}")
