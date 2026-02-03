import random
from typing import Dict, Any, List


class SyntheticOracle:
    """
    Synthetic, noisy, and optionally faulty 'materials world'.

    This plays the role of:
      - a simulator
      - a DFT service
      - an experimental instrument

    Parameters
    ----------
    seed : int
        Base random seed for reproducibility.
    fail_prob : float
        Probability that a candidate query fails outright.
    corrupt_prob : float
        Probability that a returned value is corrupted by noise.
    """

    def __init__(
        self,
        seed: int = 0,
        fail_prob: float = 0.0,
        corrupt_prob: float = 0.0,
    ):
        self.seed = seed
        self.fail_prob = fail_prob
        self.corrupt_prob = corrupt_prob

    def _rng_for_candidate(self, candidate: str) -> random.Random:
        """
        Deterministic per-candidate RNG so runs are replayable.
        """
        h = hash((self.seed, candidate)) & 0xFFFFFFFF
        return random.Random(h)

    def query_property(self, candidates: List[str], prop: str) -> Dict[str, Any]:
        """
        Query a synthetic property for a list of candidates.

        Returns a dict of the form:
        {
          "property": prop,
          "results": {
              candidate: {"ok": bool, "value": float} or {"ok": False, "error": str}
          }
        }
        """
        results: Dict[str, Any] = {}

        for c in candidates:
            rng = self._rng_for_candidate(c)

            # Hard failure
            if rng.random() < self.fail_prob:
                results[c] = {"ok": False, "error": "synthetic_failure"}
                continue

            # Base synthetic value (property-dependent but simple)
            base = rng.uniform(-1.0, 1.0)

            if prop == "stability":
                value = base
            elif prop == "bandgap":
                value = abs(base) * 2.5
            else:
                results[c] = {"ok": False, "error": f"unknown_property:{prop}"}
                continue

            # Corruption / noise injection
            if rng.random() < self.corrupt_prob:
                value += rng.gauss(0.0, 0.75)

            results[c] = {"ok": True, "value": float(value)}

        return {"property": prop, "results": results}
