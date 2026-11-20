# Esmeralda's new partition has two identical node types with 16 physical cores.
export PATH="/opt/slurm-24.11/bin:$PATH"
stack=/mnt/covadongaflash/software/stack/debian13
software=/mnt/covadongaflash/software/bin
new_node_args=(--partition=new --mem=54G)
rdma_pair_args=(--nodelist=node12,node13)
time_limit=${BENCH_TIME_LIMIT:-02:00:00}
pilot_time_limit=00:15:00

setup_solver() {
    mpi_bin="$stack/bin"
    case "$1" in
        opensees) solver=(/mnt/nfshare/bin/openseesmp-ladruno) ;;
        kratos)
            solver=("$software/kratos-mpi-python" "$repo/solvers/kratos.py")
            # Use the installed distributed MUMPS backend for the three-way comparison.
            export KRATOS_LINEAR_SOLVER_JSON=${BENCH_KRATOS_SOLVER:-'{"solver_type":"amesos","amesos_solver_type":"Amesos_Mumps"}'}
            ;;
        fenicsx)
            solver=("$software/fenicsx-python" "$repo/solvers/fenicsx.py")
            mpi_bin=/mnt/covadongaflash/software/fenicsx/current/env/bin
            ;;
    esac
}

setup_transport() {
    export BENCHMARK_TRANSPORT="$1"
}

launch() {
    if [[ "$BENCHMARK_TRANSPORT" != default && "${BENCH_TRANSPORT_LAUNCHER:-srun}" == prrte ]]; then
        # Keep process launch inside this Slurm allocation using PRRTE's Slurm plugin.
        export PATH="$mpi_bin:$PATH" PRTE_MCA_plm_slurm_args=--external-launcher
        "$mpi_bin/mpirun" --prtemca plm slurm --prtemca ras slurm \
            -n "$SLURM_NTASKS" --map-by ppr:16:node:PE=1 --bind-to core --report-bindings \
            bash "$repo/cluster/esmeralda-rank.sh" "$@"
    else
        srun --mpi=pmix --distribution=block:block --cpu-bind=cores \
            bash "$repo/cluster/esmeralda-rank.sh" "$@"
    fi
}
