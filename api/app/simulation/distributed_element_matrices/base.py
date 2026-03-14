from abc import ABC

from app.simulation.coil_discretizers.base import CoilDiscretizer


class DistributedElementMatrixSolver(ABC):
    """Base class for distributed element matrix solvers.

    Provides a shared reference to a :class:`CoilDiscretizer` that defines
    how the continuous coil structure is split into discrete virtual
    conductor segments.  Subclasses (capacitance, inductance, etc.) add
    their own abstract ``compute_*`` methods.
    """

    def __init__(self, discretizer: CoilDiscretizer, **kwargs):
        self._discretizer = discretizer
        self._kwargs = kwargs

    @property
    def discretizer(self) -> CoilDiscretizer:
        """The coil discretizer used to segment the coil."""
        return self._discretizer