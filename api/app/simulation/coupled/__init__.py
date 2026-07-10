"""
Coupled primary-secondary solve.

JavaTC treats the primary and secondary as independent resonators. This
package solves the FULL coupled system - the object that shows frequency
splitting, the primary driving-point impedance with the secondary
installed, and (for export) a SPICE-ready network.

Everything is built from matrices the rest of the pipeline already
produces (C, L, A, m, L_p, C_p), so a coupled solve is cheap linear
algebra - no FEM, fully inside the fast/analyze tier.
"""
from .coupled_system import (
    CoupledSystem,
    DrivenResponse,
    coupled_mode_frequencies,
    primary_driven_response,
    primary_input_impedance,
)
from .spice_export import export_spice_subcircuit, reconstruct_from_spice

__all__ = [
    "CoupledSystem",
    "DrivenResponse",
    "coupled_mode_frequencies",
    "primary_driven_response",
    "primary_input_impedance",
    "export_spice_subcircuit",
    "reconstruct_from_spice",
]
