"""
The continuation contract, enforced against EVERY continuation type.

A CurveContinuation promises: for any junction state (point, unit tangent),
``build(point, tangent)`` returns a unit-speed segment that starts exactly
at the point with exactly that tangent (C0/C1 - the postcondition that
makes piecewise chains tangent-continuous BY CONSTRUCTION). This suite runs
every registered continuation instance against a grid of junction states,
the same way the unit-speed suite runs every curve. Register new
continuation types in CONTINUATION_INSTANCES.
"""
import math

import pytest

from app.geometry import (
    ArcContinuation,
    CurveContinuation,
    LineContinuation,
    SplineContinuation,
    UnitSpeedCurve,
)

CONTINUATION_INSTANCES = [
    pytest.param(LineContinuation(length=3.5), id="line-from"),
    pytest.param(ArcContinuation(end=(9.0, 4.0)), id="arc-from"),
    pytest.param(ArcContinuation(end=(4.5, -2.0)), id="arc-from-big-sweep"),
    pytest.param(SplineContinuation(points=((8.0, 3.0), (9.5, 1.0))), id="spline-from"),
    pytest.param(SplineContinuation(points=((8.0, 3.0),)), id="spline-from-single-point"),
    # ← register future continuation types here
]

# Junction states: varied positions and tangent directions (all unit).
JUNCTIONS = [
    pytest.param((5.0, 0.0), (1.0, 0.0), id="east"),
    pytest.param((5.0, 0.0), (0.0, 1.0), id="north"),
    pytest.param((3.0, 2.0), (-0.6, 0.8), id="up-left"),
    pytest.param((6.0, -1.0), (0.9486832980505138, -0.31622776601683794), id="down-right"),
]


@pytest.fixture(params=CONTINUATION_INSTANCES)
def continuation(request) -> CurveContinuation:
    return request.param


class TestContinuationContract:
    @pytest.mark.parametrize("point,tangent", JUNCTIONS)
    def test_builds_a_unit_speed_curve(self, continuation, point, tangent):
        c = continuation.build(point, tangent)
        assert isinstance(c, UnitSpeedCurve)

    @pytest.mark.parametrize("point,tangent", JUNCTIONS)
    def test_c0_starts_exactly_at_the_junction(self, continuation, point, tangent):
        c = continuation.build(point, tangent)
        p = c.point_at(c.t_min)
        assert p[0] == pytest.approx(point[0], abs=1e-9)
        assert p[1] == pytest.approx(point[1], abs=1e-9)

    @pytest.mark.parametrize("point,tangent", JUNCTIONS)
    def test_c1_starts_exactly_along_the_tangent(self, continuation, point, tangent):
        c = continuation.build(point, tangent)
        d = c.derivative_at(c.t_min)
        assert d[0] == pytest.approx(tangent[0], abs=1e-9)
        assert d[1] == pytest.approx(tangent[1], abs=1e-9)

    def test_canonical_is_json_serializable(self, continuation):
        import json

        json.dumps(continuation.canonical())


class TestLineContinuation:
    def test_rejects_nonpositive_length(self):
        for bad in (0.0, -1.0):
            with pytest.raises(ValueError, match="positive"):
                LineContinuation(length=bad)

    def test_length_is_the_arc_length(self):
        c = LineContinuation(length=4.0).build((1.0, 1.0), (0.6, 0.8))
        assert c.length == pytest.approx(4.0)
        assert c.point_at(c.t_max) == pytest.approx((1.0 + 2.4, 1.0 + 3.2))


class TestArcContinuation:
    def test_ends_exactly_at_the_endpoint(self):
        c = ArcContinuation(end=(9.0, 4.0)).build((5.0, 0.0), (1.0, 0.0))
        assert c.point_at(c.t_max) == pytest.approx((9.0, 4.0), abs=1e-9)

    def test_endpoint_behind_gives_a_major_sweep(self):
        """An endpoint 'behind' the tangent direction is reached the long
        way round - sweeps beyond a semicircle are first-class."""
        c = ArcContinuation(end=(4.0, 0.5)).build((5.0, 0.0), (1.0, 0.0))
        # Sweep = arc length * |curvature|
        sweep = c.length * abs(c.curvature_at(0.0))
        assert sweep > math.pi
        assert c.point_at(c.t_max) == pytest.approx((4.0, 0.5), abs=1e-9)

    def test_bend_side_follows_the_endpoint(self):
        left = ArcContinuation(end=(8.0, 2.0)).build((5.0, 0.0), (1.0, 0.0))
        right = ArcContinuation(end=(8.0, -2.0)).build((5.0, 0.0), (1.0, 0.0))
        assert left.curvature_at(0.0) > 0   # turning left (CCW)
        assert right.curvature_at(0.0) < 0  # turning right (CW)

    def test_endpoint_straight_ahead_rejected(self):
        with pytest.raises(ValueError, match="line-from"):
            ArcContinuation(end=(9.0, 0.0)).build((5.0, 0.0), (1.0, 0.0))

    def test_endpoint_straight_behind_rejected(self):
        with pytest.raises(ValueError, match="behind"):
            ArcContinuation(end=(1.0, 0.0)).build((5.0, 0.0), (1.0, 0.0))

    def test_endpoint_at_junction_rejected(self):
        with pytest.raises(ValueError, match="differ"):
            ArcContinuation(end=(5.0, 0.0)).build((5.0, 0.0), (1.0, 0.0))


class TestSplineContinuation:
    def test_interpolates_its_points(self):
        cont = SplineContinuation(points=((8.0, 3.0), (9.5, 1.0)))
        c = cont.build((5.0, 0.0), (0.0, 1.0))
        for q in ((8.0, 3.0), (9.5, 1.0)):
            assert c.distance_to_curve(q) == pytest.approx(0.0, abs=1e-9)

    def test_requires_at_least_one_point(self):
        with pytest.raises(ValueError, match="at least 1"):
            SplineContinuation(points=())
