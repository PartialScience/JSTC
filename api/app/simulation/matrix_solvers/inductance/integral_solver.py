from typing import Tuple
from app.models.coil_models import SecondaryConductorSpec
from app.simulation.matrix_solvers.inductance.base import InductanceMatrixSolver
import methodtools as mt
from app.geometry import Rectangle


class IntegralInductanceLMatrixSolver(InductanceMatrixSolver):  
    
    @staticmethod
    def check_compatibility(secondary: SecondaryConductorSpec) -> bool:
        """Check if the solver is compatible with the given secondary conductor specification."""
        # The integral method can only be applied to secondary conductors that can be represented as rectangles.
        secondary_geometry = secondary.get_geometry()
        if not isinstance(secondary_geometry, Rectangle):
            return False
        return True
    
    @mt.lru_cache()
    @staticmethod
    def compute_inductance_matrix(
        secondary: SecondaryConductorSpec,
        discretization_order: int,
    ) -> Tuple[Tuple[float, ...], ...]:
        """
        Compute the inductance matrix using the integral method.
        
        Returns:
            A tuple of tuples representing the inductance matrix
        """
        
        if not IntegralInductanceLMatrixSolver.check_compatibility(secondary):
            raise ValueError("Incompatible secondary conductor specification.")