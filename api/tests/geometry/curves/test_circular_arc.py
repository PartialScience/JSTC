"""
Unit tests for the CircularArc parametric curve (unit-speed: t is arc length).
"""
import math

import pytest

from app.geometry.curves.circular_arc import CircularArc


# ---------------------------------------------------------------------------
# Instances registered into the universal curve property tests
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
    pytest.param(
        CircularArc((5.0, 20.0), 4.0, math.pi, math.pi / 3),
        id="clockwise-arc",
    ),
]


class TestConstruction:
    def test_rejects_nonpositive_radius(self):
        with pytest.raises(ValueError):
            CircularArc((0, 0), 0.0, 0.0, 1.0)
        with pytest.raises(ValueError):
            CircularArc((0, 0), -1.0, 0.0, 1.0)

    def test_rejects_zero_sweep(self):
        with pytest.raises(ValueError):
            CircularArc((0, 0), 1.0, 1.0, 1.0)

    def test_clockwise_arc_supported(self):
        """Decreasing angles are a CW traversal: unit tangent along travel,
        negative curvature (left normal points away from the center)."""
        import math as m
        cw = CircularArc((0.0, 0.0), 2.0, m.pi / 2, 0.0)
        assert cw.point_at(0.0) == pytest.approx((0.0, 2.0))
        assert cw.point_at(cw.t_max) == pytest.approx((2.0, 0.0))
        # At the top of the circle, CW travel heads +x
        assert cw.derivative_at(0.0) == pytest.approx((1.0, 0.0))
        assert cw.curvature_at(1.0) == pytest.approx(-0.5)

    def test_rejects_sweep_beyond_full_circle(self):
        with pytest.raises(ValueError):
            CircularArc((0, 0), 1.0, 0.0, 3 * math.pi)

    def test_structural_equality(self):
        a = CircularArc((0, 0), 2.0, 0.0, math.pi)
        b = CircularArc((0, 0), 2.0, 0.0, math.pi)
        assert a == b
        assert hash(a) == hash(b)


class TestGeometry:
    def test_t_range_is_arc_length(self):
        arc = CircularArc((0.0, 0.0), 3.0, 0.0, math.pi)
        assert arc.t_min == 0.0
        assert arc.t_max == pytest.approx(3 * math.pi)

    def test_points_on_circle(self):
        arc = CircularArc((1.0, 2.0), 3.0, 0.0, 2 * math.pi)
        for i in range(16):
            t = arc.t_max * i / 16
            x, y = arc.point_at(t)
            assert math.hypot(x - 1.0, y - 2.0) == pytest.approx(3.0)

    def test_cardinal_points(self):
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, 2 * math.pi)
        quarter = 2.0 * math.pi / 2  # R * (pi/2)
        assert arc.point_at(0.0) == pytest.approx((2.0, 0.0))
        assert arc.point_at(quarter) == pytest.approx((0.0, 2.0))
        assert arc.point_at(2 * quarter) == pytest.approx((-2.0, 0.0))

    def test_derivative_is_unit_ccw_tangent(self):
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, 2 * math.pi)
        assert arc.derivative_at(0.0) == pytest.approx((0.0, 1.0))

    def test_arc_length_identity(self):
        arc = CircularArc((0.0, 0.0), 3.0, 0.0, math.pi)
        assert arc.arc_length_between(0.0, arc.t_max) == pytest.approx(3 * math.pi)
        assert arc.arc_length_between(1.0, 2.5) == pytest.approx(1.5)

    def test_curvature_is_inverse_radius(self):
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, math.pi)
        assert arc.curvature_at(1.0) == pytest.approx(0.5)
        assert arc.max_abs_curvature() == pytest.approx(0.5)


class TestClosestParameter:
    def test_interior_angle(self):
        arc = CircularArc((0.0, 0.0), 1.0, 0.0, math.pi)
        t = arc.closest_parameter((0.0, 5.0))  # straight up -> angle pi/2
        assert t == pytest.approx(math.pi / 2)  # R = 1: t == angle sweep

    def test_wrapping(self):
        """Angle of the point is -pi/2 via atan2, but the arc covers it at
        3*pi/2: the search must find the wrapped representative."""
        arc = CircularArc((0.0, 0.0), 1.0, math.pi, 2 * math.pi)
        t = arc.closest_parameter((0.0, -5.0))
        # Angle 3*pi/2 is pi/2 past angle_start=pi -> arc length pi/2
        assert t == pytest.approx(math.pi / 2)

    def test_clamps_to_nearer_endpoint(self):
        arc = CircularArc((0.0, 0.0), 1.0, 0.0, math.pi / 2)
        p = (math.cos(-math.pi / 4), math.sin(-math.pi / 4))
        assert arc.closest_parameter(p) == pytest.approx(0.0)

    def test_distance_via_closest(self):
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, 2 * math.pi)
        assert arc.distance_to_curve((5.0, 0.0)) == pytest.approx(3.0)
        assert arc.distance_to_curve((0.0, 0.5)) == pytest.approx(1.5)

    def test_radius_scaling_of_parameter(self):
        """With R != 1 the returned parameter is an arc length, not an angle."""
        arc = CircularArc((0.0, 0.0), 2.0, 0.0, math.pi)
        t = arc.closest_parameter((0.0, 9.0))
        assert t == pytest.approx(2.0 * math.pi / 2)


class TestSampling:
    def test_chord_error_bound(self):
        arc = CircularArc((0.0, 0.0), 1.0, 0.0, 2 * math.pi)
        tol = 1e-3
        params = arc.sample_params(tol)
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

    def test_offset_sampling_tracks_the_offset_radius(self):
        """The sagitta relation is evaluated on the OFFSET arc's radius: an
        outward offset (larger radius) needs more samples than the
        centerline; an inward one (smaller radius, but proportionally
        shorter arc) needs fewer."""
        arc = CircularArc((0.0, 0.0), 1.0, 0.0, math.pi)
        tol = 1e-3
        center = arc.sample_params(tol)
        outer = arc.sample_params_for_offset(-1.0, tol)  # radius-2 offset arc
        inner = arc.sample_params_for_offset(0.9, tol)   # radius-0.1 offset arc
        assert len(outer) > len(center)
        assert len(inner) < len(center)
