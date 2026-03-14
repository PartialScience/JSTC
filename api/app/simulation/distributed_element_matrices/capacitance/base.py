from typing import Tuple
from abc import abstractmethod
from app.models.coil_models import ToploadSpec, GroundedConductorSpec, SecondaryConductorSpec
from app.simulation.distributed_element_matrices.base import DistributedElementMatrixSolver


class CapacitanceMatrixSolver(DistributedElementMatrixSolver):
    """Abstract base class for capacitance matrix solvers."""

    @abstractmethod
    def compute_capacitance_matrix(
        self,
        secondary: SecondaryConductorSpec,
        toploads: Tuple[ToploadSpec, ...],
        grounds: Tuple[GroundedConductorSpec, ...],
        discretization_order: int,
        r_max: float,
        z_max: float,
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the Maxwell mutual capacitance matrix C for the Tesla coil system."""
        ...
