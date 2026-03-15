"""
Tests for UniformArcLengthDiscretizer.

Uses a mock SecondaryConductorSpec to avoid coupling to concrete coil model
implementations. The mock's curve uses a simple arc_length_between that is
proportional to parameter difference, making expected values easy to compute.
"""
import pytest
from unittest.mock import MagicMock
from app.models.coil_models import SecondaryConductorSpec
from app.geometry.curves.base import ParametricCurve
from app.geometry.regions.offset_regions import OffsetRegion
from app.simulation.coil_discretizers.uniform_arclength_discretizer import UniformArcLengthDiscretizer


# ---------------------------------------------------------------------------
# Helper: mock secondary backed by a mock curve
# ---------------------------------------------------------------------------

def _make_mock_secondary(t_min: float, t_max: float, total_length: float):
    """
    Create a mock SecondaryConductorSpec whose curve has a linear arc length
    (i.e. arc_length_between(t1, t2) = total_length / (t_max - t_min) * (t2 - t1)).

    This simulates a curve with uniform speed parameterization.
    """
    length_per_t = total_length / (t_max - t_min)

    curve = MagicMock(spec=ParametricCurve)
    curve.t_min = t_min
    curve.t_max = t_max
    curve.arc_length_between = MagicMock(
        side_effect=lambda t1, t2: length_per_t * (t2 - t1)
    )

    geometry = MagicMock(spec=OffsetRegion)
    geometry.offset = 0.01

    secondary = MagicMock(spec=SecondaryConductorSpec)
    secondary.curve = curve
    secondary.geometry = geometry
    return secondary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def unit_secondary():
    """Curve with t in [0, 1] and total arc length = 10."""
    return _make_mock_secondary(t_min=0.0, t_max=1.0, total_length=10.0)


@pytest.fixture
def shifted_secondary():
    """Curve with t in [2, 7] and total arc length = 25."""
    return _make_mock_secondary(t_min=2.0, t_max=7.0, total_length=25.0)


# ---------------------------------------------------------------------------
# Tests for get_slices
# ---------------------------------------------------------------------------

class TestGetSlices:
    """Tests for UniformArcLengthDiscretizer.get_slices().

    get_slices returns a flat tuple of N+1 boundary parameter values
    for N slices (discretization_order). Consecutive pairs define each slice.
    """

    def test_correct_number_of_boundaries(self, unit_secondary):
        """get_slices should return exactly discretization_order + 1 boundary values."""
        for n in [2, 5, 10]:
            slices = UniformArcLengthDiscretizer.get_slices(unit_secondary, n)
            assert len(slices) == n + 1

    def test_boundaries_are_monotonically_increasing(self, unit_secondary):
        """Each boundary value should be strictly greater than its predecessor."""
        slices = UniformArcLengthDiscretizer.get_slices(unit_secondary, 4)
        for i in range(1, len(slices)):
            assert slices[i] > slices[i - 1]

    def test_slices_cover_full_range(self, unit_secondary):
        """First boundary is t_min, last boundary is t_max."""
        slices = UniformArcLengthDiscretizer.get_slices(unit_secondary, 5)
        assert slices[0] == pytest.approx(0.0)
        assert slices[-1] == pytest.approx(1.0)

    def test_slices_are_contiguous(self, unit_secondary):
        """Boundaries are shared between adjacent slices by construction."""
        slices = UniformArcLengthDiscretizer.get_slices(unit_secondary, 5)
        # Verify no gaps: boundary i is the end of slice i-1 and start of slice i
        for i in range(1, len(slices) - 1):
            assert isinstance(slices[i], float)

    def test_uniform_arc_length(self, unit_secondary):
        """Each slice should have equal arc length."""
        n = 4
        slices = UniformArcLengthDiscretizer.get_slices(unit_secondary, n)
        curve = unit_secondary.curve

        expected_arc = 10.0 / n  # total_length / n
        for i in range(n):
            arc = curve.arc_length_between(slices[i], slices[i + 1])
            assert arc == pytest.approx(expected_arc, abs=1e-8)

    def test_single_slice(self, unit_secondary):
        """discretization_order=1 should return two boundaries spanning the whole curve."""
        slices = UniformArcLengthDiscretizer.get_slices(unit_secondary, 1)
        assert len(slices) == 2
        assert slices[0] == pytest.approx(0.0)
        assert slices[1] == pytest.approx(1.0)

    def test_shifted_parameter_range(self, shifted_secondary):
        """Verify correct behavior when t_min != 0."""
        n = 5
        slices = UniformArcLengthDiscretizer.get_slices(shifted_secondary, n)
        curve = shifted_secondary.curve

        assert slices[0] == pytest.approx(2.0)
        assert slices[-1] == pytest.approx(7.0)

        expected_arc = 25.0 / n
        for i in range(n):
            arc = curve.arc_length_between(slices[i], slices[i + 1])
            assert arc == pytest.approx(expected_arc, abs=1e-8)

    def test_large_discretization(self, unit_secondary):
        """Stress test with many slices — should still be contiguous and uniform."""
        n = 100
        slices = UniformArcLengthDiscretizer.get_slices(unit_secondary, n)
        assert len(slices) == n + 1
        assert slices[0] == pytest.approx(0.0)
        assert slices[-1] == pytest.approx(1.0)

        expected_arc = 10.0 / n
        curve = unit_secondary.curve
        for i in range(n):
            arc = curve.arc_length_between(slices[i], slices[i + 1])
            assert arc == pytest.approx(expected_arc, abs=1e-6)
