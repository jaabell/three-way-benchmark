# OpenSeesMP exploration

Same steel I-beam, T10 mesh, 250 MPa J2 perfect plasticity, and 1× gravity steps as the original benchmark.
ASD uses associated von Mises flow, zero hardening, full backward Euler, closed-form derivatives and the algorithmic tangent.
The installed Ladruño build is `1f08e5934`. Runs used one physical core per rank on exclusive Esmeralda allocations.
The coarse sweep used 7,140 T10 elements and 30 steps. The fine pilots used 69,600 T10 elements and 29 steps.
The global residual tolerance was 0.1 N with an 18-iteration cap. Krylov–Newton used a subspace dimension of 3.

## Main comparisons

- J2Plasticity → ASD, default MUMPS · 11.00 → 11.03 s (+0.3%).
- ASD, general → symmetric-indefinite MUMPS · 11.03 → 7.50 s (-32.0%).
- ASD, Tcl → Ladruño with per-step flush · 12.79 → 11.00 s (-14.0%).
- ASD with symmetric MUMPS, Tcl → Ladruño with per-step flush · 9.14 → 7.74 s (-15.4%).
- Fine mesh, ASD with general → symmetric MUMPS · 156.27 → 94.01 s. One 16-rank pilot per setting.

## Timings

Medians in seconds. Ladruño records on commit inside `analyze`. Its time is included in the analysis column. Tcl extraction and writes are timed separately. Wall time covers launch through recorder close.

| Case | Output | Runs | Wall (s) | Analyze (s) | Tcl I/O (s) | Close (s) | MB | Iterations | Tip ↓ (mm) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Fine / node12 / 16 · ASD · mumps · newton | minimal | 1 | 156.27 | 154.45 | — | 0.000 | 0.00 | 53 | 78.83944 |
| Fine / node12 / 16 · ASD · mumps-sym · newton | minimal | 1 | 94.01 | 92.18 | — | 0.000 | 0.00 | 53 | 78.83944 |
| Fine / node12 / 16 · J2 · mumps · newton | minimal | 1 | 156.68 | 154.85 | — | 0.000 | 0.00 | 53 | 78.83942 |
| Coarse / node13 / 8 · ASD · mumps-amd · newton | minimal | 3 | 11.20 | 10.11 | — | 0.000 | 0.00 | 52 | 127.52811 |
| Coarse / node13 / 8 · ASD · mumps · krylov | minimal | 3 | 8.95 | 7.84 | — | 0.000 | 0.00 | 69 | 127.52811 |
| Coarse / node13 / 8 · ASD · mumps · newton | Ladruño, flush 0 s | 3 | 11.00 | 10.03 | — | 0.029 | 99.14 | 52 | 127.52811 |
| Coarse / node13 / 8 · ASD · mumps · newton | Ladruño, flush 10 s | 3 | 11.45 | 10.28 | — | 0.077 | 86.79 | 52 | 127.52811 |
| Coarse / node13 / 8 · ASD · mumps · newton | minimal | 3 | 11.03 | 9.93 | — | 0.000 | 0.00 | 52 | 127.52811 |
| Coarse / node13 / 8 · ASD · mumps · newton | tcl | 3 | 12.79 | 9.92 | 1.91 | 0.051 | 105.87 | 52 | 127.52811 |
| Coarse / node13 / 8 · ASD · mumps-sym · newton | Ladruño, flush 0 s | 3 | 7.74 | 6.68 | — | 0.030 | 98.36 | 52 | 127.52811 |
| Coarse / node13 / 8 · ASD · mumps-sym · newton | minimal | 3 | 7.50 | 6.39 | — | 0.000 | 0.00 | 52 | 127.52811 |
| Coarse / node13 / 8 · ASD · mumps-sym · newton | tcl | 3 | 9.14 | 6.28 | 1.92 | 0.051 | 105.87 | 52 | 127.52811 |
| Coarse / node13 / 8 · J2 · mumps · newton | Ladruño, flush 0 s | 3 | 11.31 | 10.25 | — | 0.033 | 98.31 | 52 | 127.52766 |
| Coarse / node13 / 8 · J2 · mumps · newton | minimal | 3 | 11.00 | 9.90 | — | 0.000 | 0.00 | 52 | 127.52766 |
| Coarse / node13 / 8 · J2 · mumps · newton | tcl | 3 | 12.92 | 10.07 | 1.93 | 0.023 | 105.87 | 52 | 127.52766 |

## Validation

- Maximum tip-history difference from the corresponding J2 baseline was 0.4575 µm.
- The coarse legacy/ASD field comparison gave peak component differences of 0.001385 MPa in stress and 6.89e-08 in strain.
- Checked 12 Ladruño/Tcl full-field pairs at every step. Maximum differences were 4.12e-12 m, 0.0102 Pa, and 4.4e-14 strain.
- The completed ASD jobs logged no full backward Euler fallback diagnostics.
- Ladruño stores f64 nodal displacement and the six stress and engineering-strain components at all four Gauss points. It also stores mesh metadata. Level 1 compression was used throughout. Flush 0 writes every step.
- MUMPS options are automatic ordering with general storage, symmetric-indefinite storage with `-matrixType 2`, and AMD with `-ICNTL7 0`.

## Probes

| Trial | Job | Accepted steps |
| --- | ---: | ---: |
| check-asd-hdf5 | 10213 | 30/30 |
| check-asd-mumps-amd-newton | 10217 | 30/30 |
| check-asd-mumps-krylov | 10218 | 30/30 |
| check-asd-mumps-sym-newton | 10216 | 30/30 |
| check-asd-profile-spd-newton | 10215 | 12/30 |
| check-asd-tcl | 10214 | 30/30 |
| pilot-asd-hdf5 | 10210 | 0/30 |
| pilot-asd-tcl | 10211 | 0/30 |

The four-minute `ParallelProfileSPD` probe reached 12 of 30 steps.

Jobs 10210, 10211 stopped before solver launch. The wrapper was fixed and the trials repeated.

Raw results on Esmeralda · `runs/opensees-exploration-2026-11-24/`.
Computing resources provided by Esmeralda through ANID–Fondecyt project 11220530.
