from typing import Tuple
from abc import ABC, abstractmethod

from app.models.coil_models import SecondaryConductorSpec, SecondaryConductorSegment
from app.simulation.coil_discretizers.connectivity_matrices import ConnectivityMatrixSolver


"""TODO:

Implement topload and ground discretization methods on the discretizer and 
update the naming so its a general discretizer not just for coils

"""

class CoilDiscretizer(ConnectivityMatrixSolver):
    """Base class for coil discretizers.

    Implementations must provide a method to discretize a secondary conductor specification
    into a set of discrete virtual conductors for matrix computations.

    Concrete implementations must also implement the ConnectivityMatrixSolver interface,
    typically by inheriting from a concrete connectivity matrix solver.
    """

    def discretize_conductor(
        self,
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
        slices = self.get_slices(secondary, discretization_order)

        segments = tuple(
            SecondaryConductorSegment(
                full_secondary=secondary,
                t1=slices[i],
                t2=slices[i+1],
                flatten_start= True if i > 0 else False,
                flatten_end= True if i < discretization_order - 1 else False,
            )
            for i in range(discretization_order)
        )
        return segments
    
    @staticmethod
    @abstractmethod
    def get_slices(
        secondary: SecondaryConductorSpec,
        discretization_order: int,
    ) -> Tuple[float]:
        """
        Provides a set of start and end points along the secondary for each discrete conductor 
        
        Args:
            secondary: The secondary conductor to discretized
            discretization_order: The number of discrete segments to use in the discretization
        
        Returns:
            A tuple of tuples, where each inner tuple contains the start and end parameter values 
            along the secondary's curve.
            
            The length of the tuple should be discretization_order + 1 (since there are N+1 boundaries for N slices)
        """
        ...
