# Esmeralda preliminary results

OpenSeesMP job 9020 and FEniCSx job 9021 ran complete nonlinear, four-rank pilots on the same 7,140-element quadratic mesh. They used 30 equal load increments up to 30 times gravity. The tip displacements differ by 0.46 µm, and their peak integration-point stresses and energy histories agree closely. In both pilots, 93.8% of integration points in elements with centroids within 180 mm of the clamp reached 99.9% of the yield stress.

| Final result | OpenSeesMP | FEniCSx |
| --- | ---: | ---: |
| Downward tip displacement | 127.5277 mm | 127.5281 mm |
| Peak von Mises stress | 250.00002 MPa | 250.00000 MPa |
| Elastic energy | 2.89271 kJ | 2.89271 kJ |
| Plastic dissipation | 5.90227 kJ | 5.90231 kJ |
| External work | 8.74660 kJ | 8.74665 kJ |
| Energy balance difference | 0.553% | 0.553% |

At 1× gravity, all three four-rank pilots agreed at a downward tip displacement of 2.235629 mm. Kratos job 9024 used the installed Amesos KLU backend. KLU is a serial factorization inside the MPI analysis, so its scaling is part of the as-installed comparison.

The stated balance difference includes numerical integration of external work over the load increments. The 30× endpoint was the requested pilot endpoint. Establish the continuum limit with the refinement and production meshes before interpreting collapse or comparing production timings.

[Fields](fields.png) · [Load history](history.png) · [OpenSeesMP energy CSV](opensees-smoke-energy.csv) · [FEniCSx energy CSV](fenicsx-smoke-energy.csv) · [Hardware and installed software](hardware.md)

Job 9017 completed the FEniCSx elastic test on both nodes with 32 ranks. UCX reported `rc_mlx5` endpoints over RoCE. Slurm/PMIx printed timeout and collective sequence errors before startup succeeded. TCP attempts 9016 and 9022 were aborted before the solver started. The current working site configuration keeps a single physical port per node in the transport comparison and tests launch adjustments with separate pilot jobs.
