"""Validate the full binary release and selected archived scientific values."""

import csv
import gzip
import json
from collections import Counter
from pathlib import Path

import numpy as np


data = Path(__file__).resolve().parents[1] / "dist/data"
manifest = json.loads((data / "manifest.json").read_text())
assert manifest["version"] == 1
assert abs(manifest["theory"]["plastic_force_N"] - 191979.1666666667) < 1e-6
assert abs(29 * manifest["theory"]["reference_weight_N"] / 1000 - 199.5840582015) < 1e-9
assert abs(manifest["reference"][-1][1] - 191.9791666667) < 1e-8
assert len(manifest["runs"]) == 7
assert len({r["job"] for r in manifest["runs"]}) == 7
tensor_meta = json.loads((data / "tensor-fields.json").read_text())
tensor_fields = [f"{family}_{key}" for family in ("stress", "strain")
                 for key in ("xx", "yy", "zz", "xy", "yz", "xz")]
assert tensor_meta["fields"] == tensor_fields
assert sum(tensor_meta["frames"].values()) == 207
for field in tensor_fields:
    lo, hi = tensor_meta["ranges"][field]
    assert lo < 0 < hi
for mesh, info in manifest["meshes"].items():
    raw = gzip.decompress((data / f"{mesh}.bin.gz").read_bytes())
    counts = (3 * info["points"], 3 * info["triangles"], info["triangles"], info["surfaceCells"])
    assert len(raw) == 4 * sum(counts)
    xyz = np.frombuffer(raw, "<f4", counts[0]).reshape(-1, 3)
    ix = np.frombuffer(raw, "<u4", counts[1], counts[0] * 4)
    source_cells = np.frombuffer(raw, "<u4", counts[2], sum(counts[:2]) * 4)
    ids = np.frombuffer(raw, "<u4", counts[3], sum(counts[:3]) * 4)
    assert np.isfinite(xyz).all()
    assert np.allclose(xyz.min(axis=0), [0, -.1, -.2], atol=3e-7)
    assert np.allclose(xyz.max(axis=0), [6, .1, .2], atol=3e-7)
    assert ix.max() < info["points"] and source_cells.max() < info["surfaceCells"]
    faces = ix.reshape(-1, 12)
    corners = faces[:, [0, 4, 8]]
    midsides = faces[:, 9:12]
    assert len(np.intersect1d(corners, midsides)) == 0
    assert len(np.unique(np.concatenate((corners, midsides), axis=1))) == info["points"]
    edge_midpoints = (xyz[corners] + xyz[corners[:, [1, 2, 0]]]) / 2
    assert np.allclose(edge_midpoints, xyz[midsides], rtol=0, atol=5e-7)
    print(mesh, "surface corners", len(np.unique(corners)), "midsides", len(np.unique(midsides)))
    assert 1 <= ids.min() <= ids.max() <= info["elements"]
    assert np.all(np.diff(ids) > 0)
    clamp = xyz[:, 0] == 0
    for run in (r for r in manifest["runs"] if r["mesh"] == mesh):
        directory = data / run["id"]
        part = np.frombuffer(gzip.decompress((directory / "partition.bin.gz").read_bytes()), "<u2")
        assert len(part) == info["surfaceCells"] and part.max() < run["ranks"]
        stop = 29 if mesh == "fine" else 30
        assert tensor_meta["frames"][run["id"]] == stop
        assert [t[0] for t in run["traces"]] == list(range(stop + 1))
        reference_tip_mm = 78.83943 if mesh == "fine" else 127.52811
        assert abs(run["traces"][-1][1] - reference_tip_mm) < 0.001
        for i in range(1, stop + 1):
            frame = np.frombuffer(gzip.decompress((directory / f"{i:02d}.bin.gz").read_bytes()), "<f4")
            assert len(frame) == counts[0] + counts[3] * len(manifest["fields"])
            assert np.isfinite(frame).all()
            u = frame[:counts[0]].reshape(-1, 3)
            assert np.abs(u[clamp]).max() < 1e-10
            fields = frame[counts[0]:].reshape(-1, counts[3])
            stresses = fields[manifest["fields"].index("stress")]
            assert stresses.min() >= 0 and stresses.max() <= 250.01
            for field, values in zip(manifest["fields"], fields, strict=True):
                lo, hi = run["levels"][field]
                assert values.min() >= lo - 2e-6 * max(1, abs(lo))
                assert values.max() <= hi + 2e-6 * max(1, abs(hi))
            raw_tensor = gzip.decompress((directory / f"tensor-{i:02d}.bin.gz").read_bytes())
            tensor = np.frombuffer(raw_tensor, "<f4").reshape(len(tensor_fields), counts[3])
            assert np.isfinite(tensor).all()
            assert np.array_equal(tensor[6], fields[manifest["fields"].index("strain")])
            for field, values in zip(tensor_fields, tensor, strict=True):
                lo, hi = tensor_meta["ranges"][field]
                assert values.min() >= lo - 2e-6 * max(1, abs(lo))
                assert values.max() <= hi + 2e-6 * max(1, abs(hi))
for suite in ["smoke-scaling", "refinement-scaling"]:
    with (data / f"{suite}-measurements.csv").open() as stream:
        runs = list(csv.DictReader(stream))
    groups = Counter((r["solver"], r["ranks"], r["transport"], r["output"]) for r in runs)
    assert len(runs) == 90 and set(groups.values()) == {3}
print("PASS 207 accepted frames with 12 signed tensor components, clamped geometry, seven run histories, beam reference, and 180 timing runs")

meta = json.loads((data / "partitions.json").read_text())
for name, expected in [("coarse", 4), ("fine", 16)]:
    info = meta[name]
    assert info["ranks"] == expected
    blob = gzip.decompress((data / f"{name}-partitions.bin.gz").read_bytes())
    xyz_count = info["points"] * 3
    n = info["triangles"]
    assert len(blob) == (xyz_count + 4*n + 3*expected) * 4
    tri = np.frombuffer(blob, "<u4", 3*n, xyz_count*4).reshape(-1, 3)
    ranks = np.frombuffer(blob, "<u4", n, (xyz_count+3*n)*4)
    assert tri.max() < info["points"]
    assert set(ranks) == set(range(expected))
    for rank in range(expected):
        triangles = tri[ranks == rank]
        edges = triangles[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)
        assert np.all(np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)[1] == 2)
print("PASS all 20 rank shells are closed, including shared interfaces")

options = json.loads((data.parent / "assets" / "solver-memory.json").read_text())
assert len(options["cpu"]) == 180 and len(options["gpu"]) == 18
for row in options["cpu"]:
    assert (row["hostKiB"] is not None) == (row["transport"] == "default")
for row in options["gpu"]:
    assert row["hostKiB"] is not None
    sampled = row["solver"].startswith("cuda-") and row["case"] != "smoke-elastic"
    assert (row["deviceKiB"] is not None) == sampled
assert next(row for row in options["gpu"] if row["job"] == 9694)["deviceKiB"] == 4098*1024
print("PASS 198 job records, rank RSS and sampled device memory")
