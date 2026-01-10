from typing import Optional, List
from app.geometry import GeometricRegion, Rectangle

class Topload:
    """A topload for a 2D tesla coil, defined by a 2D shape."""
    
    def __init__(self, geometry: GeometricRegion):
        """
        Initialize a topload.
        
        Args:
            geometry: A 2D geometric region representing the topload's cross-section
        """
        self.geometry = geometry

class SecondaryConductor:
    """A secondary conductor for a tesla coil"""
    
    def __init__(self, start: List[float], end: List[float], wire_dia: float, turns: float, conductivity: float):
        """
        Initialize a secondary conductor.
        
        Args:
            start: Starting point of the conductor as a list of two floats [x, y]
            end: Ending point of the conductor as a list of two floats [x, y]
            wire_dia: Diameter of the wire
            turns: Number of turns in the coil
            conductivity: Electrical conductivity of the conductor
        """
        self.start = start
        self.end = end
        self.wire_dia = wire_dia
        self.turns = turns
        self.conductivity = conductivity
        self.turns_per_height = turns / (end[1] - start[1])
        rectangle = Rectangle(vertices=[
            [start[0] - wire_dia / 2, start[1]],
            [start[0] + wire_dia / 2, start[1]],
            [end[0] + wire_dia / 2, end[1]],
            [end[0] - wire_dia / 2, end[1]],
        ])
        self.geometry = rectangle

class GroundedConductor: 
    """A grounded conductor representing a region in space which will be forced to 0V during all computations"""
    
    def __init__(self, geometry: GeometricRegion):
        """
        Initialize a grounded conductor.
        
        Args:
            geometry: A 2D geometric region representing the conductor's cross-section
        """
        self.geometry = geometry

class TeslaCoil: 
    """Geometric description of a tesla coil"""
    def __init__(self, 
        secondary: SecondaryConductor,
        toploads: Optional[List[Topload]] = None,
        grounds: Optional[List[GroundedConductor]] = None,
    ):
        """
        Initialize a Tesla coil model.
        
        Args:
            toploads: Optional list of Topload objects
            secondary: Optional SecondaryConductor object
        """
        self.secondary = secondary
        self.toploads = toploads if toploads is not None else []
        self.grounds = grounds if grounds is not None else []
        
