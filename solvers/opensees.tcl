# Run with OpenSeesMP. Each rank builds its own Gmsh partition.
lassign $argv mesh output mode target steps tolerance maxIterations firstFactor
if {$firstFactor eq ""} {set firstFactor 0}
source [file join $mesh model.tcl]
set rank [getPID]
set size [getNP]
source [file join $mesh opensees-$size $rank.tcl]

model BasicBuilder -ndm 3 -ndf 3
# OpenSees J2 initializes the return-mapping residual at 1 in its stress units.
# MN and m make its dimensionful local tolerance smaller than that starting value.
set E [expr {$young_modulus_pa / $force_unit_n}]
set K [expr {$E / (3.0 * (1.0 - 2.0 * $poisson_ratio))}]
set G [expr {$E / (2.0 * (1.0 + $poisson_ratio))}]
set fy [expr {$yield_stress_pa / $force_unit_n}]
nDMaterial J2Plasticity 1 $K $G $fy $fy 0.0 0.0

set hasTip 0
foreach row $nodes {
    lassign $row id x y z fixed gravityForce
    node $id $x $y $z
    if {$fixed} {fix $id 1 1 1}
    if {$id == $tip_node} {set hasTip 1}
}
foreach row $elements {
    element TenNodeTetrahedron {*}$row 1 0.0 0.0 0.0
}
timeSeries Linear 1
pattern Plain 1 1 {
    foreach row $nodes {
        lassign $row id x y z fixed gravityForce
        load $id 0.0 0.0 [expr {$gravityForce / $force_unit_n}]
    }
}

constraints Plain
if {$size == 1} {
    # Optional local check with a preinstalled serial OpenSees.
    numberer RCM
    system UmfPack
} else {
    numberer ParallelRCM
    system Mumps
}
test NormUnbalance [expr {$tolerance / $force_unit_n}] $maxIterations
algorithm Newton
set uniformIncrement [expr {double($target) / $steps}]
set firstIncrement [expr {$firstFactor > 0 ? $firstFactor : $uniformIncrement}]
integrator LoadControl $firstIncrement
analysis Static

proc writeFields {step nodes elements nodeFile cellFile forceUnit} {
    foreach row $nodes {
        set id [lindex $row 0]
        set values [nodeDisp $id]
        puts -nonewline $nodeFile [binary format i2q3 [list $step $id] $values]
    }
    foreach row $elements {
        set id [lindex $row 0]
        for {set point 1} {$point <= 4} {incr point} {
            set stress [lmap s [eleResponse $id material $point stress] {expr {$s * $forceUnit}}]
            lassign [eleResponse $id material $point strain] ex ey ez gxy gyz gxz
            set strain [list $ex $ey $ez [expr {$gxy/2}] [expr {$gyz/2}] [expr {$gxz/2}]]
            puts -nonewline $cellFile [binary format i3q12 [list $step $id $point] \
                [concat $stress $strain]]
        }
    }
    flush $nodeFile
    flush $cellFile
}

set progress [open [file join $output progress-$rank.csv] w]
puts $progress "step,factor,iterations,solve_s,output_s,tip_uz_m"
if {$mode eq "full"} {
    set nodeFile [open [file join $output nodes-$rank.bin] wb]
    set cellFile [open [file join $output cells-$rank.bin] wb]
}
barrier
for {set step 1} {$step <= $steps} {incr step} {
    set start [clock microseconds]
    if {$step == 2 && $firstFactor > 0} {
        integrator LoadControl [expr {double($target - $firstFactor) / ($steps - 1)}]
    }
    set code [analyze 1]
    set solveTime [expr {([clock microseconds] - $start) * 1.0e-6}]
    if {$code != 0} {error "Newton failed at step $step (return code $code)"}

    set fieldTime 0
    if {$mode eq "full"} {
        set start [clock microseconds]
        writeFields $step $nodes $elements $nodeFile $cellFile $force_unit_n
        set fieldTime [expr {([clock microseconds] - $start) * 1.0e-6}]
    }
    set tip ""
    if {$hasTip} {set tip [nodeDisp $tip_node 3]}
    set factor [expr {$firstFactor > 0 ? $firstFactor + ($step - 1) *
        double($target - $firstFactor) / ($steps - 1) : $step * $uniformIncrement}]
    puts $progress "$step,$factor,[testIter],$solveTime,$fieldTime,$tip"
    flush $progress
}
if {$mode eq "full"} {
    close $nodeFile
    close $cellFile
}
close $progress
barrier
wipe
