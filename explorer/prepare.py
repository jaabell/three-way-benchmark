"""Reduce real ParaView T10 load histories to browser-ready exterior fields."""

import argparse
import csv
import gzip
import json
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridReader


RUNS = [
    ("os-smoke", "OpenSeesMP", "smoke", 4, 9020, "esmeralda-nonlinear-opensees", "MUMPS"),
    ("kr-smoke", "Kratos", "smoke", 4, 9481, "esmeralda-kratos-mumps", "Amesos MUMPS"),
    ("fx-smoke", "FEniCSx", "smoke", 4, 9021, "esmeralda-nonlinear-fenicsx", "PETSc MUMPS"),
    ("os-fine", "OpenSeesMP", "fine", 16, 9580, "esmeralda-refinement-opensees", "MUMPS"),
    ("kr-fine", "Kratos", "fine", 16, 9579, "esmeralda-refinement-kratos", "Amesos MUMPS"),
    ("fx-fine", "FEniCSx", "fine", 16, 9581, "esmeralda-refinement-fenicsx", "PETSc MUMPS"),
    ("fx-gpu", "FEniCSx", "smoke", 1, 9694, "esmeralda-gpu-fenicsx-smoke", "RTX 5090 sparse QR"),
]

# Per-surface-cell float32 blocks follow the three nodal displacement components.
FIELDS = [
    ("stress", "von_Mises_Pa", 1e-6, None),
    ("strain", "strain_xx_yy_zz_xy_yz_xz", 1e3, 0),
    ("plastic", "equivalent_plastic_strain", 1e3, None),
    ("elastic", "elastic_energy_J_m3", 1e-3, None),
    ("dissipation", "plastic_dissipation_J_m3", 1e-3, None),
]
# VTK quadratic tetrahedron face templates. Opposite corner rotates with templates.
FACES = np.array([[1, 2, 3, 5, 9, 8], [0, 3, 2, 7, 9, 6],
                  [0, 1, 3, 4, 8, 7], [0, 2, 1, 6, 5, 4]])
SUBFACES = np.array([[0, 3, 5], [3, 1, 4], [5, 4, 2], [3, 4, 5]])


def read_vtu(reader, filename):
    reader.SetFileName(str(filename))
    reader.Update()
    return reader.GetOutput()


def floats(array, absolute=None):
    array = np.asarray(array)
    assert np.isfinite(array).all()
    packed = array.astype("<f4")
    limit = absolute if absolute else 2e-6 * max(float(np.max(np.abs(array))), 1e-20)
    assert np.max(np.abs(packed - array)) <= limit
    return packed


def write_binary(path, *arrays):
    with path.open("wb") as dest, gzip.GzipFile(filename="", fileobj=dest, mode="wb", mtime=0, compresslevel=4) as stream:
        for array in arrays:
            stream.write(np.ascontiguousarray(array).tobytes())


def exterior(grid):
    xyz = vtk_to_numpy(grid.GetPoints().GetData()).copy()
    tets = vtk_to_numpy(grid.GetCells().GetConnectivityArray()).copy().reshape(-1, 10)
    assert grid.GetCellType(0) == 24 and len(tets) == grid.GetNumberOfCells()
    assert tets.min() >= 0 and tets.max() < len(xyz)
    faces = tets[:, FACES].reshape(-1, 6)
    _, first, multiplicity = np.unique(np.sort(faces[:, :3], axis=1), return_index=True,
                                      return_counts=True, axis=0)
    assert multiplicity.max() == 2
    outside = np.sort(first[multiplicity == 1])
    owners = outside // 4
    faces = faces[outside]
    corners = xyz[faces[:, :3]]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    swap = np.einsum("ij,ij->i", normals, xyz[tets[owners, outside % 4]] - corners[:, 0]) > 0
    faces[swap] = faces[swap][:, [0, 2, 1, 5, 4, 3]]
    points, triangles = np.unique(faces[:, SUBFACES], return_inverse=True)
    cell_ids, mapping = np.unique(owners, return_inverse=True)
    tri_cells = np.repeat(mapping, 4)
    assert len(triangles.ravel()) == len(tri_cells) * 3
    assert len(xyz) in (13041, 116781)
    return xyz, tets, points, cell_ids, triangles.ravel(), tri_cells


def rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    repo, out = args.repo, args.output
    reports = repo / "results/esmeralda"
    out.mkdir(parents=True, exist_ok=True)
    model = json.loads((repo / "model/beam.json").read_text())
    theory = json.loads((reports / "force-displacement-reference.json").read_text())
    manifest = {"version": 1, "model": model, "theory": theory, "runs": [], "meshes": {},
                "fields": [row[0] for row in FIELDS],
                "reference": [[float(r["tip_down_mm"]), float(r["total_weight_kN"])]
                              for r in rows(reports / "force-displacement.csv")
                              if r["curve"].startswith("Euler")]}
    run_timing = []
    for tag, suite in (("smoke", "smoke-scaling"), ("fine", "refinement-scaling")):
        table = rows(reports / f"{suite}-summary.csv")
        assert len(table) == 30 and all(r["valid_repeats"] == "3" for r in table)
        run_timing.extend(dict(row, mesh=tag) for row in table)
        for suffix in ("measurements", "summary"):
            name = f"{suite}-{suffix}.csv"
            shutil.copyfile(reports / name, out / name)
    shutil.copyfile(reports / "gpu-pilot-timings.csv", out / "gpu-pilot-timings.csv")
    manifest["timings"] = run_timing
    manifest["gpu"] = rows(reports / "gpu-pilot-timings.csv")
    meshes = {}
    reader = vtkXMLUnstructuredGridReader()
    for slug, solver, mesh, ranks, job, folder, backend in RUNS:
        src = repo / "views" / folder
        frame = list(ET.parse(src / "beam.pvd").iter("DataSet"))
        energy = rows(src / "energy.csv")
        factors = [float(f.get("timestep")) for f in frame]
        assert factors == list(range(1, 30 if mesh == "fine" else 31))
        assert factors == [float(row["factor"]) for row in energy]
        first = read_vtu(reader, src / frame[0].get("file"))
        if mesh not in meshes:
            xyz, tets, points, cell_ids, triangles, tri_cells = exterior(first)
            meshes[mesh] = xyz, tets, points, cell_ids
            write_binary(out / f"{mesh}.bin.gz", floats(xyz[points], 3e-7),
                         triangles.astype("<u4"), tri_cells.astype("<u4"), (cell_ids + 1).astype("<u4"))
            manifest["meshes"][mesh] = {"nodes": len(xyz), "elements": len(tets), "points": len(points),
                                        "triangles": len(tri_cells), "surfaceCells": len(cell_ids)}
        xyz, tets, points, cell_ids = meshes[mesh]
        case = out / slug
        case.mkdir(exist_ok=True)
        levels = {key: [0.0, 0.0] for key in ["displacement", *(f[0] for f in FIELDS)]}
        partition = vtk_to_numpy(first.GetCellData().GetArray("partition")).copy()
        assert partition.min() == 0 and partition.max() == ranks - 1
        write_binary(case / "partition.bin.gz", partition[cell_ids].astype("<u2"))
        traces = [[0] * 6]
        for i, (entry, row) in enumerate(zip(frame, energy, strict=True), 1):
            grid = read_vtu(reader, src / entry.get("file"))
            assert np.array_equal(vtk_to_numpy(grid.GetPoints().GetData()), xyz)
            assert np.array_equal(vtk_to_numpy(grid.GetCells().GetConnectivityArray()).reshape(-1, 10), tets)
            cell_data = grid.GetCellData()
            assert np.array_equal(partition, vtk_to_numpy(cell_data.GetArray("partition")))
            u = vtk_to_numpy(grid.GetPointData().GetArray("displacement_m"))
            rooted = np.isclose(xyz[:, 0], 0)
            assert np.max(np.abs(u[rooted])) < 1e-10
            vy = u[points]
            peak = float(np.linalg.norm(vy, axis=1).max() * 1e3)
            levels["displacement"][1] = max(peak, levels["displacement"][1])
            blocks = [floats(vy, 3e-7)]
            for key, name, scale, component in FIELDS:
                scalar = vtk_to_numpy(cell_data.GetArray(name))[cell_ids]
                if component is not None:
                    scalar = scalar[:, component]
                scalar = scalar * scale
                blocks.append(floats(scalar))
                limits = levels[key]
                limits[0] = min(limits[0], float(scalar.min()))
                limits[1] = max(limits[1], float(scalar.max()))
            write_binary(case / f"{i:02d}.bin.gz", *blocks)
            tip = -float(row["tip_uz_m"]) * 1000
            assert 0 < tip <= peak + 1e-6
            traces.append([float(row["factor"]), tip, *(float(row[k]) / 1000 for k in
                           ("elastic_J", "plastic_dissipation_J", "external_work_J", "balance_error_J"))])
        manifest["runs"].append(dict(id=slug, solver=solver, mesh=mesh, ranks=ranks, job=job,
                                     backend=backend, traces=traces, levels=levels))
        print(slug, job, len(frame), len(points), len(cell_ids), f"tip={traces[-1][1]:.8f} mm", flush=True)
    (out / "manifest.json").write_text(json.dumps(manifest, allow_nan=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
