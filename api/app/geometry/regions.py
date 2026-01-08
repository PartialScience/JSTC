""" 
This file contains geometric region classes for defining spatial domains in tesla coil simulations.

This module provides a hierarchy of geometric region classes used to define
physical regions in 2D space. All regions support point containment testing
through the `contains()` method.

"""
from typing import List
from abc import ABC, abstractmethod

class GeometricRegion(ABC):
    """Base class for any geometric region."""
    
    def __init__(self, region_dimension: int):
        """
        Initialize a geometric region.
        
        Args:
            region_dimension: The expected dimensionality of points in this region
        """
        self.region_dimension = region_dimension
    
    def _enforce_dimension(self, point: List[float]) -> None:
        """
        Validate that a point has the correct dimensionality.
        
        Args:
            point: A list of coordinates
            
        Raises:
            ValueError: If the point doesn't match the expected dimension
        """
        if len(point) != self.region_dimension:
            raise ValueError(f"Point must be {self.region_dimension}D, got {len(point)}D")
    
    @abstractmethod
    def contains(self, point: List[float]) -> bool:
        """
        Determine if a given point (vector) is inside the region.
        
        Args:
            point: A list of coordinates representing a point
            
        Returns:
            True if the point is inside the region, False otherwise
        """
        pass


class Circle(GeometricRegion):
    """A circular 2D region."""
    
    def __init__(self, center: List[float], radius: float):
        """
        Initialize a circle.
        
        Args:
            center: [x, y] coordinates of the circle center
            radius: radius of the circle
        """
        super().__init__(region_dimension=2)
        self._enforce_dimension(center)
        
        if radius <= 0:
            raise ValueError("Radius must be positive")
            
        self.center = center
        self.radius = radius
    
    def contains(self, point: List[float]) -> bool:
        """Check if point is inside the circle."""
        self._enforce_dimension(point)
        
        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]
        distance_squared = dx * dx + dy * dy
        
        return distance_squared <= self.radius * self.radius


class Polygon(GeometricRegion):
    """A general polygon defined by a list of vertices."""
    
    def __init__(self, vertices: List[List[float]]):
        """
        Initialize a polygon from a list of vertices.
        
        Args:
            vertices: List of [x, y] coordinates defining the polygon vertices in order
        """
        super().__init__(region_dimension=2)
        
        if len(vertices) < 3:
            raise ValueError("A polygon must have at least 3 vertices")
        
        for vertex in vertices:
            self._enforce_dimension(vertex)
        
        self.vertices = vertices
    
    def contains(self, point: List[float]) -> bool:
        """
        Check if point is inside the polygon using ray casting algorithm.
        
        Args:
            point: A 2D coordinate [x, y]
            
        Returns:
            True if the point is inside the polygon, False otherwise
        """
        self._enforce_dimension(point)
        
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


class Rectangle(Polygon):
    """A rectangular 2D region defined by 4 vertices."""
    
    def __init__(self, vertices: List[List[float]]):
        """
        Initialize a rectangle from 4 vertices.
        
        Args:
            vertices: List of 4 [x, y] coordinates defining the rectangle corners in order
        """
        if len(vertices) != 4:
            raise ValueError("A rectangle must have exactly 4 vertices")
        
        # Initialize as a polygon with 4 vertices
        super().__init__(vertices=vertices)
    
    # contains() method is inherited from Polygon - no need to reimplement!
