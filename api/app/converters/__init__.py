"""
Converters package: bridge between the API layer (Pydantic schemas) and
the domain/simulation layer.
"""
from .geometry_converters import geometry_from_schema
from .coil_converters import (
    material_from_schema,
    turn_profile_from_schema,
    cross_section_from_schema,
    boundary_condition_from_schema,
    secondary_from_schema,
    primary_from_schema,
    topload_from_schema,
    ground_from_schema,
    coil_from_schema,
)
from .matrix_converters import bundle_to_schema, bundle_from_schema
from .analysis_converters import build_analysis_response

__all__ = [
    "geometry_from_schema",
    "material_from_schema",
    "turn_profile_from_schema",
    "cross_section_from_schema",
    "boundary_condition_from_schema",
    "secondary_from_schema",
    "primary_from_schema",
    "topload_from_schema",
    "ground_from_schema",
    "coil_from_schema",
    "bundle_to_schema",
    "bundle_from_schema",
    "build_analysis_response",
]
