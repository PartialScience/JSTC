"""
Converters from geometry schemas to domain GeometricRegion objects.
"""
from app.geometry import Circle, GeometricRegion, Polygon, Rectangle
from app.schemas.geometry_schemas import (
    CircleSchema,
    PolygonSchema,
    RectangleSchema,
)


def geometry_from_schema(schema) -> GeometricRegion:
    """Convert a GeometrySchema member to a domain GeometricRegion."""
    if isinstance(schema, CircleSchema):
        return Circle(center=tuple(schema.center), radius=schema.radius)
    if isinstance(schema, RectangleSchema):
        return Rectangle(vertices=tuple(tuple(v) for v in schema.vertices))
    if isinstance(schema, PolygonSchema):
        return Polygon(vertices=tuple(tuple(v) for v in schema.vertices))
    raise ValueError(f"Unknown geometry schema: {type(schema).__name__}")
