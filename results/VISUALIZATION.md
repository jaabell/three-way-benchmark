# Open the Esmeralda results in ParaView

Use the same ParaView version on your workstation as the `pvserver` installed on Esmeralda. The files already live on cluster storage.

1. On your workstation, start the server in a Slurm allocation and leave this terminal open.

   ```sh
   ssh -t jle 'bash /mnt/covadongaflash/users/jaabell/three-way-benchmark/cluster/paraview.sh'
   ```

   The script uses `pvserver` from the compute node's PATH. You can pass a node, a port, and the installed server's full path. For example, run the script with `node12 11111 /path/to/pvserver` if the installation is outside PATH. Wait for the server to print that it is accepting connections.

2. In another workstation terminal, forward the port to the server through Esmeralda. The example uses the script's default node and port.

   ```sh
   ssh -N -J jle -L 127.0.0.1:11111:127.0.0.1:11111 jaabell@node12
   ```

3. In your workstation's ParaView, choose **File → Connect → Add Server**. Select **Client / Server**, host `127.0.0.1`, port `11111`, and manual startup. Click **Connect**.

4. Use **File → Open** to browse the cluster directory `/mnt/covadongaflash/users/jaabell/three-way-benchmark`. The ParaView server reads these paths directly. Press **Ctrl+C** in the first terminal when you finish so Slurm releases the allocation.

| What to open | Path relative to the project directory |
| --- | --- |
| FEniCSx nonlinear animation | `views/esmeralda-nonlinear-fenicsx/beam.pvd` |
| OpenSeesMP nonlinear animation | `views/esmeralda-nonlinear-opensees/beam.pvd` |
| Kratos nonlinear animation | `views/esmeralda-kratos-mumps/beam.pvd` |
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
