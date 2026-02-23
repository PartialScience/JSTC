from typing import Tuple, List
from app.geometry import GeometricRegion, Rectangle
from dataclasses import dataclass, field
from abc import abstractmethod

@dataclass(frozen=True)
class CoilComponent(GeometricRegion):
    """Base class for coil components with geometric and physical properties."""
    
    @abstractmethod
    def _geometry(self) -> GeometricRegion:
        """Return the underlying GeometricRegion."""
        pass
    
    def contains(self, point: List[float]) -> bool:
        """Check if point is inside by delegating to the wrapped geometry."""
        return self._geometry.contains(point)

@dataclass(frozen=True)
class ToploadSpec(CoilComponent):
    """Specification for a topload component with geometric properties."""
    shape: GeometricRegion
    
    def _geometry(self) -> GeometricRegion:
        return self.shape

@dataclass(frozen=True)
class GroundedConductorSpec(CoilComponent):
    """Specification for a grounded conductor component with geometric properties."""
    shape: GeometricRegion
    
    def _geometry(self) -> GeometricRegion:
        return self.shape

@dataclass(frozen=True)
class SecondaryConductorSpec(CoilComponent):
    """Specification for a secondary conductor with geometric, electrical, and material properties."""
    start: Tuple[float, float]
    end: Tuple[float, float]
    wire_dia: float
    turns: float
    conductivity: float
        
    def __post_init__(self):
        """Compute and store the rectangular geometry."""
        rectangle = Rectangle(vertices=(
            (self.start[0] - self.wire_dia / 2, self.start[1]),
            (self.start[0] + self.wire_dia / 2, self.start[1]),
            (self.end[0] + self.wire_dia / 2, self.end[1]),
            (self.end[0] - self.wire_dia / 2, self.end[1]),
        ))
        # Use object.__setattr__ since frozen=True
        object.__setattr__(self, '_rectangle', rectangle)
    
    @property
    def turns_per_height(self) -> float:
        """Turns per unit height of the secondary coil."""
        return self.turns / (self.end[1] - self.start[1])
        
    def _geometry(self) -> GeometricRegion:
        """Return the stored rectangular geometry."""
        return self._rectangle
    
    def get_geometry(self) -> GeometricRegion:
        """Return the internal geometry of the secondary conductor."""
        return self._geometry()

@dataclass(frozen=True)
class SecondaryConductorSegment(CoilComponent):
    geometry: GeometricRegion
    turns: float
    conductivity: float
    
    def _geometry(self) -> GeometricRegion:
        return self.geometry

@dataclass(frozen=False)
class TeslaCoilSpec: 
    """Specification for a complete Tesla coil including secondary, toploads, and grounds."""
    # TODO: Add dataclass structure for primary coil
    secondary: SecondaryConductorSpec
    toploads: Tuple[ToploadSpec, ...] = field(default_factory=tuple)
    grounds: Tuple[GroundedConductorSpec, ...] = field(default_factory=tuple)