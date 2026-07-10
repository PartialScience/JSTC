"""
Unit tests for conductor cross-section models.
"""
import math

import pytest

from app.geometry import Circle, CircularCrossSection, Rectangle, RectangularCrossSection


class TestCircularCrossSection:
    def test_region_is_centered_circle(self):
        cs = CircularCrossSection(diameter=0.25)
        region = cs.region_at((4.0, 23.0))
        assert isinstance(region, Circle)
        assert region.center == (4.0, 23.0)
        assert region.radius == pytest.approx(0.125)

    def test_gmd_is_maxwell_disc_value(self):
        """GMD of a uniform-current disc: a * e^(-1/4)."""
        cs = CircularCrossSection(diameter=2.0)
        assert cs.gmd == pytest.approx(1.0 * math.exp(-0.25))

    def test_max_extent(self):
        assert CircularCrossSection(diameter=0.3).max_extent == pytest.approx(0.3)

    def test_rejects_nonpositive(self):
        with pytest.raises(ValueError):
            CircularCrossSection(diameter=0.0)

    def test_hashable(self):
        assert hash(CircularCrossSection(diameter=0.25)) is not None


class TestRectangularCrossSection:
    def test_region_is_centered_rectangle(self):
        cs = RectangularCrossSection(width=0.1, height=1.0)
        region = cs.region_at((5.0, 10.0))
        assert isinstance(region, Rectangle)
        assert region.contains([5.0, 10.0])
        assert region.contains([5.04, 10.49])
        assert not region.contains([5.06, 10.0])
        assert not region.contains([5.0, 10.51])

    def test_gmd_is_rosa_grover_value(self):
        cs = RectangularCrossSection(width=1.0, height=0.1)
        assert cs.gmd == pytest.approx(0.2235 * 1.1)

    def test_rejects_nonpositive(self):
        with pytest.raises(ValueError):
            RectangularCrossSection(width=0.0, height=1.0)
