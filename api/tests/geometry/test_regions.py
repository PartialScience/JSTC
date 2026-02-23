"""
Unit tests for geometric region classes.

These tests verify the correctness of point containment for various geometric shapes.
Run with: pytest tests/test_geometry.py -v
"""
import pytest
import math
from app.geometry import GeometricRegion, Circle, Polygon, Rectangle


class TestCircle:
    """Tests for the Circle class."""
    
    def test_circle_creation(self):
        """Test that a circle can be created with valid parameters."""
        circle = Circle(center=(0, 0), radius=5.0)
        assert circle.center == (0, 0)
        assert circle.radius == 5.0
    
    def test_circle_invalid_center_dimension(self):
        """Test that circle creation fails with wrong dimension center."""
        with pytest.raises(ValueError, match="Center must be 2D"):
            Circle(center=(0, 0, 0), radius=5.0)
    
    def test_circle_negative_radius(self):
        """Test that circle creation fails with negative radius."""
        with pytest.raises(ValueError, match="Radius must be positive"):
            Circle(center=(0, 0), radius=-1.0)
    
    def test_circle_zero_radius(self):
        """Test that circle creation fails with zero radius."""
        with pytest.raises(ValueError, match="Radius must be positive"):
            Circle(center=(0, 0), radius=0.0)
    
    @pytest.mark.parametrize("point,expected", [
        # Points inside
        ([0, 0], True),      # center
        ([3, 0], True),      # inside horizontally
        ([0, 4], True),      # inside vertically
        ([3, 3], True),      # inside diagonally
        # Points on boundary
        ([5, 0], True),      # boundary right
        ([0, 5], True),      # boundary top
        ([3, 4], True),      # boundary (3^2 + 4^2 = 25)
        ([-5, 0], True),     # boundary left
        ([0, -5], True),     # boundary bottom
        # Points outside
        ([6, 0], False),     # outside right
        ([0, 6], False),     # outside top
        ([10, 10], False),   # far outside
        ([-6, 0], False),    # outside left
    ])
    def test_point_containment(self, point, expected):
        """Test various points for containment in a circle."""
        circle = Circle(center=(0, 0), radius=5.0)
        assert circle.contains(point) is expected
    
    def test_circle_with_offset_center(self):
        """Test circle with non-origin center."""
        circle = Circle(center=(10, 20), radius=3.0)
        assert circle.contains([10, 20]) is True  # center
        assert circle.contains([12, 20]) is True  # inside
        assert circle.contains([14, 20]) is False  # outside
    
class TestPolygon:
    """Tests for the Polygon class."""
    
    def test_polygon_creation(self):
        """Test that a polygon can be created with valid vertices."""
        vertices = ((0, 0), (1, 0), (0, 1))
        polygon = Polygon(vertices=vertices)
        assert polygon.vertices == vertices
    
    def test_polygon_too_few_vertices(self):
        """Test that polygon creation fails with fewer than 3 vertices."""
        with pytest.raises(ValueError, match="at least 3 vertices"):
            Polygon(vertices=((0, 0), (1, 0)))
    
    def test_polygon_invalid_vertex_dimension(self):
        """Test that polygon creation fails with 3D vertices."""
        with pytest.raises(ValueError, match="Each vertex must be 2D"):
            Polygon(vertices=((0, 0), (1, 0), (0, 0, 1)))
    
    @pytest.mark.parametrize("point,expected", [
        # Points inside
        ([2, 1], True),       # center-ish
        ([1, 0.5], True),     # lower left
        ([3, 1], True),       # right edge area
        # Points outside
        ([5, 5], False),      # far outside
        ([-1, 0], False),     # left outside
        ([2, -1], False),     # below
        ([2, 4], False),      # above
    ])
    def test_triangle_containment(self, point, expected):
        """Test point containment in a triangle."""
        triangle = Polygon(vertices=((0, 0), (4, 0), (2, 3)))
        assert triangle.contains(point) is expected
    
    def test_triangle_vertex_on_boundary(self):
        """Test that vertices themselves are considered inside."""
        triangle = Polygon(vertices=((0, 0), (4, 0), (2, 3)))
        # Note: ray casting treats vertices as inside (which is correct behavior)
        assert triangle.contains([0, 0]) is True  # on vertex
        assert triangle.contains([2, 0]) is True  # on edge
    
    @pytest.mark.parametrize("point,expected", [
        # Points inside
        ([1, 1], True),
        ([0.5, 0.5], True),
        ([1.9, 1.9], True),
        # Points outside
        ([3, 3], False),
        ([-1, 1], False),
        ([1, -1], False),
        ([2.5, 1], False),
    ])
    def test_square_containment(self, point, expected):
        """Test point containment in a square polygon."""
        square = Polygon(vertices=((0, 0), (2, 0), (2, 2), (0, 2)))
        assert square.contains(point) is expected
    
    def test_convex_polygon(self):
        """Test point containment in a convex pentagon."""
        pentagon = Polygon(vertices=(
            (0, 0), (2, 0), (3, 1.5), (1, 2.5), (-0.5, 1.5)
        ))
        assert pentagon.contains([1, 1]) is True
        assert pentagon.contains([10, 10]) is False
    
    def test_concave_polygon(self):
        """Test point containment in a concave (L-shaped) polygon."""
        l_shape = Polygon(vertices=(
            (0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)
        ))
        assert l_shape.contains([0.5, 0.5]) is True  # inside lower part
        assert l_shape.contains([0.5, 1.5]) is True  # inside upper part
        assert l_shape.contains([1.5, 1.5]) is False  # in the cutout


class TestRectangle:
    """Tests for the Rectangle class."""
    
    def test_rectangle_creation(self):
        """Test that a rectangle can be created with 4 vertices."""
        vertices = ((0, 0), (2, 0), (2, 1), (0, 1))
        rect = Rectangle(vertices=vertices)
        assert rect.vertices == vertices
    
    def test_rectangle_wrong_vertex_count(self):
        """Test that rectangle creation fails without exactly 4 vertices."""
        with pytest.raises(ValueError, match="exactly 4 vertices"):
            Rectangle(vertices=((0, 0), (1, 0), (0, 1)))
        
        with pytest.raises(ValueError, match="exactly 4 vertices"):
            Rectangle(vertices=((0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5)))
    
    @pytest.mark.parametrize("point,expected", [
        # Points inside axis-aligned rectangle
        ([1, 1], True),
        ([1.5, 1], True),
        ([0.1, 0.1], True),
        ([2.9, 1.9], True),
        # Points outside
        ([4, 1], False),
        ([1, 3], False),
        ([-1, 1], False),
        ([1, -1], False),
    ])
    def test_axis_aligned_rectangle_containment(self, point, expected):
        """Test point containment in an axis-aligned rectangle."""
        rect = Rectangle(vertices=((0, 0), (3, 0), (3, 2), (0, 2)))
        assert rect.contains(point) is expected
    
    def test_rotated_rectangle(self):
        """Test point containment in a rotated rectangle."""
        # 45-degree rotated square centered around origin
        s = math.sqrt(2) / 2
        rect = Rectangle(vertices=(
            (s, 0), (0, s), (-s, 0), (0, -s)
        ))
        assert rect.contains([0, 0]) is True
        assert rect.contains([0.3, 0.3]) is True
        assert rect.contains([1, 1]) is False
    
    def test_rectangle_inherits_polygon_behavior(self):
        """Test that Rectangle properly inherits from Polygon."""
        rect = Rectangle(vertices=((0, 0), (1, 0), (1, 1), (0, 1)))
        # Verify it's a Polygon instance
        assert isinstance(rect, Polygon)
        assert isinstance(rect, GeometricRegion)

