# Kratos linear solver comparison

Esmeralda’s Kratos 10.3.0 MPI release `v10.3.0-20261120-100016` exposes distributed MUMPS 5.9.0 through Amesos and SuperLU_DIST 7.2.0 through Amesos and Amesos2. The benchmark profile selects Amesos MUMPS. All new timings use the cluster’s installed software.

## Matched nonlinear pilots

Each run used the same 7,140-element quadratic mesh, four MPI ranks on Esmeralda’s `new` partition, 30 increments to 30× gravity, a 0.1 N Newton residual tolerance, and full output. Each row is one measurement. The KLU and GMRES references used the preceding Kratos MPI release.

| Linear configuration | Slurm job | Wall | Solve | Field output | Newton iterations | Downward tip |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Amesos MUMPS | 9481 | 29.238 s | 24.045 s | 4.082 s | 56 | 127.528112 mm |
| Amesos SuperLU_DIST | 9482 | 31.204 s | 26.112 s | 3.953 s | 56 | 127.528087 mm |
| Amesos2 SuperLU_DIST | 9483 | 41.213 s | 36.001 s | 4.091 s | 56 | 127.528109 mm |
| AztecOO GMRES with overlapping KLU subdomains | 9064 | 119.376 s | 114.404 s | 3.972 s | 56 | 127.528112 mm |
| Amesos KLU | 9036 | 173.375 s | 168.155 s | 4.067 s | 56 | 127.528112 mm |

MUMPS cut wall time by 83.1% relative to the historical KLU pilot. All three distributed direct variants reproduced the final tip displacement within 0.03 µm and wrote the same 105.05 MB. The revised benchmark compares Kratos, OpenSeesMP, and FEniCSx using MUMPS through their respective installed interfaces.

## Production-mesh elastic checks

All three backends completed the 237,600-element elastic pilot in two steps to 1× gravity. Each used 16 ranks on one node and minimal output. They reproduced the FEniCSx production-mesh tip displacement of 2.243512 mm.

| Linear configuration | Slurm job | Wall | Solve | Newton iterations |
| --- | ---: | ---: | ---: | ---: |
| Amesos MUMPS | 9484 | 64.047 s | 55.142 s | 2 |
| Amesos SuperLU_DIST | 9485 | 204.698 s | 195.301 s | 2 |
| Amesos2 SuperLU_DIST | 9486 | 69.640 s | 60.417 s | 2 |

These are elastic checks on the production mesh. The repeated nonlinear production matrix awaits calibration.

## Two-node MUMPS transport checks

Both pilots used 32 ranks on nodes 12 and 13, PRRTE with its Slurm launcher, and the same physical links. The 7,140-element mesh used two elastic increments to 1× gravity and full field output. UCX logs confirmed RoCE and TCP on both nodes.

| Transport | Slurm job | Wall | Solve | Field output |
| --- | ---: | ---: | ---: | ---: |
| RoCE RDMA | 9487 | 12.807 s | 1.123 s | 0.052 s |
| TCP | 9488 | 14.608 s | 1.635 s | 0.046 s |

These short, single-run checks confirm both transport configurations. They provide limited evidence for performance on a longer load path. Set `BENCH_TRANSPORT_LAUNCHER=prrte` when repeating them.

## Repeat a case

Run the pilot from the Esmeralda project directory. The site profile defaults to Amesos MUMPS.

```sh
python3 cluster/matrix.py --pilot nonlinear --solver kratos \
  --mesh build/smoke --runs runs/kratos-mumps-repeat \
  --site cluster/esmeralda.sh --target 30 --steps 30 --max-iterations 18
```

To rerun with one of the SuperLU_DIST variants, set `BENCH_KRATOS_SOLVER` to the corresponding JSON before submitting.

| Backend | Linear solver settings |
| --- | --- |
| Amesos MUMPS | `{"solver_type":"amesos","amesos_solver_type":"Amesos_Mumps"}` |
| Amesos SuperLU_DIST | `{"solver_type":"amesos","amesos_solver_type":"Amesos_Superludist"}` |
| Amesos2 SuperLU_DIST | `{"solver_type":"amesos2","amesos2_solver_type":"amesos2_superludist"}` |

Use all job ranks for Amesos2 SuperLU_DIST, as required by the installed Trilinos build. The earlier [GMRES preset](../../cluster/kratos-gmres-schwarz.json) remains available. Its production elastic check hit the Slurm time limit, and its refinement elastic check failed Newton convergence at step 1.

[Direct-solver timing data](kratos-direct-timings.csv) · [Historical timings](kratos-linear-timings.csv)
