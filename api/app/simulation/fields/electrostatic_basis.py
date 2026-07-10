"""
Electrostatic field basis: the winding tent fields and the two primary
basis fields, sampled on a regular grid, plus the primary charge each solve
induces (for the floating-primary offset).

This is the expensive (FEM) half of the E-field feature. It is cached by
geometry + grid, so changing the drive (frequency, current, reference mode,
hot-end orientation) re-superposes instantly without re-solving.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from app.simulation.distributed_element_matrices.coupling import primary_voltage_profile
from app.simulation.electrostatics import solve_electrostatics
from app.simulation.electrostatics.coil_setup import build_coil_electrostatic_setup
from app.simulation.fields._cache import GeometryLruCache
from app.simulation.fields.grid import FieldGrid

_CACHE = GeometryLruCache(maxsize=6)


@dataclass(frozen=True)
class ElectrostaticFieldBasis:
    """Grid-sampled basis fields for the electrostatic potential.

    The operating potential is
        phi = sum_k V_k tent_fields[k]
              + V_p * (primary_profile_field or its reverse)
              + offset * primary_uniform_field
    with V_k the operating nodal voltages (V_0 = 0 prepended) and the primary
    terms present only when the coil has a primary.

    Fields are (nz, nr) arrays; conductor-interior / off-domain cells are
    NaN and False in ``mask``. ``primary_charges`` is the geometric charge
    induced on the primary group by each solve (tents..., profile, uniform),
    used to solve the charge-neutral floating offset.
    """

    grid: FieldGrid
    mask: np.ndarray                                   # (nz, nr) bool
    tent_fields: np.ndarray                            # (N+1, nz, nr)
    primary_profile_field: Optional[np.ndarray]        # (nz, nr)
    primary_uniform_field: Optional[np.ndarray]        # (nz, nr)
    primary_charges: Optional[np.ndarray]              # (n_solves,) or None
    has_primary: bool


def compute_electrostatic_basis(
    coil,
    grid: FieldGrid,
    discretizer,
    config: Tuple[Tuple[str, float], ...],
    geometry_key: str,
) -> ElectrostaticFieldBasis:
    """Compute (or reuse) the grid-sampled electrostatic basis for a coil.

    Args:
        coil: the SimulatableTeslaCoil.
        grid: the sampling grid.
        discretizer: the coil discretizer (for the winding slice nodes -
            these must match the C-matrix so fields align with V).
        config: the FEM mesh/order config as sorted (key, value) pairs.
        geometry_key: a stable fingerprint of the coil geometry + mesh
            config; the cache key (with the grid). Reused across requests so
            drive-only changes never re-solve.
    """
    return _CACHE.get_or_compute(
        ("E", geometry_key, grid),
        lambda: _compute(coil, grid, discretizer, config),
    )


def _compute(coil, grid: FieldGrid, discretizer, config) -> ElectrostaticFieldBasis:
    from app.models.simulation_models import BoundaryConditionType

    secondary = coil.secondary
    primary = coil.primary
    slices = tuple(discretizer.get_slices(secondary, coil.discretization_order))
    cfg = dict(config)

    setup = build_coil_electrostatic_setup(
        secondary=secondary,
        toploads=coil.toploads,
        grounds=coil.grounds,
        primary=primary,
        slices=slices,
        r_max=coil.r_max,
        z_max=coil.z_max,
        dirichlet_walls=(
            coil.bc_bottom.bc_type == BoundaryConditionType.DIRICHLET,
            coil.bc_right.bc_type == BoundaryConditionType.DIRICHLET,
            coil.bc_top.bc_type == BoundaryConditionType.DIRICHLET,
        ),
        cfg=cfg,
    )

    # Basis solves: the winding tents (topload on the top node) then, when a
    # primary exists, its profile and uniform (common-mode) fields.
    solves = list(setup.tent_solves)
    has_primary = bool(setup.primary_attrs)
    if has_primary:
        profile = primary_voltage_profile(primary)
        profile_solve = {
            attr: float(p) for attr, p in zip(setup.primary_attrs, profile)
        }
        uniform_solve = {attr: 1.0 for attr in setup.primary_attrs}
        solves.append(profile_solve)
        solves.append(uniform_solve)

    charge_groups = (setup.primary_attrs,) if has_primary else ()

    result = solve_electrostatics(
        mesh=setup.geo.mesh,
        dirichlet_attrs=setup.dirichlet_attrs,
        solves=solves,
        fe_order=int(cfg["fe_order"]),
        charge_groups=charge_groups,
        sample_points=grid.points(),
    )

    assert result.sampled_fields is not None and result.sample_mask is not None
    nz, nr = grid.shape
    fields = result.sampled_fields.reshape(len(solves), nz, nr)
    mask = result.sample_mask.reshape(nz, nr)

    n_tents = len(setup.tent_solves)
    tent_fields = fields[:n_tents]

    if has_primary:
        primary_profile_field = fields[n_tents]
        primary_uniform_field = fields[n_tents + 1]
        primary_charges = result.group_charges[0].copy()
    else:
        primary_profile_field = None
        primary_uniform_field = None
        primary_charges = None

    return ElectrostaticFieldBasis(
        grid=grid,
        mask=mask,
        tent_fields=tent_fields,
        primary_profile_field=primary_profile_field,
        primary_uniform_field=primary_uniform_field,
        primary_charges=primary_charges,
        has_primary=has_primary,
    )
