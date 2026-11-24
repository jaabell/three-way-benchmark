"""Validate the separate OpenSeesMP campaign and produce its Markdown report."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import median

import h5py
import numpy as np

from summarize import csv_rows


OPTIONS = ("job", "host", "ranks", "mesh", "material", "system", "algorithm", "output",
           "flush", "target", "steps")
GROUP = ("mesh", "host", "ranks", "material", "system", "algorithm", "output", "flush")
NODE = np.dtype([("step", "<i4"), ("id", "<i4"), ("value", "<f8", 3)])
CELL = np.dtype([("step", "<i4"), ("id", "<i4"), ("point", "<i4"),
                 ("stresses", "<f8", 6), ("strains", "<f8", 6)])


def compare_recorder(native, tcl, steps, ranks):
    """Compare every saved value after matching IDs and translating units."""
    errors = np.zeros(3)
    for rank in range(ranks):
        with h5py.File(native / f"fields.part-{rank}.ladruno") as file:
            fields = file["MODEL_STAGE[1]/RESULTS"]
            for i, field in enumerate(("displacement", "stresses", "strains")):
                if field == "displacement":
                    data = fields["ON_NODES/DISPLACEMENT"]
                    saved = np.fromfile(tcl / f"nodes-{rank}.bin", NODE).reshape(steps, -1)
                    ids, values = saved["id"][0], saved["value"]
                    actual = data["DATA"][:]
                else:
                    data, = fields[f"ON_ELEMENTS/{field}"].values()
                    saved = np.fromfile(tcl / f"cells-{rank}.bin", CELL).reshape(steps, -1, 4)
                    ids, values = saved["id"][0, :, 0], saved[field]
                    assert np.array_equal(saved["point"][0, 0], np.arange(1, 5))
                    actual = data["DATA"][:].reshape(steps, -1, 4, 6)
                    if field == "stresses":
                        actual *= 1e6  # MPa to Pa
                    else:
                        actual[..., 3:] *= 0.5  # engineering shear to tensor shear
                order, native_order = np.argsort(ids), np.argsort(data["ID"][:, 0])
                assert np.array_equal(ids[order], data["ID"][:, 0][native_order])
                assert np.allclose(data["TIME"][:], np.arange(1, steps + 1))
                actual, values = actual[:, native_order], values[:, order]
                errors[i] = max(errors[i], np.max(np.abs(actual - values)))
                # Independent MPI repeats can differ slightly in reduction order.
                assert np.isfinite(actual).all() and np.isfinite(values).all()
                assert errors[i] <= (1e-10, 0.05, 1e-10)[i]
    return errors


def compare_materials(campaign, tcl_cases, ranks):
    errors = np.zeros(2)
    for rank in range(ranks):
        j2, asd = (np.fromfile(campaign / case / f"cells-{rank}.bin", CELL) for case in tcl_cases)
        assert all(np.array_equal(j2[key], asd[key]) for key in ("id", "step", "point"))
        for i, field in enumerate(("stresses", "strains")):
            errors[i] = max(errors[i], np.max(np.abs(j2[field] - asd[field])))
    assert errors[0] < 1e4 and errors[1] < 1e-6
    return errors


def read_run(path, meta):
    ranks, steps = (int(meta[key]) for key in ("ranks", "steps"))
    progress = [csv_rows(path / f"progress-{rank}.csv") for rank in range(ranks)]
    assert all(len(rows) == steps for rows in progress)
    tips, solve, output, iterations = [], 0.0, 0.0, 0
    for step, rows in enumerate(zip(*progress, strict=True), 1):
        assert {int(row["step"]) for row in rows} == {step}
        assert all(np.isclose(float(row["factor"]), step * float(meta["target"]) / steps) for row in rows)
        values = [float(row["tip_uz_m"]) for row in rows if row["tip_uz_m"]]
        assert values and np.isfinite(values).all() and np.ptp(values) < 1e-9
        tips.append(-1000 * values[0])
        iterations += max(int(row["iterations"]) for row in rows)
        solve += max(float(row["solve_s"]) for row in rows)
        output += max(float(row["output_s"]) for row in rows)
    files = {
        "minimal": [],
        "tcl": [*path.glob("nodes-*.bin"), *path.glob("cells-*.bin")],
        "ladruno": list(path.glob("fields.part-*.ladruno")),
    }[meta["output"]]
    assert len(files) == {"minimal": 0, "tcl": 2 * ranks, "ladruno": ranks}[meta["output"]]
    close = max((float(p.read_text()) for p in path.glob("close-*.txt")), default=0.0)
    return dict(wall_s=float((path / "wall.txt").read_text()), analyze_s=solve, tcl_s=output,
                close_s=close, bytes=sum(p.stat().st_size for p in files), iterations=iterations,
                tip_mm=tips[-1]), np.array(tips)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    args = parser.parse_args()
    campaign = args.campaign
    submitted = {run["case"]: run for manifest in campaign.glob("*-jobs.tsv")
                 for run in csv_rows(manifest, "\t")}
    data, histories, probes = [], {}, []
    for directory in sorted(p.parent for p in campaign.glob("*/case.tsv")):
        meta = dict(zip(OPTIONS, (directory / "case.tsv").read_text().strip().split("\t"), strict=True))
        if directory.name.startswith(("pilot-", "check-")):
            files = list(directory.glob("progress-*.csv"))
            accepted = min((len(csv_rows(p)) for p in files), default=0)
            probes.append((directory.name, meta["job"], accepted, meta["steps"]))
            continue
        if (directory / "launcher-complete").is_file():
            assert all(submitted[directory.name][key] == meta[key] for key in OPTIONS)
            metrics, tips = read_run(directory, meta)
            metrics["fbe_diagnostics"] = (directory / "solver.log").read_text().count(
                "Full_Backward_Euler did not converge"
            )
            data.append(dict(case=directory.name, **meta, **metrics))
            histories[directory.name] = tips

    groups = defaultdict(list)
    for row in data:
        groups[tuple(row[key] for key in GROUP)].append(row)
    if not data:
        raise ValueError("No completed runs")
    tip_error = 0.0
    for key, runs in groups.items():
        baseline = groups[(*key[:3], "j2", "mumps", "newton", "minimal", "0")][0]
        for row in runs:
            error = np.max(np.abs(histories[row["case"]] - histories[baseline["case"]]))
            assert error < 0.01, f"Tip history differs by {error:.6g} mm in {row['case']}"
            tip_error = max(tip_error, error)

    recorder_error = np.zeros(3)
    recorder_checks = 0
    for row in data:
        if row["output"] != "ladruno":
            continue
        tcl = row["case"].replace("-ladruno-", "-tcl-").replace("-f10-", "-f0-")
        if tcl in histories:
            errors = compare_recorder(campaign / row["case"], campaign / tcl,
                                      int(row["steps"]), int(row["ranks"]))
            recorder_error = np.maximum(recorder_error, errors)
            recorder_checks += 1

    with (campaign / "measurements.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)

    report = ["# OpenSeesMP exploration", "",
              "Same steel I-beam, T10 mesh, 250 MPa J2 perfect plasticity, and 1× gravity steps as the original benchmark.",
              "ASD uses associated von Mises flow, zero hardening, full backward Euler, closed-form derivatives and the algorithmic tangent.",
              "The installed Ladruño build is `1f08e5934`. Runs used one physical core per rank on exclusive Esmeralda allocations.",
              "The coarse sweep used 7,140 T10 elements and 30 steps. The fine pilots used 69,600 T10 elements and 29 steps.",
              "The global residual tolerance was 0.1 N with an 18-iteration cap. Krylov–Newton used a subspace dimension of 3.",
              "", "## Main comparisons", ""]
    core = {key[3:]: runs for key, runs in groups.items() if key[:3] == ("smoke", "node13", "8")}
    pairs = [
        ("J2Plasticity → ASD, default MUMPS",
         ("j2", "mumps", "newton", "minimal", "0"), ("asd", "mumps", "newton", "minimal", "0")),
        ("ASD, general → symmetric-indefinite MUMPS",
         ("asd", "mumps", "newton", "minimal", "0"), ("asd", "mumps-sym", "newton", "minimal", "0")),
        ("ASD, Tcl → Ladruño with per-step flush",
         ("asd", "mumps", "newton", "tcl", "0"), ("asd", "mumps", "newton", "ladruno", "0")),
        ("ASD with symmetric MUMPS, Tcl → Ladruño with per-step flush",
         ("asd", "mumps-sym", "newton", "tcl", "0"), ("asd", "mumps-sym", "newton", "ladruno", "0")),
    ]
    for description, old, new in pairs:
        if len(core.get(old, [])) == len(core.get(new, [])) == 3:
            before, after = (median(run["wall_s"] for run in core[key]) for key in (old, new))
            report.append(f"- {description} · {before:.2f} → {after:.2f} s ({100 * (after / before - 1):+.1f}%).")
    fine = {key[4]: runs[0]["wall_s"] for key, runs in groups.items()
            if key[:4] == ("refinement", "node12", "16", "asd")}
    if {"mumps", "mumps-sym"} <= fine.keys():
        report.append(f"- Fine mesh, ASD with general → symmetric MUMPS · {fine['mumps']:.2f} → "
                      f"{fine['mumps-sym']:.2f} s. One 16-rank pilot per setting.")
    diagnosed = [row["job"] for row in data if row["fbe_diagnostics"]]
    fallback = ("- Full backward Euler fallback diagnostics appeared in jobs " + ", ".join(diagnosed) + "."
                if diagnosed else "- The completed ASD jobs logged no full backward Euler fallback diagnostics.")
    report.extend([
              "", "## Timings", "",
              "Medians in seconds. Ladruño records on commit inside `analyze`. Its time is included in the analysis column. "
              "Tcl extraction and writes are timed separately. Wall time covers launch through recorder close.",
              "", "| Case | Output | Runs | Wall (s) | Analyze (s) | Tcl I/O (s) | Close (s) | MB | Iterations | Tip ↓ (mm) |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for key, runs in groups.items():
        mesh, host, ranks, material, system, algorithm, output, flush = key
        values = [median(r[k] for r in runs) for k in ("wall_s", "analyze_s", "tcl_s", "close_s", "bytes", "iterations", "tip_mm")]
        wall, solve, io, close, size, iters, tip = values
        name = {"smoke": "Coarse", "refinement": "Fine"}[mesh]
        recorder = f"Ladruño, flush {flush} s" if output == "ladruno" else output
        tcl_time = f"{io:.2f}" if output == "tcl" else "—"
        report.append(f"| {name} / {host} / {ranks} · {material.upper()} · {system} · {algorithm} | "
                      f"{recorder} | {len(runs)} | {wall:.2f} | {solve:.2f} | {tcl_time} | "
                      f"{close:.3f} | {size / 1e6:.2f} | {iters:g} | {tip:.5f} |")
    report.extend(["", "## Validation", "",
                   f"- Maximum tip-history difference from the corresponding J2 baseline was {tip_error * 1000:.4g} µm."])
    tcl_cases = [f"smoke-{mat}-mumps-newton-tcl-f0-r1" for mat in ("j2", "asd")]
    if all(case in histories for case in tcl_cases):
        stress, strain = compare_materials(campaign, tcl_cases, 8)
        report.append(f"- The coarse legacy/ASD field comparison gave peak component differences "
                      f"of {stress / 1e6:.4g} MPa in stress and {strain:.3g} in strain.")
    report.extend([
                   f"- Checked {recorder_checks} Ladruño/Tcl full-field pairs at every step. "
                   f"Maximum differences were {recorder_error[0]:.3g} m, {recorder_error[1]:.3g} Pa, and {recorder_error[2]:.3g} strain.",
                   fallback,
                   "- Ladruño stores f64 nodal displacement and the six stress and engineering-strain components at all four Gauss points. "
                   "It also stores mesh metadata. Level 1 compression was used throughout. Flush 0 writes every step.",
                   "- MUMPS options are automatic ordering with general storage, symmetric-indefinite storage with `-matrixType 2`, and AMD with `-ICNTL7 0`.",
                   "", "## Probes", "",
                   "| Trial | Job | Accepted steps |", "| --- | ---: | ---: |"])
    report.extend(f"| {name} | {job} | {accepted}/{steps} |" for name, job, accepted, steps in probes)
    for name, job, accepted, steps in probes:
        if "profile-spd" in name and accepted < int(steps):
            report.append(f"\nThe four-minute `ParallelProfileSPD` probe reached {accepted} of {steps} steps.")
    setup_failures = [job for name, job, accepted, _ in probes if name.startswith("pilot-") and accepted == 0]
    if setup_failures:
        report.append(f"\nJobs {', '.join(setup_failures)} stopped before solver launch. The wrapper was fixed and the trials repeated.")
    missing = sorted(submitted.keys() - histories.keys())
    if missing:
        report.extend(["", "Submitted cases without a complete result.", "",
                       *(f"- `{case}` · job {submitted[case]['job']}" for case in missing)])
    report.extend(["", f"Raw results on Esmeralda · `runs/{campaign.name}/`.",
                   "Computing resources provided by Esmeralda through ANID–Fondecyt project 11220530."])
    (campaign / "report.md").write_text("\n".join(report) + "\n")


if __name__ == "__main__":
    main()
