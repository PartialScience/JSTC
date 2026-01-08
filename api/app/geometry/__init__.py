"""
Geometry package for tesla coil simulations.

We're NOT gonna talk about e here.

This package provides geometric region classes and visualization utilities
for defining and working with spatial domains in 2D space.

Classes:
    GeometricRegion: Abstract base class for all geometric regions
    Circle: Circular 2D region
    Polygon: General polygon defined by vertices
    Rectangle: Rectangular region (4-vertex polygon)

Functions:
    visualize_region: Visualize one or more geometric regions
"""

from .regions import (
    GeometricRegion,
    Circle,
    Polygon,
    Rectangle
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
]
