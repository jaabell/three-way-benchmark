# Esmeralda node13 rank scaling

All 108 timings use node13. The comparison combines 53 original node13 runs and 55 validated replacements. [Method and findings](scaling.md#balanced-node13-comparison) · [Job map](node13-replacements.tsv)

Values are median launcher wall-clock seconds across validated repeats. Parentheses show how many of the three repeats contributed.
The CSVs also report solve and output times through 29× gravity.

## Coarse

54/54 runs validated on node13.

| MPI ranks | Network | OpenSeesMP minimal | OpenSeesMP full | Kratos MUMPS minimal | Kratos MUMPS full | FEniCSx minimal | FEniCSx full |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | Single node | 13.36 (3/3) | 17.00 (3/3) | 23.06 (3/3) | 27.13 (3/3) | 12.17 (3/3) | 12.53 (3/3) |
| 8 | Single node | 11.19 (3/3) | 13.03 (3/3) | 22.04 (3/3) | 24.25 (3/3) | 11.09 (3/3) | 11.73 (3/3) |
| 16 | Single node | 13.28 (3/3) | 15.00 (3/3) | 25.44 (3/3) | 26.75 (3/3) | 13.12 (3/3) | 13.63 (3/3) |

- OpenSeesMP history from job 9532 (16 ranks).
- Kratos MUMPS history from job 9766 (16 ranks).
- FEniCSx history from job 9778 (16 ranks).

## Fine

54/54 runs validated on node13.

| MPI ranks | Network | OpenSeesMP minimal | OpenSeesMP full | Kratos MUMPS minimal | Kratos MUMPS full | FEniCSx minimal | FEniCSx full |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | Single node | 206.71 (3/3) | 239.94 (3/3) | 327.19 (3/3) | 364.11 (3/3) | 168.12 (3/3) | 168.38 (3/3) |
| 8 | Single node | 180.82 (3/3) | 199.62 (3/3) | 262.08 (3/3) | 282.45 (3/3) | 144.58 (3/3) | 145.08 (3/3) |
| 16 | Single node | 165.10 (3/3) | 174.72 (3/3) | 275.32 (3/3) | 286.63 (3/3) | 126.71 (3/3) | 126.12 (3/3) |

- OpenSeesMP history from job 9801 (16 ranks).
- Kratos MUMPS history from job 9793 (16 ranks).
- FEniCSx history from job 9805 (16 ranks).
