"""
Geometric region classes for defining spatial domains.

Provides base and derived region types including simple shapes
(circles, polygons, rectangles) and composite regions (unions,
intersections, horizontal slices).
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

__all__ = [
    'GeometricRegion',
    'Circle',
    'Polygon',
    'Rectangle',
    'RegionUnion',
    'RegionIntersection',
    'HorizontalSliceRegion',
]
