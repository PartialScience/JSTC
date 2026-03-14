"""
Base class for all parametric curves
"""

from abc import ABC, abstractmethod


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
    def derivative_at(self, t: float) -> tuple[float, ...]:
        """
        Get the derivative (tangent vector) of the curve at parameter t.
        
        Args:
            t: The parameter value
            
        Returns:
            A tuple of floats representing the components of the tangent vector
        """
        ...    
    
    @abstractmethod
    def arc_length_between(self, t1: float, t2: float) -> float:
        """
        Compute the arc length of the curve between parameters t1 and t2.
        
        Args:
            t1: The start parameter value
            t2: The end parameter value
            
        Returns:
            The arc length of the curve between t1 and t2.
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
