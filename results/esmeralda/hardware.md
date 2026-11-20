# Esmeralda hardware and software

Inventory captured through Slurm on 2026-11-19, plus a separate inventory of the login host. The benchmark uses partition `new` and writes to the NVMe-backed NFS mount `/mnt/covadongaflash`. The NFS client reports v4.2 over TCP with eight connections. Changing the MPI transport changes inter-node solver messages. Output continues to use the shared filesystem.

| Host | CPU | RAM | Motherboard | BIOS | Network and storage |
| --- | --- | ---: | --- | --- | --- |
| node12 | Ryzen 9 5950X, 16 cores, 32 threads, one NUMA node | 62.7 GiB visible; 58,000 MiB in Slurm | Gigabyte X570 AORUS ELITE WIFI | F32 | Two 25 GbE Mellanox ConnectX-4 Lx ports, both RoCE active. 476.9 GiB Kingston KC3000 local NVMe |
| node13 | Ryzen 9 5950X, 16 cores, 32 threads, one NUMA node | 62.7 GiB visible; 58,000 MiB in Slurm | Gigabyte X570S AORUS PRO AX | F5 | Two 25 GbE Mellanox ConnectX-4 Lx ports, both RoCE active. 476.9 GiB Kingston KC3000 local NVMe |
| esmeralda login | Ryzen 9 5900X, 12 cores, 24 threads | 31.3 GiB visible | Gigabyte X570 AORUS ELITE WIFI | F36e | Kingston 476.9 GiB and 3.6 TiB NVMe, Seagate 14.6 TiB SATA |

The compute nodes run Debian 13 and Slurm 24.11.5. The login host runs Ubuntu 22.04.1. The snapshot of the shared store shows 11 TiB total and 8.9 TiB free. Full CPU maps, PCI and device listings, storage mounts, RoCE link state and scheduler descriptions are in the workspace under `inventory/esmeralda/`. Jobs retain their own allocation, binding and inventory reports.

The GPU pilots run on `gpu01`, with a Ryzen 9 9950X (16 cores, 32 threads), 60,000 MiB schedulable RAM, and a GeForce RTX 5090 reporting 32,607 MiB VRAM and compute capability 12.0. The host has a Kingston KC3000 NVMe drive and two active Mellanox ConnectX-4 Lx RoCE ports. Slurm inventory job 9684 records NVIDIA driver 615.71.09. [GPU configurations and measurements](gpu-pilot.md)

| Solver | Installed pilot build |
| --- | --- |
| OpenSeesMP | ladruño, 3.8.0, commit `dfdf974251e05e30c8d0f338b0ea0de7fdd8cef4`, Open MPI 5, MUMPS |
| FEniCSx | DOLFINx and Basix 0.11.0, PETSc 3.25.6 with MUMPS, Open MPI 5.0.11 in the site's conda environment |
| Kratos | Kratos 10.3.0, Trilinos 14.4.0, METIS, Open MPI 5. The 2026-11-20 release adds Amesos MUMPS 5.9.0 and Amesos and Amesos2 SuperLU_DIST 7.2.0. Earlier pilot records used the 2026-11-19 release with serial KLU. |

Acknowledge ANID–Fondecyt project 11220530 in research outputs that benefit from Esmeralda, as requested in the cluster login notice.
