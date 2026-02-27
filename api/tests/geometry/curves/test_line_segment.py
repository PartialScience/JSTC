"""
Tests for the LineSegment concrete curve class.

This file:
  - Registers LineSegment instances into the CURVE_INSTANCES registry so
    the universal ParametricCurve property tests run against them.
  - Contains LineSegment-specific tests for expected behaviour.

Run with: pytest tests/geometry/curves/test_line_segment.py -v
"""
import pytest
import math

from app.geometry.curves.line_segment import LineSegment


# ---------------------------------------------------------------------------
# Registry of LineSegment instances for the parameterized base-class tests.
# These are imported by conftest.py and fed to the curve_instance fixture.
# ---------------------------------------------------------------------------

LINE_SEGMENT_INSTANCES = [
    pytest.param(
        LineSegment(start=(-3, -4), end=(3, 4)),
        id="LineSegment-negative-to-positive",
    ),
    pytest.param(
        LineSegment(start=(5, 5), end=(5, 5)),
        id="LineSegment-degenerate-point",
    ),
    pytest.param(
        LineSegment(start=(10.5, -2.3), end=(-4.1, 7.8)),
        id="LineSegment-arbitrary-float",
    ),
]


# ---------------------------------------------------------------------------
# LineSegment ABC conformance (quick smoke-check)
# ---------------------------------------------------------------------------

class TestLineSegmentABC:
    """Quick subclass checks for LineSegment."""

    def test_is_parametric_curve(self):
        from app.geometry.curves.base import ParametricCurve
        assert issubclass(LineSegment, ParametricCurve)


# ---------------------------------------------------------------------------
# LineSegment-specific tests
# ---------------------------------------------------------------------------

class TestLineSegmentProperties:
    """Tests for LineSegment-specific behaviour and expected values."""

    def test_t_range(self):
        """LineSegment parameter domain is [0, 1]."""
        seg = LineSegment(start=(0, 0), end=(1, 0))
        assert seg.t_min == 0.0
        assert seg.t_max == 1.0

    def test_point_at_start(self):
        """point_at(0) must return the start point."""
        seg = LineSegment(start=(2, 3), end=(8, 11))
        assert seg.point_at(0.0) == pytest.approx((2, 3))

    def test_point_at_end(self):
        """point_at(1) must return the end point."""
        seg = LineSegment(start=(2, 3), end=(8, 11))
        assert seg.point_at(1.0) == pytest.approx((8, 11))

    def test_point_at_midpoint(self):
        """point_at(0.5) must return the midpoint of the segment."""
        seg = LineSegment(start=(0, 0), end=(10, 6))
        assert seg.point_at(0.5) == pytest.approx((5, 3))

    @pytest.mark.parametrize("t,expected", [
        (0.0, (0.0, 0.0)),
        (0.25, (1.0, 0.0)),
        (0.5, (2.0, 0.0)),
        (0.75, (3.0, 0.0)),
        (1.0, (4.0, 0.0)),
    ])
    def test_point_at_horizontal(self, t, expected):
        """Verify known coordinates on a horizontal segment."""
        seg = LineSegment(start=(0, 0), end=(4, 0))
        assert seg.point_at(t) == pytest.approx(expected)

    @pytest.mark.parametrize("t,expected", [
        (0.0, (0.0, 0.0)),
        (0.25, (0.0, 2.0)),
        (0.5, (0.0, 4.0)),
        (1.0, (0.0, 8.0)),
    ])
    def test_point_at_vertical(self, t, expected):
        """Verify known coordinates on a vertical segment."""
        seg = LineSegment(start=(0, 0), end=(0, 8))
        assert seg.point_at(t) == pytest.approx(expected)

    def test_distance_point_on_segment(self):
        """Distance from a point lying on the segment should be 0."""
        seg = LineSegment(start=(0, 0), end=(4, 0))
        assert seg.distance_to_curve((2, 0)) == pytest.approx(0.0)

    def test_distance_perpendicular_offset(self):
        """Distance from a point directly above the midpoint of a horizontal segment."""
        seg = LineSegment(start=(0, 0), end=(4, 0))
        # Point (2, 3) is 3 units above the midpoint
        assert seg.distance_to_curve((2, 3)) == pytest.approx(3.0)

    def test_distance_to_endpoint(self):
        """Distance from a point beyond the segment end should be the Euclidean
        distance to the nearest endpoint."""
        seg = LineSegment(start=(0, 0), end=(4, 0))
        # Point (6, 0) is 2 units past the end
        assert seg.distance_to_curve((6, 0)) == pytest.approx(2.0)

    def test_distance_to_start_point(self):
        """Distance from a point behind the segment start."""
        seg = LineSegment(start=(0, 0), end=(4, 0))
        # Point (-3, 0) is 3 units before the start
        assert seg.distance_to_curve((-3, 0)) == pytest.approx(3.0)

    def test_distance_diagonal(self):
        """Distance from a point to a diagonal segment, perpendicular case."""
        seg = LineSegment(start=(0, 0), end=(3, 4))
        # The segment has length 5, direction (3/5, 4/5).
        # Point (4, -3) projected onto the line gives t_hat that lies on [0,1],
        # so the distance is the perpendicular distance.
        # Line: 4x - 3y = 0 → distance = |4*4 - 3*(-3)| / 5 = 25/5 = 5
        assert seg.distance_to_curve((4, -3)) == pytest.approx(5.0)

    def test_distance_degenerate_segment(self):
        """Degenerate segment (single point) — distance should be Euclidean
        distance to that point."""
        seg = LineSegment(start=(1, 1), end=(1, 1))
        assert seg.distance_to_curve((4, 5)) == pytest.approx(5.0)

    def test_bounding_box_horizontal(self):
        """Bounding box of a horizontal segment."""
        seg = LineSegment(start=(1, 3), end=(5, 3))
        bbox = seg.bounding_box()
        assert bbox[0] == pytest.approx((1, 5))  # x range
        assert bbox[1] == pytest.approx((3, 3))  # y range

    def test_bounding_box_diagonal(self):
        """Bounding box of a diagonal segment."""
        seg = LineSegment(start=(-2, -1), end=(4, 7))
        bbox = seg.bounding_box()
        assert bbox[0] == pytest.approx((-2, 4))
        assert bbox[1] == pytest.approx((-1, 7))

    def test_bounding_box_reversed_coords(self):
        """Bounding box should handle start > end in any dimension."""
        seg = LineSegment(start=(5, 8), end=(1, 2))
        bbox = seg.bounding_box()
        assert bbox[0] == pytest.approx((1, 5))
        assert bbox[1] == pytest.approx((2, 8))

    def test_bounding_box_degenerate(self):
        """Bounding box of a degenerate (zero-length) segment."""
        seg = LineSegment(start=(3, 7), end=(3, 7))
        bbox = seg.bounding_box()
        assert bbox[0] == pytest.approx((3, 3))
        assert bbox[1] == pytest.approx((7, 7))
