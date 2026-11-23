# Node12 memory fix verification · coarse mesh

The rerun used 7,140 T10 elements, the original 30 gravity steps and pinned solver releases. All 54 runs validated on node12 with exclusive allocations, one physical core per MPI rank and three repeats per setting. Newton iteration counts and field bytes matched the reference runs. The largest final tip difference was 0.000 nm.

## Paired node12 before and after

Changes are the median of the per-repeat percentage changes across matched cases. Negative means shorter time.

| Solver | Matched repeats | Wall change | Solve change |
| --- | ---: | ---: | ---: |
| OpenSeesMP | 8 | -11.7% | -12.7% |
| Kratos MUMPS | 9 | -12.4% | -13.4% |
| FEniCSx | 11 | -14.9% | -20.4% |

## Node12 after the fix vs. node13

Launcher wall time is the median of three runs in seconds. The percentage gives node12 relative to node13 for that setting.

| Solver | Ranks | Output | Node12 after (s) | Node13 (s) | Difference |
| --- | ---: | --- | ---: | ---: | ---: |
| OpenSeesMP | 4 | minimal | 13.638 | 13.364 | +2.1% |
| OpenSeesMP | 4 | full | 17.315 | 17.002 | +1.8% |
| OpenSeesMP | 8 | minimal | 10.682 | 11.187 | -4.5% |
| OpenSeesMP | 8 | full | 12.561 | 13.025 | -3.6% |
| OpenSeesMP | 16 | minimal | 13.416 | 13.278 | +1.0% |
| OpenSeesMP | 16 | full | 14.653 | 15.001 | -2.3% |
| Kratos MUMPS | 4 | minimal | 23.311 | 23.064 | +1.1% |
| Kratos MUMPS | 4 | full | 27.488 | 27.127 | +1.3% |
| Kratos MUMPS | 8 | minimal | 21.533 | 22.041 | -2.3% |
| Kratos MUMPS | 8 | full | 23.721 | 24.251 | -2.2% |
| Kratos MUMPS | 16 | minimal | 25.046 | 25.437 | -1.5% |
| Kratos MUMPS | 16 | full | 26.323 | 26.754 | -1.6% |
| FEniCSx | 4 | minimal | 12.288 | 12.169 | +1.0% |
| FEniCSx | 4 | full | 12.518 | 12.531 | -0.1% |
| FEniCSx | 8 | minimal | 10.673 | 11.092 | -3.8% |
| FEniCSx | 8 | full | 11.114 | 11.728 | -5.2% |
| FEniCSx | 16 | minimal | 13.186 | 13.116 | +0.5% |
| FEniCSx | 16 | full | 13.207 | 13.635 | -3.1% |

Esmeralda retained the raw outputs and job map under `runs/node12-memory-2026-11-23/`.
Compute resources were provided by Esmeralda, associated with ANID–Fondecyt project 11220530.
