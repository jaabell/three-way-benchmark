#!/usr/bin/env bash
# Run on the Esmeralda login host. Slurm runs pvserver on the selected compute node.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
node=${1:-node12}
port=${2:-11111}
server=${3:-pvserver}
if [[ "$node" != node12 && "$node" != node13 ]]; then
    printf 'Choose node12 or node13.\n' >&2
    exit 2
fi
if [[ ! "$port" =~ ^[0-9]+$ ]] || (( 10#$port < 1024 || 10#$port > 65535 )); then
    printf 'Choose a TCP port from 1024 to 65535.\n' >&2
    exit 2
fi
export OMP_NUM_THREADS=2 LP_NUM_THREADS=2 LIBGL_ALWAYS_SOFTWARE=1
cd "$repo/views"
exec /opt/slurm-24.11/bin/srun --mpi=none --partition=new --nodelist="$node" \
    --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=4G --time=01:00:00 \
    "$server" --no-mpi --force-offscreen-rendering --bind-address=127.0.0.1 --server-port="$port"
