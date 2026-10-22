"""
Geometric definitions for spacial curves
"""

from .base import ParametricCurve, UnitSpeedCurve
from .line_segment import LineSegment
from .sub_curve import SubCurve
from .circular_arc import CircularArc
from .offset_curve import OffsetCurve
from .catmull_rom import CatmullRomSpline
from .continuations import (
    ArcContinuation,
    CurveContinuation,
    LineContinuation,
    SplineContinuation,
)
from .piecewise import C1PiecewiseCurve

__all__ = [
    'ParametricCurve',
    'UnitSpeedCurve',
    'LineSegment',
    'SubCurve',
    'CircularArc',
    'OffsetCurve',
    'CatmullRomSpline',
    'CurveContinuation',
    'LineContinuation',
    'ArcContinuation',
    'SplineContinuation',
    'C1PiecewiseCurve',
]
