from typing import Optional, List
from pydantic import BaseModel, Field
from app.geometry import GeometricRegion


class Topload:
    """A topload for a 2D tesla coil, defined by a 2D shape."""
    
    def __init__(self, shape: GeometricRegion):
        """
        Initialize a topload.
        
        Args:
            shape: A 2D geometric region representing the topload's cross-section
        """
        if not isinstance(shape, GeometricRegion):
            raise ValueError("Shape must be a GeometricRegion instance")
            
        self.shape = shape
    
    def contains(self, point: List[float]) -> bool:
        """
        Check if a point is inside the topload region.
        
        Args:
            point: A 2D coordinate [x, y]
            
        Returns:
            True if the point is inside the topload, False otherwise
        """
        return self.shape.contains(point)

    