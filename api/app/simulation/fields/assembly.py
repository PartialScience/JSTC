"""
Superpose the grid-sampled basis fields with the operating phasors into the
complex electrostatic potential of an energized coil.

    phi(r,z) = sum_k V_k u_k  +  V_p u_diff  +  offset u_uniform

* V_k are the operating nodal voltages (V_0 = 0 at the grounded base).
* u_diff is the primary's differential (0->V_p) field: the profile field for
  a hot outer end, or (uniform - profile) for a hot inner end (the reversed
  profile is exactly 1 - p, so its field is u_uniform - u_profile).
* offset is the primary common-mode: 0 for a grounded cold end, or the
  charge-neutral value for a floating primary,
      offset = -(sum_k V_k Q_k + V_p Q_diff) / Q_uniform,
  with Q_* the primary charge each basis field induces.
"""
from __future__ import annotations

from typing import Literal

import numpy as np

from app.simulation.fields.electrostatic_basis import ElectrostaticFieldBasis

ReferenceMode = Literal["floating", "grounded"]
HotEnd = Literal["inner", "outer"]


def assemble_electrostatic_field(
    basis: ElectrostaticFieldBasis,
    node_voltages: np.ndarray,
    primary_voltage: complex = 0.0,
    reference_mode: ReferenceMode = "floating",
    hot_end: HotEnd = "outer",
) -> np.ndarray:
    """Assemble the complex operating potential on the grid.

    Args:
        basis: the grid-sampled electrostatic basis.
        node_voltages: complex operating voltages for the free nodes
            t_1..t_N (length N); the grounded base t_0 is prepended as 0.
        primary_voltage: the primary EMF V_p [V] (ignored without a primary).
        reference_mode: primary common-mode reference.
        hot_end: which primary end carries V_p.

    Returns:
        (nz, nr) complex array; cells outside the field domain are NaN.
    """
    n_tents = basis.tent_fields.shape[0]
    if len(node_voltages) != n_tents - 1:
        raise ValueError(
            f"expected {n_tents - 1} node voltages, got {len(node_voltages)}"
        )

    V = np.concatenate([[0.0 + 0.0j], np.asarray(node_voltages, dtype=complex)])
    # sum_k V_k u_k  (contract the basis over the node axis)
    phi = np.tensordot(V, basis.tent_fields, axes=(0, 0)).astype(complex)

    if basis.has_primary:
        u_prof = basis.primary_profile_field
        u_unif = basis.primary_uniform_field
        Q = basis.primary_charges
        Q_tent = Q[:n_tents]
        Q_prof = Q[n_tents]
        Q_unif = Q[n_tents + 1]

        if hot_end == "inner":
            u_diff = u_unif - u_prof
            Q_diff = Q_unif - Q_prof
        else:
            u_diff = u_prof
            Q_diff = Q_prof

        if reference_mode == "grounded":
            offset = 0.0 + 0.0j
        else:  # floating: enforce charge neutrality on the primary
            induced = complex(V @ Q_tent) + primary_voltage * Q_diff
            offset = -induced / Q_unif

        phi = phi + primary_voltage * u_diff + offset * u_unif

    return phi
