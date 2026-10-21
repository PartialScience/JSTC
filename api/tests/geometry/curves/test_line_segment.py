"""
Tests for the LineSegment concrete curve class (unit-speed: t is arc length).

This file:
  - Registers LineSegment instances into the CURVE_INSTANCES registry so
    the universal ParametricCurve/unit-speed contract tests run against them.
  - Contains LineSegment-specific tests for expected behaviour.
"""
import math

import pytest

from app.geometry.curves.line_segment import LineSegment


# ---------------------------------------------------------------------------
# Registry of LineSegment instances for the parameterized base-class tests.
# These are imported by conftest.py and fed to the curve fixtures.
# ---------------------------------------------------------------------------

LINE_SEGMENT_INSTANCES = [
    pytest.param(
        LineSegment(start=(-3, -4), end=(3, 4)),
        id="LineSegment-negative-to-positive",
    ),
    pytest.param(
        LineSegment(start=(10.5, -2.3), end=(-4.1, 7.8)),
        id="LineSegment-arbitrary-float",
    ),
    pytest.param(
        LineSegment(start=(2.26925, 23.0), end=(2.26925, 44.8085)),
        id="LineSegment-javatc-secondary",
    ),
]


class TestConstruction:
    def test_rejects_degenerate_segment(self):
        with pytest.raises(ValueError):
            LineSegment(start=(5, 5), end=(5, 5))

    def test_structural_equality(self):
        a = LineSegment((0.0, 0.0), (3.0, 4.0))
        b = LineSegment((0.0, 0.0), (3.0, 4.0))
        c = LineSegment((0.0, 0.0), (3.0, 5.0))
        assert a == b
        assert hash(a) == hash(b)
        assert a != c


class TestGeometry:
    def test_t_range_is_arc_length(self):
        seg = LineSegment(start=(0, 0), end=(3, 4))
        assert seg.t_min == 0.0
        assert seg.t_max == pytest.approx(5.0)

    def test_point_at_endpoints(self):
        seg = LineSegment(start=(2, 3), end=(8, 11))
        length = math.hypot(6, 8)
        assert seg.point_at(0.0) == pytest.approx((2, 3))
        assert seg.point_at(length) == pytest.approx((8, 11))

    def test_point_at_advances_by_arc_length(self):
        seg = LineSegment(start=(0, 0), end=(10, 0))
        assert seg.point_at(2.5) == pytest.approx((2.5, 0.0))
        assert seg.point_at(5.0) == pytest.approx((5.0, 0.0))

    def test_derivative_is_unit_tangent(self):
        seg = LineSegment(start=(0, 0), end=(3, 4))
        assert seg.derivative_at(1.0) == pytest.approx((0.6, 0.8))

    def test_zero_curvature(self):
        seg = LineSegment(start=(0, 0), end=(3, 4))
        assert seg.curvature_at(2.0) == 0.0
        assert seg.max_abs_curvature() == 0.0


class TestDistances:
    def test_distance_point_on_segment(self):
        seg = LineSegment(start=(0, 0), end=(4, 0))
        assert seg.distance_to_curve((2, 0)) == pytest.approx(0.0)

    def test_distance_perpendicular_offset(self):
        seg = LineSegment(start=(0, 0), end=(4, 0))
        assert seg.distance_to_curve((2, 3)) == pytest.approx(3.0)

    def test_distance_beyond_endpoints(self):
        seg = LineSegment(start=(0, 0), end=(4, 0))
        assert seg.distance_to_curve((6, 0)) == pytest.approx(2.0)
        assert seg.distance_to_curve((-3, 0)) == pytest.approx(3.0)

    def test_distance_diagonal(self):
        seg = LineSegment(start=(0, 0), end=(3, 4))
        # Line: 4x - 3y = 0 -> distance = |4*4 - 3*(-3)| / 5 = 5
        assert seg.distance_to_curve((4, -3)) == pytest.approx(5.0)

    def test_closest_parameter_is_arc_length_projection(self):
        seg = LineSegment(start=(0, 0), end=(0, 10))
        assert seg.closest_parameter((3.0, 7.0)) == pytest.approx(7.0)


class TestSampling:
    def test_sample_is_exact_with_two_points(self):
        seg = LineSegment(start=(0, 0), end=(0, 10))
        assert seg.sample_params(1e-9) == (0.0, 10.0)

    def test_includes_inserted_exactly(self):
        seg = LineSegment(start=(0, 0), end=(0, 10))
        params = seg.sample_params(1e-9, include=(2.5, 7.0, -1.0, 50.0))
        assert params == (0.0, 2.5, 7.0, 10.0)
