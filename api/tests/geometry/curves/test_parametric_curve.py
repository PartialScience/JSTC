"""
Universal property tests for any ParametricCurve implementation.

These tests run against every curve instance registered in the
``curve_instance`` fixture (see conftest.py).  They verify properties that
MUST hold regardless of the concrete curve type:

  1. The ABC cannot be instantiated directly.
  2. Every registered instance is a ParametricCurve subclass.
  3. t_min < t_max.
  4. point_at returns a tuple with consistent dimensionality.
  5. Points sampled via point_at have distance 0 from the curve.

Run with: pytest tests/geometry/curves/test_parametric_curve.py -v
"""
import pytest
import math

from app.geometry.curves.base import ParametricCurve


# ---------------------------------------------------------------------------
# Number of evenly‑spaced t samples (including t_min and t_max)
# ---------------------------------------------------------------------------
NUM_SAMPLES = 21


def _sample_t_values(curve: ParametricCurve, n: int = NUM_SAMPLES):
    """Return *n* evenly-spaced t values spanning [t_min, t_max]."""
    t0 = curve.t_min
    t1 = curve.t_max
    if n == 1:
        return [t0]
    return [t0 + (t1 - t0) * i / (n - 1) for i in range(n)]


# ---------------------------------------------------------------------------
# ParametricCurve ABC tests
# ---------------------------------------------------------------------------

class TestParametricCurveABC:
    """Tests for the ParametricCurve abstract base class itself."""

    def test_cannot_instantiate_directly(self):
        """The ABC should not be instantiable."""
        with pytest.raises(TypeError):
            ParametricCurve()

    def test_concrete_is_subclass(self, curve_class):
        """Every registered class must be a ParametricCurve subclass."""
        assert issubclass(curve_class, ParametricCurve)

    def test_has_required_methods(self, curve_class):
        """Every concrete curve class must expose the required API surface."""
        for attr in ("point_at", "distance_to_curve", "t_min", "t_max"):
            assert hasattr(curve_class, attr), f"{curve_class.__name__} missing {attr}"


# ---------------------------------------------------------------------------
# Universal property tests for all ParametricCurve instances
# ---------------------------------------------------------------------------

class TestParametricCurveProperties:
    """Property tests that must hold for every ParametricCurve instance."""

    def test_t_min_less_than_t_max(self, curve_instance):
        """t_min must be strictly less than t_max."""
        assert curve_instance.t_min < curve_instance.t_max, (
            f"Expected t_min < t_max, got t_min={curve_instance.t_min}, "
            f"t_max={curve_instance.t_max}"
        )

    def test_point_at_returns_tuple(self, curve_instance):
        """point_at should return a tuple of floats."""
        t = (curve_instance.t_min + curve_instance.t_max) / 2
        pt = curve_instance.point_at(t)
        assert isinstance(pt, tuple), f"Expected tuple, got {type(pt)}"
        assert all(isinstance(c, (int, float)) for c in pt)

    def test_point_at_consistent_dimension(self, curve_instance):
        """All points returned by point_at must have the same number of coordinates."""
        ts = _sample_t_values(curve_instance)
        dims = {len(curve_instance.point_at(t)) for t in ts}
        assert len(dims) == 1, (
            f"Inconsistent point dimensions across parameter range: {dims}"
        )

    # ------------------------------------------------------------------
    # distance_to_curve == 0 for every point ON the curve
    # ------------------------------------------------------------------

    def test_points_on_curve_have_zero_distance(self, curve_instance):
        """
        Every point returned by point_at(t) must have distance 0
        from the curve (within floating-point tolerance).
        """
        for t in _sample_t_values(curve_instance):
            pt = curve_instance.point_at(t)
            dist = curve_instance.distance_to_curve(pt)
            assert dist == pytest.approx(0.0, abs=1e-10), (
                f"point_at({t}) = {pt} has distance {dist} from curve; "
                f"expected 0"
            )

    def test_distance_to_curve_non_negative(self, curve_instance):
        """distance_to_curve must always return a non-negative value."""
        pt = curve_instance.point_at(
            (curve_instance.t_min + curve_instance.t_max) / 2
        )
        # Also test a point offset from the curve
        offset_pt = tuple(c + 1.0 for c in pt)
        assert curve_instance.distance_to_curve(pt) >= 0
        assert curve_instance.distance_to_curve(offset_pt) >= 0
