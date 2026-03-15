from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Tuple

from app.simulation.distributed_element_matrices.base import DistributedElementMatrixSolver

if TYPE_CHECKING:
    from app.models.simulation_models import SimulatableTeslaCoil


class InductanceMatrixSolver(DistributedElementMatrixSolver):
    """Abstract base class for inductance matrix solvers.

    Subclasses implement :meth:`geometric_inductance_matrix` to produce the
    geometric inductance matrix from a :class:`SimulatableTeslaCoil`.

    The elements in the returned matrix have the same units as the
    coil geometry.  To convert to units of inductance (Henries),
    multiply by the permeability of free space μ₀.
    """

    def compute_matrix(
        self, coil: SimulatableTeslaCoil
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the geometric inductance matrix L.

        Parameters:
            coil: The full simulatable Tesla coil specification.

        Returns:
            An NxN tuple-of-tuples geometric inductance matrix
            (N = coil.discretization_order).
        """
        return self.geometric_inductance_matrix(coil)

    @abstractmethod
    def geometric_inductance_matrix(
        self, coil: SimulatableTeslaCoil
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the geometric inductance matrix L.

        Parameters:
            coil: The full simulatable Tesla coil specification.

        Returns:
            An NxN tuple-of-tuples geometric inductance matrix
            (N = coil.discretization_order).  The returned matrix
            elements have the same units as the coil geometry.  To
            convert to units of inductance (Henries), multiply by
            the permeability of free space μ₀.
        """
        ...
