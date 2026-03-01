from typing import List
from abc import ABC, abstractmethod


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