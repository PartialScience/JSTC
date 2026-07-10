from typing import List, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from app.geometry.boundary import BoundaryLoop


class GeometricRegion(ABC):
    """Base class for any geometric region."""

    @abstractmethod
    def contains(self, point: List[float]) -> bool:
        """
        Determine if a given point (vector) is inside the region.

        Args:
            point: A list of coordinates representing a point

        Returns:
            True if the point is inside the region, False otherwise
        """
        ...

    @abstractmethod
    def boundary_loops(self) -> tuple["BoundaryLoop", ...]:
        """
        Describe the region's boundary as closed loops of parametric curves.

        Returns one loop for a simply-connected region; additional loops
        represent holes. This is the contract mesh generators consume
        (via BoundaryLoop.sample_polygon); every concrete region must
        support it in full.

        Returns:
            Tuple of BoundaryLoop objects.
        """
        ...
