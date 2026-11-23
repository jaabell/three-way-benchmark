"""Run the matched coarse single-node benchmark on node12 after the memory fix."""

import argparse
import csv
import shlex

from replay_node13 import ROOT, RUNS, prepare_launchers, select_cases, submit, submit_suite


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", help="New directory name under runs/")
    args = parser.parse_args()
    campaign = RUNS / args.campaign
    if campaign.parent != RUNS or campaign.exists():
        parser.error("Choose an unused name directly under runs/")

    suite = "smoke-scaling"
    selected = select_cases(suite)
    launchers = prepare_launchers(campaign)
    mapping = campaign / "job-map.tsv"
    with mapping.open("w", buffering=1) as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("suite", "case", "original_job", "node12_job"))
        submit_suite(suite, selected, launchers, {}, writer, campaign=campaign,
                     target_host="node12", replay_all=True)

    with mapping.open() as handle:
        jobs = [row["node12_job"] for row in csv.DictReader(handle, delimiter="\t")]
    summary = shlex.join([
        "python3", str(ROOT / "tools/scaling_report.py"),
        str(campaign / "benchmark.md"), str(campaign / suite),
    ])
    compare = shlex.join(["python3", str(ROOT / "tools/node12_memory_report.py"), str(campaign)])
    report = submit(["--partition=new", "--nodes=1", "--ntasks=1", "--cpus-per-task=1",
                     "--mem=1G", "--time=00:05:00", "--job-name=node12-report",
                     f"--output={campaign}/report-%j.log", "--dependency=afterany:" + ":".join(jobs),
                     f"--wrap={summary} && {compare}"])
    print(f"Submitted {len(jobs)} node12 runs and report job {report}.", flush=True)


if __name__ == "__main__":
    main()
