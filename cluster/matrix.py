"""Create the 90-case matrix and optionally submit one Slurm job per case."""

import argparse
import csv
import itertools
import json
import math
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys


REPO = Path(__file__).resolve().parents[1]
TIERS = [(4, 1, "default"), (8, 1, "default"), (16, 1, "default"),
         (32, 2, "rdma-on"), (32, 2, "rdma-off")]
SOLVERS = ("opensees", "kratos", "fenicsx")


def cases():
    result = []
    for (ranks, nodes, network), solver, mode, repeat in itertools.product(
            TIERS, SOLVERS, ("minimal", "full"), range(1, 4)):
        name = f"{solver}-{ranks:02d}-{network}-{mode}-r{repeat}"
        result.append((name, solver, ranks, nodes, ranks // nodes, network, mode, repeat))
    random.Random(20261119).shuffle(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--submit", action="store_true", help="Submit all production repeats")
    action.add_argument("--pilot", choices=("elastic", "nonlinear", "transport"))
    parser.add_argument("--solver", choices=SOLVERS, help="Run only this solver in a pilot")
    parser.add_argument("--pilot-ranks", type=int, choices=(4, 8, 16), default=4)
    parser.add_argument("--pilot-transport", choices=("rdma-on", "rdma-off"))
    parser.add_argument("--pilot-output", choices=("minimal", "full"), default="full")
    parser.add_argument("--target", type=float, help="Gravity multiplier for nonlinear pilot")
    parser.add_argument("--pilot-first-factor", type=float, default=0.0,
                        help="First load factor in a nonlinear pilot, followed by equal steps")
    parser.add_argument("--steps", type=int, default=40, help="Number of steps in nonlinear pilot")
    parser.add_argument("--tolerance", type=float, default=0.1, help="Pilot residual tolerance, N")
    parser.add_argument("--max-iterations", type=int, default=35)
    parser.add_argument("--mesh", type=Path)
    parser.add_argument("--runs", type=Path)
    parser.add_argument("--site", type=Path, default=REPO / "cluster/site.sh")
    parser.add_argument("--calibration", type=Path)
    args = parser.parse_args()
    rows = cases()
    headers = ["case", "solver", "ranks", "nodes", "ranks_per_node", "transport", "output", "repeat"]
    if not (args.submit or args.pilot):
        writer = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)
        return

    if not all([args.mesh, args.runs, args.site.is_file()]):
        parser.error("submission requires --mesh, --runs and a verified --site")
    mesh, runs, site = args.mesh.resolve(), args.runs.resolve(), args.site.resolve()
    model = json.loads((mesh / "model.json").read_text())
    if args.submit:
        if not args.calibration:
            parser.error("--submit requires --calibration")
        calibration = json.loads(args.calibration.read_text())
        if (model["resolution"] != "production"
                or calibration["mesh_sha256"] != model["mesh_sha256"]):
            parser.error("calibration must match the production mesh")
        target = float(calibration["target"])
        steps = int(calibration["steps"])
        tolerance = float(calibration["residual_tolerance"])
        iterations = int(calibration["max_iterations"])
    else:
        if args.pilot == "nonlinear":
            if args.target is None:
                parser.error("--pilot nonlinear requires --target")
            target, steps = args.target, args.steps
        else:
            target, steps = 1.0, 2
        tolerance, iterations = args.tolerance, args.max_iterations
        pilot_tiers = {("default", args.pilot_ranks)} if args.pilot != "transport" else {
            ("rdma-on", 32), ("rdma-off", 32)
        }
        rows = [row for row in rows
                if (row[5], row[2]) in pilot_tiers and row[6:] == (args.pilot_output, 1)
                and (args.solver is None or row[1] == args.solver)
                and (args.pilot_transport is None or row[5] == args.pilot_transport)]
    first_factor = args.pilot_first_factor
    if first_factor and (args.pilot != "nonlinear" or steps < 2 or not 0 < first_factor < target):
        parser.error("--pilot-first-factor requires a nonlinear pilot and 0 < first factor < target")
    if not rows:
        parser.error("no cases match the pilot options")
    if not (math.isfinite(target) and target > 0 and steps > 0
            and math.isfinite(tolerance) and tolerance > 0 and iterations > 0):
        parser.error("load and convergence parameters must be finite and positive")
    def site_options(format_string):
        return subprocess.check_output(
            ["bash", "-c", f'source "$1"; {format_string}', "_", site],
        ).decode().split("\0")[:-1]

    time_setting = '"${pilot_time_limit:-$time_limit}"' if args.pilot else '"$time_limit"'
    time_limit, *node_args = site_options(
        f'printf "%s\\0" {time_setting} "${{new_node_args[@]}}"'
    )
    if not node_args:
        parser.error("site configuration must select Esmeralda's new nodes")
    pair_args = site_options(
        'for opt in "${rdma_pair_args[@]}"; do printf "%s\\0" "$opt"; done'
    )

    # Noninteractive login shells may omit the scheduler from PATH.
    slurm_path, = site_options('printf "%s\\0" "$PATH"')
    launch_env = {**os.environ, "PATH": slurm_path}

    runs.mkdir(parents=True, exist_ok=False)
    snapshot = runs / "inputs"
    for directory in ("cluster", "solvers", "model"):
        shutil.copytree(REPO / directory, snapshot / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "site.sh"))
    if args.submit:
        (runs / "calibration.json").write_text(args.calibration.read_text())
    else:
        (runs / "pilot.json").write_text(json.dumps({
            "kind": args.pilot, "target": target, "steps": steps, "first_factor": first_factor,
            "residual_tolerance": tolerance, "max_iterations": iterations,
            "mesh_sha256": model["mesh_sha256"],
        }, indent=2) + "\n")
    (runs / "site.sh").write_text(site.read_text())
    site = runs / "site.sh"
    with (runs / "submissions.tsv").open("w") as out:
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        writer.writerow([*headers, "slurm_job"])
        for row in rows:
            name, solver, ranks, nodes, per_node, network, mode, _ = row
            command = [
                "sbatch", "--parsable", f"--job-name={name}", f"--time={time_limit}",
                "--exclusive", "--hint=nomultithread", "--cpus-per-task=1",
                f"--nodes={nodes}", f"--ntasks={ranks}", f"--ntasks-per-node={per_node}",
                f"--output={runs}/slurm-%j.log", *node_args, *(pair_args if ranks == 32 else []),
                str(snapshot / "cluster/run.sbatch"),
                *map(str, [snapshot, site, mesh, runs / name, solver, ranks, network, mode,
                           target, steps, tolerance, iterations, first_factor]),
            ]
            print(shlex.join(command), flush=True)
            job = subprocess.check_output(command, text=True, env=launch_env).strip()
            writer.writerow([*row, job])
            out.flush()


if __name__ == "__main__":
    main()
