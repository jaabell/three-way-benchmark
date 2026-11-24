# Options for the separate OpenSeesMP benchmark.
proc benchmarkMaterial {material E K G nu fy} {
    if {$material eq "j2"} {
        nDMaterial J2Plasticity 1 $K $G $fy $fy 0.0 0.0
    } elseif {$material eq "asd"} {
        nDMaterial ASDPlasticMaterial3D 1 VonMises_YF VonMises_PF LinearIsotropic3D_EL \
            BackStress(TensorLinearHardeningFunction):YieldStress(ScalarLinearHardeningFunction): \
            Begin_Internal_Variables BackStress 0 0 0 0 0 0 YieldStress $fy End_Internal_Variables \
            Begin_Model_Parameters InitialP0 0 MassDensity 0 YoungsModulus $E PoissonsRatio $nu \
                ScalarLinearHardeningParameter 0 TensorLinearHardeningParameter 0 End_Model_Parameters \
            Begin_Integration_Options integration_method Full_Backward_Euler derivatives Closed_Form \
                tangent_type Algorithmic return_to_yield_surface Disabled \
                f_absolute_tol 1e-9 stress_absolute_tol 1e-8 n_max_iterations 60 End_Integration_Options
    } else {
        error "Unknown material: $material"
    }
}

proc benchmarkSystem {solver} {
    switch -- $solver {
        mumps {system Mumps}
        mumps-sym {system Mumps -matrixType 2}
        mumps-amd {system Mumps -ICNTL7 0}
        profile-spd {system ParallelProfileSPD}
        default {error "Unknown system: $solver"}
    }
}

proc benchmarkAlgorithm {name} {
    switch -- $name {
        newton {algorithm Newton}
        krylov {algorithm KrylovNewton -iterate current -increment current -maxDim 3}
        default {error "Unknown algorithm: $name"}
    }
}
