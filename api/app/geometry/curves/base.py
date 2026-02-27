"""
Base class for all parametric curves
"""

from abc import ABC, abstractmethod
from typing import List, Tuple


class ParametricCurve(ABC):
    """Abstract base class for parametric curves."""
    
    @property
    @abstractmethod
    def t_min(self) -> float:
        """The minimum parameter value for the curve."""
        ...
    
    @property
    @abstractmethod
    def t_max(self) -> float:
        """The maximum parameter value for the curve."""
        ...
    
    @abstractmethod
    def point_at(self, t: float) -> tuple[float, ...]:
        """
        Get the point on the curve corresponding to the parameter t.
        
        Args:
            t: The parameter value
            
        Returns:
            A tuple of floats representing the coordinates of the point on the curve
        """
        ...
    
    @abstractmethod
    def distance_to_curve(self, point: tuple[float, ...]) -> float:
        """
        Provide the shortest distance from a given point to the curve.
        
        While this may seem like a strange way to represent parametric curves,
        it is necessary for building offset regions from them, which is their
        main purpose in this codebase. 
        
        Args:
            point: A tuple of floats representing the coordinates of the point
            
        Returns:
            The shortest distance from the point to the curve
        """
        ...
    
    def bounding_box(self) -> List[Tuple[float, float]]:
        """Return the bounding box of the curve as a list of (min, max) tuples for each dimension."""
        ...
        
