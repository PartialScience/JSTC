from typing import Tuple
from abc import abstractmethod
from app.models.coil_models import SecondaryConductorSpec
from app.simulation.distributed_element_matrices.base import DistributedElementMatrixSolver


class InductanceMatrixSolver(DistributedElementMatrixSolver):
    """Abstract base class for inductance matrix solvers."""

    @abstractmethod
    def geometric_inductance_matrix(
        self,
        secondary: SecondaryConductorSpec,
        discretization_order: int,
    ) -> Tuple[Tuple[float, ...], ...]:
        """
        Compute the mutual, geometric inductance matrix L for the Tesla coil system.
        
        The elements in the matrix will have the same units as the geometry. 
        
        For instance, if your coil spec is all in inches, the matrix will also have units
        of inches. To compute to units of inductance, multiply by the permeability of 
        free space.
        
        Parameters:
            secondary: The specification of the secondary conductor
            discretization_order: The number of discrete segments to use in the discretization
        """
        ...
