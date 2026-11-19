#!/usr/bin/env bash
set -euo pipefail
# Use the same physical port for RoCE and TCP, on the nodes' primary addresses.
if [[ "$BENCHMARK_TRANSPORT" != default ]]; then
    case "$(hostname -s)" in
        node12) rdma=rocep10s0f0:1; ethernet=enp10s0f0np0 ;;
        node13) rdma=rocep11s0f1:1; ethernet=enp11s0f1np1 ;;
        *) printf 'Unexpected node for transport comparison\n' >&2; exit 1 ;;
    esac
    export OMPI_MCA_pml=ucx OMPI_MCA_coll='^hcoll,ucc'
    # Open MPI's UCX auto-selection filters out TCP unless explicitly enabled.
    export OMPI_MCA_pml_ucx_tls=any OMPI_MCA_pml_ucx_devices=any
    case "$BENCHMARK_TRANSPORT" in
        rdma-on) export UCX_TLS=rc,sm,self UCX_NET_DEVICES="$rdma" ;;
        rdma-off) export UCX_TLS=tcp,sm,self UCX_NET_DEVICES="$ethernet" ;;
    esac
fi
exec "$@"
