"""
Operating-field visualization.

The real field around an energized coil is a superposition of basis fields
we already have from the FEM electrostatics, weighted by the operating
phasors from the coupled drive solve - no new FEM per view:

    phi(r,z) = sum_k V_k u_k  +  V_p u_p_profile  +  offset u_p_uniform

where {u_k} are the winding tent fields (topload on the top node) and the
two u_p_* are the primary basis fields (its 0->V_p differential profile and
its common-mode). The magnetic vector potential A_phi is a closed-form
ring-kernel superposition of the operating currents.

This package evaluates the basis fields on a regular (r,z) grid and
superposes them for a given drive; see the submodules.
"""
from .grid import FieldGrid
from .electrostatic_basis import ElectrostaticFieldBasis, compute_electrostatic_basis
from .assembly import assemble_electrostatic_field
from .magnetic_basis import (
    MagneticFieldBasis,
    assemble_magnetic_field,
    compute_magnetic_basis,
)

__all__ = [
    "FieldGrid",
    "ElectrostaticFieldBasis",
    "compute_electrostatic_basis",
    "assemble_electrostatic_field",
    "MagneticFieldBasis",
    "compute_magnetic_basis",
    "assemble_magnetic_field",
]
