"""
Curve continuations: segments buildable from an inherited start point and
unit tangent.

This is the EXPLICIT contract behind piecewise tangent-continuous paths:
a segment type may appear after another segment only if it can be
constructed, in closed form or with its own owned numerics, from the
junction state (point, tangent) plus its remaining free parameters. The
type system tracks the capability (a curve type without a continuation
cannot appear mid-chain), and the shared continuation contract test suite
enforces the postcondition for every registered implementation:

    c = continuation.build(point, tangent)
    c.point_at(c.t_min)      == point     (C0)
    c.derivative_at(c.t_min) == tangent   (C1, since curves are unit-speed)

Each continuation is a frozen value object carrying exactly the segment's
free parameters (the reduced DOFs) - the junction state is inherited, so
tangent continuity is met by construction rather than validated after the
fact. These objects are also the API schema members ("line-from",
"arc-from", "spline-from").
"""
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple

from app.geometry.curves.base import UnitSpeedCurve
from app.geometry.curves.catmull_rom import CatmullRomSpline
from app.geometry.curves.circular_arc import CircularArc
from app.geometry.curves.line_segment import LineSegment

Point = Tuple[float, float]


@dataclass(frozen=True)
class CurveContinuation(ABC):
    """A segment of a piecewise path, built from the inherited junction."""

    @abstractmethod
    def build(self, point: Point, tangent: Point) -> UnitSpeedCurve:
        """The unit-speed segment starting at ``point`` with unit ``tangent``.

        Implementations must satisfy the C0/C1 postcondition in the module
        docstring for every valid input, and raise ValueError (with a
        message naming the fix) for degenerate free parameters.
        """
        ...

    @abstractmethod
    def canonical(self) -> tuple:
        """JSON-serializable exact description (type tag + free parameters),
        for geometry fingerprints."""
        ...


@dataclass(frozen=True)
class LineContinuation(CurveContinuation):
    """A straight segment continuing along the inherited tangent.

    The direction is fully inherited; the single free parameter is the
    length. (Its endpoint is consequently derived, which is why saved files
    store the length - the one representation that cannot disagree with the
    tangent constraint.)
    """

    length: float

    def __post_init__(self):
        if not self.length > 0:
            raise ValueError(f"line-from length must be positive, got {self.length}")

    def build(self, point: Point, tangent: Point) -> LineSegment:
        return LineSegment(
            start=point,
            end=(point[0] + tangent[0] * self.length, point[1] + tangent[1] * self.length),
        )

    def canonical(self) -> tuple:
        return ("line-from", self.length)


@dataclass(frozen=True)
class ArcContinuation(CurveContinuation):
    """A circular arc tangent to the inherited direction, ending at ``end``.

    Centers of circles tangent to the direction T at point P lie on the
    normal line through P, so requiring the circle to pass through the
    endpoint Q is LINEAR in the center's offset s along that normal:

        |C - P| = |C - Q|,  C = P + s*n  =>  s = |Q - P|^2 / (2 n.(Q - P))

    (n the unit left normal of T). The traversal direction follows the
    sign of s (center left => CCW), and the sweep is whatever reaching Q
    takes - beyond a semicircle included. The only degenerate input is an
    endpoint ON the tangent line through P: ahead of P that is a straight
    segment (use line-from), behind it no tangent circle exists.
    """

    end: Point

    def build(self, point: Point, tangent: Point) -> CircularArc:
        px, pz = point
        tx, tz = tangent
        qx, qz = float(self.end[0]), float(self.end[1])
        dx, dz = qx - px, qz - pz
        chord = math.hypot(dx, dz)
        if chord == 0.0:
            raise ValueError("arc-from endpoint must differ from the junction point")

        nx, nz = -tz, tx  # unit left normal of the inherited tangent
        denom = 2.0 * (nx * dx + nz * dz)
        if abs(denom) <= 1e-12 * chord:
            if tx * dx + tz * dz > 0:
                raise ValueError(
                    "arc-from endpoint lies straight ahead on the tangent "
                    "line; use a line-from segment for a straight continuation."
                )
            raise ValueError(
                "arc-from endpoint lies behind the junction on the tangent "
                "line; no tangent circle passes through it."
            )
        s = (chord * chord) / denom
        center = (px + s * nx, pz + s * nz)
        radius = abs(s)

        a_start = math.atan2(pz - center[1], px - center[0])
        a_end = math.atan2(qz - center[1], qx - center[0])
        two_pi = 2.0 * math.pi
        if s > 0:
            # Center on the left of travel: counter-clockwise
            sweep = (a_end - a_start) % two_pi
            return CircularArc(
                center=center, radius=radius,
                angle_start=a_start, angle_end=a_start + sweep,
            )
        sweep = (a_start - a_end) % two_pi
        return CircularArc(
            center=center, radius=radius,
            angle_start=a_start, angle_end=a_start - sweep,
        )

    def canonical(self) -> tuple:
        return ("arc-from", tuple(self.end))


@dataclass(frozen=True)
class SplineContinuation(CurveContinuation):
    """A centripetal Catmull-Rom segment whose start tangent is clamped to
    the inherited direction, interpolating the given points.

    The free parameters are the interpolation points (the junction point is
    prepended, the start tangent clamped - see CatmullRomSpline's
    ``start_tangent`` for the exact Hermite convention).
    """

    points: Tuple[Point, ...]

    def __post_init__(self):
        pts = tuple((float(p[0]), float(p[1])) for p in self.points)
        object.__setattr__(self, "points", pts)
        if len(pts) < 1:
            raise ValueError("spline-from needs at least 1 interpolation point")

    def build(self, point: Point, tangent: Point) -> CatmullRomSpline:
        return CatmullRomSpline(
            points=(tuple(point), *self.points),
            start_tangent=(float(tangent[0]), float(tangent[1])),
        )

    def canonical(self) -> tuple:
        return ("spline-from", self.points)
