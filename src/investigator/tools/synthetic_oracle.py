import random

class SyntheticOracle:
    def query_property(self, candidates, prop):
        return {c: random.random() for c in candidates}
