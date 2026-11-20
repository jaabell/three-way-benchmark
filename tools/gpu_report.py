"""Reduce same-host MUMPS and RTX 5090 sparse QR beam pilots."""

import argparse
import csv
from pathlib import Path
import re
from statistics import median

from summarize import csv_rows, run_metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    measurements = []
    histories = {}
    incomplete = []
    for line in (args.suite / "pilots.tsv").read_text().splitlines():
        name, backend, job = line.split("\t")
        profile = name.rsplit(f"-{backend}-", 1)[0]
        run = args.suite / name
        if not (run / "launcher-complete").is_file():
            incomplete.append(job)
            continue
        _, _, _, mode, _, _, _ = (run / "case.tsv").read_text().strip().split("\t")
        case = {"case": name, "solver": "fenicsx", "ranks": "1", "transport": "default",
                "output": mode, "slurm_job": job}
        result = run_metrics(run, case)
        cuda_times = []
        if backend.startswith("cuda-"):
            method = backend.removeprefix("cuda-")
            log = (run / "solver.log").read_text()
            cuda_times = re.findall(rf"^cuda_{method}_s=([0-9.]+) ", log, re.MULTILINE)
            if f"sparse {method.upper()} on NVIDIA" not in log or len(cuda_times) != result["iterations"]:
                raise ValueError(f"CUDA timing records do not match Newton iterations in job {job}")
        histories[name] = {float(row["factor"]): float(row["tip_uz_m"])
                           for row in csv_rows(run / "progress-0.csv")}
        measurements.append({"profile": profile, "backend": backend, **result,
                             "cuda_phase_s": sum(map(float, cuda_times)) if cuda_times else None})

    report = ["# Same-host CPU and GPU beam pilots", "",
              "Median seconds and downward tip displacement over completed repeats.", "",
              "| Profile | Linear backend | Repeats | Wall (s) | Solve (s) | "
              "Field output (s) | CUDA phase (s) | Tip down (mm) |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for profile in sorted({row["profile"] for row in measurements}):
        backends = sorted({row["backend"] for row in measurements if row["profile"] == profile})
        for backend in reversed(backends):
            rows = [row for row in measurements if row["profile"] == profile and row["backend"] == backend]
            if rows:
                values = [median(row[key] for row in rows)
                          for key in ("wall_s", "solve_s", "output_s", "tip_uz_m")]
                cuda = (f"{median(row['cuda_phase_s'] for row in rows):.3f}"
                        if backend.startswith("cuda-") else "—")
                report.append(f"| {profile} | {rows[0]['backend']} | {len(rows)}/3 | "
                              f"{values[0]:.3f} | {values[1]:.3f} | {values[2]:.3f} | "
                              f"{cuda} | {-values[3] * 1e3:.9f} |")

    report.extend(["", "| Profile | Largest CPU–GPU tip difference across accepted steps |",
                   "| --- | ---: |"])
    for profile in sorted({row["profile"] for row in measurements}):
        cpu = [histories[row["case"]] for row in measurements
               if row["profile"] == profile and row["backend"] == "mumps"]
        gpu = [histories[row["case"]] for row in measurements
               if row["profile"] == profile and row["backend"].startswith("cuda-")]
        if cpu and gpu:
            if any(a.keys() != b.keys() for a in cpu for b in gpu):
                raise ValueError(f"CPU and GPU used different load steps for {profile}")
            difference = max(abs(a[step] - b[step])
                             for a in cpu for b in gpu for step in a)
            report.append(f"| {profile} | {difference * 1e6:.6f} µm |")
    if incomplete:
        report.extend(["", "Jobs without an accepted history. " + ", ".join(incomplete) + "."])
    args.report.write_text("\n".join(report) + "\n")
    if measurements:
        with args.report.with_suffix(".csv").open("w", newline="") as out:
            writer = csv.DictWriter(out, list(measurements[0]))
            writer.writeheader()
            writer.writerows(measurements)


if __name__ == "__main__":
    main()
