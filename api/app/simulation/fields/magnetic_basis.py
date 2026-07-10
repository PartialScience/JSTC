"""
Magnetic field basis: the azimuthal vector potential A_phi of each secondary
segment (unit current) and of the primary (unit current), sampled on the
grid. The operating A_phi is a superposition weighted by the drive currents:

    A_phi(r,z) = sum_k I_k A_seg[k]  +  I_p A_primary

with no FEM - each contribution is a closed-form coaxial-loop kernel summed
over the segment's turns. The client differentiates A_phi to get B.

A_phi of a unit-current loop (radius a at height z0) is scale-invariant
(depends only on coordinate ratios); B = curl(A_phi phi_hat) picks up the
length scale from the grid spacing, applied client-side in metres.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from scipy.special import ellipe, ellipk

from app.simulation.distributed_element_matrices.turn_sampling import (
    secondary_turn_points,
    segment_start_indices,
)
from app.simulation.fields._cache import GeometryLruCache
from app.simulation.fields.grid import FieldGrid

MU0 = 4e-7 * np.pi
_SAMPLES_PER_TURN = 4
_CACHE = GeometryLruCache(maxsize=6)


def loop_vector_potential(R: np.ndarray, Z: np.ndarray, a: float, z0: float) -> np.ndarray:
    """A_phi of a unit-current circular loop (radius a, height z0) over the
    grid arrays R, Z. Returns SI A_phi per ampere (multiply by the loop
    current). On the axis (R = 0) A_phi = 0 by symmetry."""
    d = Z - z0
    denom = (a + R) ** 2 + d ** 2
    # k^2 in [0, 1); clip away the self-point singularity.
    m = np.where(denom > 0, 4.0 * a * R / denom, 0.0)
    m = np.clip(m, 0.0, 1.0 - 1e-12)
    K = ellipk(m)
    E = ellipe(m)
    # k and R are only zero on the axis, where A_phi = 0 by symmetry and the
    # result is masked out; use safe values to avoid 0/0 warnings there.
    valid = R > 1e-12
    safe_r = np.where(valid, R, 1.0)
    safe_k = np.where(m > 0, np.sqrt(m), 1.0)
    g = np.sqrt(a / safe_r) / (np.pi * safe_k) * ((1.0 - m / 2.0) * K - E)
    g = np.where(valid, g, 0.0)
    return MU0 * g


@dataclass(frozen=True)
class MagneticFieldBasis:
    """Grid-sampled A_phi basis: one field per secondary segment (unit
    current) and one primary field (unit current).

    seg_fields is (N, nz, nr); primary_field is (nz, nr) or None.
    """

    grid: FieldGrid
    seg_fields: np.ndarray               # (N, nz, nr) SI A_phi per amp
    primary_field: Optional[np.ndarray]  # (nz, nr) or None
    has_primary: bool


def compute_magnetic_basis(
    coil, grid: FieldGrid, discretizer, geometry_key: str
) -> MagneticFieldBasis:
    """Compute (or reuse) the grid-sampled A_phi basis, cached by geometry."""
    return _CACHE.get_or_compute(
        ("B", geometry_key, grid),
        lambda: _compute(coil, grid, discretizer),
    )


def _compute(coil, grid: FieldGrid, discretizer) -> MagneticFieldBasis:
    secondary = coil.secondary
    primary = coil.primary
    slices = tuple(discretizer.get_slices(secondary, coil.discretization_order))
    rr, zz = np.meshgrid(grid.r_coords, grid.z_coords)  # (nz, nr)

    # Secondary turn rings, grouped into the N virtual-conductor segments.
    turn_pts = secondary_turn_points(secondary, _SAMPLES_PER_TURN)  # (M+1, 2)
    bounds = segment_start_indices(secondary, slices, len(turn_pts))
    bounds = list(bounds) + [len(turn_pts)]
    n_seg = len(bounds) - 1

    nz, nr = grid.shape
    seg_fields = np.zeros((n_seg, nz, nr))
    for k in range(n_seg):
        acc = np.zeros((nz, nr))
        for i in range(bounds[k], bounds[k + 1]):
            a, z0 = turn_pts[i]
            acc += loop_vector_potential(rr, zz, float(a), float(z0))
        seg_fields[k] = acc

    if primary is not None:
        centers = primary.ring_centers()
        weights = primary.ring_turn_fractions()
        prim = np.zeros((nz, nr))
        for (a, z0), w in zip(centers, weights):
            prim += w * loop_vector_potential(rr, zz, float(a), float(z0))
        primary_field = prim
        has_primary = True
    else:
        primary_field = None
        has_primary = False

    return MagneticFieldBasis(
        grid=grid,
        seg_fields=seg_fields,
        primary_field=primary_field,
        has_primary=has_primary,
    )


def assemble_magnetic_field(
    basis: MagneticFieldBasis,
    segment_currents: np.ndarray,
    primary_current: complex = 0.0,
) -> np.ndarray:
    """Superpose the A_phi basis with the operating currents.

    Args:
        basis: the magnetic basis.
        segment_currents: complex secondary segment currents I_k (length N).
        primary_current: complex primary current I_p.

    Returns:
        (nz, nr) complex A_phi [T*m].
    """
    n_seg = basis.seg_fields.shape[0]
    if len(segment_currents) != n_seg:
        raise ValueError(
            f"expected {n_seg} segment currents, got {len(segment_currents)}"
        )
    a_phi = np.tensordot(
        np.asarray(segment_currents, dtype=complex), basis.seg_fields, axes=(0, 0)
    ).astype(complex)
    if basis.has_primary:
        a_phi = a_phi + primary_current * basis.primary_field
    return a_phi
