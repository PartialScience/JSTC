"""
Unit tests for the centripetal Catmull-Rom spline.

The unit-speed and G1 properties are covered by the shared contract suite
(test_unit_speed_contract.py); this file tests the spline-specific
definition: interpolation, collinear exactness, centripetal behaviour, and
the exactness of its owned numerics (projection, arc length).
"""
import math

import pytest

from app.geometry.curves.catmull_rom import CatmullRomSpline


# ---------------------------------------------------------------------------
# Instances registered into the universal curve property tests
# ---------------------------------------------------------------------------

SPLINE_INSTANCES = [
    pytest.param(
        CatmullRomSpline(points=((0.0, 0.0), (1.0, 2.0), (3.0, 3.0), (5.0, 1.0))),
        id="spline-gentle-s",
    ),
    pytest.param(
        CatmullRomSpline(points=((2.0, 0.0), (2.5, 2.0), (2.0, 4.0))),
        id="spline-bulged-vertical",
    ),
    pytest.param(
        CatmullRomSpline(points=((0.0, 0.0), (4.0, 3.0))),
        id="spline-two-points",
    ),
]


class TestConstruction:
    def test_rejects_single_point(self):
        with pytest.raises(ValueError):
            CatmullRomSpline(points=((1.0, 1.0),))

    def test_rejects_repeated_consecutive_points(self):
        with pytest.raises(ValueError):
            CatmullRomSpline(points=((0.0, 0.0), (0.0, 0.0), (1.0, 1.0)))

    def test_structural_equality(self):
        a = CatmullRomSpline(points=((0.0, 0.0), (1.0, 2.0), (3.0, 3.0)))
        b = CatmullRomSpline(points=((0.0, 0.0), (1.0, 2.0), (3.0, 3.0)))
        c = CatmullRomSpline(points=((0.0, 0.0), (1.0, 2.1), (3.0, 3.0)))
        assert a == b
        assert hash(a) == hash(b)
        assert a != c


class TestInterpolation:
    def test_passes_through_every_control_point(self):
        pts = ((0.0, 0.0), (1.0, 2.0), (3.0, 3.0), (5.0, 1.0))
        spline = CatmullRomSpline(points=pts)
        for p in pts:
            assert spline.distance_to_curve(p) == pytest.approx(0.0, abs=1e-9)

    def test_endpoints_are_first_and_last_points(self):
        pts = ((0.0, 0.0), (1.0, 2.0), (3.0, 3.0))
        spline = CatmullRomSpline(points=pts)
        assert spline.point_at(spline.t_min) == pytest.approx(pts[0])
        assert spline.point_at(spline.t_max) == pytest.approx(pts[-1])

    def test_collinear_points_give_exact_line(self):
        """Catmull-Rom through collinear points is exactly straight - a
        candy-cane's straight run stays a true line within the spline."""
        spline = CatmullRomSpline(points=((0.0, 0.0), (1.0, 1.0), (2.5, 2.5), (4.0, 4.0)))
        assert spline.length == pytest.approx(4.0 * math.sqrt(2.0), rel=1e-9)
        for i in range(21):
            t = spline.t_max * i / 20
            x, y = spline.point_at(t)
            assert y == pytest.approx(x, abs=1e-9)
            assert spline.curvature_at(t) == pytest.approx(0.0, abs=1e-9)

    def test_two_points_degenerate_to_segment(self):
        spline = CatmullRomSpline(points=((0.0, 0.0), (3.0, 4.0)))
        assert spline.length == pytest.approx(5.0, rel=1e-9)
        assert spline.point_at(2.5) == pytest.approx((1.5, 2.0), abs=1e-9)


class TestProjection:
    def test_recovers_parameter_of_oncurve_points(self):
        spline = CatmullRomSpline(points=((0.0, 0.0), (1.0, 2.0), (3.0, 3.0), (5.0, 1.0)))
        for frac in (0.0, 0.17, 0.33, 0.5, 0.71, 0.95, 1.0):
            t = spline.t_max * frac
            p = spline.point_at(t)
            t_found = spline.closest_parameter(p)
            assert t_found == pytest.approx(t, abs=1e-6 * spline.length)

    def test_matches_dense_scan(self):
        spline = CatmullRomSpline(points=((2.0, 0.0), (2.5, 2.0), (2.0, 4.0)))
        q = (3.4, 1.1)
        ts = [spline.t_max * i / 4000 for i in range(4001)]
        t_dense = min(ts, key=lambda t: _d2(spline.point_at(t), q))
        t_exact = spline.closest_parameter(q)
        assert _d2(spline.point_at(t_exact), q) <= _d2(spline.point_at(t_dense), q) + 1e-12


class TestSampling:
    def test_chord_error_bound(self):
        spline = CatmullRomSpline(points=((0.0, 0.0), (1.0, 2.0), (3.0, 3.0), (5.0, 1.0)))
        tol = 1e-3
        params = spline.sample_params(tol)
        for ta, tb in zip(params[:-1], params[1:]):
            tm = 0.5 * (ta + tb)
            pa, pb, pm = spline.point_at(ta), spline.point_at(tb), spline.point_at(tm)
            chord_mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            dev = math.hypot(pm[0] - chord_mid[0], pm[1] - chord_mid[1])
            assert dev <= tol * 1.05

    def test_include_values_present(self):
        spline = CatmullRomSpline(points=((0.0, 0.0), (1.0, 2.0), (3.0, 3.0)))
        want = 0.37 * spline.t_max
        params = spline.sample_params(0.05, include=(want,))
        assert any(abs(p - want) < 1e-12 for p in params)


def _d2(p, q):
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
