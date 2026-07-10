"""
Tests for magnetic formulas.

Run with: pytest tests/formulas/test_magnetic.py -v
"""
import pytest
from numpy.testing import assert_allclose
from app.formulas.magnetic import coaxial_circle_geometric_mutual_inductance


# ---------------------------------------------------------------------------
# coaxial_circle_geometric_mutual_inductance — tabular test cases
#
# Each entry: (r1, r2, d, expected_geometric_inductance)
# ---------------------------------------------------------------------------
# Test values computed using Mathematica
MUTUAL_INDUCTANCE_CASES = [
    pytest.param(
        1, 1, 1,
        0.39317514837200473104,
        id="equal_radii_moderate_separation",
    ),
    pytest.param(
        0.5, 2.0, 1.0,
        0.14041384333770869343,
        id="unequal_radii_moderate_separation",
    ),
    pytest.param(
        1, 1, 100,
        0.00000157032523511092,
        id="large_separation",
    ),
    pytest.param(
        1, 1, 0.01,
        4.6847308133100088534,
        id="close_together",
    ),
]


class TestCoaxialCircleGeometricMutualInductance:
    """Tabular and property-based tests for coaxial_circle_geometric_mutual_inductance."""

    @pytest.mark.parametrize("r1, r2, d, expected", MUTUAL_INDUCTANCE_CASES)
    def test_mutual_inductance(self, r1, r2, d, expected):
        """Test that the computed geometric mutual inductance matches the expected value."""
        result = coaxial_circle_geometric_mutual_inductance(r1, r2, d, 0.001)
        assert_allclose(result, expected, rtol=1e-7)

    @pytest.mark.parametrize("r1, r2, d, expected", MUTUAL_INDUCTANCE_CASES)
    def test_radii_symmetry(self, r1, r2, d, expected):
        """Test that swapping r1 and r2 gives the same result."""
        result_forward = coaxial_circle_geometric_mutual_inductance(r1, r2, d, 0.001)
        result_swapped = coaxial_circle_geometric_mutual_inductance(r2, r1, d, 0.001)
        assert_allclose(result_forward, result_swapped, rtol=1e-10)

    @pytest.mark.parametrize("r1, r2, d, expected", MUTUAL_INDUCTANCE_CASES)
    def test_distance_sign_symmetry(self, r1, r2, d, expected):
        """Test that negating d gives the same result (d appears squared in k²)."""
        result_positive = coaxial_circle_geometric_mutual_inductance(r1, r2, d, 0.001)
        result_negative = coaxial_circle_geometric_mutual_inductance(r1, r2, -d, 0.001)
        assert_allclose(result_positive, result_negative, rtol=1e-10)

    @pytest.mark.parametrize("r1, r2, d, expected", MUTUAL_INDUCTANCE_CASES)
    def test_linear_scaling(self, r1, r2, d, expected):
        """Test that scaling all lengths by α scales the result by α (units of length)."""
        alpha = 3.7
        result_original = coaxial_circle_geometric_mutual_inductance(r1, r2, d, 0.001)
        result_scaled = coaxial_circle_geometric_mutual_inductance(
            alpha * r1, alpha * r2, alpha * d, alpha * 0.001
        )
        assert_allclose(result_scaled, alpha * result_original, rtol=1e-10)


class TestRingSelfInductance:
    """coaxial_ring_self_geometric_inductance."""

    def test_uniform_current_round_wire(self):
        """With the Maxwell disc GMD (a*e^-1/4) the formula reproduces
        R(ln(8R/a) - 1.75)."""
        import math
        from app.formulas.magnetic import coaxial_ring_self_geometric_inductance

        R, a = 5.0, 0.1
        gmd = a * math.exp(-0.25)
        expected = R * (math.log(8 * R / a) - 1.75)
        assert coaxial_ring_self_geometric_inductance(R, gmd) == pytest.approx(expected)


class TestStraightWireInductance:
    """straight_wire_geometric_inductance (Rosa 1908)."""

    def test_javatc_lead_value(self):
        """JavaTC's example lead: 30 in of 0.2 in wire -> 0.861 uH."""
        from scipy.constants import mu_0
        from app.formulas.magnetic import straight_wire_geometric_inductance

        L = straight_wire_geometric_inductance(30.0, 0.2) * mu_0 * 0.0254
        assert L == pytest.approx(0.861e-6, rel=0.005)

    def test_rejects_nonpositive(self):
        from app.formulas.magnetic import straight_wire_geometric_inductance

        with pytest.raises(ValueError):
            straight_wire_geometric_inductance(0.0, 0.1)
