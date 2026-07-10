from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Tuple

from app.simulation.coil_discretizers.base import CoilDiscretizer

if TYPE_CHECKING:
    from app.models.simulation_models import SimulatableTeslaCoil


class MutualCouplingSolver(ABC):
    """Abstract base class for primary-secondary coupling solvers.

    Computes the coupling vector m: entry k is the mutual inductance
    between the primary (treated as one lumped current loop - it is
    electrically short at coil frequencies) and the k-th virtual
    conductor segment of the secondary.

    The segment grouping MUST match the inductance matrix solver's (both
    use the shared turn_sampling helpers), because m borders L into the
    combined inductance matrix [[L, m], [m^T, L_p]] of the coupled
    system, which is only meaningful if rows refer to the same segments.

    Follows the DistributedElementMatrixSolver construction convention
    (discretizer + **kwargs) so facades can instantiate any solver
    uniformly; it is a separate ABC because its result is a vector, not
    a segment-by-segment matrix.
    """

    def __init__(self, discretizer: CoilDiscretizer, **kwargs):
        self._discretizer = discretizer
        self._kwargs = kwargs

    @property
    def discretizer(self) -> CoilDiscretizer:
        """The coil discretizer used to segment the secondary."""
        return self._discretizer

    @abstractmethod
    def coupling_vector(
        self, coil: SimulatableTeslaCoil
    ) -> Tuple[float, ...]:
        """Compute the geometric coupling vector m.

        Parameters:
            coil: The full simulatable Tesla coil specification. Must
                have a primary.

        Returns:
            A length-N tuple (N = coil.discretization_order) in geometric
            units; multiply by mu_0 * unit_scale for Henries.

        Raises:
            ValueError: If the coil has no primary.
        """
        ...
