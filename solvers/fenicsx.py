"""DOLFINx 0.11 input. T10 on a four-point rule and fully implicit J2 return mapping."""

from time import perf_counter

import basix.ufl
import dolfinx
from dolfinx import cpp, fem, mesh
from dolfinx.fem import petsc
from mpi4py import MPI
import numpy as np
from petsc4py import PETSc
import ufl

from common import Output, arguments, read_model


def solve(args):
    comm = MPI.COMM_WORLD
    if comm.rank == 0:
        print(f"DOLFINx {dolfinx.__version__}, Basix {basix.__version__}, PETSc {PETSc.Sys.getVersion()}")
        print(MPI.Get_library_version().rstrip("\x00"), flush=True)
    model = read_model(args.mesh)
    p2 = basix.ufl.element("Lagrange", "tetrahedron", 2, shape=(3,))
    xyz, cells = np.empty((0, 3)), np.empty((0, 10), dtype=np.int64)
    if comm.rank == 0:
        with np.load(args.mesh / "mesh.npz") as data:
            xyz, gmsh_cells = data["xyz"], data["cells"]
        permutation = cpp.io.perm_gmsh(mesh.CellType.tetrahedron, 10)
        cells = gmsh_cells[:, permutation]
    domain = mesh.create_mesh(comm, cells, ufl.Mesh(p2), xyz)
    V = fem.functionspace(domain, p2)
    fixed = fem.locate_dofs_geometrical(V, lambda x: np.isclose(x[0], 0, atol=1e-10, rtol=0))
    bcs = [fem.dirichletbc(np.zeros(3, dtype=PETSc.ScalarType), fixed, V)]

    # Degree-two tetrahedron rule: the same four points used by the built-in T10 elements.
    a, b = (5 + 3 * np.sqrt(5)) / 20, (5 - np.sqrt(5)) / 20
    points = np.array([[b, b, b], [a, b, b], [b, a, b], [b, b, a]])
    weights = np.full(4, 1 / 24)
    quadrature = basix.ufl.quadrature_element(
        "tetrahedron", points=points, weights=weights, value_shape=(3, 3)
    )
    Q = fem.functionspace(domain, quadrature)
    dx = ufl.Measure("dx", domain=domain, metadata={
        "quadrature_rule": "custom", "quadrature_points": points, "quadrature_weights": weights,
    })

    force_unit = model["force_unit_n"]
    E = model["young_modulus_pa"] / force_unit
    nu = model["poisson_ratio"]
    yield_stress = model["yield_stress_pa"] / force_unit
    shear, bulk = E / (2 * (1 + nu)), E / (3 * (1 - 2 * nu))
    u, increment = fem.Function(V), fem.Function(V)
    plastic, plastic_next = fem.Function(Q), fem.Function(Q)
    v, du = ufl.TestFunction(V), ufl.TrialFunction(V)
    strain = ufl.sym(ufl.grad(u))
    s_trial = 2 * shear * ufl.dev(strain - plastic)
    # The floor is below yield and keeps the automatic tangent regular at virgin zero stress.
    q_trial = ufl.sqrt(ufl.max_value(1.5 * ufl.inner(s_trial, s_trial), 1.0))
    stress = (bulk * ufl.tr(strain) * ufl.Identity(3)
              + ufl.min_value(1.0, yield_stress / q_trial) * s_trial)
    plastic_update = plastic + ufl.max_value(0.0, 1 - yield_stress / q_trial) * s_trial / (2 * shear)
    gravity = fem.Constant(domain, np.zeros(3, dtype=PETSc.ScalarType))
    residual = (ufl.inner(stress, ufl.sym(ufl.grad(v))) - ufl.dot(gravity, v)) * dx
    F = fem.form(residual)
    J = fem.form(ufl.derivative(residual, u, du))
    update = fem.Expression(plastic_update, points)
    A, r = petsc.create_matrix(J), petsc.create_vector(V)
    linear = PETSc.KSP().create(comm)
    linear.setType("preonly")
    linear.getPC().setType("lu")
    linear.getPC().setFactorSolverType("mumps")
    linear.setOperators(A)
    linear.setErrorIfNotConverged(True)

    owned = np.arange(domain.topology.index_map(3).size_local, dtype=np.int32)
    cell_ids = domain.topology.original_cell_index[owned] + 1
    geometry_nodes = domain.geometry.dofmaps[0][owned].ravel()
    node_ids, first = np.unique(domain.geometry.input_global_indices[geometry_nodes] + 1,
                                return_index=True)
    cell_dofs = np.array([V.dofmap.cell_dofs(cell) for cell in owned], dtype=np.int32)
    node_dofs = cell_dofs.ravel()[first]
    tip = node_dofs[node_ids == model["tip_node"]]
    output = Output(args.output, args.mode, comm.rank)
    if output.full:
        rows, columns = [0, 1, 2, 0, 1, 0], [0, 1, 2, 1, 2, 2]
        stress_expression = fem.Expression(stress, points)
        strain_expression = fem.Expression(strain, points)

    comm.barrier()
    for step in range(1, args.steps + 1):
        start = perf_counter()
        factor = args.target * step / args.steps
        gravity.value[2] = -model["density_kg_m3"] * model["gravity_m_s2"] * factor / force_unit
        for iteration in range(args.max_iterations + 1):
            with r.localForm() as local:
                local.set(0)
            petsc.assemble_vector(r, F)
            r.ghostUpdate(addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE)
            # All trial iterates satisfy the homogeneous clamp; the Newton increment is zero there.
            petsc.set_bc(r, bcs)
            norm = r.norm()
            if norm <= args.tolerance / force_unit:
                break
            if iteration == args.max_iterations or not np.isfinite(norm):
                raise RuntimeError(f"Newton failed at step {step}, residual {norm * force_unit:g} N")
            A.zeroEntries()
            petsc.assemble_matrix(A, J, bcs=bcs)
            A.assemble()
            r.scale(-1)
            linear.solve(r, increment.x.petsc_vec)
            u.x.array[:] += increment.x.array
            u.x.scatter_forward()
        plastic_next.interpolate(update, cells0=owned)
        solve_s = perf_counter() - start

        output_s = 0.0
        if output.full:
            start = perf_counter()
            sigma = stress_expression.eval(domain, owned).reshape(-1, 4, 3, 3)
            eps = strain_expression.eval(domain, owned).reshape(-1, 4, 3, 3)
            output.fields(step, node_ids, u.x.array.reshape(-1, 3)[node_dofs],
                          cell_ids, force_unit * sigma[..., rows, columns], eps[..., rows, columns])
            output_s = perf_counter() - start
        plastic.x.array[:] = plastic_next.x.array
        plastic.x.scatter_forward()
        tip_uz = u.x.array.reshape(-1, 3)[tip[0], 2] if len(tip) else ""
        output.step(step, factor, iteration, solve_s, output_s, tip_uz)

    output.close()
    linear.destroy()
    r.destroy()
    A.destroy()


if __name__ == "__main__":
    solve(arguments())
