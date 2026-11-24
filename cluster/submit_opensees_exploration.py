"""Submit matched OpenSeesMP exploration repeats to one Esmeralda host."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from replay_node13 import ROOT, submit


CORE = [
    ("j2", "mumps", "newton", "minimal", 0),
    ("asd", "mumps", "newton", "minimal", 0),
    ("j2", "mumps", "newton", "tcl", 0),
    ("asd", "mumps", "newton", "tcl", 0),
    ("j2", "mumps", "newton", "ladruno", 0),
    ("asd", "mumps", "newton", "ladruno", 0),
    ("asd", "mumps", "newton", "ladruno", 10),
    ("asd", "mumps-sym", "newton", "minimal", 0),
    ("asd", "mumps-amd", "newton", "minimal", 0),
]
OPTIONAL = {
    "profile": ("asd", "profile-spd", "newton", "minimal", 0),
    "krylov": ("asd", "mumps", "krylov", "minimal", 0),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("suite", choices=("core", *OPTIONAL, "combined", "fine", "fine-sym"))
    parser.add_argument("--host", default="node13", choices=("node12", "node13"))
    args = parser.parse_args()
    campaign = args.campaign.resolve()
    mesh, ranks, repeats = "smoke", 8, 3
    if args.suite in ("fine", "fine-sym"):
        mesh, ranks, repeats = "refinement", 16, 1
        cases = [CORE[0], CORE[1]] if args.suite == "fine" else [CORE[7]]
    elif args.suite == "combined":
        cases = [("asd", "mumps-sym", "newton", output, 0) for output in ("tcl", "ladruno")]
    else:
        cases = CORE if args.suite == "core" else [OPTIONAL[args.suite]]
    calibration = json.loads((ROOT / "cluster" / f"{mesh}-scaling.json").read_text())
    mesh_path = ROOT / "build" / mesh / "mesh.npz"
    if hashlib.sha256(mesh_path.read_bytes()).hexdigest() != calibration["mesh_sha256"]:
        raise ValueError("Unexpected mesh checksum")
    with (campaign / f"{args.suite}-jobs.tsv").open("x", buffering=1) as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("case", "job", "host", "ranks", "mesh", "material", "system",
                         "algorithm", "output", "flush", "target", "steps", "repeat"))
        for repeat in range(1, repeats + 1):
            for material, system, algorithm, output, flush in cases:
                case = f"{mesh}-{material}-{system}-{algorithm}-{output}-f{flush}-r{repeat}"
                options = (mesh, material, system, algorithm, output, flush,
                           calibration["target"], calibration["steps"])
                job = submit([
                    "-p", "new", "-w", args.host, "-N1", f"-n{ranks}", f"--ntasks-per-node={ranks}",
                    "-c1", "--hint=nomultithread", "--exclusive", "--mem=54G", "-t", "00:10:00",
                    f"--job-name=os-{case}", f"--output={campaign}/slurm-%j.log",
                    str(campaign / "inputs/opensees-explore.sbatch"), str(ROOT), str(campaign), case,
                    *map(str, options),
                ])
                writer.writerow((case, job, args.host, ranks, *options, repeat))
                print(f"{job}\t{case}", flush=True)


if __name__ == "__main__":
    main()
