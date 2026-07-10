"""
Tests for boundary_loops() across the GeometricRegion hierarchy, and for the
BoundaryLoop/BoundaryPiece sampling machinery.

Strategy: boundary loops are validated *behaviorally* against the region's
own contains() - every sampled boundary vertex must sit on the edge of the
region (a small step inward lands inside, a small step outward lands
outside). This catches construction, orientation, and cap errors without
depending on implementation details.
"""
import math

import pytest

from app.geometry import BoundaryLoop, Circle, LineSegment, OffsetRegion, Polygon, Rectangle


CHORD_TOL = 1e-4


def _polygon_centroid(poly):
    n = len(poly)
    return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)


def _assert_vertices_on_region_edge(region, poly, scale):
    """Every vertex must flip contains() across a small normal step.

    The step direction is estimated from the vertex's neighbors (polygon
    outward normal); step size is well above chord tolerance but far below
    feature size.
    """
    eps = 50 * CHORD_TOL * scale
    n = len(poly)
    misses_in = 0
    misses_out = 0
    for i in range(n):
        x, y = poly[i]
        # Outward normal from neighboring vertices, assuming CCW ordering;
        # if the loop is CW the roles of in/out swap, which we tolerate by
        # checking both and requiring consistency across the whole loop.
        xp, yp = poly[i - 1]
        xn, yn = poly[(i + 1) % n]
        tx, ty = xn - xp, yn - yp
        mag = math.hypot(tx, ty)
        nx, ny = ty / mag, -tx / mag
        side_a = region.contains([x + eps * nx, y + eps * ny])
        side_b = region.contains([x - eps * nx, y - eps * ny])
        assert side_a != side_b, (
            f"Vertex {i} ({x:.6f},{y:.6f}) does not lie on the region edge"
        )
        misses_in += side_a
        misses_out += side_b
    # Orientation must be consistent along the entire loop
    assert misses_in == 0 or misses_out == 0, "Loop crosses itself or flips orientation"


class TestCircleBoundary:
    def test_single_loop_on_circle_edge(self):
        c = Circle(center=(3.0, 4.0), radius=2.0)
        (loop,) = c.boundary_loops()
        poly = loop.sample_polygon(CHORD_TOL)
        for x, y in poly:
            assert math.hypot(x - 3.0, y - 4.0) == pytest.approx(2.0, abs=1e-9)
        _assert_vertices_on_region_edge(c, poly, scale=2.0)

    def test_ccw_orientation(self):
        c = Circle(center=(0.0, 0.0), radius=1.0)
        (loop,) = c.boundary_loops()
        assert loop.signed_area(CHORD_TOL) > 0
        assert loop.signed_area(CHORD_TOL) == pytest.approx(math.pi, rel=1e-3)


class TestPolygonBoundary:
    def test_square_loop(self):
        square = Rectangle(vertices=((0, 0), (4, 0), (4, 4), (0, 4)))
        (loop,) = square.boundary_loops()
        poly = loop.sample_polygon(CHORD_TOL)
        # Line segments need no refinement: exactly the 4 corners
        assert len(poly) == 4
        assert abs(loop.signed_area(CHORD_TOL)) == pytest.approx(16.0)
        _assert_vertices_on_region_edge(square, poly, scale=4.0)

    def test_triangle(self):
        tri = Polygon(vertices=((0, 0), (2, 0), (1, 3)))
        (loop,) = tri.boundary_loops()
        assert abs(loop.signed_area(CHORD_TOL)) == pytest.approx(3.0)


class TestOffsetRegionBoundary:
    """The stadium shape around a curve - round and flat cap variants."""

    SEG = LineSegment((2.0, 1.0), (2.0, 9.0))  # vertical, like a secondary

    def test_round_caps_close_the_loop(self):
        region = OffsetRegion(curve=self.SEG, offset=0.5)
        (loop,) = region.boundary_loops()
        poly = loop.sample_polygon(CHORD_TOL)
        _assert_vertices_on_region_edge(region, poly, scale=0.5)

    def test_round_cap_area(self):
        """Stadium area: rectangle + full circle from the two half caps."""
        region = OffsetRegion(curve=self.SEG, offset=0.5)
        (loop,) = region.boundary_loops()
        expected = 8.0 * 1.0 + math.pi * 0.25
        assert abs(loop.signed_area(CHORD_TOL)) == pytest.approx(expected, rel=1e-3)

    def test_flat_caps_area(self):
        region = OffsetRegion(curve=self.SEG, offset=0.5, flat_start=True, flat_end=True)
        (loop,) = region.boundary_loops()
        assert abs(loop.signed_area(CHORD_TOL)) == pytest.approx(8.0, rel=1e-6)

    def test_flat_caps_vertices_on_edge(self):
        region = OffsetRegion(curve=self.SEG, offset=0.5, flat_start=True, flat_end=True)
        (loop,) = region.boundary_loops()
        poly = loop.sample_polygon(CHORD_TOL)
        _assert_vertices_on_region_edge(region, poly, scale=0.5)

    def test_mixed_caps(self):
        region = OffsetRegion(curve=self.SEG, offset=0.5, flat_start=True, flat_end=False)
        (loop,) = region.boundary_loops()
        expected = 8.0 * 1.0 + 0.5 * math.pi * 0.25
        assert abs(loop.signed_area(CHORD_TOL)) == pytest.approx(expected, rel=1e-3)

    def test_slanted_curve_round_caps(self):
        slanted = LineSegment((1.0, 1.0), (4.0, 5.0))  # length 5
        region = OffsetRegion(curve=slanted, offset=0.25)
        (loop,) = region.boundary_loops()
        poly = loop.sample_polygon(CHORD_TOL)
        expected = 5.0 * 0.5 + math.pi * 0.0625
        assert abs(loop.signed_area(CHORD_TOL)) == pytest.approx(expected, rel=1e-3)
        _assert_vertices_on_region_edge(region, poly, scale=0.25)

    def test_include_slices_present_on_both_sides(self):
        """Slice parameters forwarded through sample_polygon must land as
        vertices on both the left and right offset curves (the mesher
        relies on this so no chord spans a tent kink)."""
        region = OffsetRegion(curve=self.SEG, offset=0.5)
        (loop,) = region.boundary_loops()
        slices = (0.25, 0.5, 0.75)
        poly = loop.sample_polygon(CHORD_TOL, include=slices)
        for t in slices:
            cx, cy = self.SEG.point_at(t)
            hits = [
                p for p in poly
                if math.hypot(p[0] - cx, p[1] - cy) == pytest.approx(0.5, abs=1e-6)
            ]
            assert len(hits) >= 2, f"Slice t={t} missing from offset sides"

    def test_rejects_nonpositive_offset(self):
        with pytest.raises(ValueError):
            OffsetRegion(curve=self.SEG, offset=0.0)
