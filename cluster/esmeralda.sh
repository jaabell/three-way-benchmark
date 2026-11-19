# Esmeralda's new partition has two identical node types with 16 physical cores.
export PATH="/opt/slurm-24.11/bin:$PATH"
stack=/mnt/covadongaflash/software/stack/debian13
software=/mnt/covadongaflash/software/bin
new_node_args=(--partition=new --mem=54G)
rdma_pair_args=(--nodelist=node12,node13)
time_limit=02:00:00
pilot_time_limit=00:15:00

setup_solver() {
    case "$1" in
        opensees) solver=(/mnt/nfshare/bin/openseesmp-ladruno) ;;
        kratos)
            solver=("$software/kratos-mpi-python" "$repo/solvers/kratos.py")
            # This Trilinos build lacks a distributed sparse direct solver.
            export KRATOS_LINEAR_SOLVER_JSON=${BENCH_KRATOS_SOLVER:-'{"solver_type":"multi_level","tolerance":1e-9,"max_iteration":1000}'}
            ;;
        fenicsx) solver=("$software/fenicsx-python" "$repo/solvers/fenicsx.py") ;;
    esac
}

setup_transport() {
    export BENCHMARK_TRANSPORT="$1"
    if [[ "$1" != default ]]; then
        # Apply the same job-local PMIx launch settings to both MPI data paths.
        export SLURM_PMIX_FENCE=tree SLURM_PMIX_DIRECT_CONN=false
    fi
}

launch() {
    srun --mpi=pmix --distribution=block:block --cpu-bind=cores bash "$repo/cluster/esmeralda-rank.sh" "$@"
}
