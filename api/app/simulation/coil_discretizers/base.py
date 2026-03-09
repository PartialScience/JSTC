from typing import Tuple
from abc import ABC, abstractmethod

from api.app.models.coil_models import SecondaryConductorSpec, SecondaryConductorSegment
from app.simulation.matrix_solvers.connectivity import ConnectivityMatrixSolver


class CoilDiscretizer(ConnectivityMatrixSolver):
    """Abstract base class for coil discretizers.

    Implementations must provide a method to discretize a secondary conductor specification
    into a set of discrete virtual conductors for matrix computations.

    Concrete implementations must also implement the ConnectivityMatrixSolver interface,
    typically by inheriting from a concrete connectivity matrix solver.
    """

    @staticmethod
    @abstractmethod
    def discretize_conductor(
        secondary: SecondaryConductorSpec,
        discretization_order: int,
    ) -> Tuple[SecondaryConductorSegment]:
        """
        Discretize the secondary conductor specification into discrete virtual conductors.
        
        Args:
            secondary: The specification of the secondary conductor to be discretized
            discretization_order: The number of discrete segments to use in the discretization
            
        Returns:
                A tuple of SecondaryConductorSegment objects representing representing each discrete,
                virtual conductor segment the coil was split into.
        """
        ...
