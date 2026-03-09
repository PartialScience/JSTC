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

from app.simulation.matrix_solvers.capacitance import CapacitanceMatrixSolver, FEMCapacitanceMatrixSolver
from app.simulation.matrix_solvers.inductance import InductanceMatrixSolver, IntegralInductanceLMatrixSolver
from app.simulation.matrix_solvers.connectivity import ConnectivityMatrixSolver, SeriesConnectivityMatrixSolver
from app.simulation.eigen_solvers import EigenSolverBase, VoltageModeEigenSolver
from app.simulation.facade.secondary import SecondaryView
from app.simulation.facade.primary import PrimaryView

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
        capacitance_solver: Type[CapacitanceMatrixSolver] = FEMCapacitanceMatrixSolver,
        inductance_solver: Type[InductanceMatrixSolver] = IntegralInductanceLMatrixSolver,
        connectivity_solver: Type[ConnectivityMatrixSolver] = SeriesConnectivityMatrixSolver,
        eigen_solver: Type[EigenSolverBase] = VoltageModeEigenSolver,
    ):
        self.coil = coil
        self._cap_solver = capacitance_solver
        self._ind_solver = inductance_solver
        self._conn_solver = connectivity_solver
        self._eigen_solver = eigen_solver
        self.secondary = SecondaryView(self)
        self.primary = PrimaryView(self)
