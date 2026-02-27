from typing import List, Tuple
from abc import ABC, abstractmethod
import numpy as np
from scipy.optimize import bisect as scipy_bisect

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
    def bounding_box(self) -> List[Tuple[float, float]]:
        """Return the bounding box of the region as a list of (min, max) tuples for each dimension."""
        ...