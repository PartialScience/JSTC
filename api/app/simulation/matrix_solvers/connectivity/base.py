from typing import Tuple
from abc import ABC, abstractmethod


class ConnectivityMatrixSolver(ABC):
    """Abstract base class for connectivity matrix solvers."""

    @staticmethod
    @abstractmethod
    def compute_connectivity_matrix(
        discretization_order: int,
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the connectivity matrix A for the Tesla coil system."""
        ...
