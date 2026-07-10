from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Tuple

import numpy as np

from app.formulas.magnetic import (
    coaxial_circle_geometric_mutual_inductance,
    coaxial_ring_self_geometric_inductance,
)
from app.models.coil_models import PrimarySpec, SecondaryConductorSpec
from app.simulation.distributed_element_matrices.coupling.base import MutualCouplingSolver
from app.simulation.distributed_element_matrices.turn_sampling import (
    secondary_turn_points,
    segment_start_indices,
)

if TYPE_CHECKING:
    from app.models.simulation_models import SimulatableTeslaCoil


class CoaxialRingMutualCouplingSolver(MutualCouplingSolver):
    """Coupling vector via the coaxial-ring model.

    Both windings are reduced to stacks of coaxial rings - the secondary
    at its turn boundaries (identically to the inductance matrix solver),
    the primary at its turn midpoints (PrimarySpec.ring_centers, weighted
    by the fractional final turn). Every primary-secondary ring pair
    contributes the Maxwell mutual-inductance formula; turn-level values
    are grouped into segments with the shared turn_sampling convention.

    Supported kwargs:
        turn_interpolation_density (int): Dense samples per turn for
            inverting the secondary's turn_fxn (default 10, matching the
            inductance solver).
    """

    _DEFAULT_TURN_INTERPOLATION_DENSITY = 10

    @property
    def turn_interpolation_density(self) -> int:
        return self._kwargs.get(
            "turn_interpolation_density",
            self._DEFAULT_TURN_INTERPOLATION_DENSITY,
        )

    def coupling_vector(
        self, coil: SimulatableTeslaCoil
    ) -> Tuple[float, ...]:
        """Compute the geometric coupling vector m (length N)."""
        if coil.primary is None:
            raise ValueError("Coupling requires a coil with a primary")

        secondary = coil.secondary
        slices = tuple(self.discretizer.get_slices(secondary, coil.discretization_order))
        m_full = self._compute_full_turn_vector(
            secondary, coil.primary, self.turn_interpolation_density
        )
        indices = segment_start_indices(secondary, slices, len(m_full))
        m_seg = np.add.reduceat(m_full, indices)
        return tuple(float(v) for v in m_seg)

    @staticmethod
    @functools.lru_cache
    def _compute_full_turn_vector(
        secondary: SecondaryConductorSpec,
        primary: PrimarySpec,
        turn_interpolation_density: int,
    ) -> np.ndarray:
        """Mutual inductance between the whole primary and each secondary
        turn ring: m_full[i] = sum_p w_p * M(ring_p, ring_i)."""
        sec_points = secondary_turn_points(secondary, turn_interpolation_density)
        prim_centers = primary.ring_centers()
        prim_weights = primary.ring_turn_fractions()

        m_full = np.zeros(len(sec_points))
        for (rp, zp), w in zip(prim_centers, prim_weights):
            for i, (rs, zs) in enumerate(sec_points):
                m_full[i] += w * coaxial_circle_geometric_mutual_inductance(
                    rp, rs, zs - zp, 0.0,
                )
        return m_full


@functools.lru_cache
def primary_geometric_self_inductance(primary: PrimarySpec) -> float:
    """Geometric self-inductance of the primary winding.

    Ring model with fractional-turn weighting:

        L_p = sum_pq w_p w_q M_pq

    where the diagonal uses the ring self-inductance with the
    cross-section's uniform-current GMD (the low-frequency convention,
    matching JavaTC's Ldc), and off-diagonals the Maxwell mutual formula.
    Multiply by mu_0 * unit_scale for Henries.
    """
    centers = primary.ring_centers()
    weights = primary.ring_turn_fractions()
    gmd = primary.cross_section.gmd

    total = 0.0
    for p, ((rp, zp), wp) in enumerate(zip(centers, weights)):
        total += wp * wp * coaxial_ring_self_geometric_inductance(rp, gmd)
        for q in range(p + 1, len(centers)):
            (rq, zq), wq = centers[q], weights[q]
            total += 2.0 * wp * wq * coaxial_circle_geometric_mutual_inductance(
                rp, rq, zq - zp, 0.0,
            )
    return total


def primary_voltage_profile(primary: PrimarySpec) -> np.ndarray:
    """Normalized potential of each primary ring along the winding.

    In operation the primary is not equipotential: current through its
    (self + mutual) inductance produces an end-to-end voltage V_p, and the
    potential at a point s along the winding (relative to the cold/grounded
    terminal) is jw times the PARTIAL flux linkage from that terminal up to
    s. Normalizing by the total linkage gives a geometry-only profile
    p_k in (0, 1) that the field solve scales by V_p.

    p_k is the partial linkage evaluated at ring k's midpoint:

        S_p   = w_p * sum_q w_q M_pq          (ring p's weighted linkage)
        p_k   = (cumsum(S)_k - S_k/2) / sum(S)

    where M is the ring self/mutual inductance (same formula and GMD as
    primary_geometric_self_inductance, so sum(S) == that L_p). The profile
    is returned in ring order (turn 0 first); the field solve reverses it
    when the hot end is the first turn.

    Returns:
        Length-(n_rings) array of normalized potentials, ascending.
    """
    centers = primary.ring_centers()
    weights = primary.ring_turn_fractions()
    gmd = primary.cross_section.gmd
    n = len(centers)

    linkage = np.zeros(n)
    for p, ((rp, zp), wp) in enumerate(zip(centers, weights)):
        inner = 0.0
        for q, ((rq, zq), wq) in enumerate(zip(centers, weights)):
            if q == p:
                m_pq = coaxial_ring_self_geometric_inductance(rp, gmd)
            else:
                m_pq = coaxial_circle_geometric_mutual_inductance(rp, rq, zq - zp, 0.0)
            inner += wq * m_pq
        linkage[p] = wp * inner

    total = linkage.sum()
    if total <= 0:
        raise ValueError("Primary has non-positive total inductance")
    return (np.cumsum(linkage) - 0.5 * linkage) / total
