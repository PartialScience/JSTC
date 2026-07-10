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
    OffsetRegion
)

from .visualization import visualize_region

from .curves import (
    ParametricCurve,
    LineSegment,
    SubCurve,
    CircularArc,
    OffsetCurve,
)

from .boundary import BoundaryLoop, BoundaryPiece

from .cross_sections import (
    CrossSection,
    CircularCrossSection,
    RectangularCrossSection,
)

__all__ = [
    # Region classes
    'GeometricRegion',
    'Circle',
    'Polygon',
    'Rectangle',
    # Visualization
    'visualize_region',
    'OffsetRegion',
    # Curves
    'ParametricCurve',
    'LineSegment',
    'SubCurve',
    'CircularArc',
    'OffsetCurve',
    # Boundary description
    'BoundaryLoop',
    'BoundaryPiece',
    # Cross-sections
    'CrossSection',
    'CircularCrossSection',
    'RectangularCrossSection',
]
