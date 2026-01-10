"""
Schemas package for API request/response models.
"""
from .geometry_schemas import CircleSchema, PolygonSchema, RectangleSchema, GeometrySchema
from .coil_schemas import (
    BoundaryConditionTypeSchema,
    BoundaryConditionSchema,
    ToploadSchema,
    SecondaryConductorSchema,
    GroundedConductorSchema,
    TeslaCoilSchema,
    SimulatableTeslaCoilSchema
)

__all__ = [
    'CircleSchema',
    'PolygonSchema', 
    'RectangleSchema',
    'GeometrySchema',
    'BoundaryConditionTypeSchema',
    'BoundaryConditionSchema',
    'ToploadSchema',
    'SecondaryConductorSchema',
    'GroundedConductorSchema',
    'TeslaCoilSchema',
    'SimulatableTeslaCoilSchema',
]

