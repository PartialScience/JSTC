"""
Simulation facade — a thin wiring layer that connects mutable coil geometry
to cached pure-function solvers.

Properties compute lazily on read. Caching is handled by ``@lru_cache`` on
the underlying solver static methods, keyed on frozen input arguments:

* Same coil geometry → same arguments → cache hit → instant.
* Changed geometry   → new arguments  → cache miss → recompute.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Type

from app.simulation.distributed_element_matrices.capacitance import CapacitanceMatrixSolver, FEMCapacitanceMatrixSolver
from app.simulation.distributed_element_matrices.inductance import InductanceMatrixSolver, CoaxialRingInductanceLMatrixSolver
from app.simulation.distributed_element_matrices.coupling import MutualCouplingSolver, CoaxialRingMutualCouplingSolver
from app.simulation.coil_discretizers.connectivity_matrices import ConnectivityMatrixSolver, SeriesConnectivityMatrixSolver
from app.simulation.coil_discretizers.base import CoilDiscretizer
from app.simulation.coil_discretizers.uniform_arclength_discretizer import UniformArcLengthDiscretizer
from app.simulation.eigen_solvers import EigenSolverBase, VoltageModeEigenSolver
from app.simulation.facade.secondary import SecondaryView
from app.simulation.facade.primary import PrimaryView
from app.simulation.facade.coupling import CouplingView
from app.simulation.facade.coupled import CoupledView
from app.simulation.facade.field import FieldView
from app.simulation.facade.matrices import (
    BundleMatrixProvider,
    GeometricMatrixBundle,
    SolverMatrixProvider,
    geometry_fingerprint,
)

if TYPE_CHECKING:
    from app.models.simulation_models import SimulatableTeslaCoil


class TeslaCoilSimulation:
    """
    Facade that wires a mutable coil geometry reference to cached solvers.

    Usage::

        sim = TeslaCoilSimulation(coil)

        sim.secondary.resonant_frequency      # computes lazily, cached
        sim.secondary.resonant_frequency      # instant (cache hit)

        sim.coil = modified_coil              # swap geometry
        sim.secondary.resonant_frequency      # recomputes (cache miss)
    """

    def __init__(
        self,
        coil: SimulatableTeslaCoil,
        *,
        discretizer: CoilDiscretizer | None = None,
        capacitance_solver: Type[CapacitanceMatrixSolver] = FEMCapacitanceMatrixSolver,
        inductance_solver: Type[InductanceMatrixSolver] = CoaxialRingInductanceLMatrixSolver,
        coupling_solver: Type[MutualCouplingSolver] = CoaxialRingMutualCouplingSolver,
        connectivity_solver: Type[ConnectivityMatrixSolver] = SeriesConnectivityMatrixSolver,
        eigen_solver: Type[EigenSolverBase] = VoltageModeEigenSolver,
        matrices: GeometricMatrixBundle | None = None,
    ):
        self.coil = coil
        self._discretizer = discretizer or UniformArcLengthDiscretizer()
        self._cap_solver = capacitance_solver(discretizer=self._discretizer)
        self._ind_solver = inductance_solver(discretizer=self._discretizer)
        self._coupling_solver = coupling_solver(discretizer=self._discretizer)
        self._conn_solver = connectivity_solver
        self._eigen_solver = eigen_solver

        # Matrix source: injected precomputed bundle (fast) or the solvers
        # (slow). When a bundle is supplied it is validated against the
        # coil so a stale bundle cannot silently give wrong answers.
        if matrices is not None:
            self._matrices = BundleMatrixProvider(
                matrices, coil, self._cap_config()
            )
        else:
            self._matrices = SolverMatrixProvider(self)

        self.secondary = SecondaryView(self)
        self.primary = PrimaryView(self)
        self.coupling = CouplingView(self)
        self.coupled = CoupledView(self)
        self.field = FieldView(self)

    def _cap_config(self) -> tuple[tuple[str, float], ...]:
        """The capacitance solver's effective mesh configuration - part of
        the geometry fingerprint (its accuracy dials change the matrices)."""
        solver = self._cap_solver
        defaults = getattr(type(solver), "_DEFAULTS", {})
        return tuple(
            (key, solver._kwargs.get(key, default))
            for key, default in sorted(defaults.items())
        )

    def compute_matrix_bundle(self) -> GeometricMatrixBundle:
        """Compute the geometry-only matrix bundle for this coil (the slow
        path - runs the FEM capacitance solve). The returned bundle can be
        handed back to construct a simulation with ``matrices=bundle`` for
        millisecond re-analysis under cheap parameter changes."""
        provider = SolverMatrixProvider(self)
        return GeometricMatrixBundle(
            nodal_capacitance=provider.nodal_capacitance_geo(),
            topload_charge=provider.topload_charge_geo(),
            inductance=provider.inductance_geo(),
            coupling=provider.coupling_geo(),
            discretization_order=self.coil.discretization_order,
            geometry_fingerprint=geometry_fingerprint(self.coil, self._cap_config()),
        )
