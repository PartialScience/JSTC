"""
Shared fixtures for curve tests.

Fixture dependency graph::

    curve_instance       (parameterized: CURVE_INSTANCES registry)
        │                 → ParametricCurve concrete instance
        │
        ▼
    [base class tests]   (tests/geometry/curves/test_parametric_curve.py)

To add a new concrete curve → register instances in the test file for that
curve (e.g. test_line_segment.py) and add them to the CURVE_INSTANCES list
in this file.
"""
import pytest

from app.geometry.curves.circular_arc import CircularArc
from app.geometry.curves.line_segment import LineSegment
from app.geometry.curves.offset_curve import OffsetCurve
from tests.geometry.curves.test_line_segment import LINE_SEGMENT_INSTANCES
from tests.geometry.curves.test_circular_arc import ARC_INSTANCES
from tests.geometry.curves.test_offset_curve import OFFSET_CURVE_INSTANCES


# ---------------------------------------------------------------------------
# Aggregate registry of all concrete ParametricCurve instances.
# Import and extend this list as new curve types are added.
# ---------------------------------------------------------------------------

CURVE_INSTANCES = [
    *LINE_SEGMENT_INSTANCES,
    *ARC_INSTANCES,
    *OFFSET_CURVE_INSTANCES,
    # ← register future curve instance lists here
]


# ---------------------------------------------------------------------------
# Registry of concrete ParametricCurve *classes* (one entry per type).
# Used for tests that only need to run once per class, not per instance.
# ---------------------------------------------------------------------------

CURVE_CLASSES = [
    pytest.param(LineSegment, id="LineSegment"),
    pytest.param(CircularArc, id="CircularArc"),
    pytest.param(OffsetCurve, id="OffsetCurve"),
    # ← register future curve classes here
]


# ---------------------------------------------------------------------------
# Parameterized curve fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(params=CURVE_INSTANCES)
def curve_instance(request):
    """
    Yield one concrete ParametricCurve instance at a time.

    Every entry in CURVE_INSTANCES is tested against the universal
    ParametricCurve property tests.
    """
    return request.param


@pytest.fixture(params=CURVE_CLASSES)
def curve_class(request):
    """
    Yield one concrete ParametricCurve *class* at a time.

    Used for ABC-conformance tests that only need to run once per
    concrete type rather than once per instance.
    """
    return request.param
