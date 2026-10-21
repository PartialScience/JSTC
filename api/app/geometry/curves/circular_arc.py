"""
Circular arc, parameterized by arc length.
"""
import math
from dataclasses import dataclass

from app.geometry.curves.base import UnitSpeedCurve


@dataclass(frozen=True)
class CircularArc(UnitSpeedCurve):
    """An arc of a circle, parameterized by ARC LENGTH: t runs over
    [0, radius * |angle_end - angle_start|] and the angle at parameter t is
    angle_start + sign(sweep) * t / radius. Every quantity is closed-form.

    ``angle_start`` and ``angle_end`` are the angles of the START and END
    of the traversal: an increasing range is a CCW arc, a decreasing range
    a CW arc. With the left-normal sign convention a CCW arc has curvature
    +1/radius (left normal toward the center) and a CW arc -1/radius (left
    normal away from the center).
    """

    center: tuple[float, float]
    radius: float
    angle_start: float
    angle_end: float

    def __post_init__(self):
        if self.radius <= 0:
            raise ValueError(f"Radius must be positive, got {self.radius}")
        if self.angle_end == self.angle_start:
            raise ValueError("angle_end must differ from angle_start")
        if abs(self.angle_end - self.angle_start) > 2 * math.pi + 1e-12:
            raise ValueError(
                f"Sweep {abs(self.angle_end - self.angle_start)} exceeds a full circle"
            )

    @classmethod
    def from_endpoints(
        cls,
        start: tuple[float, float],
        end: tuple[float, float],
        radius: float,
    ) -> "CircularArc":
        """The minor arc from ``start`` to ``end`` with the given SIGNED
        radius - the user-facing arc description (start point, end point,
        radius), as the editor specifies it.

        Sign convention: positive radius places the center on the LEFT of
        the start->end direction, so the path bends left (CCW, positive
        curvature); negative radius bends right (CW). |radius| must be at
        least half the chord length. The minor arc (sweep <= pi) is always
        taken; larger sweeps are built from multiple arcs or a spline.
        """
        ax, ay = float(start[0]), float(start[1])
        bx, by = float(end[0]), float(end[1])
        cx_, cy_ = bx - ax, by - ay
        chord = math.hypot(cx_, cy_)
        if chord == 0.0:
            raise ValueError("Arc start and end must differ")
        r = abs(float(radius))
        if radius == 0.0:
            raise ValueError("Arc radius must be non-zero")
        if r < chord / 2.0:
            raise ValueError(
                f"Arc radius {r} is smaller than half the chord ({chord / 2.0:.6g}); "
                "no circle of that radius passes through both endpoints."
            )
        side = 1.0 if radius > 0 else -1.0
        # Unit left normal of the start->end direction
        nx, ny = -cy_ / chord, cx_ / chord
        # Center: on the chosen side of the chord midpoint
        h = math.sqrt(max(r * r - (chord / 2.0) ** 2, 0.0))
        mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
        center = (mx + side * h * nx, my + side * h * ny)

        angle_start = math.atan2(ay - center[1], ax - center[0])
        sweep = 2.0 * math.asin(min(1.0, chord / (2.0 * r)))
        # Center on the left => bending left => CCW (increasing angles)
        angle_end = angle_start + side * sweep
        return cls(center=center, radius=r, angle_start=angle_start, angle_end=angle_end)

    # -- parameter/angle mapping ------------------------------------------------

    @property
    def _direction(self) -> float:
        """+1 for CCW (increasing angles), -1 for CW."""
        return 1.0 if self.angle_end > self.angle_start else -1.0

    def _angle_at(self, t: float) -> float:
        return self.angle_start + self._direction * t / self.radius

    @property
    def t_min(self) -> float:
        return 0.0

    @property
    def t_max(self) -> float:
        return self.radius * abs(self.angle_end - self.angle_start)

    # -- geometry ----------------------------------------------------------------

    def point_at(self, t: float) -> tuple[float, float]:
        a = self._angle_at(t)
        return (
            self.center[0] + self.radius * math.cos(a),
            self.center[1] + self.radius * math.sin(a),
        )

    def derivative_at(self, t: float) -> tuple[float, float]:
        """Unit tangent in the traversal direction."""
        a = self._angle_at(t)
        d = self._direction
        return (-d * math.sin(a), d * math.cos(a))

    def curvature_at(self, t: float) -> float:
        return self._direction / self.radius

    def max_abs_curvature(self) -> float:
        return 1.0 / self.radius

    def closest_parameter_in_range(
        self, point: tuple[float, float], t1: float, t2: float
    ) -> float:
        """Exact closest parameter on the arc restricted to [t1, t2].

        The unconstrained minimizer is the angle of the point as seen from
        the center; project it into the angular window of [t1, t2]
        accounting for 2*pi wrapping, falling back to the nearer endpoint.
        """
        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]
        if dx == 0.0 and dy == 0.0:
            # Point at the center: every arc point is equidistant
            return t1
        phi = math.atan2(dy, dx)

        # Angular window in traversal order; normalize to the increasing
        # interval [lo, hi] so the mod-2*pi search is direction-agnostic.
        a1, a2 = self._angle_at(t1), self._angle_at(t2)
        lo, hi = (a1, a2) if a1 <= a2 else (a2, a1)
        k_min = math.ceil((lo - phi) / (2 * math.pi))
        candidate = phi + 2 * math.pi * k_min
        if candidate <= hi:
            return self._direction * (candidate - self.angle_start) * self.radius

        # Outside the range: nearer endpoint wins
        d1 = sum((a - b) ** 2 for a, b in zip(point, self.point_at(t1)))
        d2 = sum((a - b) ** 2 for a, b in zip(point, self.point_at(t2)))
        return t1 if d1 <= d2 else t2

    # -- sampling ----------------------------------------------------------------

    @staticmethod
    def _max_step_angle(radius: float, max_chord_error: float) -> float:
        """Largest angular step whose chord deviates from the arc by at most
        the tolerance - the exact sagitta relation e = R(1 - cos(phi/2)),
        capped at pi/2 so even sloppy tolerances keep polygons sane."""
        if max_chord_error >= radius:
            return math.pi / 2
        return min(2.0 * math.acos(1.0 - max_chord_error / radius), math.pi / 2)

    @staticmethod
    def _uniform_params_with_includes(
        t_min: float, t_max: float, max_step: float, include: tuple[float, ...]
    ) -> tuple[float, ...]:
        """Uniform subdivision at or below max_step, with include values
        inserted exactly (nearby grid points yield to the include value so
        no sliver segments appear)."""
        span = t_max - t_min
        n = max(1, math.ceil(span / max_step))
        grid = [t_min + span * i / n for i in range(n + 1)]
        interior = sorted(t for t in set(include) if t_min < t < t_max)
        if interior:
            step = span / n
            kept = [
                g for g in grid[1:-1]
                if all(abs(g - t) > 0.25 * step for t in interior)
            ]
            grid = sorted([t_min, *kept, *interior, t_max])
        return tuple(grid)

    def sample_params(
        self,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        """Exact sagitta-based uniform sampling (plus forced includes)."""
        step = self._max_step_angle(self.radius, max_chord_error) * self.radius
        return self._uniform_params_with_includes(self.t_min, self.t_max, step, include)

    def sample_params_for_offset(
        self,
        offset: float,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        """The offset of an arc is a concentric arc of radius R - offset
        (left-positive offset, curvature +1/R: the left normal points toward
        the center). Sampling uses that arc's exact sagitta relation,
        expressed in THIS curve's (the centerline's) parameters."""
        # Curvature is signed by direction: a left offset moves toward the
        # center on a CCW arc and away from it on a CW arc.
        r_off = abs(self.radius - self._direction * offset)
        if r_off == 0.0:
            raise ValueError("Offset equals the arc radius; the offset curve degenerates to a point")
        phi = self._max_step_angle(r_off, max_chord_error)
        # One angular step phi corresponds to a centerline parameter step R*phi
        return self._uniform_params_with_includes(
            self.t_min, self.t_max, phi * self.radius, include
        )

    def canonical(self) -> tuple:
        return ("arc", tuple(self.center), self.radius, self.angle_start, self.angle_end)
