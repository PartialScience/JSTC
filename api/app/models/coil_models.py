from typing import Optional, Tuple, List, Callable
from app.models.materials import Material
from app.geometry import GeometricRegion, LineSegment, OffsetRegion, ParametricCurve, SubCurve
from dataclasses import dataclass, field
from abc import abstractmethod


@dataclass(frozen=True)
class CoilComponent(GeometricRegion):
    """Base class for coil components with geometric and physical properties."""
    
    material: Material
    """The material of the coil component conductor"""
    
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
    """Specification for a secondary conductor
    
    All secondaries for the axial-symmetric tesla coil computations are modeled as a parametric
    curve in the (r,z) plane with a given thickness representing the wire diameter. Along with a 
    density function that gives the number of turns at a given point along the parameterization
    of the curve. 
    
    This physically represents a coil of wire whose turns are all centered along the z axis. If
    you were to take a cross section of this coil in the (r,z) plane, you would see a string of
    circles of diameter (wire_dia) centered along the curve defined by the parametric curve.
    
    Finally, this representation also allows for coils which don't necessarily have a uniform 
    spacing between turns, as the turn function does not need to be constant. 
    """
    _offsetRegion: Optional[OffsetRegion] = field(default=None, init=False, repr=False)
    """The offset region representing cross section of the coil's windings in the (r,z) plane."""
    turn_fxn: Callable[[float], float]
    """A function that takes in a parameter t along the curve and returns the number of turns up to that point."""
    
    def _geometry(self) -> GeometricRegion:
        return self._offsetRegion
    
    @property
    def get_curve(self) -> ParametricCurve:
        """Get the central curve of the secondary conductor."""
        return self._offsetRegion.curve
    
    @property
    def get_geometry(self) -> OffsetRegion:
        """Return the internal geometry of the secondary conductor."""
        return self._offsetRegion
    
    @property
    def total_turns(self) -> float:
        """Return the total number of turns in the secondary coil."""
        return self.turn_fxn(self.get_curve.t_max)

@dataclass(frozen=True)
class LinearSecondaryConductorSpec(SecondaryConductorSpec):
    """Representation of a secondary as a single straight line segment with a given wire diameter."""
    start: Tuple[float, float]
    end: Tuple[float, float]
    wire_dia: float
    
    def __post_init__(self):
        """Compute an offset region from the inputs and store it as the geometry."""
        line_segment = LineSegment(self.start, self.end)
        offsetRegion = OffsetRegion(curve=line_segment, offset=self.wire_dia / 2)
        # Usturne object.__setattr__ since frozen=True
        object.__setattr__(self, '_offsetRegion', offsetRegion)

@dataclass(frozen=True)
class SecondaryConductorSegment(SecondaryConductorSpec):
    """A segment of a SecondaryConductorSpec restricted to parameter range [t1, t2].
    
    Constructed from an existing SecondaryConductorSpec. Automatically derives its
    geometry (sub-curve + offset region), material, and turn function from the parent.
    """
    full_secondary: SecondaryConductorSpec = field(repr=False)
    t1: float
    t2: float
    
    def __post_init__(self):
        parent = self.full_secondary
        sub_curve = SubCurve(parent.get_curve, self.t1, self.t2)
        offset_region = OffsetRegion(curve=sub_curve, offset=parent.get_geometry.offset)
        
        # Derive a turn function relative to t1
        parent_turn_fxn = parent.turn_fxn
        segment_turn_fxn = lambda t, _f=parent_turn_fxn, _t1=self.t1: _f(t) - _f(_t1)
        
        # Use object.__setattr__ since frozen=True
        object.__setattr__(self, '_offsetRegion', offset_region)
        object.__setattr__(self, 'turn_fxn', segment_turn_fxn)
        object.__setattr__(self, 'material', parent.material)

@dataclass(frozen=False)
class TeslaCoilSpec: 
    """Specification for a complete Tesla coil including secondary, toploads, and grounds."""
    # TODO: Add dataclass structure for primary coil
    secondary: SecondaryConductorSpec
    toploads: Tuple[ToploadSpec, ...] = field(default_factory=tuple)
    grounds: Tuple[GroundedConductorSpec, ...] = field(default_factory=tuple)