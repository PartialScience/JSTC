from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Tuple

from app.simulation.distributed_element_matrices.base import DistributedElementMatrixSolver

if TYPE_CHECKING:
    from app.models.simulation_models import SimulatableTeslaCoil


class CapacitanceMatrixSolver(DistributedElementMatrixSolver):
    """Abstract base class for capacitance matrix solvers.

    Subclasses implement :meth:`maxwell_capacitance_matrix` to produce the
    Maxwell mutual capacitance matrix from a :class:`SimulatableTeslaCoil`.
    """

    def compute_matrix(
        self, coil: SimulatableTeslaCoil
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the Maxwell mutual capacitance matrix C.

        Parameters:
            coil: The full simulatable Tesla coil specification.

        Returns:
            An NxN tuple-of-tuples capacitance matrix.
        """
        return self.maxwell_capacitance_matrix(coil)

    @abstractmethod
    def maxwell_capacitance_matrix(
        self, coil: SimulatableTeslaCoil
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the Maxwell mutual capacitance matrix C.

        Parameters:
            coil: The full simulatable Tesla coil specification.

        Returns:
            An NxN tuple-of-tuples capacitance matrix.
        """
        ...
