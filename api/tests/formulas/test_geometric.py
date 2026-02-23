"""
Tests for geometric formulas.

Run with: pytest tests/formulas/test_geometric.py -v
"""
import pytest
import numpy as np
from numpy.testing import assert_allclose
from app.formulas.geometric import conical_helix_arclength


# ---------------------------------------------------------------------------
# conical_helix_arclength — tabular test cases
#
# Each entry: (r1, r2, h1, h2, n, expected_length)
# ---------------------------------------------------------------------------
# Test values computed using Mathematica's ArcLength function
ARCLENGTH_CASES = [
    # -- Cylindrical helix (r1 == r2) ----------------------------------------
    pytest.param(
        6, 6, 0, 50, 900,
        33929.237500171777207,
        id="cylidrical_helix",
    ),
    pytest.param(
        4, 10, 0, 0, 12,
        527.82402219957573285,
        id="flat_spiral",
    ),
    pytest.param(
        2, 40, -4, 100, 21,
        2774.5215140214553993,
        id="standard_conical_helix",
    ),
]

class TestConicalHelixArclength:
    """Tabular tests for conical_helix_arclength."""

    @pytest.mark.parametrize("r1, r2, h1, h2, n, expected", ARCLENGTH_CASES)
    def test_arclength(self, r1, r2, h1, h2, n, expected):
        """Test that the computed arclength matches the expected value for each case."""
        result = conical_helix_arclength(r1, r2, h1, h2, n)
        assert_allclose(result, expected, rtol=1e-10)
    
    @pytest.mark.parametrize("r1, r2, h1, h2, n, expected", ARCLENGTH_CASES)
    def test_symmetry(self, r1, r2, h1, h2, n, expected):
        """Test that swapping start and end points gives the same length."""
        result_forward = conical_helix_arclength(r1, r2, h1, h2, n)
        result_reverse = conical_helix_arclength(r2, r1, h2, h1, n)
        assert_allclose(result_forward, result_reverse, rtol=1e-10)
    
    @pytest.mark.parametrize("r1, r2, h1, h2, n, expected", ARCLENGTH_CASES)
    def test_negative_heights(self, r1, r2, h1, h2, n, expected):
        """Test that the same values are returned when negating the heights."""
        result_positive = conical_helix_arclength(r1, r2, h1, h2, n)
        result_negative = conical_helix_arclength(r1, r2, -h1, -h2, n)
        assert_allclose(result_positive, result_negative, rtol=1e-10)
    
    @pytest.mark.parametrize("r1, r2, h1, h2, n, expected", ARCLENGTH_CASES)
    def test_negative_radii(self, r1, r2, h1, h2, n, expected):
        """Test that the same values are returned when negating the radii."""
        result_positive = conical_helix_arclength(r1, r2, h1, h2, n)
        result_negative = conical_helix_arclength(-r1, -r2, h1, h2, n)
        assert_allclose(result_positive, result_negative, rtol=1e-10)
        
    @pytest.mark.parametrize("r1, r2, h1, h2, n, expected", ARCLENGTH_CASES)
    def test_negative_turns(self, r1, r2, h1, h2, n, expected):
        """Test that the same values are returned when negating the number of turns."""
        result_positive = conical_helix_arclength(r1, r2, h1, h2, n)
        result_negative = conical_helix_arclength(r1, r2, h1, h2, -n)
        assert_allclose(result_positive, result_negative, rtol=1e-10)