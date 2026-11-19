"""Validate completed cases and report solver and output timings across repeats."""

import argparse
import csv
from collections import defaultdict
import math
from pathlib import Path
import statistics
import sys


def csv_rows(path, delimiter=","):
    with path.open(newline="") as source:
        return list(csv.DictReader(source, delimiter=delimiter))


def run_metrics(path, case):
    if not (path / "launcher-complete").is_file():
        raise ValueError("launcher incomplete")
    ranks = int(case["ranks"])
    _, nranks, transport, output, target, nsteps, job = (path / "case.tsv").read_text().strip().split("\t")
    if (nranks, transport, output) != tuple(case[key] for key in ("ranks", "transport", "output")):
        raise ValueError("run metadata differs from the submission")
    steps, target = int(nsteps), float(target)
    first_factor_path = path / "first_factor.txt"
    first_factor = float(first_factor_path.read_text()) if first_factor_path.exists() else 0.0
    rank_rows = [csv_rows(path / f"progress-{rank}.csv") for rank in range(ranks)]
    if any(len(rows) != steps for rows in rank_rows):
        raise ValueError("incomplete progress history")
    solve = fields = 0.0
    iterations = 0
    tip = float("nan")
    for step, rows in enumerate(zip(*rank_rows, strict=True), 1):
        expected = (first_factor + (target - first_factor) * (step - 1) / (steps - 1)
                    if first_factor else target * step / steps)
        if any(int(row["step"]) != step or not math.isclose(float(row["factor"]), expected)
               for row in rows):
            raise ValueError("inconsistent load steps")
        tips = [float(row["tip_uz_m"]) for row in rows if row["tip_uz_m"]]
        if not tips or any(not math.isclose(t, tips[0], rel_tol=1e-7, abs_tol=1e-9) for t in tips):
            raise ValueError("missing or inconsistent tip displacement")
        tip = tips[0]
        solve += max(float(row["solve_s"]) for row in rows)
        fields += max(float(row["output_s"]) for row in rows)
        iterations += max(int(row["iterations"]) for row in rows)
    size = 0
    if output == "full":
        for kind in ("nodes", "cells"):
            for rank in range(ranks):
                size += (path / f"{kind}-{rank}.bin").stat().st_size
    wall = float((path / "timing.tsv").read_text().split()[0])
    return {"case": case["case"], "job": job, "wall_s": wall, "solve_s": solve,
            "output_s": fields, "bytes": size, "iterations": iterations, "tip_uz_m": tip}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path)
    args = parser.parse_args()
    cases = csv_rows(args.runs / "submissions.tsv", "\t")
    groups = defaultdict(list)
    keys = ("solver", "ranks", "transport", "output")
    failure = False
    with (args.runs / "measurements.csv").open("w", newline="") as out:
        writer = csv.DictWriter(out, [*keys, "case", "job", "wall_s", "solve_s", "output_s", "bytes",
                                      "iterations", "tip_uz_m"])
        writer.writeheader()
        for case in cases:
            try:
                result = run_metrics(args.runs / case["case"], case)
            except (OSError, ValueError, KeyError, IndexError) as err:
                print(f"{case['case']}: {err}", file=sys.stderr)
                failure = True
                continue
            group = tuple(case[key] for key in keys)
            groups[group].append(result)
            writer.writerow({**dict(zip(keys, group)), **result})

    metrics = ("wall_s", "solve_s", "output_s", "bytes", "iterations", "tip_uz_m")
    writer = csv.writer(sys.stdout)
    writer.writerow([*keys, "valid_repeats", *(f"median_{m}" for m in metrics),
                     "min_wall_s", "max_wall_s"])
    for group, values in sorted(groups.items()):
        wall = [result["wall_s"] for result in values]
        writer.writerow([*group, len(values),
                         *(statistics.median(r[m] for r in values) for m in metrics),
                         min(wall), max(wall)])
    if failure:
        sys.exit(1)


if __name__ == "__main__":
    main()
