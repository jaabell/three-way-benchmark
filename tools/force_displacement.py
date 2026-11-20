"""Compare finite-element tip histories with a pure-bending beam reference."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def beam_reference(model):
    L = model["length_m"]
    h = model["depth_m"] / 2
    d = h - model["flange_thickness_m"]
    bw, bf = model["web_thickness_m"], model["flange_width_m"]
    E, fy = model["young_modulus_pa"], model["yield_stress_pa"]
    intervals = [(0, d, bw), (d, h, bf)]
    area = 2 * sum(width * (top - bottom) for bottom, top, width in intervals)
    inertia = 2 / 3 * sum(width * (top**3 - bottom**3) for bottom, top, width in intervals)
    plastic_modulus = sum(width * (top**2 - bottom**2) for bottom, top, width in intervals)
    reference_weight = area * L * model["density_kg_m3"] * model["gravity_m_s2"]
    yield_moment = fy * inertia / h
    plastic_moment = fy * plastic_modulus

    def moment(curvature):
        # With plane sections, sigma(z) = min(E * curvature * z, fy) on the top half.
        yield_depth = fy / (E * curvature)
        result = np.zeros_like(curvature)
        for bottom, top, width in intervals:
            split = np.clip(yield_depth, bottom, top)
            result += 2 * width * (E * curvature * (split**3 - bottom**3) / 3
                                  + fy * (top**2 - split**2) / 2)
        return result

    limit_force = 2 * plastic_moment / L
    yield_force = 2 * yield_moment / L
    forces = limit_force * np.r_[np.linspace(0, 0.98, 151), np.linspace(0.981, 1, 60)]
    # x=L*t² clusters integration points by the clamp and removes the endpoint
    # curvature singularity from the tip-displacement integral at the limit.
    t, weights = np.polynomial.legendre.leggauss(160)
    t, weights = (t + 1) / 2, weights / 2
    x = L * t**2
    target = forces[:, None] * (L - x)**2 / (2 * L)
    lo = np.zeros_like(target)
    hi = np.full_like(target, fy / (E * h))
    for _ in range(60):
        if np.all(moment(hi) >= target):
            break
        hi = np.where(moment(hi) < target, 2 * hi, hi)
    else:
        raise RuntimeError("Could not bracket the section curvature")

    for _ in range(60):
        trial = (lo + hi) / 2
        below = moment(trial) < target
        lo = np.where(below, trial, lo)
        hi = np.where(below, hi, trial)
    displacement = ((lo + hi) / 2) @ (weights * (L - x) * 2 * L * t)
    return (forces, displacement, {
        "reference_weight_N": reference_weight, "yield_force_N": yield_force,
        "plastic_force_N": limit_force, "plastic_moment_Nm": plastic_moment,
        "plastic_multiplier": limit_force / reference_weight,
        "first_yield_multiplier": yield_force / reference_weight,
        "inertia_m4": inertia, "plastic_modulus_m3": plastic_modulus,
        "limit_tip_mm": float(displacement[-1] * 1e3),
    })


def read_history(path, reference_weight):
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    tip = np.array([0, *(-float(row["tip_uz_m"]) for row in rows)])
    factors = np.array([0, *(float(row["factor"]) for row in rows)])
    return tip, factors * reference_weight


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path, help="Output prefix for PNG and CSV")
    parser.add_argument("histories", nargs="+", metavar="LABEL=CSV")
    args = parser.parse_args()
    forces, displacement, theory = beam_reference(json.loads(args.model.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    (args.output.parent / f"{args.output.name}-reference.json").write_text(
        json.dumps(theory, indent=2) + "\n"
    )
    fig, (full, detail) = plt.subplots(1, 2, figsize=(10.5, 4.8), layout="constrained")
    fig.suptitle("Cantilever under increasing self-weight", fontsize=15, weight="bold")
    curves = [("Euler–Bernoulli, perfect plasticity", displacement, forces)]
    for entry in args.histories:
        label, path = entry.split("=", 1)
        curves.append((label, *read_history(Path(path), theory["reference_weight_N"])))
    with args.output.with_suffix(".csv").open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["curve", "tip_down_mm", "total_weight_kN", "gravity_multiplier"])
        for name, tip, load in curves:
            writer.writerows((name, u * 1e3, force * 1e-3, force / theory["reference_weight_N"])
                             for u, force in zip(tip, load))
    for axis in (full, detail):
        axis.axhline(theory["plastic_force_N"] / 1e3, color="#6d7984", ls="--", lw=1.1,
                     label="Theoretical plastic limit")
        for index, (label, tip, load) in enumerate(curves):
            axis.plot(tip * 1e3, load * 1e-3, label=label, linewidth=1.8,
                      marker="" if index == 0 else ("o", "s", "^", "D", "v", "P")[(index - 1) % 6],
                      markersize=3, markevery=(index % 3, 3), alpha=0.9)
        axis.set_xlabel("Downward tip displacement [mm]")
        axis.set_ylabel("Total applied weight [kN]")
        axis.grid(alpha=0.24)
    full.set_xlim(left=0)
    full.set_ylim(bottom=0)
    detail.set_xlim(left=48)
    detail.set_ylim(bottom=165)
    detail.set_title("Near the plastic limit", loc="left")
    full.legend(loc="lower right", frameon=True, fontsize=8)
    fig.savefig(args.output.with_suffix(".png"), dpi=180)


if __name__ == "__main__":
    main()
