from typing import Tuple
from abc import ABC, abstractmethod
from app.models.coil_models import ToploadSpec, GroundedConductorSpec, SecondaryConductorSpec


class CapacitanceMatrixSolver(ABC):
    """Abstract base class for capacitance matrix solvers."""

    @staticmethod
    @abstractmethod
    def compute_capacitance_matrix(
        secondary: SecondaryConductorSpec,
        toploads: Tuple[ToploadSpec, ...],
        grounds: Tuple[GroundedConductorSpec, ...],
        discretization_order: int,
        r_max: float,
        z_max: float,
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the Maxwell mutual capacitance matrix C for the Tesla coil system."""
        ...
