"""
Geometry package for tesla coil simulations.

We're NOT gonna talk about e here.

This package provides geometric region classes and visualization utilities
for defining and working with spatial domains in 2D space.
"""

from .regions import (
    GeometricRegion,
    Circle,
    Polygon,
    Rectangle,
    RegionUnion,
    RegionIntersection,
    HorizontalSliceRegion,
    OffsetRegion
)

from .visualization import visualize_region

from .curves import (
    ParametricCurve,
    LineSegment,
    SubCurve,
)   

__all__ = [
    # Region classes
    'GeometricRegion',
    'Circle',
    'Polygon',
    'Rectangle',
    # Visualization
    'visualize_region',
    'RegionUnion',
    'RegionIntersection',
    'HorizontalSliceRegion',
    'OffsetRegion',
    # Curves
    'ParametricCurve',
    'LineSegment',
    'SubCurve',
]
