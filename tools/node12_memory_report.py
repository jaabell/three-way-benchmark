"""Compare validated coarse post-fix runs on node12 with the two archived baselines."""

import argparse
import math
from collections import defaultdict
from itertools import product
from pathlib import Path
from statistics import median

from scaling_report import SOLVERS
from summarize import csv_rows


def change(before, after, key):
    return 100 * (float(after[key]) / float(before[key]) - 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    args = parser.parse_args()
    campaign = args.campaign.resolve()
    before = campaign.parent / "smoke-scaling"
    comparison_host = campaign.parent / "node13-scaling" / "smoke-scaling"
    after = campaign / "smoke-scaling"
    node13 = {run["case"]: run for run in csv_rows(comparison_host / "measurements.csv")}
    original = {run["case"]: run for run in csv_rows(before / "measurements.csv") if run["ranks"] != "32"}
    reruns = csv_rows(after / "measurements.csv")
    if len(reruns) != 54 or {r["case"] for r in reruns} != original.keys() or node13.keys() != original.keys():
        raise ValueError("Expected 54 validated runs in each single-node comparison")
    if any((path / "calibration.json").read_bytes() != (before / "calibration.json").read_bytes()
           for path in (after, comparison_host)):
        raise ValueError("Calibration differs across the campaigns")

    settings = defaultdict(list)
    prior_node12 = defaultdict(list)
    tip_error = 0.0
    for run in reruns:
        case = run["case"]
        old, reference = original[case], node13[case]
        ranks = int(run["ranks"])
        settings[run["solver"], ranks, run["output"]].append((run, reference))
        for sample in (old, reference):
            tip_error = max(tip_error, abs(float(run["tip_uz_m"]) - float(sample["tip_uz_m"])))
            if (run["iterations"], run["bytes"]) != (sample["iterations"], sample["bytes"]) or not math.isclose(
                float(run["tip_uz_m"]), float(sample["tip_uz_m"]), abs_tol=1e-9, rel_tol=0
            ):
                raise ValueError(f"Physical result or output size mismatch for {case}")
        host = (before / case / "nodelist").read_text().strip()
        if host == "node12":
            prior_node12[run["solver"]].append((old, run))
        elif host != "node13":
            raise ValueError(f"Unexpected original host {host}")
    if sum(map(len, prior_node12.values())) != 28:
        raise ValueError("Expected 28 matched pre-fix node12 repeats")

    report = [
        "# Node12 memory fix verification · coarse mesh", "",
        "The rerun used 7,140 T10 elements, the original 30 gravity steps and pinned solver releases. "
        "All 54 runs validated on node12 with exclusive allocations, one physical core per MPI rank and three repeats per setting. "
        f"Newton iteration counts and field bytes matched the reference runs. The largest final tip difference was {tip_error * 1e9:.3f} nm.",
        "", "## Paired node12 before and after", "",
        "Changes are the median of the per-repeat percentage changes across matched cases. Negative means shorter time.",
        "", "| Solver | Matched repeats | Wall change | Solve change |",
        "| --- | ---: | ---: | ---: |",
    ]
    for solver, name in SOLVERS.items():
        pairs = prior_node12[solver]
        wall, solve = (median(change(old, new, key) for old, new in pairs) for key in ("wall_s", "solve_s"))
        report.append(f"| {name} | {len(pairs)} | {wall:+.1f}% | {solve:+.1f}% |")
    report.extend([
        "", "## Node12 after the fix vs. node13", "",
        "Launcher wall time is the median of three runs in seconds. The percentage gives node12 relative to node13 for that setting.",
        "", "| Solver | Ranks | Output | Node12 after (s) | Node13 (s) | Difference |",
        "| --- | ---: | --- | ---: | ---: | ---: |",
    ])
    for solver, ranks, output in product(SOLVERS, (4, 8, 16), ("minimal", "full")):
        pairs = settings[solver, ranks, output]
        if len(pairs) != 3:
            raise ValueError(f"Expected three repeats for {solver} {ranks} {output}")
        current, control = (median(float(pair[i]["wall_s"]) for pair in pairs) for i in (0, 1))
        report.append(f"| {SOLVERS[solver]} | {ranks} | {output} | {current:.3f} | {control:.3f} | {100 * (current / control - 1):+.1f}% |")
    report.extend(["", f"Esmeralda retained the raw outputs and job map under `runs/{campaign.name}/`.",
                   "Compute resources were provided by Esmeralda, associated with ANID–Fondecyt project 11220530."])
    (campaign / "comparison.md").write_text("\n".join(report) + "\n")


if __name__ == "__main__":
    main()
