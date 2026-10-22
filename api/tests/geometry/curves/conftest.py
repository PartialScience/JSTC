"""
Shared fixtures for curve tests.

Fixture dependency graph::

    curve_instance            (parameterized: CURVE_INSTANCES registry)
        │                      → every concrete ParametricCurve instance
        ▼
    [base class tests]        (test_parametric_curve.py)

    unit_speed_instance       (parameterized: UNIT_SPEED_INSTANCES registry)
        │                      → every concrete UnitSpeedCurve instance
        ▼
    [unit-speed contract]     (test_unit_speed_contract.py)

To add a new concrete curve → register instances in its own test file and
add them to the registries below. A winding-capable curve goes in BOTH
lists; a non-unit-speed curve (only OffsetCurve today) goes in
CURVE_INSTANCES alone.
"""
import pytest

from app.geometry.curves.catmull_rom import CatmullRomSpline
from app.geometry.curves.piecewise import C1PiecewiseCurve
from app.geometry.curves.circular_arc import CircularArc
from app.geometry.curves.line_segment import LineSegment
from app.geometry.curves.offset_curve import OffsetCurve
from app.geometry.curves.sub_curve import SubCurve
from tests.geometry.curves.test_line_segment import LINE_SEGMENT_INSTANCES
from tests.geometry.curves.test_circular_arc import ARC_INSTANCES
from tests.geometry.curves.test_offset_curve import OFFSET_CURVE_INSTANCES
from tests.geometry.curves.test_catmull_rom import SPLINE_INSTANCES
from tests.geometry.curves.test_piecewise import (
    CLAMPED_SPLINE_INSTANCES,
    PIECEWISE_INSTANCES,
)


# SubCurve instances: sub-ranges of each kind of parent curve.
SUB_CURVE_INSTANCES = [
    pytest.param(
        SubCurve(LineSegment((0.0, 0.0), (0.0, 10.0)), 2.0, 7.5),
        id="SubCurve-of-line",
    ),
    pytest.param(
        SubCurve(CircularArc((0.0, 0.0), 2.0, 0.0, 3.14159265), 1.0, 5.0),
        id="SubCurve-of-arc",
    ),
    pytest.param(
        SubCurve(
            CatmullRomSpline(points=((0.0, 0.0), (1.0, 2.0), (3.0, 3.0), (5.0, 1.0))),
            0.5,
            4.5,
        ),
        id="SubCurve-of-spline",
    ),
]


# ---------------------------------------------------------------------------
# Aggregate registry of all concrete ParametricCurve instances.
# ---------------------------------------------------------------------------

UNIT_SPEED_INSTANCES = [
    *LINE_SEGMENT_INSTANCES,
    *ARC_INSTANCES,
    *SPLINE_INSTANCES,
    *CLAMPED_SPLINE_INSTANCES,
    *SUB_CURVE_INSTANCES,
    *PIECEWISE_INSTANCES,
    # ← register future winding-capable curve instance lists here
]

CURVE_INSTANCES = [
    *UNIT_SPEED_INSTANCES,
    *OFFSET_CURVE_INSTANCES,
    # ← register future non-unit-speed curve instance lists here
]


# ---------------------------------------------------------------------------
# Registry of concrete ParametricCurve *classes* (one entry per type).
# Used for tests that only need to run once per class, not per instance.
# ---------------------------------------------------------------------------

CURVE_CLASSES = [
    pytest.param(LineSegment, id="LineSegment"),
    pytest.param(CircularArc, id="CircularArc"),
    pytest.param(CatmullRomSpline, id="CatmullRomSpline"),
    pytest.param(SubCurve, id="SubCurve"),
    pytest.param(C1PiecewiseCurve, id="C1PiecewiseCurve"),
    pytest.param(OffsetCurve, id="OffsetCurve"),
    # ← register future curve classes here
]


# ---------------------------------------------------------------------------
# Parameterized curve fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(params=CURVE_INSTANCES)
def curve_instance(request):
    """Yield one concrete ParametricCurve instance at a time."""
    return request.param


@pytest.fixture(params=UNIT_SPEED_INSTANCES)
def unit_speed_instance(request):
    """Yield one concrete UnitSpeedCurve instance at a time - the registry
    the unit-speed contract suite runs against."""
    return request.param


@pytest.fixture(params=CURVE_CLASSES)
def curve_class(request):
    """Yield one concrete ParametricCurve *class* at a time."""
    return request.param
