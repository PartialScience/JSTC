"""
Unit tests for the OffsetCurve parallel curve.

OffsetCurve is the documented, typed exception to the unit-speed contract:
it shares its parent's parameter domain (that correspondence is what the
winding boundary machinery relies on), so its speed is |1 - offset*k|.
"""
import math

import pytest

from app.geometry.curves.base import UnitSpeedCurve
from app.geometry.curves.circular_arc import CircularArc
from app.geometry.curves.line_segment import LineSegment
from app.geometry.curves.offset_curve import OffsetCurve


# ---------------------------------------------------------------------------
# Instances registered into the universal ParametricCurve property tests
# (see tests/geometry/curves/conftest.py)
# ---------------------------------------------------------------------------

OFFSET_CURVE_INSTANCES = [
    pytest.param(
        OffsetCurve(LineSegment((0.0, 0.0), (0.0, 10.0)), 0.5),
        id="left-of-vertical-line",
    ),
    pytest.param(
        OffsetCurve(LineSegment((1.0, 2.0), (4.0, 6.0)), -0.25),
        id="right-of-slanted-line",
    ),
    pytest.param(
        OffsetCurve(CircularArc((0.0, 0.0), 2.0, 0.0, math.pi), 0.5),
        id="inside-of-arc",
    ),
]


class TestConstruction:
    def test_rejects_zero_offset(self):
        with pytest.raises(ValueError):
            OffsetCurve(LineSegment((0, 0), (1, 0)), 0.0)

    def test_is_not_unit_speed(self):
        """The deliberate exception: OffsetCurve must never pass as a
        winding centerline."""
        off = OffsetCurve(LineSegment((0, 0), (1, 0)), 0.1)
        assert not isinstance(off, UnitSpeedCurve)

    def test_shares_parent_domain(self):
        seg = LineSegment((0, 0), (1, 0))
        off = OffsetCurve(seg, 0.1)
        assert off.t_min == seg.t_min
        assert off.t_max == seg.t_max


class TestGeometry:
    def test_vertical_line_left_offset(self):
        """Vertical line going up: left normal points -x. (t is the parent's
        arc length.)"""
        seg = LineSegment((2.0, 0.0), (2.0, 10.0))
        off = OffsetCurve(seg, 0.5)
        assert off.point_at(0.0) == pytest.approx((1.5, 0.0))
        assert off.point_at(5.0) == pytest.approx((1.5, 5.0))
        assert off.point_at(10.0) == pytest.approx((1.5, 10.0))

    def test_vertical_line_right_offset(self):
        seg = LineSegment((2.0, 0.0), (2.0, 10.0))
        off = OffsetCurve(seg, -0.5)
        assert off.point_at(5.0) == pytest.approx((2.5, 5.0))

    def test_every_point_at_offset_distance_from_parent(self):
        parent = CircularArc((0.0, 0.0), 2.0, 0.0, math.pi)
        off = OffsetCurve(parent, 0.3)
        for i in range(11):
            t = parent.t_max * i / 10
            d = parent.distance_to_curve(off.point_at(t))
            assert d == pytest.approx(0.3, abs=1e-9)

    def test_arc_offset_is_concentric_circle(self):
        """For a CCW arc the left normal points toward the center, so a
        positive offset moves inward and a negative offset outward."""
        arc = CircularArc((1.0, 1.0), 2.0, 0.0, math.pi)
        inner = OffsetCurve(arc, 0.5)
        outer = OffsetCurve(arc, -0.5)
        for i in range(5):
            t = arc.t_max * i / 4
            xi, yi = inner.point_at(t)
            xo, yo = outer.point_at(t)
            assert math.hypot(xi - 1.0, yi - 1.0) == pytest.approx(1.5)
            assert math.hypot(xo - 1.0, yo - 1.0) == pytest.approx(2.5)

    def test_derivative_exact_frenet_scaling(self):
        """derivative = (1 - offset*k) * T_hat, exactly."""
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, math.pi)  # k = +0.5
        inner = OffsetCurve(arc, 0.5)   # scale 0.75
        outer = OffsetCurve(arc, -0.5)  # scale 1.25
        t = 1.3
        tx, ty = arc.derivative_at(t)
        assert inner.derivative_at(t) == pytest.approx((0.75 * tx, 0.75 * ty))
        assert outer.derivative_at(t) == pytest.approx((1.25 * tx, 1.25 * ty))

    def test_curvature_of_offset_arc(self):
        """k_off = k / (1 - offset*k): a concentric arc's actual curvature."""
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, math.pi)
        inner = OffsetCurve(arc, 0.5)  # radius 1.5
        assert inner.curvature_at(1.0) == pytest.approx(1.0 / 1.5)

    def test_arc_length_of_offset_line_matches_parent(self):
        seg = LineSegment((0.0, 0.0), (3.0, 4.0))
        off = OffsetCurve(seg, 1.0)
        assert off.arc_length_between(0.0, 5.0) == pytest.approx(5.0, rel=1e-9)

    def test_arc_length_of_offset_arc_scales_with_radius(self):
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, math.pi)
        inner = OffsetCurve(arc, 0.5)  # left of CCW = inward: radius 1.5
        assert inner.arc_length_between(0.0, arc.t_max) == pytest.approx(
            1.5 * math.pi, rel=1e-9
        )


class TestClosestParameter:
    def test_recovers_parameter_of_oncurve_point(self):
        seg = LineSegment((2.0, 0.0), (2.0, 10.0))
        off = OffsetCurve(seg, 0.5)
        for t in (0.0, 2.5, 7.0, 10.0):
            p = off.point_at(t)
            assert off.closest_parameter(p) == pytest.approx(t, abs=1e-9)

    def test_delegates_to_parent_projection(self):
        """A point off the curve projects to the same parameter the parent
        assigns it (normal projection property)."""
        seg = LineSegment((0.0, 0.0), (0.0, 10.0))
        off = OffsetCurve(seg, 0.5)
        assert off.closest_parameter((3.0, 7.0)) == pytest.approx(7.0)


class TestSampling:
    def test_chord_error_bound_on_offset_of_arc(self):
        """Sampling the inner offset of an arc must honor the tolerance on
        the OFFSET curve (the smaller, more curved circle)."""
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, math.pi)
        off = OffsetCurve(arc, 1.5)  # radius 0.5 - much more curved
        tol = 1e-3
        params = off.sample_params(tol)
        for ta, tb in zip(params[:-1], params[1:]):
            tm = 0.5 * (ta + tb)
            pa, pb, pm = off.point_at(ta), off.point_at(tb), off.point_at(tm)
            chord_mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            dev = math.hypot(pm[0] - chord_mid[0], pm[1] - chord_mid[1])
            assert dev <= tol * 1.01
