#!/usr/bin/env bash
set -euo pipefail
repo=$1
site=$2
mesh=$3
out=$4
name=$5
ranks=$6
network=$7
mode=$8
target=$9
steps=${10}
tolerance=${11}
iterations=${12}

mkdir -p "$(dirname "$out")"
mkdir "$out"
source "$site"
setup_solver "$name"

export OMP_NUM_THREADS=1 OMP_DYNAMIC=false OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1 MKL_DYNAMIC=false BLIS_NUM_THREADS=1
export EIGEN_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export XDG_CACHE_HOME="$out/cache"
cd "$out"
cp "$mesh/model.json" model.json
cp "$site" site.sh
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$name" "$ranks" "$network" "$mode" "$target" "$steps" "$SLURM_JOB_ID" > case.tsv
printf '%s\n' "$SLURM_JOB_NODELIST" > nodelist
scontrol show job "$SLURM_JOB_ID" > allocation.txt
srun --mpi=none --nodes="$SLURM_JOB_NUM_NODES" --ntasks="$SLURM_JOB_NUM_NODES" --ntasks-per-node=1 \
    --output="$out/hardware-%N.txt" bash "$repo/cluster/inventory.sh"
srun --mpi=none --ntasks="$ranks" --distribution=block:block --cpu-bind=cores bash -c \
    'cpus=$(awk "/Cpus_allowed_list/ {print \$2}" /proc/self/status); printf "%s\t%s\t%s\n" "$SLURM_PROCID" "$(hostname)" "$cpus"' \
    | sort -n > binding.tsv

setup_transport "$network"
# Record UCX endpoint selection on transport pilots, outside the production matrix.
if [[ -f "$(dirname "$out")/pilot.json" && "$network" != default ]]; then
    export UCX_LOG_LEVEL=info
fi
{
    printf 'solver command:'
    printf ' %q' "${solver[@]}"
    printf '\n'
    executable=$(command -v "${solver[0]}")
    printf '%s\n' "$executable"
    if [[ -f "$executable" ]]; then
        sha256sum "$executable"
        ldd "$executable" || true
    fi
    env | sort | grep -E '^(UCX_|OMPI_MCA_|FI_|I_MPI_|OMP_|MKL_|KRATOS_LINEAR_SOLVER_JSON=)' || true
} > runtime.txt 2>&1

if [[ "$name" == opensees ]]; then
    solver+=("$repo/solvers/opensees.tcl")
fi
# Separate the allocation/setup overhead from the solver process timing. Bash's
# time works with site launch functions as well as ordinary MPI commands.
TIMEFORMAT=$'%3R\t%3U\t%3S'
{ time launch "${solver[@]}" "$mesh" "$out" "$mode" "$target" "$steps" "$tolerance" "$iterations" \
       > solver.log 2>&1; } 2> timing.tsv
touch launcher-complete
