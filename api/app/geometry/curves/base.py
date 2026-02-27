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
    def distance_to_curve_for_range(self, point: tuple[float, ...], t1: float, t2: float) -> float:
        """
        Provide the shortest distance from a given point to the portion of
        the curve restricted to the parameter range [t1, t2].
        
        Args:
            point: A tuple of floats representing the coordinates of the point
            t1: The start of the parameter range
            t2: The end of the parameter range
            
        Returns:
            The shortest distance from the point to the curve over [t1, t2]
        """
        ...
    
    @abstractmethod
    def bounding_box_for_range(self, t1: float, t2: float) -> List[Tuple[float, float]]:
        """Return the bounding box of the curve over parameter range [t1, t2]
        as a list of (min, max) tuples for each dimension."""
        ...

    def distance_to_curve(self, point: tuple[float, ...]) -> float:
        """
        Provide the shortest distance from a given point to the curve.
        
        Delegates to distance_to_curve_for_range over the full parameter domain.
        
        Args:
            point: A tuple of floats representing the coordinates of the point
            
        Returns:
            The shortest distance from the point to the curve
        """
        return self.distance_to_curve_for_range(point, self.t_min, self.t_max)

    def bounding_box(self) -> List[Tuple[float, float]]:
        """Return the bounding box of the curve as a list of (min, max) tuples for each dimension.
        
        Delegates to bounding_box_for_range over the full parameter domain.
        """
        return self.bounding_box_for_range(self.t_min, self.t_max)
        
