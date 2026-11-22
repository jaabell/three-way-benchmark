# Esmeralda benchmark archive

[Illustrated report](../../REPORT.md) · [Original CPU timings](scaling-timings.md) · [Node13 CPU timings](node13-timings.md) · [GPU pilots](gpu-pilot.md) · [Hardware](hardware.md) · [ParaView](../VISUALIZATION.md)

The private repository contains the model, Gmsh meshes, benchmark scripts, explorer source, and both timing datasets. The node13 analysis contains 53 original runs and 55 replacements at 4, 8, and 16 ranks. The original 32-rank RoCE and TCP experiments used nodes 12 and 13.

## Files on Esmeralda

Connect with `ssh jle`. The following paths are relative to `/mnt/covadongaflash/users/jaabell/three-way-benchmark/`.

| Material | Path |
| --- | --- |
| Coarse, fine, and production meshes | `build/smoke/`, `build/refinement/`, `build/production/` |
| Original cases, solver input snapshots, hardware, bindings, and field files | `runs/smoke-scaling/`, `runs/refinement-scaling/` |
| Node13 reruns, original-job mapping, and comparison Markdown and CSVs | `runs/node13-scaling/` |
| Original scaling report and force–displacement data | `runs/scaling-report/` |
| GPU pilots and diagnostic attempts | `runs/gpu-pilot/` |
| ParaView animations and field exports | `views/` |
| Prepared browser data, solver memory, website bundle, and 1080p slides | `runs/web-explorer/` |
| Source and report snapshot, website bundle, slides, and checksums | `archive/2026-11-21/` |

The dated archive packages the Git snapshot and recording assets. The run directories hold the raw numerical outputs and job logs. The website snapshot uses the original CPU scaling and GPU tables. The balanced comparison is in the node13 report and CSVs.
