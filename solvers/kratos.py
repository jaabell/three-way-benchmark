"""Kratos MPI input using its compiled von Mises law and Trilinos solver."""

import json
import os
from time import perf_counter

import KratosMultiphysics as KM
import KratosMultiphysics.ConstitutiveLawsApplication
import KratosMultiphysics.MetisApplication
import KratosMultiphysics.mpi
import KratosMultiphysics.TrilinosApplication
from KratosMultiphysics.StructuralMechanicsApplication.structural_mechanics_analysis import (
    StructuralMechanicsAnalysis,
)
import numpy as np

from common import Output, arguments, read_model


class BeamAnalysis(StructuralMechanicsAnalysis):
    def __init__(self, args):
        self.args = args
        self.beam = read_model(args.mesh)
        self.comm = KM.ParallelEnvironment.GetDefaultDataCommunicator()
        parameters = self.setup_parameters()
        super().__init__(KM.Model(), KM.Parameters(json.dumps(parameters)))

    def setup_parameters(self):
        args, beam = self.args, self.beam
        force_unit = beam["force_unit_n"]
        # Kratos 10.3 reports the free-DOF L2 residual divided by its DOF count.
        free_dofs = 3 * (beam["node_count"] - beam["clamp_node_count"])
        materials = args.output / "materials.json"
        if self.comm.Rank() == 0:
            materials.write_text(json.dumps({"properties": [{
                "model_part_name": "beam",
                "properties_id": 1,
                "Material": {
                    "constitutive_law": {"name": "SmallStrainIsotropicPlasticity3DVonMisesVonMises"},
                    "Variables": {
                        "DENSITY": beam["density_kg_m3"] / force_unit,
                        "YOUNG_MODULUS": beam["young_modulus_pa"] / force_unit,
                        "POISSON_RATIO": beam["poisson_ratio"],
                        "YIELD_STRESS_TENSION": beam["yield_stress_pa"] / force_unit,
                        "YIELD_STRESS_COMPRESSION": beam["yield_stress_pa"] / force_unit,
                        "FRACTURE_ENERGY": 1.0e9 / force_unit,
                        "HARDENING_CURVE": 3
                    },
                    "Tables": {}
                }
            }]}, indent=2) + "\n")
        self.comm.Barrier()
        return {
            "problem_data": {
                "problem_name": "I-beam",
                "parallel_type": "MPI",
                "echo_level": 0,
                "start_time": 0.0,
                "end_time": float(args.steps)
            },
            "solver_settings": {
                "solver_type": "static",
                "model_part_name": "beam",
                "domain_size": 3,
                "model_import_settings": {
                    "input_type": "mdpa",
                    "input_filename": str(args.mesh / "beam"),
                    "partition_in_memory": True
                },
                "material_import_settings": {"materials_filename": str(materials)},
                "time_stepping": {"time_step": 1.0},
                "move_mesh_flag": False,
                "compute_reactions": False,
                "convergence_criterion": "residual_criterion",
                "residual_relative_tolerance": 0.0,
                "residual_absolute_tolerance": args.tolerance / (force_unit * free_dofs),
                "max_iteration": args.max_iterations,
                "linear_solver_settings": json.loads(os.environ["KRATOS_LINEAR_SOLVER_JSON"])
            }
        }

    def ModifyInitialGeometry(self):
        for node in self.model["beam.clamp"].Nodes:
            for dof in (KM.DISPLACEMENT_X, KM.DISPLACEMENT_Y, KM.DISPLACEMENT_Z):
                node.Fix(dof)

    def RunSolutionLoop(self):
        args = self.args
        solver = self._GetSolver()
        part = solver.GetComputingModelPart()
        if not self.comm.IsDistributed() or self.comm.Size() < 2:
            raise RuntimeError("Kratos requires its MPI runtime for this benchmark")
        local = part.GetCommunicator().LocalMesh()
        owned_nodes = list(local.Nodes)
        elements = list(local.Elements)
        if self.comm.SumAll(len(elements)) != self.beam["element_count"]:
            raise RuntimeError("Kratos partition does not own every element exactly once")
        node_ids = [node.Id for node in owned_nodes]
        cell_ids = [element.Id for element in elements]
        tip_node = next((node for node in owned_nodes if node.Id == self.beam["tip_node"]), None)
        output = Output(args.output, args.mode, self.comm.Rank())
        self.comm.Barrier()
        for step in range(1, args.steps + 1):
            start = perf_counter()
            self.time = self._AdvanceTime()
            factor = args.target * step / args.steps
            acceleration_z = -self.beam["gravity_m_s2"] * factor
            for node in part.Nodes:
                node.SetSolutionStepValue(KM.VOLUME_ACCELERATION_Z, acceleration_z)
            self.InitializeSolutionStep()
            solver.Predict()
            if not solver.SolveSolutionStep():
                raise RuntimeError(f"Newton failed at step {step}, gravity factor {factor:g}")
            self.FinalizeSolutionStep()
            solve_s = perf_counter() - start
            iterations = part.ProcessInfo[KM.NL_ITERATION_NUMBER]

            output_s = 0.0
            if output.full:
                start = perf_counter()
                displacement = [list(node.GetSolutionStepValue(KM.DISPLACEMENT)) for node in owned_nodes]
                stress, strain = [], []
                for element in elements:
                    stress.append([list(row) for row in element.CalculateOnIntegrationPoints(
                        KM.CAUCHY_STRESS_VECTOR, part.ProcessInfo)])
                    # SmallDisplacement provides its infinitesimal B*u strain for this query.
                    strain.append([list(row) for row in element.CalculateOnIntegrationPoints(
                        KM.GREEN_LAGRANGE_STRAIN_VECTOR, part.ProcessInfo)])
                stress = self.beam["force_unit_n"] * np.array(stress).reshape(len(elements), 4, 6)
                strain = np.array(strain).reshape(len(elements), 4, 6)
                strain[..., 3:] *= 0.5
                output.fields(step, node_ids, np.array(displacement).reshape(-1, 3),
                              cell_ids, stress, strain)
                output_s = perf_counter() - start
            tip = "" if tip_node is None else tip_node.GetSolutionStepValue(KM.DISPLACEMENT_Z)
            output.step(step, factor, iterations, solve_s, output_s, tip)
        output.close()


if __name__ == "__main__":
    BeamAnalysis(arguments()).Run()
