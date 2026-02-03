#!/usr/bin/env python3
"""
Run a reliability grid for long-horizon investigator agents with adaptive repeats.

This script:
  - varies tool failure probability
  - varies tool corruption probability
  - varies belief decay (forgetting)
  - increases repetitions in high-variance regimes
  - records trajectory-level outcomes in a CSV

Usage:
  python experiments/run_reliability_grid.py
"""

import subprocess
import sqlite3
import time
import itertools
import csv
import sys
import json
from pathlib import Path

# --------------------------------------------------
# Paths
# --------------------------------------------------

DB_PATH = "runs/events.db"
OUT_CSV = "experiments/output/reliability_results.csv"

# --------------------------------------------------
# Experiment parameters
# --------------------------------------------------

CALLS = 300

FAIL_PROBS = [0.0, 0.02, 0.05, 0.1]
CORRUPT_PROBS = [0.0, 0.02, 0.05]
DECAYS = [1.0, 0.98]

# --------------------------------------------------
# Adaptive repetition policy
# --------------------------------------------------

def repeats_for(fail_prob, corrupt_prob):
    """
    Increase repeats where stochasticity is highest.
    """
    severity = fail_prob + corrupt_prob
    if severity < 0.03:
        return 10
    elif severity < 0.08:
        return 20
    else:
        return 30

# --------------------------------------------------
# Investigator invocation
# --------------------------------------------------

def run_investigator(calls, fail_prob, corrupt_prob, belief_decay):
    """
    Run the investigator using the current Python interpreter.
    If it fails, print stdout/stderr so we can see the real error.
    """
    cmd = [
        sys.executable,
        "-m",
        "investigator.cli",
        "--calls", str(calls),
        "--fail-prob", str(fail_prob),
        "--corrupt-prob", str(corrupt_prob),
        "--belief-decay", str(belief_decay),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Investigator failed!\n"
            f"CMD: {' '.join(cmd)}\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )

    for line in result.stdout.splitlines():
        if line.startswith("run_id:"):
            return line.split("run_id:")[1].strip()

    raise RuntimeError(
        f"Could not parse run_id.\nSTDOUT:\n{result.stdout}"
    )

# --------------------------------------------------
# Event log access
# --------------------------------------------------

def load_events(run_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT ts, step, payload FROM events WHERE run_id=? ORDER BY id ASC",
        (run_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows

# --------------------------------------------------
# Run summarization
# --------------------------------------------------

def summarize_run(run_id):
    """
    Compute trajectory-level metrics from the event log.
    """
    events = load_events(run_id)

    step_counts = {}
    best_score = None
    first_valid_step = None
    stagnation = 0
    max_stagnation = 0
    step_idx = 0

    for _, step, payload_json in events:
        step_counts[step] = step_counts.get(step, 0) + 1

        if step == "INTERPRET":
            payload = json.loads(payload_json)
            beliefs = payload.get("updated_beliefs", {})

            if beliefs:
                local_best = max(float(v) for v in beliefs.values())

                if best_score is None or local_best > best_score:
                    best_score = local_best
                    if first_valid_step is None:
                        first_valid_step = step_idx
                    stagnation = 0
                else:
                    stagnation += 1
                    max_stagnation = max(max_stagnation, stagnation)

        step_idx += 1

    termination = "unknown"
    for _, step, payload_json in reversed(events):
        if step == "UPDATE":
            termination = json.loads(payload_json).get("reason", "unknown")
            break

    return {
        "run_id": run_id,
        "best_score": best_score,
        "first_valid_step": first_valid_step,
        "max_stagnation": max_stagnation,
        "termination": termination,
        "total_steps": sum(step_counts.values()),
    }

# --------------------------------------------------
# Main experiment loop
# --------------------------------------------------

def main():
    Path("experiments").mkdir(exist_ok=True)

    results = []

    print("Starting reliability grid with adaptive repeats")

    for fail_prob, corrupt_prob, decay in itertools.product(
        FAIL_PROBS, CORRUPT_PROBS, DECAYS
    ):
        reps = repeats_for(fail_prob, corrupt_prob)

        print(
            f"\nCondition:"
            f" fail={fail_prob:.2f}"
            f" corrupt={corrupt_prob:.2f}"
            f" decay={decay:.2f}"
            f" → reps={reps}"
        )

        for rep in range(reps):
            print(f"  run {rep + 1}/{reps}")
            run_id = run_investigator(
                CALLS,
                fail_prob,
                corrupt_prob,
                decay,
            )

            # small pause to reduce SQLite contention
            time.sleep(0.2)

            summary = summarize_run(run_id)
            summary.update({
                "calls": CALLS,
                "fail_prob": fail_prob,
                "corrupt_prob": corrupt_prob,
                "belief_decay": decay,
                "rep": rep,
            })

            results.append(summary)

    # --------------------------------------------------
    # Write CSV
    # --------------------------------------------------

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\nCompleted {len(results)} runs")
    print(f"Wrote results to {OUT_CSV}")

# --------------------------------------------------

if __name__ == "__main__":
    main()
