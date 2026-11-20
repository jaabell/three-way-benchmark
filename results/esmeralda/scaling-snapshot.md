# Esmeralda rank scaling

Interim snapshot taken 2026-11-20 11:26 -03. [Model, beam limit and cluster reports](scaling.md)

Values are median launcher wall-clock seconds across validated repeats. Parentheses show how many of the three repeats contributed.
The CSVs also report solve and output times through 29× gravity.

## Smoke

21/90 runs validated.

| MPI ranks | Network | OpenSeesMP minimal | OpenSeesMP full | Kratos MUMPS minimal | Kratos MUMPS full | FEniCSx minimal | FEniCSx full |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | Single node | — | 17.00 (1/3) | — | 27.13 (1/3) | — | 12.53 (1/3) |
| 8 | Single node | — | — | — | — | 12.15 (1/3) | — |
| 16 | Single node | 16.28 (1/3) | 16.08 (2/3) | — | 31.24 (2/3) | 15.70 (1/3) | 14.67 (2/3) |
| 32 | RoCE | 25.58 (1/3) | 26.29 (2/3) | 41.47 (1/3) | 42.34 (1/3) | — | 24.01 (1/3) |
| 32 | TCP | — | — | 51.97 (1/3) | 47.31 (1/3) | 29.91 (1/3) | — |

- OpenSeesMP history from job 9500 (16 ranks).
- Kratos MUMPS history from job 9505 (16 ranks).
- FEniCSx history from job 9503 (16 ranks).

## Refinement

0/90 runs validated.

| MPI ranks | Network | OpenSeesMP minimal | OpenSeesMP full | Kratos MUMPS minimal | Kratos MUMPS full | FEniCSx minimal | FEniCSx full |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | Single node | — | — | — | — | — | — |
| 8 | Single node | — | — | — | — | — | — |
| 16 | Single node | — | — | — | — | — | — |
| 32 | RoCE | — | — | — | — | — | — |
| 32 | TCP | — | — | — | — | — | — |
