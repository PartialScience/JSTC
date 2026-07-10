from typing import Optional, Tuple, List, Callable
from app.models.materials import Material
from app.geometry import BoundaryLoop, GeometricRegion, LineSegment, OffsetRegion, ParametricCurve, SubCurve
from app.geometry.cross_sections import CrossSection
from app.models.turn_profiles import ShiftedTurnProfile
from dataclasses import dataclass, field
from abc import abstractmethod
from math import ceil


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
        return self._geometry().contains(point)

    def boundary_loops(self) -> Tuple[BoundaryLoop, ...]:
        """Describe the boundary by delegating to the wrapped geometry."""
        return self._geometry().boundary_loops()

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
    def curve(self) -> ParametricCurve:
        """Get the central curve of the secondary conductor."""
        return self._offsetRegion.curve
    
    @property
    def geometry(self) -> OffsetRegion:
        """Return the internal geometry of the secondary conductor."""
        return self._offsetRegion
    
    @property
    def total_turns(self) -> int:
        """
        Return the total number of turns in the secondary coil. 
        
        If there are a fractional number of turns, it will be 
        rounded up to the nearest int. This is so that the added
        height of the turn is always counted even if the turn does
        not fully wrap around the coil. These fractional effects
        are almost always negligible anyway, and even adding/subtracting 
        a few extra turns is likely to be negligible. So the height is
        a more important consideration. 
        """
        return int(ceil(self.turn_fxn(self.curve.t_max)))

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
    flatten_start: bool = False
    flatten_end: bool = False
    
    def __post_init__(self):
        parent = self.full_secondary
        sub_curve = SubCurve(parent.curve, self.t1, self.t2)
        offset_region = OffsetRegion(
            curve=sub_curve, 
            offset=parent.geometry.offset,
            flat_start=self.flatten_start,
            flat_end=self.flatten_end,
        )
        
        # Derive a turn function relative to t1 (kept hashable via a
        # ShiftedTurnProfile rather than a closure).
        segment_turn_fxn = ShiftedTurnProfile(base=parent.turn_fxn, t_shift=self.t1)

        # Use object.__setattr__ since frozen=True
        object.__setattr__(self, '_offsetRegion', offset_region)
        object.__setattr__(self, 'turn_fxn', segment_turn_fxn)
        object.__setattr__(self, 'material', parent.material)

@dataclass(frozen=True)
class PrimarySpec:
    """Specification of the primary coil.

    Mirrors the secondary's representation: a parametric curve in the
    (r, z) plane traced by the winding centerline, a cumulative turn
    function along it, and a conductor cross-section (round wire by
    default, rectangular for ribbon primaries). A flat spiral is a
    horizontal curve; a saucer primary is a slanted one.

    Solvers consume DERIVED representations, never this spec directly:

      * Electrostatics: one grounded cross-section region per turn
        (ring_regions) - the primary sits at ~ground potential on
        secondary-resonance timescales.
      * Magnetics: one coaxial ring per turn (ring_centers), with the
        cross-section's GMD supplying the self-inductance terms.

    Circuit-level attributes (tank_capacitance, leads) describe the
    primary's resonant circuit rather than its geometry; tank capacitance
    is in Farads (SI), while all geometry shares the coil's unit system.
    """

    material: Material
    """Conductor material of the primary winding."""

    turn_fxn: Callable[[float], float]
    """Cumulative number of turns at parameter t along the curve."""

    cross_section: CrossSection
    """Conductor cross-section profile in the (r, z) plane."""

    tank_capacitance: float = 0.0
    """Primary tank capacitance in Farads (0 = no tank specified)."""

    lead_length: float = 0.0
    """Total connection lead length, in geometry units."""

    lead_dia: float = 0.0
    """Connection lead conductor diameter, in geometry units."""

    @property
    def curve(self) -> ParametricCurve:
        """The winding centerline in the (r, z) plane."""
        raise NotImplementedError("Concrete primary specs must provide a curve")

    @property
    def total_turns(self) -> float:
        """Total number of turns (fractional turns preserved - a 8.438
        turn primary is meaningfully different from 9 turns)."""
        return float(self.turn_fxn(self.curve.t_max))

    def ring_centers(self) -> Tuple[Tuple[float, float], ...]:
        """Centerline position of each turn's equivalent coaxial ring.

        Turn k occupies [k, k+1] in turn-space (the final turn possibly
        fractional); its ring sits at the turn-space midpoint, located on
        the curve by inverting turn_fxn via dense linear interpolation.
        """
        import numpy as np

        curve = self.curve
        total = self.total_turns
        if total <= 0:
            raise ValueError(f"Primary must have positive turns, got {total}")

        n_rings = int(ceil(total))
        mid_turns = [
            (k + min(k + 1.0, total)) / 2.0 for k in range(n_rings)
        ]

        t_sample = np.linspace(curve.t_min, curve.t_max, max(64, 32 * n_rings))
        turn_sample = np.array([self.turn_fxn(t) for t in t_sample])
        t_mid = np.interp(mid_turns, turn_sample, t_sample)
        return tuple(curve.point_at(float(t)) for t in t_mid)

    def ring_regions(self) -> Tuple[GeometricRegion, ...]:
        """The (r, z) cross-section region of each turn - the primary's
        representation for the electrostatic (grounded conductor) solve."""
        return tuple(
            self.cross_section.region_at(center) for center in self.ring_centers()
        )

    def ring_turn_fractions(self) -> Tuple[float, ...]:
        """Fraction of a full turn each ring represents (1.0 except for a
        fractional final turn). Magnetics must weight ring currents and
        flux linkages by these - a 0.438-turn arc links 0.438 of a full
        ring's flux. (Electrostatics ignores them: a partial arc still
        cannot be represented axisymmetrically, and the capacitance
        effect of the difference is negligible.)"""
        total = self.total_turns
        n_rings = int(ceil(total))
        return tuple(min(k + 1.0, total) - k for k in range(n_rings))


@dataclass(frozen=True)
class LinearPrimarySpec(PrimarySpec):
    """A primary whose centerline is a straight segment in the (r, z)
    plane: flat Archimedean spirals (horizontal), helical primaries
    (vertical), and saucer/conical primaries (slanted)."""

    start: Tuple[float, float] = (0.0, 0.0)
    end: Tuple[float, float] = (0.0, 0.0)

    def __post_init__(self):
        if self.start == self.end:
            raise ValueError("Primary start and end must differ")

    @property
    def curve(self) -> ParametricCurve:
        return LineSegment(self.start, self.end)


@dataclass(frozen=False)
class TeslaCoilSpec:
    """Specification for a complete Tesla coil including secondary, primary, toploads, and grounds."""
    secondary: SecondaryConductorSpec
    toploads: Tuple[ToploadSpec, ...] = field(default_factory=tuple)
    grounds: Tuple[GroundedConductorSpec, ...] = field(default_factory=tuple)
    primary: Optional[PrimarySpec] = None