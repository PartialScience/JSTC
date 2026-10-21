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
    def from_three_points(
        cls,
        start: tuple[float, float],
        mid: tuple[float, float],
        end: tuple[float, float],
    ) -> "CircularArc":
        """The unique circular arc from ``start`` to ``end`` passing through
        ``mid`` - the user-facing arc description (three points on the arc,
        in traversal order).

        The through point fixes everything the signed-radius form could not
        express without conventions: the circle (its circumcircle), the bend
        direction, and whether the minor or major arc is taken (a sweep
        beyond a semicircle simply follows from where ``mid`` sits).

        Raises:
            ValueError: when any two points coincide, or when the three
                points are (numerically) collinear - a straight path is a
                line, not an arc.
        """
        ax, ay = float(start[0]), float(start[1])
        mx, my = float(mid[0]), float(mid[1])
        bx, by = float(end[0]), float(end[1])
        for p, q, names in (
            ((ax, ay), (mx, my), "start and mid"),
            ((mx, my), (bx, by), "mid and end"),
            ((ax, ay), (bx, by), "start and end"),
        ):
            if p == q:
                raise ValueError(f"Arc {names} points must differ")

        # Circumcenter via the standard determinant form; d is 4x the signed
        # triangle area, so |d| ~ 0 means the points are collinear and the
        # center computation would be pure cancellation noise.
        d = 2.0 * (ax * (my - by) + mx * (by - ay) + bx * (ay - my))
        scale = max(
            math.hypot(mx - ax, my - ay),
            math.hypot(bx - mx, by - my),
            math.hypot(bx - ax, by - ay),
        )
        if abs(d) <= 1e-12 * scale * scale:
            raise ValueError(
                "Arc points are collinear; use a line path for a straight "
                "centerline."
            )
        aa = ax * ax + ay * ay
        mm = mx * mx + my * my
        bb = bx * bx + by * by
        center = (
            (aa * (my - by) + mm * (by - ay) + bb * (ay - my)) / d,
            (aa * (bx - mx) + mm * (ax - bx) + bb * (mx - ax)) / d,
        )
        radius = math.hypot(ax - center[0], ay - center[1])

        a_s = math.atan2(ay - center[1], ax - center[0])
        a_m = math.atan2(my - center[1], mx - center[0])
        a_e = math.atan2(by - center[1], bx - center[0])

        two_pi = 2.0 * math.pi
        ccw_to_mid = (a_m - a_s) % two_pi
        ccw_to_end = (a_e - a_s) % two_pi
        if ccw_to_mid < ccw_to_end:
            # Traveling CCW from start passes mid before end: CCW arc
            angle_end = a_s + ccw_to_end
        else:
            # Otherwise the arc runs clockwise through mid
            angle_end = a_s - ((a_s - a_e) % two_pi)
        return cls(center=center, radius=radius, angle_start=a_s, angle_end=angle_end)

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
