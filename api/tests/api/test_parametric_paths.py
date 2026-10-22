"""
API-level coverage of parametric winding paths and graded turn profiles:
payload -> schema -> converter -> domain spec.
"""
import math

import pytest
from pydantic import TypeAdapter, ValidationError

from app.converters import coil_from_schema
from app.geometry import CatmullRomSpline, CircularArc
from app.models.turn_profiles import GradedTurns
from app.schemas.analysis_schemas import MatricesRequest


def _payload(secondary_path, primary_path=None, secondary_turns=None):
    coil = {
        "secondary": {
            "material": "copper",
            "turn_fxn": secondary_turns or {"kind": "uniform", "total_turns": 100},
            "path": secondary_path,
            "wire_dia": 0.02,
        },
        "toploads": [],
        "grounds": [],
        "r_max": 50,
        "z_max": 80,
        "discretization_order": 10,
    }
    if primary_path is not None:
        coil["primary"] = {
            "material": "copper",
            "turn_fxn": {"kind": "uniform", "total_turns": 8.5},
            "cross_section": {"kind": "circular", "diameter": 0.25},
            "path": primary_path,
        }
    return {"coil": coil}


def test_arc_primary_converts():
    req = MatricesRequest.model_validate(_payload(
        {"kind": "line", "start": [2.0, 20.0], "end": [2.0, 40.0]},
        primary_path={"kind": "arc", "start": [4.0, 20.0], "mid": [6.2, 22.8], "end": [9.0, 24.0]},
    ))
    coil = coil_from_schema(req.coil)
    arc = coil.primary.curve
    assert isinstance(arc, CircularArc)
    assert arc.point_at(arc.t_min) == pytest.approx((4.0, 20.0))
    assert arc.point_at(arc.t_max) == pytest.approx((9.0, 24.0))
    # The through point lies on the arc
    assert arc.distance_to_curve((6.2, 22.8)) == pytest.approx(0.0, abs=1e-9)
    assert len(coil.primary.ring_centers()) == 9


def test_arc_direction_follows_the_through_point():
    """The same endpoints bend left or right depending on where mid sits."""
    def arc_for(mid):
        req = MatricesRequest.model_validate(_payload(
            {"kind": "line", "start": [2.0, 20.0], "end": [2.0, 40.0]},
            primary_path={"kind": "arc", "start": [4.0, 20.0], "mid": mid, "end": [9.0, 24.0]},
        ))
        return coil_from_schema(req.coil).primary.curve

    # A through point left of the start->end direction bulges the arc left,
    # putting the center on the right: clockwise, negative curvature.
    assert arc_for([6.2, 22.8]).curvature_at(0.0) < 0
    assert arc_for([6.8, 21.0]).curvature_at(0.0) > 0


def test_collinear_arc_points_rejected():
    req = MatricesRequest.model_validate(_payload(
        {"kind": "line", "start": [2.0, 20.0], "end": [2.0, 40.0]},
        primary_path={"kind": "arc", "start": [4.0, 20.0], "mid": [6.5, 22.0], "end": [9.0, 24.0]},
    ))
    with pytest.raises(ValueError, match="collinear"):
        coil_from_schema(req.coil)


def test_spline_secondary_with_graded_turns_converts():
    req = MatricesRequest.model_validate(_payload(
        {"kind": "spline", "points": [[2.0, 10.0], [2.6, 20.0], [2.0, 30.0]]},
        secondary_turns={"kind": "graded", "points": [[0.0, 0.0], [0.3, 60.0], [1.0, 100.0]]},
    ))
    coil = coil_from_schema(req.coil)
    assert isinstance(coil.secondary.curve, CatmullRomSpline)
    assert isinstance(coil.secondary.turns, GradedTurns)
    assert coil.secondary.total_turns == 100
    # Graded profile: 60 turns by 30% of the arc length
    L = coil.secondary.curve.length
    assert coil.secondary.turn_fxn(0.3 * L) == pytest.approx(60.0)


def test_graded_turns_validation_rejects_bad_points():
    for bad in (
        [[0.1, 0.0], [1.0, 10.0]],          # does not start at u=0
        [[0.0, 5.0], [1.0, 10.0]],          # does not start at n=0
        [[0.0, 0.0], [0.8, 10.0]],          # does not end at u=1
        [[0.0, 0.0], [0.5, 10.0], [1.0, 5.0]],  # non-monotone turns
    ):
        req = MatricesRequest.model_validate(_payload(
            {"kind": "line", "start": [2.0, 20.0], "end": [2.0, 40.0]},
            secondary_turns={"kind": "graded", "points": bad},
        ))
        with pytest.raises(ValueError):
            coil_from_schema(req.coil)


def test_self_approaching_spline_rejected():
    """A hairpin path whose conductor envelope would overlap itself."""
    req = MatricesRequest.model_validate(_payload(
        {"kind": "spline", "points": [[2.0, 10.0], [6.0, 10.2], [6.2, 10.4], [2.0, 10.3]]},
        secondary_turns={"kind": "uniform", "total_turns": 50},
    ))
    req.coil.secondary.wire_dia = 0.4
    with pytest.raises(ValueError, match="approaches itself"):
        coil_from_schema(req.coil)


def test_piecewise_primary_converts_and_solves():
    """Line-into-arc QCW-style primary through the full API path."""
    from app.geometry import C1PiecewiseCurve

    req = MatricesRequest.model_validate(_payload(
        {"kind": "line", "start": [2.0, 20.0], "end": [2.0, 40.0]},
        primary_path={
            "kind": "piecewise",
            "first": {"kind": "line", "start": [4.0, 20.0], "end": [4.0, 23.0]},
            "rest": [
                {"kind": "arc-from", "end": [7.0, 26.0]},
                {"kind": "line-from", "length": 1.5},
                {"kind": "spline-from", "points": [[10.0, 27.0]]},
            ],
        },
    ))
    coil = coil_from_schema(req.coil)
    chain = coil.primary.curve
    assert isinstance(chain, C1PiecewiseCurve)
    assert len(chain.pieces) == 4
    assert chain.point_at(0.0) == pytest.approx((4.0, 20.0))
    assert len(coil.primary.ring_centers()) == 9


def test_piecewise_secondary_with_graded_turns():
    req = MatricesRequest.model_validate(_payload(
        {
            "kind": "piecewise",
            "first": {"kind": "line", "start": [2.0, 10.0], "end": [2.0, 25.0]},
            "rest": [{"kind": "arc-from", "end": [5.0, 28.0]}],
        },
        secondary_turns={"kind": "graded", "points": [[0.0, 0.0], [0.6, 80.0], [1.0, 100.0]]},
    ))
    coil = coil_from_schema(req.coil)
    L = coil.secondary.curve.length
    assert coil.secondary.turn_fxn(0.6 * L) == pytest.approx(80.0)


def test_piecewise_rejects_degenerate_continuation():
    req = MatricesRequest.model_validate(_payload(
        {"kind": "line", "start": [2.0, 20.0], "end": [2.0, 40.0]},
        primary_path={
            "kind": "piecewise",
            "first": {"kind": "line", "start": [4.0, 20.0], "end": [4.0, 23.0]},
            "rest": [{"kind": "arc-from", "end": [4.0, 30.0]}],  # straight ahead
        },
    ))
    with pytest.raises(ValueError, match="line-from"):
        coil_from_schema(req.coil)


def test_piecewise_nesting_unrepresentable():
    """The schema forbids piecewise-in-piecewise by type."""
    with pytest.raises(ValidationError):
        MatricesRequest.model_validate(_payload(
            {"kind": "line", "start": [2.0, 20.0], "end": [2.0, 40.0]},
            primary_path={
                "kind": "piecewise",
                "first": {
                    "kind": "piecewise",
                    "first": {"kind": "line", "start": [4.0, 20.0], "end": [4.0, 23.0]},
                    "rest": [{"kind": "line-from", "length": 1.0}],
                },
                "rest": [{"kind": "line-from", "length": 1.0}],
            },
        ))


def test_piecewise_segment_cap():
    with pytest.raises(ValidationError):
        MatricesRequest.model_validate(_payload(
            {"kind": "line", "start": [2.0, 20.0], "end": [2.0, 40.0]},
            primary_path={
                "kind": "piecewise",
                "first": {"kind": "line", "start": [4.0, 20.0], "end": [4.0, 23.0]},
                "rest": [{"kind": "line-from", "length": 0.5}] * 25,
            },
        ))
