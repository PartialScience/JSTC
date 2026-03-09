from typing import Tuple
from abc import ABC, abstractmethod
from app.models.coil_models import SecondaryConductorSpec


class InductanceMatrixSolver(ABC):
    """Abstract base class for inductance matrix solvers."""

    @staticmethod
    @abstractmethod
    def compute_inductance_matrix(
        secondary: SecondaryConductorSpec,
        discretization_order: int,
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the mutual inductance matrix L for the Tesla coil system."""
        ...
