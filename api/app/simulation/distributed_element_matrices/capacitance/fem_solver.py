import functools
from typing import Tuple
from app.models.coil_models import ToploadSpec, GroundedConductorSpec, SecondaryConductorSpec
from app.simulation.distributed_element_matrices.capacitance.base import CapacitanceMatrixSolver


class FEMCapacitanceMatrixSolver(CapacitanceMatrixSolver):
    """Use the Finite Element Method to compute the capacitance matrix from coil geometry."""
    
    def compute_capacitance_matrix(
        self,
        secondary: SecondaryConductorSpec, 
        toploads: Tuple[ToploadSpec, ...], 
        grounds: Tuple[GroundedConductorSpec, ...], 
        discretization_order: int,
        r_max: float, 
        z_max: float,
    ) -> Tuple[Tuple[float, ...], ...]:
        """
        Compute the capacitance matrix using FEM.
        
        Delegates to a cached static method so that identical inputs
        produce cache hits regardless of instance.
        """
        slices = tuple(self.discretizer.get_slices(secondary, discretization_order))
        return self._compute(
            secondary=secondary,
            toploads=toploads,
            grounds=grounds,
            slices=slices,
            r_max=r_max,
            z_max=z_max,
        )

    @staticmethod
    @functools.lru_cache
    def _compute(
        secondary: SecondaryConductorSpec,
        toploads: Tuple[ToploadSpec, ...],
        grounds: Tuple[GroundedConductorSpec, ...],
        slices: Tuple[float, ...],
        r_max: float,
        z_max: float,
    ) -> Tuple[Tuple[float, ...], ...]:
        """
        Pure cached computation of the capacitance matrix.
        
        Args are passed explicitly to allow for proper caching based on dependencies.
        Note: Tuples are used instead of lists to enable proper caching.
        """
        pass
