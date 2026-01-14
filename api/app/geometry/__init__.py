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
