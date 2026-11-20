"""Send single-rank PETSc Newton systems to the cluster's CUDA JAX runtime."""

import os
from pathlib import Path
import struct
import subprocess
import sys
from time import perf_counter

import numpy as np


SYSTEM_SIZE = struct.Struct("<II")


def read_array(stream, count, dtype):
    size = count * np.dtype(dtype).itemsize
    data = stream.read(size)
    if len(data) != size:
        raise EOFError("Incomplete CUDA sparse solver response or request")
    return np.frombuffer(data, dtype=dtype)


class CudaSparseSolver:
    def __init__(self, python):
        self.python = python
        self.method = os.environ.get("BENCH_FENICSX_JAX_METHOD", "qr")
        if self.method not in ("qr", "cg"):
            raise ValueError("Select qr or cg for the CUDA linear solver")

    def __enter__(self):
        self.worker = subprocess.Popen(
            [self.python, str(Path(__file__).resolve()), self.method],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            env={**os.environ, "JAX_PLATFORMS": "cuda", "JAX_ENABLE_X64": "true",
                 "XLA_PYTHON_CLIENT_PREALLOCATE": "false"},
        )
        return self

    def __exit__(self, error, *_):
        self.worker.stdin.close()
        self.worker.stdout.close()
        code = self.worker.wait()
        if code and error is None:
            raise RuntimeError(f"CUDA sparse solver exited with status {code}")

    def solve(self, matrix, rhs, increment):
        offsets, columns, values = matrix.getValuesCSR()
        if len(values) > np.iinfo(np.int32).max:
            raise ValueError("The CUDA solver requires 32-bit CSR indices")
        load = rhs.array_r
        if values.dtype != np.float64 or load.dtype != np.float64:
            raise ValueError("This pilot requires real double precision")
        self.worker.stdin.write(SYSTEM_SIZE.pack(len(load), len(values)))
        for array in (offsets.astype(np.int32, copy=False), columns.astype(np.int32, copy=False),
                      values, load):
            self.worker.stdin.write(memoryview(np.ascontiguousarray(array)).cast("B"))
        if self.method == "cg":
            diagonal = matrix.getDiagonal()
            try:
                self.worker.stdin.write(memoryview(diagonal.array_r).cast("B"))
            finally:
                diagonal.destroy()
        self.worker.stdin.flush()
        result = read_array(self.worker.stdout, len(load), np.float64)
        if not np.isfinite(result).all():
            raise ValueError("CUDA sparse solver returned an invalid Newton increment")
        increment.array[:] = result


def worker(method):
    import jax
    import jax.numpy as jnp
    from jax.experimental.sparse import CSR
    from jax.experimental.sparse.linalg import spsolve
    from jax.scipy.sparse.linalg import cg

    device, = jax.devices("cuda")
    print(f"JAX {jax.__version__} sparse {method.upper()} on {device.device_kind}, FP64",
          file=sys.stderr, flush=True)

    @jax.jit
    def solve_cg(values, columns, offsets, rhs, diagonal):
        matrix = CSR((values, columns, offsets), shape=(rhs.size, rhs.size))
        result, _ = cg(lambda x: matrix @ x, rhs, M=lambda x: x / diagonal,
                       tol=1e-10, maxiter=200_000)
        relative_residual = jnp.linalg.norm(matrix @ result - rhs) / jnp.linalg.norm(rhs)
        return result, relative_residual

    source, sink = sys.stdin.buffer, sys.stdout.buffer
    while header := source.read(SYSTEM_SIZE.size):
        rows, nnz = SYSTEM_SIZE.unpack(header)
        offsets = read_array(source, rows + 1, np.int32)
        columns = read_array(source, nnz, np.int32)
        values = read_array(source, nnz, np.float64)
        rhs = read_array(source, rows, np.float64)
        diagonal = read_array(source, rows, np.float64) if method == "cg" else None
        start = perf_counter()
        inputs = jax.device_put((values, columns, offsets, rhs), device)
        diagnostic = ""
        if method == "cg":
            if not (diagonal > 0).all():
                raise ValueError("Jacobi CG requires a positive diagonal")
            result, error = solve_cg(*inputs, jax.device_put(diagonal, device))
            if not float(error) < 1e-5:
                raise RuntimeError(f"CUDA CG relative residual {error} exceeds tolerance")
            diagnostic = f" relative_residual={float(error):.3e}"
            result = np.asarray(result)
        else:
            result = np.asarray(spsolve(*inputs, tol=1e-12, reorder=3))
        print(f"cuda_{method}_s={perf_counter() - start:.6f} rows={rows} nnz={nnz}{diagnostic}",
              file=sys.stderr, flush=True)
        sink.write(memoryview(result).cast("B"))
        sink.flush()


if __name__ == "__main__":
    worker(sys.argv[1])
