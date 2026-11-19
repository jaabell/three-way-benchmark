#!/usr/bin/env bash
# Run once on the login host and once per allocated compute node.
set -u
export LC_ALL=C
probe() {
    printf '\n$'
    printf ' %q' "$@"
    printf '\n'
    if ! "$@" 2>&1; then
        printf '[unavailable or failed]\n'
    fi
}
probe date -u
probe hostname -f
probe uname -a
probe cat /etc/os-release
probe lscpu
probe lscpu -e
probe lstopo-no-graphics --of console
probe numactl --hardware
probe free -b
probe lsblk -e 7 -o NAME,MODEL,SIZE,TYPE,TRAN,ROTA
probe lspci -nn
probe lshw -short
probe dmidecode --type memory
probe bash -c 'for f in /sys/class/dmi/id/{sys_vendor,product_name,product_version,board_name,bios_version}; do if test -r "$f"; then printf "%s: " "$f"; cat "$f"; fi; done'
probe findmnt -T "$PWD"
probe df -hT "$PWD"
probe ip -br address
probe ip -br link
probe rdma link show
probe ibv_devinfo -v
probe ibstat
probe ibdev2netdev
probe nvidia-smi -L
probe grep Cpus_allowed_list /proc/self/status
probe scontrol show node -o
probe sinfo -Nel
probe srun --mpi=list
probe mpirun --version
probe ompi_info --param pml all
probe ucx_info -v
probe ucx_info -d
