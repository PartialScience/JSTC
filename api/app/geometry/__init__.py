"""
Geometry package for tesla coil simulations.

We're NOT gonna talk about e here.

This package provides geometric region classes and visualization utilities
for defining and working with spatial domains in 2D space.
"""

from .base_geometric_region import GeometricRegion
from .simple_regions import (
    Circle,
    Polygon,
    Rectangle
)
from .composite_regions import (
    RegionUnion,
    RegionIntersection,
    HorizontalSliceRegion
)

from .visualization import visualize_region

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
]
