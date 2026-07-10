"""
Circular arc parametric curve.
"""
import math

from app.geometry.curves.base import ParametricCurve


class CircularArc(ParametricCurve):
    """
    An arc of a circle, parameterized by angle (radians, CCW).

    The parameter t IS the angle: point_at(t) = center + radius*(cos t, sin t).
    The angle range must be increasing (CCW traversal); a full circle is
    CircularArc(center, radius, 0, 2*pi). To traverse clockwise, consume the
    arc in reverse (see BoundaryPiece.reverse).
    """

    def __init__(
        self,
        center: tuple[float, float],
        radius: float,
        angle_start: float,
        angle_end: float,
    ) -> None:
        """
        Initialize a circular arc.

        Args:
            center: Center of the circle (x, y)
            radius: Radius of the circle (must be positive)
            angle_start: Starting angle in radians
            angle_end: Ending angle in radians (must exceed angle_start;
                the sweep angle_end - angle_start must not exceed 2*pi)
        """
        if radius <= 0:
            raise ValueError(f"Radius must be positive, got {radius}")
        if angle_end <= angle_start:
            raise ValueError(
                f"angle_end ({angle_end}) must exceed angle_start ({angle_start})"
            )
        if angle_end - angle_start > 2 * math.pi + 1e-12:
            raise ValueError(
                f"Sweep {angle_end - angle_start} exceeds a full circle"
            )
        self.center = center
        self.radius = radius
        self.angle_start = angle_start
        self.angle_end = angle_end

    @property
    def t_min(self) -> float:
        return self.angle_start

    @property
    def t_max(self) -> float:
        return self.angle_end

    def point_at(self, t: float) -> tuple[float, float]:
        """Get the point on the arc at angle t."""
        return (
            self.center[0] + self.radius * math.cos(t),
            self.center[1] + self.radius * math.sin(t),
        )

    def derivative_at(self, t: float) -> tuple[float, float]:
        """Get the tangent vector of the arc at angle t (CCW direction)."""
        return (
            -self.radius * math.sin(t),
            self.radius * math.cos(t),
        )

    def arc_length_between(self, t1: float, t2: float) -> float:
        """Exact arc length: radius times swept angle."""
        return self.radius * abs(t2 - t1)

    def closest_parameter_in_range(
        self, point: tuple[float, float], t1: float, t2: float
    ) -> float:
        """
        Exact closest angle on the arc restricted to [t1, t2].

        The unconstrained minimizer is the angle of the point as seen from
        the center; project it into [t1, t2] accounting for 2*pi wrapping,
        falling back to the nearer endpoint when the angle lies outside.
        """
        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]
        if dx == 0.0 and dy == 0.0:
            # Point at the center: every arc point is equidistant
            return t1
        phi = math.atan2(dy, dx)

        # Find the representative of phi (mod 2*pi) inside [t1, t2], if any
        k_min = math.ceil((t1 - phi) / (2 * math.pi))
        candidate = phi + 2 * math.pi * k_min
        if candidate <= t2:
            return candidate

        # Outside the range: nearer endpoint wins
        d1 = sum((a - b) ** 2 for a, b in zip(point, self.point_at(t1)))
        d2 = sum((a - b) ** 2 for a, b in zip(point, self.point_at(t2)))
        return t1 if d1 <= d2 else t2
