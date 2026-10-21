"""
Circular arc, parameterized by arc length.
"""
import math
from dataclasses import dataclass

from app.geometry.curves.base import UnitSpeedCurve


@dataclass(frozen=True)
class CircularArc(UnitSpeedCurve):
    """An arc of a circle traversed CCW, parameterized by ARC LENGTH:
    t runs over [0, radius * (angle_end - angle_start)] and the angle at
    parameter t is angle_start + t / radius. Every quantity is closed-form.

    The angle range must be increasing (CCW traversal); to traverse
    clockwise, consume the arc in reverse (see BoundaryPiece.reverse).
    With the left-normal sign convention, a CCW arc has curvature
    +1/radius (the left normal points toward the center).
    """

    center: tuple[float, float]
    radius: float
    angle_start: float
    angle_end: float

    def __post_init__(self):
        if self.radius <= 0:
            raise ValueError(f"Radius must be positive, got {self.radius}")
        if self.angle_end <= self.angle_start:
            raise ValueError(
                f"angle_end ({self.angle_end}) must exceed angle_start ({self.angle_start})"
            )
        if self.angle_end - self.angle_start > 2 * math.pi + 1e-12:
            raise ValueError(
                f"Sweep {self.angle_end - self.angle_start} exceeds a full circle"
            )

    # -- parameter/angle mapping ------------------------------------------------

    def _angle_at(self, t: float) -> float:
        return self.angle_start + t / self.radius

    @property
    def t_min(self) -> float:
        return 0.0

    @property
    def t_max(self) -> float:
        return self.radius * (self.angle_end - self.angle_start)

    # -- geometry ----------------------------------------------------------------

    def point_at(self, t: float) -> tuple[float, float]:
        a = self._angle_at(t)
        return (
            self.center[0] + self.radius * math.cos(a),
            self.center[1] + self.radius * math.sin(a),
        )

    def derivative_at(self, t: float) -> tuple[float, float]:
        """Unit tangent in the CCW direction."""
        a = self._angle_at(t)
        return (-math.sin(a), math.cos(a))

    def curvature_at(self, t: float) -> float:
        return 1.0 / self.radius

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

        a1, a2 = self._angle_at(t1), self._angle_at(t2)
        # Find the representative of phi (mod 2*pi) inside [a1, a2], if any
        k_min = math.ceil((a1 - phi) / (2 * math.pi))
        candidate = phi + 2 * math.pi * k_min
        if candidate <= a2:
            return (candidate - self.angle_start) * self.radius

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
        r_off = abs(self.radius - offset)
        if r_off == 0.0:
            raise ValueError("Offset equals the arc radius; the offset curve degenerates to a point")
        phi = self._max_step_angle(r_off, max_chord_error)
        # One angular step phi corresponds to a centerline parameter step R*phi
        return self._uniform_params_with_includes(
            self.t_min, self.t_max, phi * self.radius, include
        )

    def canonical(self) -> tuple:
        return ("arc", tuple(self.center), self.radius, self.angle_start, self.angle_end)
