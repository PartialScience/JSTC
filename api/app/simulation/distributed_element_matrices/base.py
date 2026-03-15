from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Tuple

from app.simulation.coil_discretizers.base import CoilDiscretizer

if TYPE_CHECKING:
    from app.models.simulation_models import SimulatableTeslaCoil


class DistributedElementMatrixSolver(ABC):
    """Base class for distributed element matrix solvers.

    Provides a shared reference to a :class:`CoilDiscretizer` that defines
    how the continuous coil structure is split into discrete virtual
    conductor segments.  Subclasses implement :meth:`compute_matrix` to
    produce their specific matrix from a full coil specification.

    Solver-specific configuration is passed as ``**kwargs`` and stored in
    ``_kwargs`` so that every concrete class can be instantiated with the
    same ``solver_cls(discretizer=d, **config)`` call.
    """

    def __init__(self, discretizer: CoilDiscretizer, **kwargs):
        self._discretizer = discretizer
        self._kwargs = kwargs

    @property
    def discretizer(self) -> CoilDiscretizer:
        """The coil discretizer used to segment the coil."""
        return self._discretizer

    @abstractmethod
    def compute_matrix(
        self, coil: SimulatableTeslaCoil
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the matrix for the given coil specification.

        Parameters:
            coil: A :class:`SimulatableTeslaCoil` instance.

        Returns:
            An NxN tuple-of-tuples matrix.
        """
        ...