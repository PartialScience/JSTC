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
        primary_path={"kind": "arc", "start": [4.0, 20.0], "end": [9.0, 24.0], "radius": 6.0},
    ))
    coil = coil_from_schema(req.coil)
    arc = coil.primary.curve
    assert isinstance(arc, CircularArc)
    assert arc.point_at(arc.t_min) == pytest.approx((4.0, 20.0))
    assert arc.point_at(arc.t_max) == pytest.approx((9.0, 24.0))
    assert arc.curvature_at(0.0) == pytest.approx(1.0 / 6.0)  # positive: bends left
    assert len(coil.primary.ring_centers()) == 9


def test_negative_radius_bends_right():
    req = MatricesRequest.model_validate(_payload(
        {"kind": "line", "start": [2.0, 20.0], "end": [2.0, 40.0]},
        primary_path={"kind": "arc", "start": [4.0, 20.0], "end": [9.0, 24.0], "radius": -6.0},
    ))
    coil = coil_from_schema(req.coil)
    assert coil.primary.curve.curvature_at(0.0) == pytest.approx(-1.0 / 6.0)


def test_arc_radius_below_half_chord_rejected():
    req = MatricesRequest.model_validate(_payload(
        {"kind": "line", "start": [2.0, 20.0], "end": [2.0, 40.0]},
        primary_path={"kind": "arc", "start": [4.0, 20.0], "end": [9.0, 24.0], "radius": 1.0},
    ))
    with pytest.raises(ValueError, match="smaller than half the chord"):
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
