#!/usr/bin/env bash
set -euo pipefail
root=$1
repo=$root
campaign=$2
case_name=$3
mesh_name=$4
material=$5
system=$6
algorithm=$7
output=$8
flush=$9
target=${10}
steps=${11}
out="$campaign/$case_name"
mkdir "$out"
source "$root/cluster/esmeralda.sh"
setup_solver opensees
setup_transport default
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
release=/mnt/covadongaflash/software/opensees-ladruno/releases/20261120-1400-1f08e5934
cp "$release/VERSION" "$out/"
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$SLURM_JOB_ID" "$SLURM_JOB_NODELIST" "$SLURM_NTASKS" "$mesh_name" "$material" \
    "$system" "$algorithm" "$output" "$flush" "$target" "$steps" > "$out/case.tsv"
srun --mpi=none -n "$SLURM_NTASKS" --cpu-bind=cores bash -c \
    'printf "%s\t%s\n" "$SLURM_PROCID" "$(awk "/Cpus_allowed_list/ {print \$2}" /proc/self/status)"' \
    | sort -n > "$out/binding.tsv"
mode=minimal
recorder=tcl
if [[ "$output" != minimal ]]; then
    mode=full
    recorder=$output
fi
TIMEFORMAT=$'%3R'
{ time launch "$release/OpenSeesMP" "$campaign/inputs/opensees.tcl" \
    "$root/build/$mesh_name" "$out" "$mode" "$target" "$steps" 0.1 18 0 \
    "$material" "$system" "$algorithm" "$recorder" "$flush" > "$out/solver.log" 2>&1; } \
    2> "$out/wall.txt"
for ((rank=0; rank<SLURM_NTASKS; rank++)); do
    test "$(wc -l < "$out/progress-$rank.csv")" = "$((steps+1))"
done
touch "$out/launcher-complete"
