# Copy to cluster/site.sh and fill this using the Esmeralda login instructions.
# One environment per solver is fine. Keep the rank placement identical.
new_node_args=(--constraint=new)  # Replace with the confirmed Slurm feature/partition.
# Optionally pin both 32-rank transports to the same two verified new nodes.
rdma_pair_args=()  # Example: (--nodelist=host1,host2)
time_limit=02:00:00

setup_solver() {
    case "$1" in
        opensees) solver=(OpenSeesMP) ;;
        kratos)
            solver=(python3 "$repo/solvers/kratos.py")
            # Verify the Amesos factory name and MUMPS backend on the installed build.
            export KRATOS_LINEAR_SOLVER_JSON='{"solver_type":"amesos","amesos_solver_type":"Amesos_Mumps"}'
            ;;
        fenicsx) solver=(python3 "$repo/solvers/fenicsx.py") ;;
    esac
}

setup_transport() {
    # Example for Open MPI + UCX. Fill in actual port and TCP interface names.
    # Retain the same PML, rank placement and on-node shared-memory transports.
    export OMPI_MCA_pml=ucx
    export OMPI_MCA_coll="^hcoll,ucc"
    case "$1" in
        default) ;;
        rdma-on)
            export UCX_TLS=rc,sm,self
            export UCX_NET_DEVICES="${ESMERALDA_RDMA_PORT:?Set the confirmed RDMA port}"
            ;;
        rdma-off)
            export UCX_TLS=tcp,sm,self
            export UCX_NET_DEVICES="${ESMERALDA_TCP_INTERFACE:?Set the confirmed TCP interface}"
            ;;
    esac
}

# Confirm the site's Slurm MPI plugin for each solver before using this launcher.
launch() {
    srun --mpi=pmix --distribution=block:block --cpu-bind=cores "$@"
}
