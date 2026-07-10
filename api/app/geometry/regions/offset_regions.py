import math
from typing import List, Tuple

from .base_geometric_region import GeometricRegion
from app.geometry.boundary import BoundaryLoop, BoundaryPiece
from app.geometry.curves.base import ParametricCurve
from app.geometry.curves.circular_arc import CircularArc
from app.geometry.curves.line_segment import LineSegment
from app.geometry.curves.offset_curve import OffsetCurve


class OffsetRegion(
    GeometricRegion
):
    """
    A geometric region which contains all points within a set offset distance from a
    parametric curve.
    """

    def __init__(self, curve: ParametricCurve, offset: float, flat_start: bool = False, flat_end: bool = False):
        """
        Initialize an offset region with a parametric curve and an offset distance.

        Args:
            curve: A ParametricCurve object representing the central curve of the region
            offset: A float representing the distance from the curve that defines the region
            flat_start: If True, the start endpoint cap is flat (perpendicular cut) instead of rounded
            flat_end: If True, the end endpoint cap is flat (perpendicular cut) instead of rounded
        """
        if offset <= 0:
            raise ValueError(f"Offset must be positive, got {offset}")
        self._flat_start = flat_start
        self._flat_end = flat_end
        self._curve = curve
        self._offset = offset

    @property
    def offset(self) -> float:
        return self._offset

    @property
    def curve(self) -> ParametricCurve:
        return self._curve

    @property
    def flat_start(self) -> bool:
        return self._flat_start

    @property
    def flat_end(self) -> bool:
        return self._flat_end

    def contains(self, point: List[float]) -> bool:
        """
        Determine if a point is in the region by seeing if it is within
        "offset" of the curve.

        When an end is set ot be flat, the rounded caps at the curve endpoints are
        replaced by flat cuts perpendicular to the tangent direction. A point
        near an endpoint is excluded if it falls on the outward side of the
        perpendicular plane through that endpoint.
        """
        if self.curve.distance_to_curve(point) > self.offset:
            return False

        if self._flat_start:
            # Start endpoint: reject points that are "before" the start plane
            start = self.curve.point_at(self.curve.t_min)
            tangent_start = self.curve.derivative_at(self.curve.t_min)
            dot_start = sum((p - s) * d for p, s, d in zip(point, start, tangent_start))
            if dot_start < 0:
                return False

        if self._flat_end:
            # End endpoint: reject points that are "past" the end plane
            end = self.curve.point_at(self.curve.t_max)
            tangent_end = self.curve.derivative_at(self.curve.t_max)
            dot_end = sum((p - e) * d for p, e, d in zip(point, end, tangent_end))
            if dot_end > 0:
                return False

        return True

    def _unit_left_normal_angle(self, t: float) -> float:
        """Angle of the central curve's unit left normal at parameter t."""
        dx, dy = self._curve.derivative_at(t)
        # Left normal = tangent rotated +90 degrees CCW: (-dy, dx)
        return math.atan2(dx, -dy)

    def boundary_loops(self) -> Tuple[BoundaryLoop, ...]:
        """
        The stadium-shaped boundary of the offset region, as a single loop:

            left offset curve (t_min -> t_max)
            end cap (left end point -> right end point)
            right offset curve, reversed (t_max -> t_min)
            start cap (right start point -> left start point)

        Caps are semicircular arcs by default, or perpendicular line
        segments where flat_start/flat_end is set. All pieces share the
        parent's derivative for their normals, so junctions coincide
        exactly.

        The parameter values of the two offset-curve pieces are the parent
        curve's own parameters, so loop-wide `include` values (e.g.
        discretization slice boundaries) land on both sides of the winding.
        """
        curve, a = self._curve, self._offset
        left = OffsetCurve(curve, +a)
        right = OffsetCurve(curve, -a)

        t0, t1 = curve.t_min, curve.t_max
        end_center, start_center = curve.point_at(t1), curve.point_at(t0)

        # --- End cap: from left(t1) to right(t1) ---
        if self._flat_end:
            end_cap = BoundaryPiece(
                curve=LineSegment(left.point_at(t1), right.point_at(t1))
            )
        else:
            # Sweep from the left normal angle down through the outward
            # (tangent) direction to the right normal angle: decreasing
            # angle, expressed as a reversed CCW arc.
            theta_n = self._unit_left_normal_angle(t1)
            end_cap = BoundaryPiece(
                curve=CircularArc(end_center, a, theta_n - math.pi, theta_n),
                reverse=True,
            )

        # --- Start cap: from right(t0) to left(t0) ---
        if self._flat_start:
            start_cap = BoundaryPiece(
                curve=LineSegment(right.point_at(t0), left.point_at(t0))
            )
        else:
            # Sweep from the right normal angle down through the outward
            # (anti-tangent) direction back to the left normal angle.
            theta_n = self._unit_left_normal_angle(t0)
            start_cap = BoundaryPiece(
                curve=CircularArc(start_center, a, theta_n - 2 * math.pi, theta_n - math.pi),
                reverse=True,
            )

        loop = BoundaryLoop(pieces=(
            BoundaryPiece(curve=left),
            end_cap,
            BoundaryPiece(curve=right, reverse=True),
            start_cap,
        ))
        return (loop,)
