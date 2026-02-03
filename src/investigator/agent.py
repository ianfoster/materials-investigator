from __future__ import annotations

import uuid
import random
from typing import Dict, Any, List

from investigator.types import (
    Event,
    Hypothesis,
    TestDesign,
    Interpretation,
    Budget,
)
from investigator.store import EventStore


class Investigator:
    """
    Persistent investigator loop.

    The agent alternates between:
      HYPOTHESIS -> DESIGN -> EXECUTE -> INTERPRET

    and stops when either:
      - constraints are satisfied, or
      - the tool-call budget is exhausted.
    """

    def __init__(self, oracle, store: EventStore):
        self.oracle = oracle
        self.store = store

    def run(
        self,
        budget: Budget,
        constraints: Dict[str, Any],
        seed: int = 0,
    ) -> str:
        run_id = str(uuid.uuid4())
        rng = random.Random(seed)

        # Internal belief state:
        # candidate -> observed properties
        beliefs: Dict[str, Dict[str, float]] = {}

        step = 0

        while budget.tool_calls_used < budget.max_tool_calls:
            # -----------------------
            # HYPOTHESIS
            # -----------------------
            candidates = self._propose_candidates(
                n=constraints.get("batch_size", 12),
                rng=rng,
            )

            hypothesis = Hypothesis(
                statement="Some candidates satisfy stability and bandgap constraints.",
                candidates=candidates,
                assumptions=[
                    "Synthetic oracle provides noisy but informative measurements."
                ],
            )

            self.store.append(
                Event(
                    run_id=run_id,
                    step="HYPOTHESIS",
                    payload=hypothesis.model_dump(),
                )
            )

            # -----------------------
            # DESIGN
            # -----------------------
            prop = "stability" if step % 2 == 0 else "bandgap"

            design = TestDesign(
                hypothesis_id=hypothesis.id,
                test_type="query_property",
                target_property=prop,
                candidates=candidates,
                rationale=f"Measure {prop} to reduce uncertainty.",
            )

            self.store.append(
                Event(
                    run_id=run_id,
                    step="DESIGN",
                    payload=design.model_dump(),
                )
            )

            # -----------------------
            # EXECUTE
            # -----------------------
            budget.tool_calls_used += 1
            raw = self.oracle.query_property(candidates, prop)

            self.store.append(
                Event(
                    run_id=run_id,
                    step="EXECUTE",
                    payload={
                        "tool": "oracle.query_property",
                        "property": prop,
                        "results": raw,
                    },
                )
            )

            # -----------------------
            # INTERPRET
            # -----------------------
            results = raw.get("results", {})
            for c, r in results.items():
                if not r.get("ok"):
                    continue
                beliefs.setdefault(c, {})[prop] = float(r["value"])

            # Forgetting: exponential decay of old beliefs
            decay = constraints.get("belief_decay", 0.98)
            for rec in beliefs.values():
                for k in list(rec.keys()):
                    rec[k] *= decay

            # Compute scalar scores when possible
            scored: Dict[str, float] = {}
            target_bg = constraints.get("target_bandgap", 1.5)

            for c, rec in beliefs.items():
                if "stability" in rec and "bandgap" in rec:
                    scored[c] = rec["stability"] - abs(rec["bandgap"] - target_bg)

            interpretation = Interpretation(
                hypothesis_id=hypothesis.id,
                summary=f"Updated beliefs after measuring {prop}.",
                updated_beliefs=dict(
                    sorted(scored.items(), key=lambda kv: kv[1], reverse=True)[:10]
                ),
                uncertainty_notes=[
                    "Scalarization is heuristic.",
                    "Noise and failures may bias early measurements.",
                ],
            )

            self.store.append(
                Event(
                    run_id=run_id,
                    step="INTERPRET",
                    payload=interpretation.model_dump(),
                )
            )

            # -----------------------
            # STOP CHECK
            # -----------------------
            if self._meets_constraints(beliefs, constraints):
                self.store.append(
                    Event(
                        run_id=run_id,
                        step="UPDATE",
                        payload={
                            "status": "done",
                            "reason": "constraints_met",
                            "budget": budget.model_dump(),
                        },
                    )
                )
                return run_id

            step += 1

        # Budget exhausted
        self.store.append(
            Event(
                run_id=run_id,
                step="UPDATE",
                payload={
                    "status": "done",
                    "reason": "budget_exhausted",
                    "budget": budget.model_dump(),
                },
            )
        )

        return run_id

    def _propose_candidates(self, n: int, rng: random.Random) -> List[str]:
        """
        Minimal candidate generator.

        This stands in for:
          - chemical enumeration
          - generative models
          - structure libraries

        We keep it simple and deterministic.
        """
        elems = ["Li", "Na", "K", "Mg", "Al", "Si", "P", "S", "Cl", "O"]
        cands = []
        for _ in range(n):
            a, b, c = rng.sample(elems, 3)
            cands.append(f"{a}{rng.randint(1,3)}{b}{rng.randint(1,3)}{c}{rng.randint(1,6)}")
        return cands

    def _meets_constraints(
        self,
        beliefs: Dict[str, Dict[str, float]],
        constraints: Dict[str, Any],
    ) -> bool:
        stab_min = constraints.get("stability_min", -1.2)
        bg_min = constraints.get("bandgap_min", 1.0)
        bg_max = constraints.get("bandgap_max", 2.0)

        for rec in beliefs.values():
            if "stability" in rec and "bandgap" in rec:
                if (
                    rec["stability"] >= stab_min
                    and bg_min <= rec["bandgap"] <= bg_max
                ):
                    return True
        return False
