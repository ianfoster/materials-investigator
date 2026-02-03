#!/usr/bin/env python3
"""
Plot reliability experiment results with belief decay comparison.

Usage:
  python experiments/plot_reliability.py
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

CSV = "experiments/output/reliability_results.csv"
OUT = Path("experiments/output/figures")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV)

# Ensure consistent ordering
df = df.sort_values(by=["belief_decay", "fail_prob", "corrupt_prob"])

# -------------------------------------------------
# Helper: plot grouped means with shaded confidence intervals
# -------------------------------------------------

def plot_metric(metric, ylabel, filename):
    plt.figure(figsize=(8, 5))

    for decay in sorted(df["belief_decay"].unique()):
        sub_d = df[df["belief_decay"] == decay]

        for corrupt in [0.0, 0.05]:  # Only plot corrupt=0 and 0.05
            sub = sub_d[sub_d["corrupt_prob"] == corrupt]
            grp = sub.groupby("fail_prob")[metric]
            means = grp.mean()
            stds = grp.std()

            label = f"decay={decay}, corrupt={corrupt}"
            line, = plt.plot(
                means.index,
                means.values,
                marker="o",
                label=label,
            )
            # Shaded region for ±1 std deviation
            plt.fill_between(
                means.index,
                means.values - stds.values,
                means.values + stds.values,
                alpha=0.2,
                color=line.get_color(),
            )

    plt.xlabel("Tool failure probability")
    plt.ylabel(ylabel)
    plt.legend(fontsize=8, loc="best")

    # Set consistent y-axis ranges for each metric
    if "first_valid" in filename:
        plt.ylim(145, 180)

    plt.tight_layout()
    plt.savefig(OUT / filename, dpi=150)
    plt.close()


# -------------------------------------------------
# Figure 1: Best score vs failure probability
# -------------------------------------------------

plot_metric(
    metric="best_score",
    ylabel="Mean best score achieved",
    filename="best_score_vs_fail_prob.png",
)

# -------------------------------------------------
# Figure 2: Time to first valid candidate
# -------------------------------------------------

plot_metric(
    metric="first_valid_step",
    ylabel="Mean step of first valid candidate",
    filename="time_to_first_valid.png",
)

# -------------------------------------------------
# Figure 3: Maximum stagnation length
# -------------------------------------------------

plot_metric(
    metric="max_stagnation",
    ylabel="Mean maximum stagnation length",
    filename="stagnation_vs_fail_prob.png",
)

print(f"Wrote figures to {OUT}/")
