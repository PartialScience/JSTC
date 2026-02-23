"""
Unit tests for composite geometric region classes (RegionUnion, RegionIntersection, HorizontalSliceRegion).

These tests verify containment logic and bounding box computation for regions
composed from simpler geometric primitives.
"""
import pytest
from app.geometry import Circle, Polygon, Rectangle
from app.geometry.composite_regions import (
    RegionUnion,
    RegionIntersection,
    HorizontalSliceRegion,
)


# ---------------------------------------------------------------------------
# Fixtures: reusable building-block regions
# ---------------------------------------------------------------------------

@pytest.fixture
def left_circle():
    """Circle centered at (0, 0) with radius 2."""
    return Circle(center=(0, 0), radius=2.0)


@pytest.fixture
def right_circle():
    """Circle centered at (3, 0) with radius 2."""
    return Circle(center=(3, 0), radius=2.0)


@pytest.fixture
def unit_square():
    """Axis-aligned unit square from (0,0) to (1,1)."""
    return Rectangle(vertices=((0, 0), (1, 0), (1, 1), (0, 1)))


@pytest.fixture
def tall_rectangle():
    """Axis-aligned rectangle from (0,0) to (2,6)."""
    return Rectangle(vertices=((0, 0), (2, 0), (2, 6), (0, 6)))


# ---------------------------------------------------------------------------
# RegionUnion
# ---------------------------------------------------------------------------

class TestRegionUnion:
    """Tests for the RegionUnion class."""

    @pytest.mark.parametrize("point,expected", [
        # Inside left circle only
        ([-1, 0], True),
        # Inside right circle only
        ([4, 0], True),
        # In overlap zone
        ([1.5, 0], True),
        # Outside both
        ([6, 6], False),
        ([-3, 0], False),
    ])
    def test_containment(self, left_circle, right_circle, point, expected):
        """A union contains any point that is in at least one constituent."""
        union = RegionUnion(regions=(left_circle, right_circle))
        assert union.contains(point) is expected

    def test_bounding_box_two_circles(self, left_circle, right_circle):
        """Bounding box of a union is the outer envelope of constituent boxes."""
        union = RegionUnion(regions=(left_circle, right_circle))
        box = union.bounding_box()
        # left_circle box: (-2,2) x (-2,2)
        # right_circle box: (1,5) x (-2,2)
        assert box == [(-2.0, 5.0), (-2.0, 2.0)]

    def test_bounding_box_mixed_shapes(self, left_circle, unit_square):
        """Bounding box works across different region types."""
        union = RegionUnion(regions=(left_circle, unit_square))
        box = union.bounding_box()
        # left_circle box: (-2,2) x (-2,2); unit_square box: (0,1) x (0,1)
        assert box == [(-2.0, 2.0), (-2.0, 2.0)]

    def test_single_region_union(self, left_circle):
        """Union of a single region behaves like the region itself."""
        union = RegionUnion(regions=(left_circle,))
        assert union.contains([0, 0]) is True
        assert union.contains([5, 5]) is False
        assert union.bounding_box() == left_circle.bounding_box()


# ---------------------------------------------------------------------------
# RegionIntersection
# ---------------------------------------------------------------------------

class TestRegionIntersection:
    """Tests for the RegionIntersection class."""

    @pytest.mark.parametrize("point,expected", [
        # In overlap zone of both circles
        ([1.5, 0], True),
        # Inside left circle only
        ([-1, 0], False),
        # Inside right circle only
        ([4, 0], False),
        # Outside both
        ([6, 6], False),
    ])
    def test_containment(self, left_circle, right_circle, point, expected):
        """An intersection contains only points in all constituents."""
        inter = RegionIntersection(regions=(left_circle, right_circle))
        assert inter.contains(point) is expected

    def test_bounding_box_two_circles(self, left_circle, right_circle):
        """Bounding box of an intersection is the tightest overlap of constituent boxes."""
        inter = RegionIntersection(regions=(left_circle, right_circle))
        box = inter.bounding_box()
        # left_circle box: (-2,2) x (-2,2)
        # right_circle box: (1,5) x (-2,2)
        # intersection box: max of mins, min of maxes
        assert box == [(1.0, 2.0), (-2.0, 2.0)]


# ---------------------------------------------------------------------------
# HorizontalSliceRegion
# ---------------------------------------------------------------------------

class TestHorizontalSliceRegion:
    """Tests for the HorizontalSliceRegion class."""

    @pytest.mark.parametrize("point,expected", [
        # Inside rectangle and within slice
        ([1, 3], True),
        ([1, 2], True),
        ([1, 4], True),
        # Inside rectangle but outside slice (below)
        ([1, 0.5], False),
        # Inside rectangle but outside slice (above)
        ([1, 5.5], False),
        # Outside rectangle entirely
        ([5, 3], False),
    ])
    def test_containment(self, tall_rectangle, point, expected):
        """Slice contains points inside the base region AND within [y_min, y_max]."""
        sliced = HorizontalSliceRegion(region=tall_rectangle, y_min=2.0, y_max=4.0)
        assert sliced.contains(point) is expected

    def test_bounding_box_clamps_y(self, tall_rectangle):
        """Bounding box y-range is clamped to the slice bounds."""
        sliced = HorizontalSliceRegion(region=tall_rectangle, y_min=2.0, y_max=4.0)
        box = sliced.bounding_box()
        # tall_rectangle box: (0,2) x (0,6); clamped to y in [2,4]
        assert box == [(0, 2), (2.0, 4.0)]

    def test_bounding_box_slice_wider_than_region(self, unit_square):
        """When slice bounds exceed the region, the region's y-range wins."""
        sliced = HorizontalSliceRegion(region=unit_square, y_min=-5.0, y_max=5.0)
        box = sliced.bounding_box()
        # unit_square box: (0,1) x (0,1); clamp keeps (0,1) since it's tighter
        assert box == [(0, 1), (0, 1)]

    def test_bounding_box_circle_slice(self, left_circle):
        """Horizontal slice of a circle clamps the y-range correctly."""
        sliced = HorizontalSliceRegion(region=left_circle, y_min=-1.0, y_max=1.0)
        box = sliced.bounding_box()
        # left_circle box: (-2,2) x (-2,2); clamped to y in [-1,1]
        assert box == [(-2.0, 2.0), (-1.0, 1.0)]

    @pytest.mark.parametrize("point,expected", [
        ([0, 0], True),      # boundary of slice
        ([0, 1.0], True),    # boundary of slice
        ([0, 1.01], False),  # just outside slice
    ])
    def test_containment_at_slice_boundary(self, left_circle, point, expected):
        """Slice boundaries are inclusive."""
        sliced = HorizontalSliceRegion(region=left_circle, y_min=0.0, y_max=1.0)
        assert sliced.contains(point) is expected
