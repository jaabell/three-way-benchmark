"""Rerun the validated node12-only repeats, pinned to Esmeralda node13."""

import csv
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
CAMPAIGN = RUNS / "node13-scaling"
SOFTWARE = Path("/mnt/covadongaflash/software")
SLURM = Path("/opt/slurm-24.11/bin")
SUITES = {"smoke-scaling": ("smoke", 28), "refinement-scaling": ("refinement", 27)}
RELEASES = (
    (Path("/mnt/nfshare/bin/openseesmp-ladruno"), "opensees-ladruno",
     "20261120-1400-1f08e5934", "OpenSeesMP"),
    (SOFTWARE / "bin/kratos-mpi-python", "kratos-mpi",
     "v10.3.0-20261120-100016", "env/bin/python"),
    (SOFTWARE / "bin/fenicsx-python", "fenicsx",
     "20261118-135244", "env/bin/python"),
)


def rows(path, delimiter):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def select_cases(suite):
    original = RUNS / suite
    cases = rows(original / "submissions.tsv", "\t")
    valid = {row["job"] for row in rows(original / "measurements.csv", ",")}
    if len(valid) != 90 or valid != {row["slurm_job"] for row in cases}:
        raise ValueError(f"{suite} is missing verified original jobs")
    selected = []
    for case in cases:
        if case["nodes"] != "1":
            continue
        old = original / case["case"]
        if not (old / "launcher-complete").is_file():
            raise ValueError(f"Incomplete original run {old}")
        host = (old / "nodelist").read_text().strip()
        if host not in ("node12", "node13"):
            raise ValueError(f"Unexpected single-node allocation {host}")
        selected.append((case, host))
    if len(selected) != 54 or sum(host == "node12" for _, host in selected) != SUITES[suite][1]:
        raise ValueError(f"Unexpected allocation count for {suite}")
    return selected


def pinned_wrappers():
    entries = {}
    for wrapper, tool, revision, executable in RELEASES:
        current = SOFTWARE / tool / "current"
        release = SOFTWARE / tool / "releases" / revision
        source = wrapper.read_text()
        if not (release / executable).is_file() or source.count(str(current)) != 1:
            raise ValueError(f"Could not pin {tool} to {release}")
        entries[wrapper] = source.replace(str(current), str(release))
    return entries


def submit(command):
    result = subprocess.check_output([str(SLURM / "sbatch"), "--parsable", *command], text=True)
    job = result.strip().split(";", 1)[0]
    if not job.isdecimal():
        raise ValueError(f"Unexpected submission response {result!r}")
    return job


def submit_suite(suite, selected, launchers, gates, replacements):
    original = RUNS / suite
    source = original / "inputs"
    mesh = ROOT / "build" / SUITES[suite][0]
    dest = CAMPAIGN / suite
    dest.mkdir()
    calibration = json.loads((original / "calibration.json").read_text())
    model = json.loads((mesh / "model.json").read_text())
    if model["mesh_sha256"] != calibration["mesh_sha256"]:
        raise ValueError(f"Archived calibration and mesh differ for {suite}")
    with (mesh / "mesh.npz").open("rb") as data:
        if hashlib.file_digest(data, "sha256").hexdigest() != calibration["mesh_sha256"]:
            raise ValueError(f"Mesh data have changed for {suite}")
    shutil.copyfile(original / "calibration.json", dest / "calibration.json")
    shutil.copyfile(mesh / "model.json", dest / "model.json")
    site = dest / "site.sh"
    code = (original / "site.sh").read_text()
    for before, after in launchers.items():
        if code.count(before) != 1:
            raise ValueError(f"Unexpected solver launcher in {suite}")
        code = code.replace(before, str(after))
    site.write_text(code + '\nunset BENCH_KRATOS_SOLVER BENCH_FENICSX_JAX BENCH_FENICSX_JAX_METHOD\n')

    with (dest / "submissions.tsv").open("w") as manifest:
        writer = csv.DictWriter(manifest, [*selected[0][0], "host"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for case, host in selected:
            name, solver, ranks = (case[k] for k in ("case", "solver", "ranks"))
            old = original / name
            if host == "node13":
                (dest / name).symlink_to(old, target_is_directory=True)
                writer.writerow({**case, "host": "node13"})
                continue
            cap, = re.findall(r"\bTimeLimit=(\S+)", (old / "allocation.txt").read_text())
            first = (old / "first_factor.txt").read_text().strip()
            dependency = [f"--dependency=afterok:{gates[solver]}", "--kill-on-invalid-dep=yes"] if solver in gates else []
            job = submit([
                "--partition=new", "--nodelist=node13", "--mem=54G", f"--time={cap}",
                "--exclusive", "--hint=nomultithread", "--nodes=1", "--cpus-per-task=1",
                f"--ntasks={ranks}", f"--ntasks-per-node={ranks}", f"--job-name=n13-{name}",
                f"--output={dest}/slurm-%j.log", "--export=ALL,BENCH_TRANSPORT_LAUNCHER=prrte",
                *dependency, str(source / "cluster/run.sbatch"),
                *map(str, (source, site, mesh, dest / name, solver, ranks, case["transport"],
                           case["output"], calibration["target"], calibration["steps"],
                           calibration["residual_tolerance"], calibration["max_iterations"], first)),
            ])
            gates.setdefault(solver, job)
            replacements.writerow((suite, name, case["slurm_job"], job))
            writer.writerow({**case, "slurm_job": job, "host": "node13"})
            manifest.flush()
            print(f"{suite}\t{name}\t{case['slurm_job']}\t{job}", flush=True)


def main():
    selected = {suite: select_cases(suite) for suite in SUITES}
    wrappers = pinned_wrappers()
    CAMPAIGN.mkdir(exist_ok=False)
    bin_dir = CAMPAIGN / "launchers"
    bin_dir.mkdir()
    launchers = {}
    for original, content in wrappers.items():
        launcher = bin_dir / original.name
        launcher.write_text(content)
        launcher.chmod(0o755)
        # The archived profiles refer either to an absolute wrapper or to the software/bin variable.
        key = str(original) if original.parent == Path("/mnt/nfshare/bin") else f"$software/{original.name}"
        launchers[key] = launcher
    with (CAMPAIGN / "replacements.tsv").open("w", buffering=1) as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("suite", "case", "original_job", "node13_job"))
        gates = {}
        for suite in SUITES:
            submit_suite(suite, selected[suite], launchers, gates, writer)
    jobs = [row["node13_job"] for row in rows(CAMPAIGN / "replacements.tsv", "\t")]
    command = shlex.join([
        "python3", str(ROOT / "tools/scaling_report.py"), str(CAMPAIGN / "benchmark.md"),
        *(str(CAMPAIGN / suite) for suite in SUITES),
    ])
    report = submit(["--partition=new", "--nodes=1", "--ntasks=1", "--cpus-per-task=1",
                     "--mem=1G", "--time=00:05:00", "--job-name=node13-report",
                     f"--output={CAMPAIGN}/report-%j.log", "--dependency=afterany:" + ":".join(jobs),
                     f"--wrap={command}"])
    print(f"Submitted {len(jobs)} replacements, first jobs {gates}, and report job {report}.")


if __name__ == "__main__":
    main()
