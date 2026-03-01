""" 
This file contains geometric region classes for defining spatial domains in tesla coil simulations.

This module provides a hierarchy of geometric region classes used to define
physical regions in 2D space. All regions support point containment testing
through the `contains()` method.

"""
from typing import List, Tuple
from dataclasses import dataclass

from .base_geometric_region import GeometricRegion


@dataclass(frozen=True)
class Circle(GeometricRegion):
    """A circular 2D region."""
    center: Tuple[float, float]
    radius: float
    
    def __post_init__(self):
        """Validate circle parameters after initialization."""
        if len(self.center) != 2:
            raise ValueError(f"Center must be 2D, got {len(self.center)}D")
        if self.radius <= 0:
            raise ValueError("Radius must be positive")
    
    def contains(self, point: List[float]) -> bool:
        """Check if point is inside the circle."""
        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]
        distance_squared = dx * dx + dy * dy
        
        return distance_squared <= self.radius * self.radius

@dataclass(frozen=True)
class Polygon(GeometricRegion):
    """A general polygon defined by a tuple of vertices."""
    vertices: Tuple[Tuple[float, float], ...]
    
    def __post_init__(self):
        """Validate polygon vertices after initialization."""
        if len(self.vertices) < 3:
            raise ValueError("A polygon must have at least 3 vertices")
        
        for vertex in self.vertices:
            if len(vertex) != 2:
                raise ValueError(f"Each vertex must be 2D, got {len(vertex)}D")
    
    def contains(self, point: List[float]) -> bool:
        """
        Check if point is inside the polygon using ray casting algorithm.
        
        Args:
            point: A 2D coordinate [x, y]
            
        Returns:
            True if the point is inside the polygon, False otherwise
        """
        x, y = point[0], point[1]
        inside = False
        n = len(self.vertices)
        
        for i in range(n):
            j = (i + 1) % n
            xi, yi = self.vertices[i][0], self.vertices[i][1]
            xj, yj = self.vertices[j][0], self.vertices[j][1]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
        
        return inside

@dataclass(frozen=True)
class Rectangle(Polygon):
    """A rectangular 2D region defined by 4 vertices."""
    
    def __post_init__(self):
        """Validate rectangle has exactly 4 vertices."""
        if len(self.vertices) != 4:
            raise ValueError("A rectangle must have exactly 4 vertices")
        
        # Call parent validation
        super().__post_init__()
    
    # contains() method is inherited from Polygon - no need to reimplement!
