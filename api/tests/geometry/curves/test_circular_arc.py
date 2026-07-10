"""
Unit tests for the CircularArc parametric curve.
"""
import math

import pytest

from app.geometry.curves.circular_arc import CircularArc


# ---------------------------------------------------------------------------
# Instances registered into the universal ParametricCurve property tests
# (see tests/geometry/curves/conftest.py)
# ---------------------------------------------------------------------------

ARC_INSTANCES = [
    pytest.param(
        CircularArc((0.0, 0.0), 1.0, 0.0, 2 * math.pi),
        id="unit-full-circle",
    ),
    pytest.param(
        CircularArc((2.0, -3.0), 0.5, 0.0, math.pi / 2),
        id="offset-quarter-arc",
    ),
    pytest.param(
        CircularArc((10.5, 48.8), 3.125, -math.pi, math.pi),
        id="toroid-cross-section",
    ),
]


class TestConstruction:
    def test_rejects_nonpositive_radius(self):
        with pytest.raises(ValueError):
            CircularArc((0, 0), 0.0, 0.0, 1.0)
        with pytest.raises(ValueError):
            CircularArc((0, 0), -1.0, 0.0, 1.0)

    def test_rejects_decreasing_angles(self):
        with pytest.raises(ValueError):
            CircularArc((0, 0), 1.0, 1.0, 1.0)
        with pytest.raises(ValueError):
            CircularArc((0, 0), 1.0, 2.0, 1.0)

    def test_rejects_sweep_beyond_full_circle(self):
        with pytest.raises(ValueError):
            CircularArc((0, 0), 1.0, 0.0, 3 * math.pi)


class TestGeometry:
    def test_points_on_circle(self):
        arc = CircularArc((1.0, 2.0), 3.0, 0.0, 2 * math.pi)
        for i in range(16):
            t = 2 * math.pi * i / 16
            x, y = arc.point_at(t)
            assert math.hypot(x - 1.0, y - 2.0) == pytest.approx(3.0)

    def test_cardinal_points(self):
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, 2 * math.pi)
        assert arc.point_at(0.0) == pytest.approx((2.0, 0.0))
        assert arc.point_at(math.pi / 2) == pytest.approx((0.0, 2.0))
        assert arc.point_at(math.pi) == pytest.approx((-2.0, 0.0))

    def test_derivative_is_ccw_tangent(self):
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, 2 * math.pi)
        dx, dy = arc.derivative_at(0.0)  # at (2, 0), CCW tangent points +y
        assert (dx, dy) == pytest.approx((0.0, 2.0))

    def test_arc_length_exact(self):
        arc = CircularArc((0.0, 0.0), 3.0, 0.0, math.pi)
        assert arc.arc_length_between(0.0, math.pi) == pytest.approx(3 * math.pi)
        assert arc.arc_length_between(0.0, math.pi / 2) == pytest.approx(1.5 * math.pi)


class TestClosestParameter:
    def test_interior_angle(self):
        arc = CircularArc((0.0, 0.0), 1.0, 0.0, math.pi)
        t = arc.closest_parameter((0.0, 5.0))  # straight up -> angle pi/2
        assert t == pytest.approx(math.pi / 2)

    def test_wrapping(self):
        """Angle of the point is -pi/2 via atan2, but the arc covers it
        at 3*pi/2: the search must find the wrapped representative."""
        arc = CircularArc((0.0, 0.0), 1.0, math.pi, 2 * math.pi)
        t = arc.closest_parameter((0.0, -5.0))
        assert t == pytest.approx(3 * math.pi / 2)

    def test_clamps_to_nearer_endpoint(self):
        arc = CircularArc((0.0, 0.0), 1.0, 0.0, math.pi / 2)
        # Point at angle -pi/4: nearest arc point is the t=0 endpoint
        p = (math.cos(-math.pi / 4), math.sin(-math.pi / 4))
        assert arc.closest_parameter(p) == pytest.approx(0.0)

    def test_distance_via_closest(self):
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, 2 * math.pi)
        assert arc.distance_to_curve((5.0, 0.0)) == pytest.approx(3.0)
        assert arc.distance_to_curve((0.0, 0.5)) == pytest.approx(1.5)


class TestSampling:
    def test_chord_error_bound(self):
        arc = CircularArc((0.0, 0.0), 1.0, 0.0, 2 * math.pi)
        tol = 1e-3
        params = arc.sample_params(tol)
        # Verify every chord stays within tolerance of the curve
        for ta, tb in zip(params[:-1], params[1:]):
            tm = 0.5 * (ta + tb)
            pa, pb, pm = arc.point_at(ta), arc.point_at(tb), arc.point_at(tm)
            chord_mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            dev = math.hypot(pm[0] - chord_mid[0], pm[1] - chord_mid[1])
            assert dev <= tol * 1.01

    def test_include_values_present(self):
        arc = CircularArc((0.0, 0.0), 1.0, 0.0, math.pi)
        params = arc.sample_params(0.1, include=(0.3, 1.234))
        assert any(abs(p - 0.3) < 1e-12 for p in params)
        assert any(abs(p - 1.234) < 1e-12 for p in params)

    def test_out_of_domain_include_ignored(self):
        arc = CircularArc((0.0, 0.0), 1.0, 0.0, math.pi)
        params = arc.sample_params(0.1, include=(-5.0, 42.0))
        assert all(0.0 <= p <= math.pi for p in params)
