# Esmeralda preliminary results

OpenSeesMP job 9020, FEniCSx job 9021 and Kratos job 9036 ran complete nonlinear, four-rank pilots on the same 7,140-element quadratic mesh. They used 30 equal load increments up to 30 times gravity. Their final tip displacements agree within 0.46 µm. In the OpenSeesMP and FEniCSx pilots, 93.8% of integration points in elements with centroids within 180 mm of the clamp reached 99.9% of the yield stress.

| Final result | OpenSeesMP | FEniCSx | Kratos |
| --- | ---: | ---: | ---: |
| Downward tip displacement | 127.5277 mm | 127.5281 mm | 127.5281 mm |
| Peak von Mises stress | 250.00002 MPa | 250.00000 MPa | 250.00000 MPa |
| Elastic energy | 2.89271 kJ | 2.89271 kJ | 2.89271 kJ |
| Plastic dissipation | 5.90227 kJ | 5.90231 kJ | 5.90231 kJ |
| External work | 8.74660 kJ | 8.74665 kJ | 8.74665 kJ |
| Energy balance difference | 0.553% | 0.553% | 0.553% |

At 1× gravity, all three four-rank pilots agreed at a downward tip displacement of 2.235629 mm. Kratos job 9030 reached 30× gravity in 15 equal increments with a final downward tip displacement of 127.9520 mm, peak stress of 250.00 MPa, and plastic dissipation of 5.94471 kJ. A local OpenSees check on the same 15-step load path gave 127.9515 mm and 5.94466 kJ. Kratos used its installed Amesos KLU backend, which factors on one rank inside its MPI analysis.

The stated balance difference includes numerical integration of external work over the load increments. The last unit-gravity increment in the smoke pilots added about 55 mm of downward tip displacement, compared with 2.24 mm per unit of gravity in the elastic range. The FEniCSx refinement pilot (job 9025, 69,600 elements, 16 ranks) reached 29× gravity and 78.84 mm downward displacement. Newton failed at 30×. This gives a numerical bracket for calibration on the production mesh.

[Fields](fields.png) · [Load history](history.png) · [Three-solver tip comparison](tip-load-comparison.png) · [OpenSeesMP energy CSV](opensees-smoke-energy.csv) · [FEniCSx energy CSV](fenicsx-smoke-energy.csv) · [Kratos 30-step energy CSV](kratos-smoke-30steps-energy.csv) · [Kratos 15-step energy CSV](kratos-smoke-energy.csv) · [Refinement tip history](fenicsx-refinement-tip.csv) · [Hardware and installed software](hardware.md)

Job 9017 completed the FEniCSx elastic test on both nodes with 32 ranks. UCX reported `rc_mlx5` endpoints over RoCE. Slurm/PMIx printed timeout and collective sequence errors before startup succeeded. TCP attempts 9016 and 9022 were aborted before the solver started. Retry 9029 reached Slurm/PMIx inter-node timeouts with no solver output and was stopped after repeated errors. A subsequent FEniCSx pilot, job 9033, completed with PRRTE and the Slurm launcher. UCX reported TCP on both nodes. RoCE job 9037 used the same PRRTE launcher as TCP job 9033 and completed with `rc_mlx5` on both nodes. These two-step trials are single measurements. The original RoCE run used `srun` and logged substantial launch delays. The current working site configuration keeps a single physical port per node in the transport comparison and tests launch adjustments with separate pilot jobs.

Production pilots did not complete. FEniCSx job 9032 reached 29× and 81.69 mm downward displacement before MUMPS stopped during the final load step with error −9. Kratos job 9031 stopped at the first production-mesh increment after Newton failed to converge. Both pilots used minimal output.

[Production tip history](fenicsx-production-tip.csv) · [Pilot timings](pilot-timings.csv) · [ParaView connection and file index](../VISUALIZATION.md)
