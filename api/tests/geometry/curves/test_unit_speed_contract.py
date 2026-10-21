"""
The unit-speed curve contract, enforced against EVERY concrete curve.

Every winding centerline curve must be parameterized by arc length and be
G1-smooth. These are the preconditions of the whole solver chain (turn
densities in turns-per-length, exact discretization, offset-region
construction), so they are tested generically here, the same way the matrix
solvers share their parameterized suites: register instances in
UNIT_SPEED_INSTANCES (conftest.py) and every contract property runs against
them.

OffsetCurve is the documented exception (it shares its parent's parameter)
and is checked separately in test_offset_curve.py; the type system keeps it
out of the specs, and a dedicated test here keeps it out of this registry.
"""
import math

import pytest

from app.geometry.curves.base import ParametricCurve, UnitSpeedCurve
from app.geometry.curves.offset_curve import OffsetCurve
from tests.geometry.curves.conftest import UNIT_SPEED_INSTANCES


def _samples(curve, n=257):
    return [curve.t_min + (curve.t_max - curve.t_min) * i / (n - 1) for i in range(n)]


class TestRegistry:
    def test_every_instance_is_unit_speed_typed(self, unit_speed_instance):
        assert isinstance(unit_speed_instance, UnitSpeedCurve)

    def test_offset_curve_is_excluded_by_type(self):
        assert not issubclass(OffsetCurve, UnitSpeedCurve)
        assert issubclass(OffsetCurve, ParametricCurve)


class TestUnitSpeed:
    def test_derivative_is_unit_everywhere(self, unit_speed_instance):
        c = unit_speed_instance
        for t in _samples(c):
            dx, dy = c.derivative_at(t)
            assert math.hypot(dx, dy) == pytest.approx(1.0, abs=1e-8), (
                f"|derivative| != 1 at t={t}"
            )

    def test_arc_length_is_parameter_difference(self, unit_speed_instance):
        c = unit_speed_instance
        span = c.t_max - c.t_min
        for f1, f2 in ((0.0, 1.0), (0.1, 0.35), (0.5, 0.95)):
            t1 = c.t_min + f1 * span
            t2 = c.t_min + f2 * span
            assert c.arc_length_between(t1, t2) == pytest.approx(t2 - t1, rel=1e-12)

    def test_chord_length_matches_parameter_locally(self, unit_speed_instance):
        """Independent check of the parameterization itself: summing chords
        of a fine polyline must reproduce the parameter span."""
        c = unit_speed_instance
        ts = _samples(c, 4097)
        chord_sum = 0.0
        prev = c.point_at(ts[0])
        for t in ts[1:]:
            p = c.point_at(t)
            chord_sum += math.hypot(p[0] - prev[0], p[1] - prev[1])
            prev = p
        span = c.t_max - c.t_min
        # Polyline underestimates arc length by O(h^2 * curvature^2)
        assert chord_sum == pytest.approx(span, rel=1e-4)
        assert chord_sum <= span * (1 + 1e-12)


class TestDerivativeConsistency:
    def test_derivative_matches_finite_difference(self, unit_speed_instance):
        c = unit_speed_instance
        h = (c.t_max - c.t_min) * 1e-7
        for f in (0.1, 0.3, 0.5, 0.7, 0.9):
            t = c.t_min + f * (c.t_max - c.t_min)
            p0 = c.point_at(t - h)
            p1 = c.point_at(t + h)
            fd = ((p1[0] - p0[0]) / (2 * h), (p1[1] - p0[1]) / (2 * h))
            dx, dy = c.derivative_at(t)
            assert dx == pytest.approx(fd[0], abs=1e-5)
            assert dy == pytest.approx(fd[1], abs=1e-5)

    def test_curvature_matches_tangent_rotation_rate(self, unit_speed_instance):
        """For a unit-speed curve, dT/ds = curvature * left_normal: the
        curvature is the tangent's rotation rate. Checked by finite
        differences of the tangent angle."""
        c = unit_speed_instance
        h = max((c.t_max - c.t_min) * 1e-6, 1e-9)
        for f in (0.15, 0.4, 0.6, 0.85):
            t = c.t_min + f * (c.t_max - c.t_min)
            d0 = c.derivative_at(t - h)
            d1 = c.derivative_at(t + h)
            a0 = math.atan2(d0[1], d0[0])
            a1 = math.atan2(d1[1], d1[0])
            dtheta = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            kappa_fd = dtheta / (2 * h)
            assert c.curvature_at(t) == pytest.approx(kappa_fd, abs=2e-3 * (1 + abs(kappa_fd)))


class TestG1Continuity:
    def test_tangent_direction_is_continuous(self, unit_speed_instance):
        """No kinks: between every pair of adjacent dense samples, the
        tangent may rotate at most what the local curvature allows (with
        slack for the finite step)."""
        c = unit_speed_instance
        ts = _samples(c, 2049)
        step = ts[1] - ts[0]
        for t0, t1 in zip(ts[:-1], ts[1:]):
            d0 = c.derivative_at(t0)
            d1 = c.derivative_at(t1)
            a0 = math.atan2(d0[1], d0[0])
            a1 = math.atan2(d1[1], d1[0])
            dtheta = abs((a1 - a0 + math.pi) % (2 * math.pi) - math.pi)
            kappa = max(abs(c.curvature_at(t0)), abs(c.curvature_at(t1)))
            allowed = 1.5 * kappa * step + 1e-6
            assert dtheta <= allowed, (
                f"tangent jumped {dtheta:.3g} rad over step {step:.3g} at t={t0:.6g} "
                f"(curvature allows {allowed:.3g}) - G1 violation (kink)"
            )


class TestProjectionAndBounds:
    def test_closest_parameter_matches_dense_scan(self, unit_speed_instance):
        """closest_parameter must find the GLOBAL minimum."""
        c = unit_speed_instance
        # Probe points: on-curve, near-curve, and far away on both sides
        probes = []
        for f in (0.08, 0.37, 0.62, 0.91):
            t = c.t_min + f * (c.t_max - c.t_min)
            x, y = c.point_at(t)
            dx, dy = c.derivative_at(t)
            probes += [(x, y), (x - dy * 0.3, y + dx * 0.3), (x + dy * 2.0, y - dx * 2.0)]
        ts = _samples(c, 4001)
        for q in probes:
            t_found = c.closest_parameter(q)
            d_found = math.hypot(*(a - b for a, b in zip(c.point_at(t_found), q)))
            d_dense = min(
                math.hypot(*(a - b for a, b in zip(c.point_at(t), q))) for t in ts
            )
            assert d_found <= d_dense + 1e-7 * (1 + d_dense)

    def test_max_abs_curvature_bounds_samples(self, unit_speed_instance):
        c = unit_speed_instance
        bound = c.max_abs_curvature()
        worst = max(abs(c.curvature_at(t)) for t in _samples(c, 1025))
        assert worst <= bound * (1 + 1e-9)


class TestSamplingContract:
    @pytest.mark.parametrize("tol_frac", [1e-2, 1e-4])
    def test_sample_params_honors_tolerance(self, unit_speed_instance, tol_frac):
        c = unit_speed_instance
        tol = tol_frac * c.length
        params = c.sample_params(tol)
        assert params[0] == c.t_min and params[-1] == c.t_max
        assert all(b > a for a, b in zip(params[:-1], params[1:]))
        for ta, tb in zip(params[:-1], params[1:]):
            for frac in (0.25, 0.5, 0.75):
                tm = ta + frac * (tb - ta)
                pa, pb, pm = c.point_at(ta), c.point_at(tb), c.point_at(tm)
                chord = (
                    pa[0] + frac * (pb[0] - pa[0]),
                    pa[1] + frac * (pb[1] - pa[1]),
                )
                dev = math.hypot(pm[0] - chord[0], pm[1] - chord[1])
                assert dev <= tol * 1.05

    def test_includes_appear_exactly(self, unit_speed_instance):
        c = unit_speed_instance
        want = tuple(c.t_min + f * c.length for f in (0.21, 0.5, 0.83))
        params = c.sample_params(0.05 * c.length, include=want)
        for w in want:
            assert w in params

    def test_offset_sampling_honors_tolerance_on_the_offset(self, unit_speed_instance):
        """The polyline of the PARALLEL curve built from
        sample_params_for_offset must meet the tolerance."""
        c = unit_speed_instance
        kappa = c.max_abs_curvature()
        # A representative conductor radius: well inside the validity tube.
        # (kappa * length below float noise means the curve is straight.)
        a = 0.2 / kappa if kappa * c.length > 1e-9 else 0.02 * c.length
        tol = 1e-3 * c.length

        def off_point(t):
            x, y = c.point_at(t)
            dx, dy = c.derivative_at(t)
            return (x - a * dy, y + a * dx)

        params = c.sample_params_for_offset(a, tol)
        for ta, tb in zip(params[:-1], params[1:]):
            tm = 0.5 * (ta + tb)
            pa, pb, pm = off_point(ta), off_point(tb), off_point(tm)
            chord_mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            dev = math.hypot(pm[0] - chord_mid[0], pm[1] - chord_mid[1])
            assert dev <= tol * 1.05
