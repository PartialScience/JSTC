import functools
from typing import Tuple
from app.simulation.coil_discretizers.connectivity_matrices.base import ConnectivityMatrixSolver


class SeriesConnectivityMatrixSolver(ConnectivityMatrixSolver):
    """Compute a standard series connectivity matrix for a Tesla coil system."""
    
    @functools.lru_cache
    @staticmethod
    def compute_connectivity_matrix(
        discretization_order: int
    ) -> Tuple[Tuple[float, ...], ...]:
        """
        Compute the connectivity matrix for the Tesla coil system with the following:
        
        Assumptions:
            1. The (0,0) element corresponds to the bottommost virtual conductor of the secondary coil.
        
            2. The nth virtual conductor in the L and C matrices is wired in series with the (n+1)th conductor
            
            3. The capacitive effects of the topload are lumped into the topmost virtual conductor.
            
            4. The bottommost virtual conductor is grounded (has a voltage of 0V)
        
        Dimension:
            N x N, where N is the discretization order (number of virtual conductors)
        """
        N = discretization_order
        
        Aelement = lambda i, j: (
            1.0 if i == j else
            -1.0 if i == j - 1 else
            0.0
        )
        
        A = tuple(
            tuple(
                Aelement(i, j) for j in range(N)
            )
            for i in range(N)
        )
        
        return A
