"""
Geometric validation helpers for winding curves.

These are model-construction checks (fail fast with a clear message), not
solver math: they protect the preconditions the solvers and the mesher
assume - chiefly that a winding's conductor envelope (the tube of radius
wire_dia/2 around its centerline) never intersects itself.
"""
from __future__ import annotations

from typing import Optional, Tuple

from app.geometry.curves.base import UnitSpeedCurve


def _segment_distance_sq(
    a0: Tuple[float, float], a1: Tuple[float, float],
    b0: Tuple[float, float], b1: Tuple[float, float],
) -> float:
    """Squared minimum distance between two 2-D segments."""
    def clamp01(x: float) -> float:
        return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

    def point_seg_sq(p, q0, q1):
        vx, vy = q1[0] - q0[0], q1[1] - q0[1]
        wx, wy = p[0] - q0[0], p[1] - q0[1]
        vv = vx * vx + vy * vy
        t = clamp01((wx * vx + wy * vy) / vv) if vv > 0 else 0.0
        dx, dy = wx - t * vx, wy - t * vy
        return dx * dx + dy * dy

    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    # Proper intersection -> distance zero
    o1, o2 = orient(a0, a1, b0), orient(a0, a1, b1)
    o3, o4 = orient(b0, b1, a0), orient(b0, b1, a1)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return 0.0

    return min(
        point_seg_sq(a0, b0, b1),
        point_seg_sq(a1, b0, b1),
        point_seg_sq(b0, a0, a1),
        point_seg_sq(b1, a0, a1),
    )


def tube_self_approach(
    curve: UnitSpeedCurve, radius: float
) -> Optional[Tuple[float, float]]:
    """Check whether the tube of the given radius around the curve
    approaches itself.

    The curve is sampled into a polyline at a chord tolerance of radius/4.
    A pair of polyline segments marks a self-approach when they are closer
    than the tube diameter IN SPACE while being far apart ALONG the curve.
    The along-curve criterion is the semicircle bound: two points of a
    smooth curve at Euclidean distance d that belong to the same local bend
    are at most (pi/2) * d apart in arc length (equality on a semicircle),
    because the offset-region validation already guarantees the tube radius
    stays below the curve's minimum radius of curvature. A pair that is both
    close in space and farther than that along the curve can only be two
    distinct passes of the winding - a genuine self-approach.

    Sampling tolerances are credited in the safe direction on both tests, so
    a legitimately clear tube never fails from discretization.

    Returns:
        None when the tube is clear, else the pair of parameter values
        (t_a, t_b) bracketing the closest approach found.
    """
    from math import pi, sqrt

    tol = radius / 4.0
    params = curve.sample_params(tol)
    pts = [curve.point_at(t) for t in params]
    n_seg = len(pts) - 1

    for i in range(n_seg):
        for j in range(i + 1, n_seg):
            d_sq = _segment_distance_sq(pts[i], pts[i + 1], pts[j], pts[j + 1])
            # Upper bound on the true curve-to-curve distance for this pair
            d_true = sqrt(d_sq) + 2.0 * tol
            if d_true >= 2.0 * radius:
                continue
            # Arc-length gap between the two sub-arcs (segment interiors)
            gap_along = params[j] - params[i + 1]
            if gap_along > (pi / 2.0) * d_true:
                return (params[i], params[j])
    return None
