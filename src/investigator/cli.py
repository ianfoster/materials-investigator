import typer
from .agent import Investigator
from .store import EventStore
from .types import Budget
from .tools.synthetic_oracle import SyntheticOracle

app = typer.Typer()

@app.command()
def run(calls: int = 20):
    store = EventStore("runs/events.db")
    oracle = SyntheticOracle()
    agent = Investigator(oracle, store)
    run_id = agent.run(Budget(max_tool_calls=calls))
    print("run_id:", run_id)
