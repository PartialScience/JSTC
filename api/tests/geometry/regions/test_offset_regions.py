

"""
Unit tests for the OffsetRegion class.

These tests verify containment logic and bounding box computation for regions
defined as the set of all points within a fixed offset distance from a
parametric curve, using a mock ParametricCurve to avoid coupling to any
concrete curve implementation.
"""
import math
import pytest
from unittest.mock import MagicMock
from app.geometry.regions.offset_regions import OffsetRegion
from app.geometry.curves.base import ParametricCurve


# ---------------------------------------------------------------------------
# Helper: lightweight mock curve
# ---------------------------------------------------------------------------

def _make_mock_curve(distance_fn, bbox):
    """
    Create a mock ParametricCurve whose distance_to_curve and bounding_box
    are backed by the supplied callable / value.

    Args:
        distance_fn: callable(point) -> float
        bbox: list of (min, max) tuples returned by bounding_box()
    """
    curve = MagicMock(spec=ParametricCurve)
    curve.distance_to_curve = MagicMock(side_effect=distance_fn)
    curve.bounding_box = MagicMock(return_value=bbox)
    return curve


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def origin_point_curve():
    """A curve that behaves like a single point at the origin.

    distance_to_curve returns the Euclidean distance from (0, 0).
    bounding_box is [(0, 0), (0, 0)].
    """
    def distance_fn(point):
        return math.hypot(point[0], point[1])

    return _make_mock_curve(distance_fn, bbox=[(0.0, 0.0), (0.0, 0.0)])


@pytest.fixture
def horizontal_line_curve():
    """A curve that behaves like a horizontal segment from (0, 0) to (4, 0).

    distance_to_curve projects onto [0, 4] on the x-axis.
    bounding_box is [(0, 4), (0, 0)].
    """
    def distance_fn(point):
        px, py = point[0], point[1]
        # closest x on segment [0, 4]
        cx = min(max(px, 0.0), 4.0)
        return math.hypot(px - cx, py)

    return _make_mock_curve(distance_fn, bbox=[(0.0, 4.0), (0.0, 0.0)])


@pytest.fixture
def shifted_vertical_curve():
    """A curve that behaves like a vertical segment from (1, 1) to (1, 5).

    bounding_box is [(1, 1), (1, 5)].
    """
    def distance_fn(point):
        px, py = point[0], point[1]
        cy = min(max(py, 1.0), 5.0)
        return math.hypot(px - 1.0, py - cy)

    return _make_mock_curve(distance_fn, bbox=[(1.0, 1.0), (1.0, 5.0)])


# ---------------------------------------------------------------------------
# TestOffsetRegion – Containment
# ---------------------------------------------------------------------------

class TestOffsetRegionContainment:
    """Tests for OffsetRegion.contains()."""

    @pytest.mark.parametrize("curve_fixture, point, expected", [
        # Horizontal: points on the curve itself
        ("horizontal_line_curve", (0.0, 0.0), True),
        ("horizontal_line_curve", (2.0, 0.0), True),
        ("horizontal_line_curve", (4.0, 0.0), True),
        # Horizontal: within offset distance (above / below)
        ("horizontal_line_curve", (2.0, 0.5), True),
        ("horizontal_line_curve", (2.0, -0.5), True),
        ("horizontal_line_curve", (2.0, 1.0), True),   # exactly on boundary
        # Horizontal: outside offset distance
        ("horizontal_line_curve", (2.0, 1.5), False),
        ("horizontal_line_curve", (2.0, -1.5), False),
        # Horizontal: near endpoints, within offset
        ("horizontal_line_curve", (0.0, 1.0), True),
        ("horizontal_line_curve", (-1.0, 0.0), True),  # exactly at offset from start
        # Horizontal: near endpoints, outside offset
        ("horizontal_line_curve", (-1.5, 0.0), False),
        ("horizontal_line_curve", (5.5, 0.0), False),
        # Vertical: on the curve
        ("shifted_vertical_curve", (1.0, 3.0), True),
        # Vertical: within offset
        ("shifted_vertical_curve", (1.5, 3.0), True),
        ("shifted_vertical_curve", (0.5, 3.0), True),
        # Vertical: outside offset
        ("shifted_vertical_curve", (3.0, 3.0), False),
        # Vertical: beyond endpoints
        ("shifted_vertical_curve", (1.0, -0.5), False),
        ("shifted_vertical_curve", (1.0, 6.5), False),
    ])
    def test_containment(self, curve_fixture, point, expected, request):
        curve = request.getfixturevalue(curve_fixture)
        region = OffsetRegion(curve=curve, offset=1.0)
        assert region.contains(point) == expected

    def test_containment_point_curve(self, origin_point_curve):
        """An offset around a point-like curve acts like a circle."""
        region = OffsetRegion(curve=origin_point_curve, offset=2.0)
        assert region.contains((0.0, 0.0)) is True
        assert region.contains((2.0, 0.0)) is True   # on boundary
        assert region.contains((0.0, -2.0)) is True   # on boundary
        assert region.contains((2.1, 0.0)) is False

    def test_boundary_is_inclusive(self, horizontal_line_curve):
        """Points exactly at the offset distance should be contained (<=)."""
        region = OffsetRegion(curve=horizontal_line_curve, offset=2.0)
        assert region.contains((2.0, 2.0)) is True

    def test_zero_offset(self, horizontal_line_curve):
        """With zero offset only points exactly on the curve are contained."""
        region = OffsetRegion(curve=horizontal_line_curve, offset=0.0)
        assert region.contains((2.0, 0.0)) is True
        assert region.contains((2.0, 0.001)) is False

    def test_contains_delegates_to_distance_to_curve(self):
        """contains() should call distance_to_curve and compare to offset."""
        curve = _make_mock_curve(lambda p: 3.0, bbox=[(0, 1), (0, 1)])
        region = OffsetRegion(curve=curve, offset=5.0)
        assert region.contains((99, 99)) is True
        curve.distance_to_curve.assert_called_once_with((99, 99))


# ---------------------------------------------------------------------------
# TestOffsetRegion – Bounding Box
# ---------------------------------------------------------------------------

class TestOffsetRegionBoundingBox:
    """Tests for OffsetRegion.bounding_box()."""

    def test_bounding_box_horizontal(self, horizontal_line_curve):
        region = OffsetRegion(curve=horizontal_line_curve, offset=1.0)
        bbox = region.bounding_box()
        # x: curve spans [0, 4] → [-1, 5]
        assert bbox[0] == pytest.approx((-1.0, 5.0))
        # y: curve spans [0, 0] → [-1, 1]
        assert bbox[1] == pytest.approx((-1.0, 1.0))

    def test_bounding_box_vertical(self, shifted_vertical_curve):
        region = OffsetRegion(curve=shifted_vertical_curve, offset=0.5)
        bbox = region.bounding_box()
        assert bbox[0] == pytest.approx((0.5, 1.5))
        assert bbox[1] == pytest.approx((0.5, 5.5))

    def test_bounding_box_point_curve(self, origin_point_curve):
        region = OffsetRegion(curve=origin_point_curve, offset=3.0)
        bbox = region.bounding_box()
        assert bbox[0] == pytest.approx((-3.0, 3.0))
        assert bbox[1] == pytest.approx((-3.0, 3.0))

    def test_bounding_box_zero_offset(self, horizontal_line_curve):
        region = OffsetRegion(curve=horizontal_line_curve, offset=0.0)
        bbox = region.bounding_box()
        assert bbox[0] == pytest.approx((0.0, 4.0))
        assert bbox[1] == pytest.approx((0.0, 0.0))

    def test_bounding_box_delegates_to_curve(self):
        """bounding_box() should call curve.bounding_box() and expand by offset."""
        curve = _make_mock_curve(lambda p: 0.0, bbox=[(2.0, 8.0), (3.0, 7.0)])
        region = OffsetRegion(curve=curve, offset=1.5)
        bbox = region.bounding_box()
        curve.bounding_box.assert_called_once()
        assert bbox == pytest.approx([(0.5, 9.5), (1.5, 8.5)])


# ---------------------------------------------------------------------------
# TestOffsetRegion – Properties
# ---------------------------------------------------------------------------

class TestOffsetRegionProperties:
    """Tests for OffsetRegion property accessors."""

    def test_offset_property(self, horizontal_line_curve):
        region = OffsetRegion(curve=horizontal_line_curve, offset=2.5)
        assert region.offset == 2.5

    def test_curve_property(self, horizontal_line_curve):
        region = OffsetRegion(curve=horizontal_line_curve, offset=1.0)
        assert region.curve is horizontal_line_curve
    