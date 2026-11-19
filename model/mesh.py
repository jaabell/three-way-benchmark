"""Generate one Gmsh tetrahedral mesh and straightforward solver input files."""

import argparse
import hashlib
import json
from pathlib import Path

import gmsh
import numpy as np


MODEL = Path(__file__).with_name("beam.json")


def mesh_beam(spec, resolution, output):
    length = spec["length_m"]
    y, z = spec["flange_width_m"] / 2, spec["depth_m"] / 2
    w, d = spec["web_thickness_m"] / 2, z - spec["flange_thickness_m"]
    section = [
        (-y, -z), (y, -z), (y, -d), (w, -d), (w, d), (y, d),
        (y, z), (-y, z), (-y, d), (-w, d), (-w, -d), (-y, -d),
    ]
    size = resolution["section_size_m"]
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.NumThreads", 1)
        gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
        gmsh.model.add("I-beam")
        geo = gmsh.model.geo
        points = [geo.addPoint(0, y, z, size) for y, z in section]
        edges = [geo.addLine(a, b) for a, b in zip(points, points[1:] + points[:1])]
        root = geo.addPlaneSurface([geo.addCurveLoop(edges)])
        layers = int(np.ceil(length / resolution["axial_size_m"]))
        entities = geo.extrude([(2, root)], length, 0, 0, [layers])
        geo.synchronize()
        volume = next(tag for dim, tag in entities if dim == 3)
        gmsh.model.addPhysicalGroup(3, [volume], name="steel")
        gmsh.model.addPhysicalGroup(2, [root], name="clamp")
        gmsh.model.addPhysicalGroup(2, [entities[0][1]], name="tip")
        gmsh.model.mesh.generate(3)
        gmsh.option.setNumber("Mesh.SecondOrderLinear", 1)
        gmsh.model.mesh.setOrder(2)
        gmsh.write(str(output / "beam.msh"))

        tags, xyz, _ = gmsh.model.mesh.getNodes()
        order = np.argsort(tags)
        xyz = xyz.reshape(-1, 3)[order]
        element_tags, connectivity = gmsh.model.mesh.getElementsByType(11)
        if len(element_tags) != sum(len(tags) for tags in gmsh.model.mesh.getElements(3)[1]):
            raise RuntimeError("Expected only ten-node quadratic tetrahedra")
        cells = np.searchsorted(tags[order], connectivity).reshape(-1, 10)
        cells = cells[np.argsort(element_tags)]
    finally:
        gmsh.finalize()

    vertices = xyz[cells[:, :4]]
    determinant = np.linalg.det(vertices[:, 1:] - vertices[:, :1])
    reverse = determinant < 0
    # Swapping vertices 2 and 3 also permutes their midside nodes.
    cells[reverse] = cells[reverse][:, [0, 2, 1, 3, 6, 5, 4, 7, 9, 8]]
    edges = np.array([(0, 1), (1, 2), (2, 0), (0, 3), (2, 3), (1, 3)])
    if not np.allclose(xyz[cells[:, 4:]], xyz[cells[:, edges]].mean(axis=2), atol=1e-12):
        raise RuntimeError("Unexpected quadratic tetrahedron connectivity")
    volumes = np.abs(determinant) / 6
    fixed = np.flatnonzero(np.isclose(xyz[:, 0], 0, atol=1e-10, rtol=0))
    end = np.flatnonzero(np.isclose(xyz[:, 0], length, atol=1e-10, rtol=0))
    tip = end[np.argmin(np.sum(xyz[end, 1:] ** 2, axis=1))]
    area = 4 * (y * (z - d) + w * d)
    plastic_modulus = 2 * (y * (z**2 - d**2) + w * d**2)
    if not (np.all(volumes > 0) and len(fixed) and np.isclose(volumes.sum(), area * length)):
        raise RuntimeError("Mesh failed volume, orientation or clamp validation")
    nominal_factor = (
        2 * spec["yield_stress_pa"] * plastic_modulus
        / (spec["density_kg_m3"] * spec["gravity_m_s2"] * area * length**2)
    )
    spec.update(
        element_order=2, node_count=len(xyz), element_count=len(cells), clamp_node_count=len(fixed),
        tip_node=int(tip) + 1, volume_m3=float(volumes.sum()),
        area_m2=area, plastic_section_modulus_m3=plastic_modulus,
        nominal_plastic_load_factor=nominal_factor, gmsh_version=gmsh.__version__,
    )
    np.savez(output / "mesh.npz", xyz=xyz, cells=cells, volumes=volumes, fixed=fixed)
    spec["mesh_sha256"] = hashlib.sha256((output / "mesh.npz").read_bytes()).hexdigest()
    (output / "model.json").write_text(json.dumps(spec, indent=2) + "\n")
    write_kratos(output / "beam.mdpa", xyz, cells, fixed)
    write_opensees(output, spec, xyz, cells, fixed, volumes)


def write_kratos(path, xyz, cells, fixed):
    with path.open("w") as out:
        out.write("Begin Properties 1\nEnd Properties\n\nBegin Nodes\n")
        for i, (x, y, z) in enumerate(xyz, 1):
            out.write(f"{i} {x:.17g} {y:.17g} {z:.17g}\n")
        out.write("End Nodes\n\nBegin Elements SmallDisplacementElement3D10N\n")
        for i, conn in enumerate(cells[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]] + 1, 1):
            out.write(f"{i} 1 {' '.join(map(str, conn))}\n")
        out.write("End Elements\n\nBegin SubModelPart clamp\n    Begin SubModelPartNodes\n")
        out.writelines(f"        {node}\n" for node in fixed + 1)
        out.write("    End SubModelPartNodes\nEnd SubModelPart\n")


def write_opensees(output, spec, xyz, cells, fixed, volumes):
    fixed_nodes = set(fixed)
    with (output / "model.tcl").open("w") as out:
        for key, value in spec.items():
            if isinstance(value, (int, float)):
                out.write(f"set {key} {value}\n")

    # Split Gmsh's cell dual graph with METIS for OpenSeesMP. The other
    # solvers read the same unpartitioned mesh and use their native partitioner.
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.NumThreads", 1)
        gmsh.option.setNumber("Mesh.PartitionCreateTopology", 0)
        gmsh.option.setNumber("Mesh.PartitionCreateGhostCells", 0)
        gmsh.open(str(output / "beam.msh"))
        tags, _ = gmsh.model.mesh.getElementsByType(11)
        tags = np.sort(tags)
        for size in (1, 4, 8, 16, 32):
            if size > 1:
                gmsh.model.mesh.partition(size)
            directory = output / f"opensees-{size}"
            directory.mkdir()
            owners = np.zeros(len(cells), dtype=int)
            if size > 1:
                owners.fill(-1)
                for dim, entity in gmsh.model.getEntities(3):
                    partitions = gmsh.model.getPartitions(dim, entity)
                    if len(partitions):
                        part_tags, _ = gmsh.model.mesh.getElementsByType(11, entity)
                        owners[np.searchsorted(tags, part_tags)] = partitions[0] - 1
            if np.any(owners < 0):
                raise RuntimeError("Gmsh left unassigned cells")
            for rank in range(size):
                cell_ids = np.flatnonzero(owners == rank)
                if not len(cell_ids):
                    raise RuntimeError(f"Empty partition {rank} at {size} ranks")
                conn = cells[cell_ids]
                nodes, local_conn = np.unique(conn, return_inverse=True)
                # Exact consistent body load for straight T10 elements.
                shape_integral = np.array([-1 / 20] * 4 + [1 / 5] * 6)
                weight = np.bincount(
                    local_conn.ravel(),
                    (volumes[cell_ids, None] * shape_integral).ravel(),
                    minlength=len(nodes),
                )
                weight *= -spec["density_kg_m3"] * spec["gravity_m_s2"]
                with (directory / f"{rank}.tcl").open("w") as out:
                    out.write("set nodes {\n")
                    for node, force in zip(nodes, weight):
                        x, y, z = xyz[node]
                        out.write(f"    {{{node + 1} {x:.17g} {y:.17g} {z:.17g} "
                                  f"{int(node in fixed_nodes)} {force:.17g}}}\n")
                    out.write("}\nset elements {\n")
                    for cell_id, row in zip(cell_ids + 1, conn + 1):
                        out.write(f"    {{{cell_id} {' '.join(map(str, row))}}}\n")
                    out.write("}\n")
            if size > 1:
                gmsh.model.mesh.unpartition()
    finally:
        gmsh.finalize()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resolution", choices=("smoke", "refinement", "production"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    spec = json.loads(MODEL.read_text())
    spec["resolution"] = args.resolution
    mesh_beam(spec, spec["mesh"][args.resolution], args.output)


if __name__ == "__main__":
    main()
