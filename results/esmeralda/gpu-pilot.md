# RTX 5090 beam pilots

The FEniCSx input uses Esmeralda’s installed JAX 0.11.2 CUDA runtime for FP64 sparse linear solves. FEniCSx assembles the tangent and residual, advances Newton, and writes fields on the host. A persistent Python process moves the CSR matrix and right-hand side to the GPU and returns the displacement increment. The CPU baseline uses PETSc MUMPS on the same host. These comparisons include transfer overhead and the effect of choosing a different linear solver. [JAX sparse direct solver](https://docs.jax.dev/en/latest/_autosummary/jax.experimental.sparse.linalg.spsolve.html)

Both variants use one MPI rank and one allocated physical core on `gpu01`, with an AMD Ryzen 9 9950X, an NVIDIA GeForce RTX 5090 (32,607 MiB usable VRAM), and NVIDIA driver 615.71.09. The GPU allocation is exclusive, including for the CPU controls. Slurm job 9684 captured the hardware and driver inventory. The meshes, material, volume quadrature and convergence requirements match the main benchmark. [Main scaling report](scaling.md)

| Profile | T10 elements | Gravity path | Output | GPU solver |
| --- | ---: | --- | --- | --- |
| Smoke elastic | 7,140 | 0.5×, 1× | Full | Sparse QR |
| Smoke nonlinear | 7,140 | 30 increments of 1×, through 30× | Full | Sparse QR |
| Fine elastic | 69,600 | 0.5×, 1× | Minimal | Jacobi-preconditioned conjugate gradients |

The fine-mesh QR attempt (job 9693) hit a cuSOLVER allocation failure on the first increment. The CG trials with 20,000 and 200,000 allowed iterations returned true relative residuals of $3.45\times10^{-3}$ and $3.76\times10^{-6}$ on the first increment. The recorded fine-mesh comparison (jobs 9713–9715) uses a $10^{-5}$ relative linear acceptance threshold and retains the benchmark's 0.1 N absolute Newton convergence tolerance. [JAX conjugate gradients](https://docs.jax.dev/en/latest/_autosummary/jax.scipy.sparse.linalg.cg.html)

The RTX 5090 comparisons are separate from the 4–32-rank CPU sweep on nodes 12 and 13. The installed OpenSeesMP and Kratos benchmark backends continue to run on the CPU.

## Measurements

All three smoke elastic repeats per backend converged. The largest difference in downward tip displacement across the two increments was 15 pm. GPU QR took 4.4× the CPU MUMPS wall time.

| Smoke elastic | Repeats | Median wall (s) | Median solve (s) | Downward tip at 1× (mm) |
| --- | ---: | ---: | ---: | ---: |
| CPU MUMPS | 3 | 3.508 | 0.662 | 2.235629112 |
| GPU sparse QR | 3 | 15.514 | 12.459 | 2.235629097 |

The first nonlinear CPU/GPU pair completed all 30 increments at 127.528 mm downward tip displacement. Wall time was 19.101 s for CPU MUMPS (job 9696) and 309.965 s for GPU QR (job 9694). The largest tip difference at an accepted increment was 29 pm.

## Esmeralda files

Paths relative to the project directory `/mnt/covadongaflash/users/jaabell/three-way-benchmark`.

| Path | Contents |
| --- | --- |
| `runs/gpu-pilot/pilots.tsv` | Case directories, backends, and Slurm job IDs |
| `runs/gpu-pilot/inventory-9684.log` | Hardware and driver inventory |
| `runs/gpu-pilot/current.md` | Interim timing table |
| `runs/gpu-pilot/benchmark.md` and `benchmark.csv` | Final timings, tip agreement, and individual measurements from Slurm job 9705 |
| `views/esmeralda-gpu-fenicsx-smoke/beam.pvd` | Nonlinear GPU animation from export job 9709, following successful completion of job 9694 |

The standard FEniCSx input selects MUMPS by default. Set `BENCH_FENICSX_JAX=/mnt/covadongaflash/software/jupyter/envs/jax/bin/python` in a one-rank Slurm GPU job to select sparse QR. Set `BENCH_FENICSX_JAX_METHOD=cg` for the elastic conjugate-gradient pilot. The solver log identifies the CUDA device and records each linear solve. The CUDA phase includes transfers, JAX dispatch and synchronization. Launcher wall time includes the Python worker, data exchange, host assembly and field writes.
