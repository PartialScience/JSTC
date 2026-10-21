"""
Cross-language contract for the primary's ring spacing.

The 2-D editor and the 3-D viewer both draw the primary as one ring per
turn. Those rings MUST land exactly where the physics places them -
``PrimarySpec.ring_centers()`` - because that same spacing feeds the
coupling vector, the primary self-inductance, and the electrostatic
grounded-ring solve. If the drawing and the math ever disagree, the
picture is lying about what was solved.

The frontend can't call this Python, so the two sides are pinned to a
shared golden fixture instead:

  * this test regenerates the fixture from ``ring_centers()`` and asserts
    the committed copy still matches (guards the fixture against solver
    drift), and
  * ``frontend/src/editor/primaryRings.test.ts`` loads the SAME file and
    asserts its TypeScript ``primaryRingCenters()`` reproduces it.

Each case is expressed as API-schema fragments (path + turn profile), the
exact shapes both sides consume, and spans every path kind (line, arc,
spline) and both turn-profile kinds (uniform, graded).

If ``ring_centers()`` changes, this test fails until the fixture is
regenerated (``JSTC_REGEN_RING_FIXTURE=1 pytest``); the regenerated
fixture then fails the TS test until the TypeScript is updated to match.
Neither side can drift silently.
"""
import json
import os
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from app.converters.coil_converters import (
    path_from_schema,
    turn_distribution_from_schema,
)
from app.geometry import CircularCrossSection
from app.models.coil_models import CurvePrimarySpec
from app.models.materials import Material
from app.schemas.component_schemas import TurnProfileSchema
from app.schemas.geometry_schemas import PathSchema

# Repo-root-relative path to the fixture the frontend test imports.
# api/tests/models/<this file>  ->  parents[3] == repo root.
FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "frontend"
    / "src"
    / "editor"
    / "__fixtures__"
    / "primaryRings.json"
)

# Input cases spanning every path kind and turn-profile kind the editor can
# build: flat spirals, helices, saucers, reversed direction, single /
# fractional / many turns, both arc bend directions, splines, and graded
# density. Each case is the exact API-schema fragment pair the frontend
# holds in its coil model.
CASES = [
    {"name": "javatc-flat-spiral",
     "path": {"kind": "line", "start": [3.75, 23.0], "end": [7.969, 23.0]},
     "turn_fxn": {"kind": "uniform", "total_turns": 8.438}},
    {"name": "integer-flat-spiral",
     "path": {"kind": "line", "start": [3.0, 10.0], "end": [7.0, 10.0]},
     "turn_fxn": {"kind": "uniform", "total_turns": 8.0}},
    {"name": "single-turn",
     "path": {"kind": "line", "start": [2.0, 5.0], "end": [3.0, 5.0]},
     "turn_fxn": {"kind": "uniform", "total_turns": 1.0}},
    {"name": "vertical-helix",
     "path": {"kind": "line", "start": [4.0, 20.0], "end": [4.0, 26.0]},
     "turn_fxn": {"kind": "uniform", "total_turns": 6.0}},
    {"name": "slanted-saucer",
     "path": {"kind": "line", "start": [3.0, 12.0], "end": [9.0, 18.0]},
     "turn_fxn": {"kind": "uniform", "total_turns": 10.0}},
    {"name": "reversed-direction",
     "path": {"kind": "line", "start": [8.0, 30.0], "end": [3.0, 30.0]},
     "turn_fxn": {"kind": "uniform", "total_turns": 5.0}},
    {"name": "many-turns",
     "path": {"kind": "line", "start": [2.5, 0.0], "end": [12.5, 0.0]},
     "turn_fxn": {"kind": "uniform", "total_turns": 24.0}},
    {"name": "fractional-few",
     "path": {"kind": "line", "start": [1.0, 1.0], "end": [4.0, 2.0]},
     "turn_fxn": {"kind": "uniform", "total_turns": 3.75}},
    {"name": "arc-bend-left",
     "path": {"kind": "arc", "start": [4.0, 20.0], "end": [9.0, 24.0], "radius": 6.0},
     "turn_fxn": {"kind": "uniform", "total_turns": 8.5}},
    {"name": "arc-bend-right",
     "path": {"kind": "arc", "start": [4.0, 20.0], "end": [9.0, 24.0], "radius": -6.0},
     "turn_fxn": {"kind": "uniform", "total_turns": 7.0}},
    {"name": "spline-qcw-ramp",
     "path": {"kind": "spline", "points": [[3.5, 18.0], [5.5, 19.0], [7.0, 21.5], [7.5, 24.0]]},
     "turn_fxn": {"kind": "uniform", "total_turns": 12.0}},
    {"name": "graded-flat-spiral",
     "path": {"kind": "line", "start": [3.0, 10.0], "end": [9.0, 10.0]},
     "turn_fxn": {"kind": "graded", "points": [[0.0, 0.0], [0.3, 6.0], [1.0, 10.0]]}},
    {"name": "graded-spline",
     "path": {"kind": "spline", "points": [[3.5, 18.0], [5.5, 19.0], [7.5, 22.0]]},
     "turn_fxn": {"kind": "graded", "points": [[0.0, 0.0], [0.5, 2.0], [1.0, 9.5]]}},
]

_PATH_ADAPTER = TypeAdapter(PathSchema)
_TURNS_ADAPTER = TypeAdapter(TurnProfileSchema)


def _spec(case: dict) -> CurvePrimarySpec:
    return CurvePrimarySpec(
        material=Material.COPPER,
        turns=turn_distribution_from_schema(_TURNS_ADAPTER.validate_python(case["turn_fxn"])),
        cross_section=CircularCrossSection(diameter=0.25),
        path=path_from_schema(_PATH_ADAPTER.validate_python(case["path"])),
    )


def _expected_fixture() -> dict:
    return {
        "_comment": (
            "Golden primary ring centers from PrimarySpec.ring_centers(). "
            "Generated by api/tests/models/test_primary_ring_fixture.py "
            "(JSTC_REGEN_RING_FIXTURE=1). Consumed by that test and by "
            "frontend/src/editor/primaryRings.test.ts to keep the UI ring "
            "spacing identical to the solver's."
        ),
        "cases": [
            {
                **case,
                "ring_centers": [[r, z] for r, z in _spec(case).ring_centers()],
                "ring_fractions": list(_spec(case).ring_turn_fractions()),
            }
            for case in CASES
        ],
    }


def test_ring_fixture_matches_solver():
    fixture = _expected_fixture()

    if os.environ.get("JSTC_REGEN_RING_FIXTURE"):
        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_PATH.write_text(json.dumps(fixture, indent=2) + "\n")

    assert FIXTURE_PATH.exists(), (
        f"Missing fixture {FIXTURE_PATH}. Regenerate with "
        f"JSTC_REGEN_RING_FIXTURE=1 pytest."
    )
    committed = json.loads(FIXTURE_PATH.read_text())

    assert [c["name"] for c in committed["cases"]] == [c["name"] for c in CASES]
    for expected, actual in zip(fixture["cases"], committed["cases"]):
        assert expected["name"] == actual["name"]
        exp_centers = expected["ring_centers"]
        act_centers = actual["ring_centers"]
        assert len(exp_centers) == len(act_centers), expected["name"]
        for (er, ez), (ar, az) in zip(exp_centers, act_centers):
            assert er == pytest.approx(ar, abs=1e-9, rel=1e-9), expected["name"]
            assert ez == pytest.approx(az, abs=1e-9, rel=1e-9), expected["name"]
        assert expected["ring_fractions"] == pytest.approx(actual["ring_fractions"])
