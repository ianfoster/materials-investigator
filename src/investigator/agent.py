import uuid
from .types import *
from .store import EventStore
from .tools.synthetic_oracle import SyntheticOracle

class Investigator:
    def __init__(self, oracle, store: EventStore):
        self.oracle = oracle
        self.store = store

    def run(self, budget: Budget):
        run_id = str(uuid.uuid4())
        step = 0
        while budget.tool_calls_used < budget.max_tool_calls:
            cands = [f"C{step}_{i}" for i in range(5)]
            h = Hypothesis(statement="Test hypothesis", candidates=cands)
            self.store.append(Event(run_id=run_id, step="HYPOTHESIS", payload=h.model_dump()))

            prop = "stability"
            raw = self.oracle.query_property(cands, prop)
            budget.tool_calls_used += 1

            tc = ToolCall(tool="oracle", input={"prop":prop}, output=raw, ok=True)
            self.store.append(Event(run_id=run_id, step="EXECUTE", payload=tc.model_dump()))

            step += 1
        return run_id
