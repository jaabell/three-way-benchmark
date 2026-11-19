# Kratos linear solver comparison

The installed Kratos 10.3.0 MPI build exposes Amesos KLU and LAPACK. Runtime checks confirmed that Amesos MUMPS, SuperLU_DIST, and ScaLAPACK are unavailable, along with Amesos2. The original Kratos timing uses KLU, which factors on one rank inside the MPI analysis.

## Matched nonlinear pilots

Both runs used the same 7,140-element quadratic mesh, four MPI ranks, 30 increments to 30× gravity, a 0.1 N Newton residual tolerance, and full output. The two nodes have the same CPU model and different motherboards. Each row is one measurement.

| Kratos linear configuration | Slurm job | Node | Wall | Solve | Field output | Newton iterations | Downward tip |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| Amesos KLU | 9036 | node12 | 173.375 s | 168.155 s | 4.067 s | 56 | 127.528112 mm |
| AztecOO GMRES with overlapping Ifpack/Amesos KLU subdomains | 9064 | node13 | 119.376 s | 114.404 s | 3.972 s | 56 | 127.528112 mm |

Distributed GMRES reduced wall time by 31.1%. The overlapping local factorizations serve as preconditioners. GMRES solves the distributed global system. The 300-vector Krylov space and three partition-overlap layers are important settings for this model. The matched pilot retains metres and meganewtons internally.

## Run the preset

From the Esmeralda project directory, use the same mesh and case settings and select the [GMRES preset](../../cluster/kratos-gmres-schwarz.json).

```sh
BENCH_KRATOS_SOLVER="$(cat cluster/kratos-gmres-schwarz.json)" \
python3 cluster/matrix.py --pilot nonlinear --solver kratos \
  --mesh build/smoke --runs runs/kratos-gmres-repeat \
  --site cluster/esmeralda.sh --target 30 --steps 30 --max-iterations 18
```

The site default remains the original KLU configuration. The GMRES result establishes a faster smoke-mesh run. Production-scale validation is required before replacing the benchmark baseline. A Kratos/Trilinos build exposing distributed MUMPS would also allow a direct-solver comparison with OpenSeesMP and FEniCSx.

[Kratos Trilinos solver documentation](https://github.com/KratosMultiphysics/Kratos/blob/master/applications/TrilinosApplication/README.md)
