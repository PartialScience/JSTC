from typing import Optional, Tuple, List
from app.models.materials import Material
from app.geometry import (
    BoundaryLoop,
    GeometricRegion,
    LineSegment,
    OffsetRegion,
    SubCurve,
    UnitSpeedCurve,
)
from app.geometry.cross_sections import CrossSection
from app.geometry.validation import tube_self_approach
from app.models.turn_profiles import ShiftedTurnProfile, TurnDistribution, TurnProfile
from dataclasses import dataclass, field
from abc import abstractmethod
from math import ceil


def _turn_count_ceil(total: float, rel_tol: float = 1e-9) -> int:
    """Ceiling of a turn count that is immune to float rounding noise.

    Turn totals are evaluated as ``turn_fxn(curve.t_max)``, where the
    profile's own t_max and the curve's t_max are the same quantity
    computed through different float expressions. Non-associative
    rounding can leave the result a few ulp above the exact integer
    (e.g. 1400 * 0.37 / 0.37 == 1400.0000000000002), and a bare ceil
    then invents a whole phantom turn - which downstream becomes a
    duplicate sampling ring coincident with the winding end and a
    divergent ring mutual inductance. A value within rel_tol of an
    integer IS that integer; only genuine fractional turns round up.
    """
    nearest = round(total)
    if abs(total - nearest) <= rel_tol * max(1.0, abs(total)):
        return int(nearest)
    return int(ceil(total))


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
    """Specification for a secondary conductor.

    All secondaries for the axial-symmetric tesla coil computations are
    modeled as a UNIT-SPEED parametric curve in the (r, z) plane (the
    winding centerline, parameterized by arc length) with a wire diameter,
    plus a turn distribution giving how the turns are laid out along it.

    This physically represents a coil of wire whose turns are all centered
    along the z axis: a cross-section in the (r, z) plane shows a string of
    circles of diameter wire_dia centered along the curve.

    Everything the solvers consume is DERIVED here, from the defining
    fields, so it can never disagree with them:

      * ``_offsetRegion``: the conductor envelope (curve + wire radius),
      * ``turn_fxn``: the cumulative turn profile, instantiated over the
        curve's actual arc-length domain [0, L] - the turn distribution
        itself knows nothing about the curve, which eliminates the
        profile/curve domain-mismatch class of bugs by construction.

    Derived fields are excluded from equality/hashing (compare=False), so
    identically-specified coils stay equal and the solver caches work.

    Construction validates the physical preconditions the solvers assume:
    positive wire diameter, an envelope that does not reach the curve's
    minimum radius of curvature (OffsetRegion), and a winding tube that
    never approaches itself closer than the wire diameter.
    """
    _offsetRegion: Optional[OffsetRegion] = field(
        default=None, init=False, repr=False, compare=False
    )
    """Derived conductor envelope in the (r, z) plane."""

    turn_fxn: Optional[TurnProfile] = field(
        default=None, init=False, repr=False, compare=False
    )
    """Derived cumulative turn profile over the curve's arc length."""

    turns: TurnDistribution = None
    """How the turns are distributed along the winding."""

    wire_dia: float = 0.0
    """Conductor (wire) diameter, in geometry units."""

    @abstractmethod
    def _curve(self) -> UnitSpeedCurve:
        """The winding centerline (unit-speed, from the defining fields)."""
        ...

    def __post_init__(self):
        if self.turns is None:
            raise ValueError("A secondary requires a turn distribution")
        if self.wire_dia <= 0:
            raise ValueError(f"wire_dia must be positive, got {self.wire_dia}")
        curve = self._curve()
        radius = self.wire_dia / 2
        approach = tube_self_approach(curve, radius)
        if approach is not None:
            t_a, t_b = approach
            raise ValueError(
                "The winding path approaches itself closer than the wire "
                f"diameter (between arc lengths {t_a:.6g} and {t_b:.6g}); "
                "the conductor would overlap itself."
            )
        object.__setattr__(self, '_offsetRegion', OffsetRegion(curve=curve, offset=radius))
        object.__setattr__(self, 'turn_fxn', self.turns.profile_over(curve.length))

    def _geometry(self) -> GeometricRegion:
        return self._offsetRegion

    @property
    def curve(self) -> UnitSpeedCurve:
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
        return _turn_count_ceil(self.turn_fxn(self.curve.t_max))

@dataclass(frozen=True)
class LinearSecondaryConductorSpec(SecondaryConductorSpec):
    """A secondary wound along a straight centerline from start to end."""
    start: Tuple[float, float] = (0.0, 0.0)
    end: Tuple[float, float] = (0.0, 0.0)

    def _curve(self) -> UnitSpeedCurve:
        return LineSegment(self.start, self.end)

@dataclass(frozen=True)
class CurveSecondaryConductorSpec(SecondaryConductorSpec):
    """A secondary wound along an arbitrary unit-speed centerline (arc,
    spline, ...). The curve classes are hashable value objects, so the spec
    stays structurally comparable and cache-friendly."""
    path: UnitSpeedCurve = None

    def __post_init__(self):
        if self.path is None:
            raise ValueError("CurveSecondaryConductorSpec requires a path")
        if not isinstance(self.path, UnitSpeedCurve):
            raise TypeError(
                f"A winding centerline must be unit-speed; got {type(self.path).__name__}"
            )
        super().__post_init__()

    def _curve(self) -> UnitSpeedCurve:
        return self.path

@dataclass(frozen=True)
class SecondaryConductorSegment(SecondaryConductorSpec):
    """A segment of a SecondaryConductorSpec restricted to parameter range [t1, t2].

    Constructed from an existing SecondaryConductorSpec. Automatically derives its
    geometry (sub-curve + offset region), material, turn distribution/profile and
    wire diameter from the parent.
    """
    full_secondary: SecondaryConductorSpec = field(default=None, repr=False)
    t1: float = 0.0
    t2: float = 0.0
    flatten_start: bool = False
    flatten_end: bool = False

    def _curve(self) -> UnitSpeedCurve:
        return SubCurve(self.full_secondary.curve, self.t1, self.t2)

    def __post_init__(self):
        parent = self.full_secondary
        if parent is None:
            raise ValueError("SecondaryConductorSegment requires full_secondary")
        sub_curve = self._curve()
        offset_region = OffsetRegion(
            curve=sub_curve,
            offset=parent.geometry.offset,
            flat_start=self.flatten_start,
            flat_end=self.flatten_end,
        )

        # Derive a turn function relative to t1 (kept hashable via a
        # ShiftedTurnProfile rather than a closure).
        segment_turn_fxn = ShiftedTurnProfile(base=parent.turn_fxn, t_shift=self.t1)

        # Use object.__setattr__ since frozen=True. The defining fields are
        # mirrored from the parent so equality still compares what the
        # segment physically is.
        object.__setattr__(self, '_offsetRegion', offset_region)
        object.__setattr__(self, 'turn_fxn', segment_turn_fxn)
        object.__setattr__(self, 'material', parent.material)
        object.__setattr__(self, 'turns', parent.turns)
        object.__setattr__(self, 'wire_dia', parent.wire_dia)

@dataclass(frozen=True)
class PrimarySpec:
    """Specification of the primary coil.

    Mirrors the secondary's representation: a unit-speed parametric curve in
    the (r, z) plane traced by the winding centerline, a turn distribution
    along it, and a conductor cross-section (round wire by default,
    rectangular for ribbon primaries). A flat spiral is a horizontal curve;
    a saucer primary is a slanted one; a QCW arc primary is a CircularArc.

    Solvers consume DERIVED representations, never this spec directly:

      * Electrostatics: one grounded cross-section region per turn
        (ring_regions) - the primary sits at ~ground potential on
        secondary-resonance timescales.
      * Magnetics: one coaxial ring per turn (ring_centers), with the
        cross-section's GMD supplying the self-inductance terms.

    The cumulative turn profile (turn_fxn) is derived from the turn
    distribution over the curve's actual arc length, exactly as for the
    secondary.

    Circuit-level attributes (tank_capacitance, leads) describe the
    primary's resonant circuit rather than its geometry; tank capacitance
    is in Farads (SI), while all geometry shares the coil's unit system.
    """

    material: Material
    """Conductor material of the primary winding."""

    turn_fxn: Optional[TurnProfile] = field(
        default=None, init=False, repr=False, compare=False
    )
    """Derived cumulative turn profile over the curve's arc length."""

    turns: TurnDistribution = None
    """How the turns are distributed along the winding."""

    cross_section: CrossSection = None
    """Conductor cross-section profile in the (r, z) plane."""

    tank_capacitance: float = 0.0
    """Primary tank capacitance in Farads (0 = no tank specified)."""

    lead_length: float = 0.0
    """Total connection lead length, in geometry units."""

    lead_dia: float = 0.0
    """Connection lead conductor diameter, in geometry units."""

    @property
    def curve(self) -> UnitSpeedCurve:
        """The winding centerline in the (r, z) plane."""
        raise NotImplementedError("Concrete primary specs must provide a curve")

    def __post_init__(self):
        if self.turns is None:
            raise ValueError("A primary requires a turn distribution")
        if self.cross_section is None:
            raise ValueError("A primary requires a conductor cross-section")
        object.__setattr__(self, 'turn_fxn', self.turns.profile_over(self.curve.length))

    @property
    def total_turns(self) -> float:
        """Total number of turns (fractional turns preserved - a 8.438
        turn primary is meaningfully different from 9 turns)."""
        return float(self.turn_fxn(self.curve.t_max))

    def ring_centers(self) -> Tuple[Tuple[float, float], ...]:
        """Centerline position of each turn's equivalent coaxial ring.

        Turn k occupies [k, k+1] in turn-space (the final turn possibly
        fractional); its ring sits at the turn-space midpoint, located on
        the curve by the profile's EXACT inverse.
        """
        curve = self.curve
        total = self.total_turns
        if total <= 0:
            raise ValueError(f"Primary must have positive turns, got {total}")

        n_rings = _turn_count_ceil(total)
        mid_turns = [
            (k + min(k + 1.0, total)) / 2.0 for k in range(n_rings)
        ]
        return tuple(curve.point_at(self.turn_fxn.inverse(m)) for m in mid_turns)

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
        n_rings = _turn_count_ceil(total)
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
        super().__post_init__()

    @property
    def curve(self) -> UnitSpeedCurve:
        return LineSegment(self.start, self.end)


@dataclass(frozen=True)
class CurvePrimarySpec(PrimarySpec):
    """A primary wound along an arbitrary unit-speed centerline (e.g. the
    circular-arc primaries used on QCW coils, or a spline path)."""

    path: UnitSpeedCurve = None

    def __post_init__(self):
        if self.path is None:
            raise ValueError("CurvePrimarySpec requires a path")
        if not isinstance(self.path, UnitSpeedCurve):
            raise TypeError(
                f"A winding centerline must be unit-speed; got {type(self.path).__name__}"
            )
        super().__post_init__()

    @property
    def curve(self) -> UnitSpeedCurve:
        return self.path


@dataclass(frozen=False)
class TeslaCoilSpec:
    """Specification for a complete Tesla coil including secondary, primary, toploads, and grounds."""
    secondary: SecondaryConductorSpec
    toploads: Tuple[ToploadSpec, ...] = field(default_factory=tuple)
    grounds: Tuple[GroundedConductorSpec, ...] = field(default_factory=tuple)
    primary: Optional[PrimarySpec] = None
