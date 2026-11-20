"""Write the rank-by-rank timing table and representative force–displacement histories."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

from summarize import csv_rows


SOLVERS = {"opensees": "OpenSeesMP", "kratos": "Kratos MUMPS", "fenicsx": "FEniCSx"}
RANKS = (("4", "default"), ("8", "default"), ("16", "default"),
         ("32", "rdma-on"), ("32", "rdma-off"))
TRANSPORTS = {"default": "Single node", "rdma-on": "RoCE", "rdma-off": "TCP"}


def summarize_suite(suite, report, through_factor):
    with (suite / "summary.csv").open("w") as summary, (suite / "validation.log").open("w") as log:
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("summarize.py")),
                                 str(suite), "--through-factor", str(through_factor)],
                                stdout=summary, stderr=log)
    expected = len(csv_rows(suite / "submissions.tsv", "\t"))
    measurements = csv_rows(suite / "measurements.csv")
    if result.returncode and result.returncode != 1:
        result.check_returncode()
    groups = {(row["solver"], row["ranks"], row["transport"], row["output"]): row
              for row in csv_rows(suite / "summary.csv")}
    labels = [f"{name} {output}" for name in SOLVERS.values() for output in ("minimal", "full")]
    report.extend([f"## {suite.name.replace('-scaling', '').capitalize()}", "",
                   f"{len(measurements)}/{expected} runs validated.", "",
                   "| MPI ranks | Network | " + " | ".join(labels) + " |",
                   "| ---: | --- |" + " ---: |" * len(labels)])
    for ranks, transport in RANKS:
        times = []
        for solver in SOLVERS:
            for output in ("minimal", "full"):
                row = groups.get((solver, ranks, transport, output))
                times.append(f"{float(row['median_wall_s']):.2f} ({row['valid_repeats']}/3)"
                             if row else "—")
        report.append(f"| {ranks} | {TRANSPORTS[transport]} | " + " | ".join(times) + " |")
    report.append("")
    curves = []
    for solver, name in SOLVERS.items():
        choices = [row for row in measurements if row["solver"] == solver and row["output"] == "full"]
        if not choices:
            continue
        case = min(choices, key=lambda row: (row["ranks"] != "16", row["case"]))
        tips = {}
        for rank in range(int(case["ranks"])):
            for row in csv_rows(suite / case["case"] / f"progress-{rank}.csv"):
                if row["tip_uz_m"]:
                    tips[int(row["step"])] = (row["factor"], row["tip_uz_m"])
        path = suite / f"{solver}-representative-tip.csv"
        with path.open("w", newline="") as out:
            writer = csv.writer(out)
            writer.writerow(("factor", "tip_uz_m"))
            writer.writerows(tips[step] for step in sorted(tips))
        curves.append(f"{name} · {suite.name.replace('-scaling', '')}={path}")
        report.append(f"- {name} history from job {case['job']} ({case['ranks']} ranks).")
    report.append("")
    return curves


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("suites", nargs="+", type=Path)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    through_factor = min(float(json.loads((suite / "calibration.json").read_text())["target"])
                         for suite in args.suites)
    report = ["# Esmeralda rank scaling", "",
              "Values are median launcher wall-clock seconds across validated repeats. "
              "Parentheses show how many of the three repeats contributed.",
              f"The CSVs also report solve and output times through {through_factor:g}× gravity.", ""]
    curves = []
    for suite in args.suites:
        curves.extend(summarize_suite(suite, report, through_factor))
    if args.plot and curves:
        tools = Path(__file__).resolve().parent
        prefix = args.output.parent / "force-displacement"
        subprocess.run([sys.executable, str(tools / "force_displacement.py"),
                        str(tools.parent / "model" / "beam.json"), str(prefix), *curves], check=True)
        theory = json.loads(prefix.with_name("force-displacement-reference.json").read_text())
        report.extend(["## Force–displacement", "",
                       "The pure-bending reference reaches its plastic limit at "
                       f"{theory['plastic_force_N'] / 1e3:.2f} kN "
                       f"({theory['plastic_multiplier']:.3f}× gravity).", "",
                       "![Applied weight versus downward tip displacement](force-displacement.png)", "",
                       "[Curve data](force-displacement.csv)", ""])
    args.output.write_text("\n".join(report).rstrip() + "\n")


if __name__ == "__main__":
    main()
