"""Convert complete rank output to ParaView and integrate elastic/plastic energy."""

import argparse
import csv
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pyvista as pv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "solvers"))
from common import CELL_RECORD, NODE_RECORD


def grid_from_mesh(xyz, cells):
    # VTK and Kratos both swap Gmsh's final two edge nodes.
    vtk_cells = cells[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]
    connectivity = np.column_stack((np.full(len(cells), 10), vtk_cells)).ravel()
    types = np.full(len(cells), int(pv.CellType.QUADRATIC_TETRA), dtype=np.uint8)
    return pv.UnstructuredGrid(connectivity, types, xyz)


def opensees_partitions(mesh, out, ranks, nelements, grid):
    owners = np.full(nelements, -1, dtype=np.int32)
    for rank in range(ranks):
        part = mesh / f"opensees-{ranks}" / f"{rank}.tcl"
        elements = part.read_text().split("set elements {\n", 1)[1].splitlines()[:-1]
        ids = np.array([int(line.strip().split()[0][1:]) - 1 for line in elements])
        if np.any(owners[ids] != -1) or len(ids) != len(np.unique(ids)):
            raise ValueError(f"Duplicate cell ownership in {part}")
        owners[ids] = rank
    if np.any(owners < 0):
        raise ValueError("Mesh has unassigned cells")
    grid.cell_data["partition"] = owners
    grid.save(out / f"opensees-partitions-{ranks}.vtu")


def frames(stack, paths, dtype, steps):
    for path in paths:
        count, remainder = divmod(path.stat().st_size, dtype.itemsize * steps)
        if remainder:
            raise ValueError(f"Incomplete output in {path}")
        yield stack.enter_context(path.open("rb")), count


def frame(stream, dtype, count, step):
    records = np.fromfile(stream, dtype=dtype, count=count)
    if len(records) != count or np.any(records["step"] != step):
        raise ValueError(f"Missing or invalid step {step} in {stream.name}")
    return records


def contraction(a, b):
    # Voigt order xx yy zz xy yz xz with tensor shears.
    return np.sum(a * b * [1, 1, 1, 2, 2, 2], axis=-1)


def convert(mesh, run, out, grid, xyz, volumes, spec):
    if not (run / "launcher-complete").exists():
        raise ValueError("Solver launcher did not finish successfully")
    _, nranks, _, mode, target, nsteps, _ = (run / "case.tsv").read_text().strip().split("\t")
    if mode != "full" or spec["mesh_sha256"] != json.loads(
            (run / "model.json").read_text())["mesh_sha256"]:
        raise ValueError("A complete run and its original mesh are required")
    nranks, nsteps, target = int(nranks), int(nsteps), float(target)
    nnodes, nelements = len(xyz), len(volumes)
    E, nu, fy = (spec[name] for name in ("young_modulus_pa", "poisson_ratio", "yield_stress_pa"))
    gauss_volumes = volumes[:, None] / 4
    previous_plastic = np.zeros((nelements, 4, 6))
    eq_plastic = np.zeros((nelements, 4))
    # The same exact consistent T10 load used by the solvers.
    with np.load(mesh / "mesh.npz") as data:
        cells = data["cells"]
    weights = np.array([-1 / 20] * 4 + [1 / 5] * 6)
    base_force = np.bincount(cells.ravel(), (volumes[:, None] * weights).ravel(), minlength=nnodes)
    base_force *= -spec["density_kg_m3"] * spec["gravity_m_s2"]
    previous_u, external_work = np.zeros(nnodes), 0.0
    collection = ET.Element("VTKFile", type="Collection", version="0.1", byte_order="LittleEndian")
    data_sets = ET.SubElement(collection, "Collection")

    with ExitStack() as stack:
        nodal = list(frames(stack, [run / f"nodes-{rank}.bin" for rank in range(nranks)],
                            NODE_RECORD, nsteps))
        gauss = list(frames(stack, [run / f"cells-{rank}.bin" for rank in range(nranks)],
                            CELL_RECORD, nsteps))
        energy = csv.writer(stack.enter_context((out / "energy.csv").open("w")))
        energy.writerow(["step", "factor", "elastic_J", "plastic_dissipation_J",
                         "external_work_J", "balance_error_J", "tip_uz_m", "max_mises_Pa"])
        for step in range(1, nsteps + 1):
            u = np.full((nnodes, 3), np.nan)
            stress = np.full((nelements, 4, 6), np.nan)
            strain = np.full_like(stress, np.nan)
            owners = np.full(nelements, -1, dtype=np.int32)
            for rank, ((node_file, nn), (cell_file, ng)) in enumerate(zip(nodal, gauss)):
                nodes = frame(node_file, NODE_RECORD, nn, step)
                ids = nodes["node"] - 1
                if (np.any(ids < 0) or np.any(ids >= nnodes) or len(np.unique(ids)) != nn):
                    raise ValueError(f"Invalid node IDs in {node_file.name}")
                seen = np.isfinite(u[ids, 0])
                if not np.allclose(u[ids[seen]], nodes["u"][seen], atol=1e-9, rtol=1e-7):
                    raise ValueError(f"Ranks disagree on interface displacement at step {step}")
                u[ids] = nodes["u"]

                points = frame(cell_file, CELL_RECORD, ng, step)
                ids, q = points["cell"] - 1, points["point"] - 1
                if (np.any(ids < 0) or np.any(ids >= nelements) or np.any(q < 0) or np.any(q >= 4)
                        or len(np.unique(4 * ids + q)) != ng or np.any(owners[ids] != -1)):
                    raise ValueError(f"Invalid or duplicate element output in {cell_file.name}")
                owners[ids] = rank
                stress[ids, q], strain[ids, q] = points["stress"], points["strain"]

            if not all(np.isfinite(values).all() for values in (u, stress, strain)):
                raise ValueError(f"Missing or nonfinite output at step {step}")

            mean = stress[..., :3].mean(axis=-1, keepdims=True)
            deviator = stress.copy()
            deviator[..., :3] -= mean
            mises = np.sqrt(1.5 * contraction(deviator, deviator))
            elastic_strain = (1 + nu) * stress / E
            elastic_strain[..., :3] -= 3 * nu * mean / E
            plastic = strain - elastic_strain
            increment = plastic - previous_plastic
            eq_plastic += np.sqrt(2 / 3 * contraction(increment, increment))
            previous_plastic = plastic
            elastic = 0.5 * contraction(stress, elastic_strain)
            dissipated = fy * eq_plastic
            elastic_total = np.sum(elastic * gauss_volumes)
            plastic_total = np.sum(dissipated * gauss_volumes)
            factor = target * step / nsteps
            external_work += target * (step - 0.5) / nsteps * (base_force @ (u[:, 2] - previous_u))
            previous_u = u[:, 2]
            energy.writerow([step, factor, elastic_total, plastic_total, external_work,
                             external_work - elastic_total - plastic_total,
                             u[spec["tip_node"] - 1, 2], mises.max()])

            grid.point_data["displacement_m"] = u
            grid.cell_data["partition"] = owners
            grid.cell_data["stress_Pa_xx_yy_zz_xy_yz_xz"] = stress.mean(axis=1)
            grid.cell_data["strain_xx_yy_zz_xy_yz_xz"] = strain.mean(axis=1)
            grid.cell_data["von_Mises_Pa"] = mises.mean(axis=1)
            grid.cell_data["equivalent_plastic_strain"] = eq_plastic.mean(axis=1)
            grid.cell_data["elastic_energy_J_m3"] = elastic.mean(axis=1)
            grid.cell_data["plastic_dissipation_J_m3"] = dissipated.mean(axis=1)
            filename = f"step-{step:04d}.vtu"
            grid.save(out / filename)
            ET.SubElement(data_sets, "DataSet", timestep=str(factor), group="", part="0", file=filename)

    ET.indent(collection)
    ET.ElementTree(collection).write(out / "beam.pvd", encoding="utf-8", xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mesh", type=Path)
    parser.add_argument("output", type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run", type=Path)
    source.add_argument("--opensees-partitions", type=int, choices=(4, 8, 16, 32))
    args = parser.parse_args()
    spec = json.loads((args.mesh / "model.json").read_text())
    with np.load(args.mesh / "mesh.npz") as data:
        xyz, cells, volumes = data["xyz"], data["cells"], data["volumes"]
    grid = grid_from_mesh(xyz, cells)
    args.output.mkdir(parents=True, exist_ok=False)
    if args.run:
        convert(args.mesh, args.run, args.output, grid, xyz, volumes, spec)
    else:
        opensees_partitions(args.mesh, args.output, args.opensees_partitions, len(cells), grid)


if __name__ == "__main__":
    main()
