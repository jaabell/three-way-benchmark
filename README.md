# Esmeralda three-way finite-element benchmark

[Read the illustrated benchmark report](REPORT.md) for the dimensioned model, downloadable Gmsh meshes, ParaView snapshots, and measured pilot timings.

The model is a 6 m steel cantilever with a 400 mm deep, 200 mm wide I-section, 25 mm flanges and a 14 mm web. The root face is clamped in three directions. A uniform downward body force ramps from zero to a common gravity multiplier. All cases use small-strain kinematics, associative J2 flow, perfect plasticity at 250 MPa and straight-sided ten-node quadratic tetrahedra from Gmsh. The four-point integration rule and consistent body force are common across the three solvers. The model uses metres and meganewtons internally, with SI output. This keeps the installed OpenSees J2 local return-map tolerance below its initial residual.

| Mesh | Quadratic tetrahedra | Nodes |
| --- | ---: | ---: |
| Smoke | 7,140 | 13,041 |
| Refinement | 69,600 | 116,781 |
| Production | 237,600 | 372,337 |

The ideal section plastic moment gives a gravity multiplier of 27.895. This is a starting point for identifying the continuum model's plastic limit. The benchmark measures material collapse in small strain. Local or lateral-torsional buckling requires different kinematics and setup.

## Build the inputs

```sh
python model/mesh.py smoke build/smoke
python model/mesh.py refinement build/refinement
python model/mesh.py production build/production
python cluster/matrix.py
```

Mesh generation requires Gmsh with its Python API and NumPy. The common files are `beam.msh`, `mesh.npz` and `model.json`. OpenSees uses Gmsh/METIS partitions, Kratos uses its in-memory METIS importer, and DOLFINx uses its installed mesh partitioner. Output includes actual per-solver ownership. Read the input scripts in `solvers/` to compare their implementations. [OpenSees quadratic tetrahedron](https://opensees.github.io/OpenSeesDocumentation/user/manual/model/elements/TenNodeTetrahedron.html) · [Kratos T10 geometry](https://raw.githubusercontent.com/KratosMultiphysics/Kratos/master/kratos/geometries/tetrahedra_3d_10.h) · [DOLFINx 0.10 mesh API](https://docs.fenicsproject.org/dolfinx/v0.10.0/python/_modules/dolfinx/mesh.html)

## Esmeralda launch

1. Log in with `ssh jle`, read the login guidance, then run `bash cluster/inventory.sh` on the login host. Use the cluster profile `cluster/esmeralda.sh`. It selects Slurm partition `new` and the installed solver commands. The two-node launcher uses UCX on the same physical ports for the RoCE and TCP tests.
2. Confirm the installed OpenSeesMP has the corrected T10 integration, Kratos has StructuralMechanics, ConstitutiveLaws, METIS and Trilinos with a validated installed linear backend, and DOLFINx 0.11 has a working MPI/PETSc/MUMPS stack. Use the installed builds. Record the actual backends and their versions, including the algorithm difference if Kratos uses an iterative solve. Run the elastic and transport pilots before timing production.
3. Check the elastic agreement using tip response and the stress, strain and energy output. The local OpenSees smoke model gave −2.236 mm at one gravity with a linear response between half and full gravity. The T10 OpenSees documentation records an older sixfold integration error, making this comparison important. For transport, verify UCX endpoint logs use the intended inter-node path, check the actual CPU binding and physical hosts, and pin the same two nodes for both transports if the scheduler permits.
4. Use nonlinear pilots to bracket the limit on the refinement and production meshes. Begin below 27.895, approach with smaller load increments and check for a high plastic fraction through the root region and sharply increasing tip compliance. Confirm the result against all solvers and a finer load schedule. A failed Newton solve alone is insufficient evidence of collapse. Choose one common multiplier just below the verified limit and verify every solver completes the same load path. `--pilot-first-factor` can jump over a confirmed elastic range and spend the remaining increments around the limit.
5. Create a calibration JSON with `mesh_sha256` from the production model, the agreed `target`, `steps`, `residual_tolerance` in N and `max_iterations`. Keep the pilot evidence with it. Check each solver's residual normalization and report actual iterations. Run the production matrix and summarize after completion.

```sh
python cluster/matrix.py --pilot elastic --mesh build/smoke --runs runs/elastic --site cluster/esmeralda.sh
python cluster/matrix.py --pilot transport --mesh build/smoke --runs runs/transport --site cluster/esmeralda.sh
python cluster/matrix.py --pilot nonlinear --mesh build/refinement --runs runs/near-limit --site cluster/esmeralda.sh --target 27 --steps 40
python cluster/matrix.py --submit --mesh build/production --runs runs/benchmark --site cluster/esmeralda.sh --calibration calibration.json
python tools/summarize.py runs/benchmark > runs/benchmark/summary.csv
```

The 90 runs cover three solvers, 4/8/16 ranks on one new node, 32 ranks at 16 per node on two new nodes with RDMA on and off, both output modes, and three repeats. The 16-to-32 comparison includes the transition to two nodes. The 32-rank pair isolates the transport setting when placement and hosts match. Jobs use one physical core and numerical-library thread per rank and exclusive node allocations. Per-node inventory captures CPU topology, RAM, NUMA, firmware, disks, mounts, NICs, RDMA, MPI and the scheduler description where available. [Open MPI InfiniBand and RoCE](https://docs.open-mpi.org/en/main/tuning-apps/networking/ib-and-roce.html)

## Output and views

Minimal output records convergence, timings and tip displacement each step. Full output also records all displacements and four-point stress and strain in a common little-endian binary format. Each rank flushes each step. The reported output time includes field queries, serialization and writes through the operating system page cache. It does not measure durable disk commits. Solver launch wall time includes startup and model setup. Per-step solve and output times each use the slowest rank for that phase. Comparisons should report wall, solve and output times, bytes, iterations and physical agreement. The production output is roughly 0.11 GB per step per full run before interface-node duplication and visualization. At 40 steps, budget roughly 200 GB for the 45 full runs.

```sh
python tools/views.py build/production views/opensees32 --opensees-partitions 32
python tools/views.py build/production views/run --run runs/benchmark/CASE_NAME
python tools/render.py views/run
```

The view exporter uses PyVista and writes a ParaView `beam.pvd` series, quadratic T10 VTUs and `energy.csv`. Use **Warp By Vector** with `displacement_m` for true-scale deformations. Use cell scalars for partitions, stress, strain, elastic energy and accumulated plastic dissipation. Energy is derived from the recorded integration-point history in postprocessing. The results also report external work and the balance error. The headless renderer uses Matplotlib and produces a field overview and load history.

## Local verification

An existing serial OpenSees 3.8.0 build ran the smoke mesh locally. The local nonlinear pilot reached 27.058 in 12 increments. The final downward displacement was 60.88 mm, peak von Mises stress was 250 MPa, and estimated plastic dissipation was 33.88 J. Yielding began in the root flanges. The pilot did not establish the continuum collapse load. Its [energy and tip history](results/preliminary/openSees-local-energy.csv) is tracked here. Esmeralda access was subsequently enabled. The [on-cluster preliminary results](results/esmeralda/README.md) include nonlinear agreement between OpenSeesMP and FEniCSx, and the [hardware snapshot](results/esmeralda/hardware.md) records both new nodes. Production measurements require the solver, transport, and collapse calibration pilots.
