"""
Offset (parallel) curve of an arbitrary parametric curve.
"""

from app.geometry.curves.base import ParametricCurve


class OffsetCurve(ParametricCurve):
    """
    The parallel curve at a signed offset distance from a parent curve:

        offset_point(t) = parent(t) + offset * n_hat(t)

    where n_hat is the parent's unit *left* normal (the unit tangent rotated
    +90 degrees CCW). A positive offset therefore lies to the left of the
    direction of travel, a negative offset to the right.

    This is a fully general implementation in terms of the ParametricCurve
    abstraction - it works for any 2D parent curve. The one mathematical
    constraint: |offset| must be smaller than the parent's minimum radius of
    curvature, or the offset curve self-intersects. For coil geometry this
    is guaranteed physically (wire radius << winding curvature); it is the
    caller's responsibility otherwise.

    The parameter domain is shared with the parent curve, so a parameter
    value t refers to corresponding points on both curves.
    """

    def __init__(self, parent: ParametricCurve, offset: float) -> None:
        """
        Initialize an offset curve.

        Args:
            parent: The curve to offset from.
            offset: Signed offset distance (positive = parent's left side).
        """
        if offset == 0:
            raise ValueError("Offset must be non-zero; use the parent curve instead")
        self._parent = parent
        self._offset = offset
        # Step for the numerical derivative, scaled to the parameter domain
        self._fd_step = (parent.t_max - parent.t_min) * 1e-6

    @property
    def parent(self) -> ParametricCurve:
        """The curve this offset curve is derived from."""
        return self._parent

    @property
    def offset(self) -> float:
        """The signed offset distance from the parent curve."""
        return self._offset

    @property
    def t_min(self) -> float:
        return self._parent.t_min

    @property
    def t_max(self) -> float:
        return self._parent.t_max

    def _unit_left_normal(self, t: float) -> tuple[float, float]:
        """The parent's unit tangent rotated +90 degrees CCW."""
        dx, dy = self._parent.derivative_at(t)
        mag = (dx * dx + dy * dy) ** 0.5
        if mag == 0.0:
            raise ValueError(f"Parent curve has zero tangent at t={t}")
        return (-dy / mag, dx / mag)

    def point_at(self, t: float) -> tuple[float, float]:
        """Get the point on the offset curve at parameter t."""
        px, py = self._parent.point_at(t)
        nx, ny = self._unit_left_normal(t)
        return (px + self._offset * nx, py + self._offset * ny)

    def derivative_at(self, t: float) -> tuple[float, float]:
        """
        Tangent of the offset curve at parameter t.

        The exact tangent involves the parent's curvature (a second
        derivative the ParametricCurve contract does not expose), so it is
        computed by central finite differences of point_at. Accuracy is
        ample for sampling, orientation and cap construction; a concrete
        subclass with a known curvature can override with the closed form.
        """
        h = self._fd_step
        lo = max(t - h, self.t_min)
        hi = min(t + h, self.t_max)
        (x0, y0), (x1, y1) = self.point_at(lo), self.point_at(hi)
        span = hi - lo
        return ((x1 - x0) / span, (y1 - y0) / span)

    def closest_parameter_in_range(
        self, point: tuple[float, float], t1: float, t2: float
    ) -> float:
        """
        Delegate the closest-parameter search to the parent curve.

        For any point within the offset's tube of validity (|offset| below
        the parent's radius of curvature - the same constraint the curve
        itself requires), the normal projection onto the parent and onto
        the offset curve identify the same parameter.
        """
        return self._parent.closest_parameter_in_range(point, t1, t2)
