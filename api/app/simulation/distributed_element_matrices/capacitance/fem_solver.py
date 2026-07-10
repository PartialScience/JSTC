from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Tuple

from typing import Optional

from app.models.coil_models import (
    GroundedConductorSpec,
    PrimarySpec,
    SecondaryConductorSpec,
    ToploadSpec,
)
from app.models.simulation_models import BoundaryConditionType
from app.simulation.distributed_element_matrices.capacitance.base import CapacitanceMatrixSolver
from app.simulation.electrostatics import solve_electrostatics
from app.simulation.electrostatics.coil_setup import build_coil_electrostatic_setup

if TYPE_CHECKING:
    from app.models.simulation_models import SimulatableTeslaCoil


class FEMCapacitanceMatrixSolver(CapacitanceMatrixSolver):
    """Compute the nodal capacitance matrix with the Finite Element Method.

    Pipeline (each stage is a separately tested package):

        coil geometry -> boundary loops sampled at the slice nodes
                      -> MeshSpec -> GmshMesher -> mfem.Mesh
                      -> N+1 tent-profile Dirichlet solves
                      -> Gram extraction C_geo[j,k] = U_j^T K U_k

    The winding is meshed as ONE hole; the discretization enters only as
    the tent boundary profiles, evaluated by projecting boundary points
    onto the winding's central curve (closest_parameter). Slice parameters
    are forced into the boundary sampling so no mesh edge spans a tent
    kink.

    Supported kwargs (accuracy/cost dials; defaults tuned for the JavaTC
    validation tolerance):

        winding_mesh_size_factor (float): Boundary element size on the
            winding, as a multiple of the wire diameter. Default 1.0.
        component_mesh_fraction (float): Boundary element size on toploads
            and grounds, as a fraction of the component's smallest bounding
            box side. Default 0.05.
        wall_mesh_fraction (float): Element size on the domain walls as a
            fraction of the larger domain extent. Default 0.125.
        size_grading (float): Distance over which the fine conductor mesh
            grows to the coarse wall size, as a fraction of the domain
            extent (a distance-threshold size field). Smaller = fewer
            elements/faster; the near-conductor resolution that sets
            accuracy is unaffected. Default 0.08.
        fe_order (int): H1 element order. Default 2.
    """

    _DEFAULTS = dict(
        winding_mesh_size_factor=1.0,
        component_mesh_fraction=0.05,
        wall_mesh_fraction=0.125,
        size_grading=0.08,
        fe_order=2,
    )

    def nodal_capacitance_matrix(
        self,
        coil: SimulatableTeslaCoil,
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the (N+1)x(N+1) nodal capacitance matrix for the coil.

        Delegates to a cached static method so that identical inputs
        produce cache hits regardless of instance.
        """
        return self._cached_solution(coil)[0]

    def topload_charge_vector(
        self,
        coil: SimulatableTeslaCoil,
    ) -> Tuple[float, ...]:
        """Geometric charge on the topload group per unit (tent) solve.

        Entry k is the charge induced on ALL topload surfaces when the
        winding carries the tent profile of node k. By linearity, the
        topload charge for any nodal voltage profile V is sum_k q_k V_k.
        Extracted from the same cached FEM solution as the matrix - no
        extra solves.
        """
        return self._cached_solution(coil)[1]

    def _cached_solution(self, coil: SimulatableTeslaCoil):
        """Assemble hashable arguments and hit the lru_cached computation."""
        secondary = coil.secondary
        slices = tuple(self.discretizer.get_slices(secondary, coil.discretization_order))
        config = tuple(
            (key, self._kwargs.get(key, default))
            for key, default in sorted(self._DEFAULTS.items())
        )
        return self._compute(
            secondary=secondary,
            toploads=coil.toploads,
            grounds=coil.grounds,
            primary=coil.primary,
            slices=slices,
            r_max=coil.r_max,
            z_max=coil.z_max,
            dirichlet_walls=(
                coil.bc_bottom.bc_type == BoundaryConditionType.DIRICHLET,
                coil.bc_right.bc_type == BoundaryConditionType.DIRICHLET,
                coil.bc_top.bc_type == BoundaryConditionType.DIRICHLET,
            ),
            config=config,
        )

    @staticmethod
    @functools.lru_cache
    def _compute(
        secondary: SecondaryConductorSpec,
        toploads: Tuple[ToploadSpec, ...],
        grounds: Tuple[GroundedConductorSpec, ...],
        primary: Optional[PrimarySpec],
        slices: Tuple[float, ...],
        r_max: float,
        z_max: float,
        dirichlet_walls: Tuple[bool, bool, bool],
        config: Tuple[Tuple[str, float], ...],
    ) -> Tuple[Tuple[float, ...], ...]:
        """
        Pure cached computation of the nodal capacitance matrix.

        Args are passed explicitly (as hashables) so caching keys on
        exactly the physics-relevant inputs.
        """
        cfg = dict(config)

        setup = build_coil_electrostatic_setup(
            secondary=secondary,
            toploads=toploads,
            grounds=grounds,
            primary=primary,
            slices=slices,
            r_max=r_max,
            z_max=z_max,
            dirichlet_walls=dirichlet_walls,
            cfg=cfg,
        )

        # --- Solve and extract ---
        result = solve_electrostatics(
            mesh=setup.geo.mesh,
            dirichlet_attrs=setup.dirichlet_attrs,
            solves=setup.tent_solves,
            fe_order=int(cfg["fe_order"]),
            charge_groups=((setup.topload_attrs,) if setup.topload_attrs else ()),
        )

        nodal = tuple(tuple(float(x) for x in row) for row in result.gram)
        if result.group_charges is not None:
            topload_charges = tuple(float(q) for q in result.group_charges[0])
        else:
            topload_charges = tuple(0.0 for _ in slices)
        return nodal, topload_charges
