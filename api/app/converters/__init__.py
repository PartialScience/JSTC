"""
Converters package for transforming API schemas into domain models.

This package bridges the gap between the API layer (Pydantic schemas)
and the domain layer (geometry and coil classes).
"""
from .geometry_converters import geometry_from_schema, rectangle_from_schema
from .coil_converters import (
    topload_from_schema,
    secondary_from_schema,
    grounded_from_schema,
    coil_from_schema,
    boundary_condition_from_schema,
    simulatable_coil_from_schema
)

__all__ = [
    # Geometry converters
    'geometry_from_schema',
    'rectangle_from_schema',
    # Coil component converters
    'topload_from_schema',
    'secondary_from_schema',
    'grounded_from_schema',
    'coil_from_schema',
    'boundary_condition_from_schema',
    'simulatable_coil_from_schema',
]
