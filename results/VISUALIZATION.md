# Open the Esmeralda results in ParaView

Esmeralda runs ParaView Server 6.2.1. Use ParaView 6.2.x on your workstation. The files already live on cluster storage.

1. On your workstation, submit a server on the partition that can access the project storage.

   ```sh
   ssh -t jle 'paraview-server -p new -n 1 -m 4G -t 1:00:00'
   ```

   Once the job starts, the command prints the private node address, port, and connection ID. Use `ssh jle 'paraview-server --list'` to retrieve them again. The job can queue while the benchmarks occupy both nodes.

2. On your workstation, use the printed SSH tunnel command with the `jle` alias. Substitute the printed address and port for the placeholders and leave the tunnel open.

   ```sh
   ssh -N -L 127.0.0.1:11111:NODE_IP:SERVER_PORT jle
   ```

3. Start your workstation's ParaView with `paraview --connect-id=CONNECTION_ID` using the printed connection ID. Choose **File → Connect → Add Server**. Select **Client / Server**, host `127.0.0.1`, port `11111`, and manual startup. Click **Connect**.

4. Use **File → Open** to browse the cluster directory `/mnt/covadongaflash/users/jaabell/three-way-benchmark`. The server reads these paths directly. Disconnect when finished, or stop the allocation with `ssh jle 'paraview-server --stop JOB_ID'` using the printed job ID.

| What to open | Path relative to the project directory |
| --- | --- |
| FEniCSx nonlinear animation | `views/esmeralda-nonlinear-fenicsx/beam.pvd` |
| OpenSeesMP nonlinear animation | `views/esmeralda-nonlinear-opensees/beam.pvd` |
| Kratos nonlinear animation | `views/esmeralda-kratos-mumps/beam.pvd` |
| FEniCSx RTX 5090 nonlinear animation | `views/esmeralda-gpu-fenicsx-smoke/beam.pvd` |
| Fine-mesh nonlinear animations | `views/esmeralda-refinement-<solver>/beam.pvd` for `opensees`, `kratos`, or `fenicsx` once export jobs 9674–9676 finish |
| Elastic animations | `views/esmeralda-elastic-<solver>/beam.pvd` |
| Actual FEniCSx partition and fields with RoCE or TCP | `views/esmeralda-fenicsx-rdma-on-prrte/beam.pvd` or `views/esmeralda-fenicsx-rdma-off/beam.pvd` |
| Actual Kratos MUMPS partitions with RoCE or TCP | `views/esmeralda-kratos-mumps-rdma-on/beam.pvd` or `views/esmeralda-kratos-mumps-rdma-off/beam.pvd` |
| Planned OpenSeesMP production partition | `views/production/opensees-partitions-32.vtu` |
| Production Gmsh mesh | `build/production/beam.msh` (open in Gmsh) |
| Energy and load history | `energy.csv` next to each `beam.pvd` |
| Timing data | `results/esmeralda/pilot-timings.csv` |
| Hardware reports | `inventory/esmeralda/` and `results/esmeralda/hardware.md` |

Open a `.pvd` once to load its full time series. Click **Apply**, then **Play**. Add **Warp By Vector** with `displacement_m` and scale 1 for true-scale shape. Color by `von_Mises_Pa`, `equivalent_plastic_strain`, `elastic_energy_J_m3`, `plastic_dissipation_J_m3`, or `partition`. Use the stress and strain arrays to inspect individual tensor components. The `energy.csv` can be plotted with **Plot Data**.

[ParaView remote visualization documentation](https://docs.paraview.org/en/v6.2.1/ReferenceManual/parallelDataVisualization.html)
