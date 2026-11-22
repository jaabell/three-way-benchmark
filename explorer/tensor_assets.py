"""Export the six stress and strain components from the saved T10 surface cells."""

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridReader

from prepare import RUNS, exterior, floats, read_vtu, write_binary


ORDER = ("xx", "yy", "zz", "xy", "yz", "xz")
FIELDS = (
    ("stress", "stress_Pa_xx_yy_zz_xy_yz_xz", 1e-6),
    ("strain", "strain_xx_yy_zz_xy_yz_xz", 1e3),
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    reader = vtkXMLUnstructuredGridReader()
    bounds = {f"{kind}_{key}": [0.0, 0.0] for kind, _, _ in FIELDS for key in ORDER}
    meshes = {}
    frames = {}
    for slug, _, mesh, _, _, folder, _ in RUNS:
        src = args.repo / "views" / folder
        entries = list(ET.parse(src / "beam.pvd").iter("DataSet"))
        dest = args.output / slug
        dest.mkdir(exist_ok=True)
        for step, entry in enumerate(entries, 1):
            assert float(entry.get("timestep")) == step
            grid = read_vtu(reader, src / entry.get("file"))
            if mesh not in meshes:
                xyz, tets, _, cell_ids, _, _ = exterior(grid)
                meshes[mesh] = xyz, tets, cell_ids
            xyz, tets, cell_ids = meshes[mesh]
            assert np.array_equal(vtk_to_numpy(grid.GetPoints().GetData()), xyz)
            assert np.array_equal(vtk_to_numpy(grid.GetCells().GetConnectivityArray()).reshape(-1, 10), tets)
            arrays = []
            for kind, field, scale in FIELDS:
                values = (vtk_to_numpy(grid.GetCellData().GetArray(field))[cell_ids] * scale).T
                assert values.shape == (len(ORDER), len(cell_ids))
                arrays.append(floats(values))
                for key, component in zip(ORDER, values, strict=True):
                    limit = bounds[f"{kind}_{key}"]
                    limit[0] = min(limit[0], float(component.min()))
                    limit[1] = max(limit[1], float(component.max()))
            write_binary(dest / f"tensor-{step:02d}.bin.gz", *arrays)
        frames[slug] = len(entries)
        print(slug, frames[slug], len(cell_ids), flush=True)
    (args.output / "tensor-fields.json").write_text(json.dumps(
        {"fields": list(bounds), "ranges": bounds, "frames": frames}, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
