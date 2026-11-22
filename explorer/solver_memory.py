"""Convert Slurm solver-step accounting and the validated run lists to browser JSON."""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from timing_assets import comparison, rows


def kib_value(value):
    if not value:
        return None
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([KMGT]?)", value)
    if not match:
        raise ValueError(f"Unrecognized Slurm memory value {value!r}")
    amount = float(match[1])
    factor = {"": 1, "K": 1, "M": 1024, "G": 1024**2, "T": 1024**3}[match[2]]
    return int(round(amount * factor)) if amount else None


def accounting():
    steps, hosts = {}, {}
    for job, name, state, tasks, rss, usage, nodes in csv.reader(sys.stdin, delimiter="|"):
        if job.isdecimal() and state == "COMPLETED":
            hosts[job] = nodes
        # run.sbatch launches inventory and binding as steps .0 and .1.
        if job.endswith(".2") and name == "bash" and state == "COMPLETED":
            resources = dict(pair.split("=", 1) for pair in usage.split(",") if "=" in pair)
            steps[job[:-2]] = int(tasks), kib_value(rss), kib_value(resources.get("gres/gpumem", ""))
    return steps, hosts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path)
    args = parser.parse_args()
    steps, hosts = accounting()
    cpu = []
    for row in comparison(args.reports, "measurements"):
        job = row["job"]
        single_node = row["ranks"] != "32"
        expected = "node13" if single_node else "node[12-13]"
        if hosts.get(job) != expected:
            raise ValueError(f"Expected {expected} for job {job}, found {hosts.get(job)}")
        task_count, host, _ = steps.get(job, (0, None, None))
        # PRRTE records the runtime launcher, so exclude those samples from rank RSS.
        direct_step = single_node and task_count == int(row["ranks"])
        cpu.append({"mesh": "coarse" if row["mesh"] == "smoke" else "fine",
                    "solver": row["solver"], "ranks": int(row["ranks"]), "hosts": row["hosts"],
                    "transport": row["transport"], "output": row["output"],
                    "repeat": int(row["case"].rsplit("-r", 1)[1]), "job": int(job),
                    "hostKiB": host if direct_step else None})
    gpu = []
    for row in rows(args.reports / "gpu-pilot-timings.csv"):
        job = row["job"]
        task_count, host, device = steps.get(job, (0, None, None))
        if task_count != 1:
            host = device = None
        gpu.append({"case": row["profile"], "solver": row["backend"], "job": int(job),
                    "hostKiB": host, "deviceKiB": device if row["backend"].startswith("cuda-") else None})
    if len(cpu) != 180 or len(gpu) != 18 or not any(r["hostKiB"] for r in cpu):
        raise ValueError("Missing Slurm records or validated case lists")
    json.dump({"cpu": cpu, "gpu": gpu}, sys.stdout, separators=(",", ":"))
    print()


if __name__ == "__main__":
    main()
