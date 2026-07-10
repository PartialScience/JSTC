"""
Geometric region classes for defining spatial domains.

Provides base and derived region types including simple shapes
(circles, polygons, rectangles) and offset regions around curves.
"""

from .base_geometric_region import GeometricRegion
from .simple_regions import (
    Circle,
    Polygon,
    Rectangle
)

from .offset_regions import OffsetRegion

__all__ = [
    'GeometricRegion',
    'Circle',
    'Polygon',
    'Rectangle',
    'OffsetRegion',
]
