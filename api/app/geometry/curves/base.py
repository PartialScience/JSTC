"""
Base classes for parametric curves.

Two levels of contract:

``ParametricCurve``
    The minimal interface every curve-shaped object provides. Every method
    is abstract: there are NO generic numeric fallbacks. If a curve's shape
    is known there is always a better-than-generic algorithm for each of
    these quantities, and concrete classes are required to supply it (see
    LineSegment and CircularArc for fully closed-form examples, and
    CatmullRomSpline for a curve that owns its deliberate numerics).

``UnitSpeedCurve``
    A ParametricCurve whose parameter IS arc length: t runs over
    [t_min, t_max] in geometry units with |derivative_at(t)| == 1
    everywhere. Every winding centerline must satisfy this contract - it is
    what makes turn densities physically meaningful (turns per unit length),
    makes discretization exact, and is enforced by the parameterized
    contract test suite (tests/geometry/curves/test_unit_speed_contract.py).

    The deliberate exception is OffsetCurve, which shares its parent's
    parameter by construction (so winding slice parameters land on both
    sides of the conductor boundary) and therefore cannot be unit speed.
    It remains a plain ParametricCurve, so the type system prevents it from
    ever being used as a winding centerline.

Curvature sign convention (shared by every implementation): curvature is
signed with respect to the LEFT normal of the direction of travel - the
unit tangent rotated +90 degrees CCW. A CCW circular arc has positive
curvature; its left normal points toward the center.
"""

from abc import ABC, abstractmethod


class ParametricCurve(ABC):
    """Abstract base class for parametric curves. See the module docstring
    for the design contract; every method here is abstract on purpose."""

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
    def point_at(self, t: float) -> tuple[float, float]:
        """The point on the curve at parameter t."""
        ...

    @abstractmethod
    def derivative_at(self, t: float) -> tuple[float, float]:
        """The tangent vector of the curve at parameter t.

        For a UnitSpeedCurve this is the unit tangent.
        """
        ...

    @abstractmethod
    def curvature_at(self, t: float) -> float:
        """Signed curvature at parameter t (left-normal convention)."""
        ...

    @abstractmethod
    def arc_length_between(self, t1: float, t2: float) -> float:
        """Arc length of the curve between parameters t1 and t2."""
        ...

    @abstractmethod
    def closest_parameter_in_range(
        self, point: tuple[float, float], t1: float, t2: float
    ) -> float:
        """The parameter t* in [t1, t2] minimizing |point - point_at(t)|.

        Implementations must locate the GLOBAL minimum over the range.
        """
        ...

    @abstractmethod
    def sample_params(
        self,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        """Parameter values whose polyline deviates from the curve by at
        most ``max_chord_error``.

        Args:
            max_chord_error: Maximum allowed curve-to-chord deviation of any
                sampled segment.
            include: Parameter values that must appear exactly in the sample
                (values outside the domain are ignored, so a loop-wide list
                can be forwarded to every boundary piece).

        Returns:
            Sorted tuple of parameter values from t_min to t_max.
        """
        ...

    @abstractmethod
    def canonical(self) -> tuple:
        """A JSON-serializable canonical description of the curve: a type
        tag plus the exact defining parameters. Used for geometry
        fingerprints, so it must uniquely determine the curve."""
        ...

    # ------------------------------------------------------------------
    # Exact conveniences in terms of the abstract interface
    # ------------------------------------------------------------------

    def closest_parameter(self, point: tuple[float, float]) -> float:
        """The parameter of the curve point closest to *point* over the
        full domain."""
        return self.closest_parameter_in_range(point, self.t_min, self.t_max)

    def distance_to_curve_for_range(
        self, point: tuple[float, float], t1: float, t2: float
    ) -> float:
        """Shortest distance from *point* to the curve restricted to
        [t1, t2] - exact given the exact projection."""
        t_star = self.closest_parameter_in_range(point, t1, t2)
        p = self.point_at(t_star)
        return ((point[0] - p[0]) ** 2 + (point[1] - p[1]) ** 2) ** 0.5

    def distance_to_curve(self, point: tuple[float, float]) -> float:
        """Shortest distance from *point* to the curve."""
        return self.distance_to_curve_for_range(point, self.t_min, self.t_max)


class UnitSpeedCurve(ParametricCurve):
    """A ParametricCurve parameterized BY ARC LENGTH (unit speed).

    Contract (enforced by the shared contract test suite):
      * |derivative_at(t)| == 1 for every t in [t_min, t_max];
      * arc_length_between(t1, t2) == t2 - t1 identically;
      * derivative_at is continuous (G1 - no kinks).

    Winding specs require this type for their centerlines.
    """

    def arc_length_between(self, t1: float, t2: float) -> float:
        """Arc length is the parameter difference - the defining identity."""
        return t2 - t1

    @property
    def length(self) -> float:
        """Total arc length of the curve."""
        return self.t_max - self.t_min

    @abstractmethod
    def max_abs_curvature(self) -> float:
        """An upper bound on |curvature| over the curve, used to validate
        offset constructions (the offset distance must stay below the
        minimum radius of curvature)."""
        ...

    @abstractmethod
    def sample_params_for_offset(
        self,
        offset: float,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        """Parameter values (in THIS curve's parameterization) such that the
        polyline through the PARALLEL curve at signed distance ``offset``
        deviates from it by at most ``max_chord_error``.

        Each concrete curve knows its offsets exactly (a line's offset is a
        parallel line, an arc's a concentric arc, a spline's a curve whose
        curvature follows from the spline's), so offset sampling lives here
        rather than as a numeric search on OffsetCurve.
        """
        ...
