from typing import Tuple
from abc import ABC, abstractmethod


class EigenSolverBase(ABC):
    """Abstract base class for eigen-analysis solvers.

    Implementations must provide methods to compute eigenfrequencies,
    voltage eigenmodes, and current eigenmodes from the system matrices.
    """

    @staticmethod
    @abstractmethod
    def compute_eigen_frequencies(
        capacitance_matrix: Tuple[Tuple[float, ...], ...],
        inductance_matrix: Tuple[Tuple[float, ...], ...],
        connectivity_matrix: Tuple[Tuple[float, ...], ...],
    ) -> Tuple[float, ...]:
        """Return eigenfrequencies sorted ascending."""
        ...

    @staticmethod
    @abstractmethod
    def compute_voltage_eigen_modes(
        capacitance_matrix: Tuple[Tuple[float, ...], ...],
        inductance_matrix: Tuple[Tuple[float, ...], ...],
        connectivity_matrix: Tuple[Tuple[float, ...], ...],
    ) -> Tuple[Tuple[float, ...], ...]:
        """Return voltage eigenmodes corresponding to the eigenfrequencies."""
        ...

    @staticmethod
    @abstractmethod
    def compute_current_eigen_modes(
        capacitance_matrix: Tuple[Tuple[float, ...], ...],
        inductance_matrix: Tuple[Tuple[float, ...], ...],
        connectivity_matrix: Tuple[Tuple[float, ...], ...],
    ) -> Tuple[Tuple[float, ...], ...]:
        """Return current eigenmodes derived from voltage eigenmodes."""
        ...
