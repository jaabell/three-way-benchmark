"""Render a headless overview from a generated ParaView view directory."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.ticker import MaxNLocator
import numpy as np
import pyvista as pv


def draw_mesh(path, png):
    grid = pv.read(path)
    surface = grid.extract_surface(algorithm="dataset_surface", nonlinear_subdivision=2).triangulate()
    faces = surface.faces.reshape(-1, 4)[:, 1:]
    xyz = surface.points.copy()
    fields = []
    if "displacement_m" in surface.point_data:
        u = surface.point_data["displacement_m"]
        xyz += u  # True physical displacement scale.
        fields = [
            ("Displacement magnitude [mm]", 1000 * np.linalg.norm(u[faces], axis=2).mean(axis=1)),
            ("von Mises stress [MPa]", surface.cell_data["von_Mises_Pa"] / 1e6),
            ("Equivalent plastic strain [%]", 100 * surface.cell_data["equivalent_plastic_strain"]),
            ("Elastic energy density [kJ/m³]", surface.cell_data["elastic_energy_J_m3"] / 1000),
            ("Plastic dissipation density [kJ/m³]", surface.cell_data["plastic_dissipation_J_m3"] / 1000),
        ]
    owners = surface.cell_data["partition"]
    if fields and owners.min() == owners.max():
        fields.append(("Axial strain [µε]", 1e6 * surface.cell_data["strain_xx_yy_zz_xy_yz_xz"][:, 0]))
    else:
        fields.append(("MPI partition", owners))
    projection = np.column_stack((xyz[:, 0] - 0.8 * xyz[:, 1],
                                  xyz[:, 2] + 0.55 * xyz[:, 1]))
    order = np.argsort(xyz[faces, 1].mean(axis=1))
    vertices = projection[faces[order]]
    columns = 2 if len(fields) > 1 else 1
    rows = len(fields) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(13 if columns == 2 else 11, 2.2 * rows),
                             squeeze=False, layout="constrained")
    for ax, (label, values) in zip(axes.flat, fields, strict=True):
        colors = "turbo" if label == "MPI partition" else "viridis"
        patches = PolyCollection(vertices, array=values[order], cmap=colors, linewidths=0)
        ax.add_collection(patches)
        ax.autoscale_view()
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title(label)
        if label != "MPI partition" or values.max() > values.min():
            colorbar = fig.colorbar(patches, ax=ax, orientation="horizontal", shrink=0.55, pad=0.04)
            colorbar.locator = MaxNLocator(nbins=5, integer=(label == "MPI partition"))
            colorbar.update_ticks()
    fig.savefig(png, dpi=180)
    plt.close(fig)


def draw_energy(path, png):
    with path.open(newline="") as source:
        data = list(csv.DictReader(source))
    factor = [float(row["factor"]) for row in data]
    fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for key, label in [("elastic_J", "Stored elastic energy"),
                       ("plastic_dissipation_J", "Plastic dissipation"),
                       ("external_work_J", "External work")]:
        left.plot(factor, [float(row[key]) / 1000 for row in data], label=label)
    right.plot(factor, [-1000 * float(row["tip_uz_m"]) for row in data], color="tab:purple")
    left.set_ylabel("Energy [kJ]")
    right.set_ylabel("Downward tip displacement [mm]")
    left.legend()
    for ax in (left, right):
        ax.set_xlabel("Gravity multiplier")
        ax.grid(alpha=0.25)
    fig.savefig(png, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    steps = sorted(args.directory.glob("step-*.vtu"))
    if steps:
        draw_mesh(steps[-1], args.directory / "fields.png")
        draw_energy(args.directory / "energy.csv", args.directory / "history.png")
    else:
        for path in sorted(args.directory.glob("*partitions-*.vtu")):
            draw_mesh(path, path.with_suffix(".png"))


if __name__ == "__main__":
    main()
