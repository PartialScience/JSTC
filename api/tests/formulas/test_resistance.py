"""
Unit tests for AC resistance formulas (skin effect + Medhurst proximity).
"""
import math

import pytest

from app.formulas.resistance import medhurst_proximity_factor, skin_effect_factor


class TestSkinEffectFactor:
    def test_low_frequency_limit_is_unity(self):
        # Wire much thinner than skin depth: no skin effect
        assert skin_effect_factor(0.001, 1.0) == pytest.approx(1.0, abs=1e-9)

    def test_high_frequency_limit(self):
        """For a >> delta: Rac/Rdc -> a/(2*delta) + 1/4."""
        a, delta = 0.01, 0.0001  # a/delta = 100
        expected = a / (2 * delta) + 0.25
        assert skin_effect_factor(2 * a, delta) == pytest.approx(expected, rel=1e-3)

    def test_monotonic_in_frequency(self):
        """Thinner skin depth (higher f) must never lower the factor."""
        d = 0.001
        factors = [skin_effect_factor(d, delta) for delta in (1e-3, 3e-4, 1e-4, 3e-5)]
        assert all(b >= a for a, b in zip(factors, factors[1:]))

    def test_rejects_nonpositive(self):
        with pytest.raises(ValueError):
            skin_effect_factor(0.0, 1.0)
        with pytest.raises(ValueError):
            skin_effect_factor(1.0, -1.0)


class TestMedhurstProximityFactor:
    def test_table_corners_exact(self):
        assert medhurst_proximity_factor(1.00, 1.0) == pytest.approx(5.55)
        assert medhurst_proximity_factor(2.50, 6.0) == pytest.approx(1.56)
        assert medhurst_proximity_factor(1.25, 4.0) == pytest.approx(2.60)

    def test_interpolates_between_columns(self):
        phi = medhurst_proximity_factor(1.18, 2.0)  # between 1.11 and 1.25
        assert 2.74 < phi < 3.36

    def test_clamps_outside_table(self):
        assert medhurst_proximity_factor(5.0, 4.0) == pytest.approx(1.54)
        assert medhurst_proximity_factor(1.0, 20.0) == pytest.approx(3.31)

    def test_close_wound_worse_than_spaced(self):
        assert medhurst_proximity_factor(1.0, 4.0) > medhurst_proximity_factor(2.0, 4.0)

    def test_rejects_nonpositive(self):
        with pytest.raises(ValueError):
            medhurst_proximity_factor(0.0, 1.0)
