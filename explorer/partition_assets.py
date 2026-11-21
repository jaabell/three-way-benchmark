"""Export closed OpenSeesMP rank shells, including both sides of each MPI interface."""

import argparse
import json
from pathlib import Path

import numpy as np
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridReader

from prepare import FACES, SUBFACES, floats, read_vtu, write_binary


def partition_shells(grid):
    xyz = vtk_to_numpy(grid.GetPoints().GetData())
    tets = vtk_to_numpy(grid.GetCells().GetConnectivityArray()).reshape(-1, 10)
    ranks = vtk_to_numpy(grid.GetCellData().GetArray("partition"))
    faces = tets[:, FACES].reshape(-1, 6)
    keys = np.sort(faces[:, :3], axis=1)
    order = np.lexsort(keys.T)
    shared = np.all(keys[order[:-1]] == keys[order[1:]], axis=1)
    adjacent = order[:-1][shared], order[1:][shared]
    assert not np.any(shared[:-1] & shared[1:])
    interior = ranks[adjacent[0] // 4] == ranks[adjacent[1] // 4]
    keep = np.ones(len(faces), dtype=bool)
    for side in adjacent:
        keep[side[interior]] = False
    ids = np.flatnonzero(keep)
    shell = faces[ids].copy()
    corners = xyz[shell[:, :3]]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    flip = np.einsum("ij,ij->i", normals, xyz[tets[ids // 4, ids % 4]] - corners[:, 0]) > 0
    shell[flip] = shell[flip][:, [0, 2, 1, 5, 4, 3]]
    points, triangles = np.unique(shell[:, SUBFACES], return_inverse=True)
    ownership = np.repeat(ranks[ids // 4], 4)
    centers = xyz[tets[:, :4]].mean(axis=1)
    centers = np.array([centers[ranks == i].mean(axis=0) for i in range(ranks.max() + 1)])
    # Every rank shell must be closed under the corner-edge adjacency.
    for rank in range(len(centers)):
        local = shell[ranks[ids // 4] == rank, :3]
        edges = np.sort(local[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1)
        assert np.all(np.unique(edges, axis=0, return_counts=True)[1] == 2), rank
    return (floats(xyz[points], 3e-7), triangles.ravel().astype("<u4"),
            ownership.astype("<u4"), floats(centers, 3e-7))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    reader = vtkXMLUnstructuredGridReader()
    manifest = {}
    sources = {"coarse": ("esmeralda-nonlinear-opensees", 9020),
               "fine": ("esmeralda-refinement-opensees", 9580)}
    for key, (folder, job) in sources.items():
        grid = read_vtu(reader, args.repo / "views" / folder / "step-0001.vtu")
        xyz, indices, ownership, centers = partition_shells(grid)
        write_binary(args.output / f"{key}-partitions.bin.gz", xyz, indices, ownership, centers)
        manifest[key] = dict(points=len(xyz), triangles=len(ownership), ranks=len(centers), job=job)
    (args.output / "partitions.json").write_text(json.dumps(manifest) + "\n")
    print(manifest, flush=True)


if __name__ == "__main__":
    main()
