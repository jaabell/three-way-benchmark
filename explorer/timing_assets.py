"""Build the explorer CPU tables from node13 repeats and the original 32-rank cases."""

import argparse
import csv
import json
from collections import Counter
from itertools import product
from pathlib import Path


SOURCES = (("smoke", "coarse", "smoke-scaling"), ("fine", "fine", "refinement-scaling"))


def rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def comparison(reports, kind):
    for mesh, name, original in SOURCES:
        for suite, ranks, hosts in (
            (f"node13-{name}", {"4", "8", "16"}, "node13"),
            (original, {"32"}, "node12 + node13"),
        ):
            selected = [row for row in rows(reports / f"{suite}-{kind}.csv") if row["ranks"] in ranks]
            transports = ("default",) if hosts == "node13" else ("rdma-on", "rdma-off")
            settings = product(("opensees", "kratos", "fenicsx"), ranks, transports, ("full", "minimal"))
            expected = dict.fromkeys(settings, 3 if kind == "measurements" else 1)
            counts = Counter(tuple(row[key] for key in ("solver", "ranks", "transport", "output")) for row in selected)
            if counts != expected or (kind == "summary" and any(r["valid_repeats"] != "3" for r in selected)):
                raise ValueError(f"Incomplete {suite} {kind}")
            yield from (dict(row, mesh=mesh, hosts=hosts) for row in selected)


def export_cpu(reports, output):
    measurements = list(comparison(reports, "measurements"))
    for name, selected in (
        ("node13-coarse", [r for r in measurements if r["mesh"] == "smoke" and r["ranks"] != "32"]),
        ("node13-fine", [r for r in measurements if r["mesh"] == "fine" and r["ranks"] != "32"]),
        ("two-node", [r for r in measurements if r["ranks"] == "32"]),
    ):
        with (output / f"{name}-measurements.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(selected[0]))
            writer.writeheader()
            writer.writerows(selected)
    return list(comparison(reports, "summary"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path)
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    path = args.data / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["timings"] = export_cpu(args.reports, args.data)
    path.write_text(json.dumps(manifest, separators=(",", ":"), allow_nan=False) + "\n")
