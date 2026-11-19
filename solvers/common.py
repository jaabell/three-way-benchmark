"""Command line and output shared by the Python input scripts."""

import argparse
import json
from pathlib import Path

import numpy as np

# Little-endian IDs followed by IEEE doubles, with no padding.
NODE_RECORD = np.dtype([("step", "<i4"), ("node", "<i4"), ("u", "<f8", 3)])
CELL_RECORD = np.dtype([("step", "<i4"), ("cell", "<i4"), ("point", "<i4"),
                        ("stress", "<f8", 6), ("strain", "<f8", 6)])


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("mesh", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("mode", choices=("full", "minimal"))
    parser.add_argument("target", type=float, help="Final gravity multiplier")
    parser.add_argument("steps", type=int)
    parser.add_argument("tolerance", type=float, help="Absolute residual tolerance, N")
    parser.add_argument("max_iterations", type=int)
    parser.add_argument("first_factor", type=float, nargs="?", default=0.0)
    return parser.parse_args()


def load_factor(args, step):
    if not args.first_factor:
        return args.target * step / args.steps
    return args.first_factor + (args.target - args.first_factor) * (step - 1) / (args.steps - 1)


def read_model(mesh):
    return json.loads((mesh / "model.json").read_text())


class Output:
    """Global node and element IDs are one-based. All shears are tensor components."""

    def __init__(self, path, mode, rank):
        self.progress = (path / f"progress-{rank}.csv").open("w")
        self.progress.write("step,factor,iterations,solve_s,output_s,tip_uz_m\n")
        self.full = mode == "full"
        if self.full:
            self.nodes = (path / f"nodes-{rank}.bin").open("wb")
            self.cells = (path / f"cells-{rank}.bin").open("wb")

    def fields(self, step, node_ids, displacement, cell_ids, stress, strain):
        # Node format: step node ux uy uz. Cell format: step element point stress[6] strain[6].
        node_rows = np.empty(len(node_ids), dtype=NODE_RECORD)
        node_rows["step"], node_rows["node"], node_rows["u"] = step, node_ids, displacement
        n_points = stress.shape[1]
        cell_rows = np.empty(len(cell_ids) * n_points, dtype=CELL_RECORD)
        cell_rows["step"] = step
        cell_rows["cell"] = np.repeat(cell_ids, n_points)
        cell_rows["point"] = np.tile(np.arange(1, n_points + 1), len(cell_ids))
        cell_rows["stress"], cell_rows["strain"] = stress.reshape(-1, 6), strain.reshape(-1, 6)
        node_rows.tofile(self.nodes)
        cell_rows.tofile(self.cells)
        self.nodes.flush()
        self.cells.flush()

    def step(self, step, factor, iterations, solve_s, output_s, tip):
        self.progress.write(f"{step},{factor:.17g},{iterations},{solve_s:.9f},{output_s:.9f},{tip}\n")
        self.progress.flush()

    def close(self):
        self.progress.close()
        if self.full:
            self.nodes.close()
            self.cells.close()
