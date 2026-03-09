"""
Converters for geometric shapes from API schemas to domain models.
"""
from app.schemas import CircleSchema, PolygonSchema, RectangleSchema, GeometrySchema
from app.geometry import Circle, Polygon, Rectangle, GeometricRegion


def geometry_from_schema(schema: GeometrySchema) -> GeometricRegion:
    """
    Convert a GeometrySchema to a domain GeometricRegion.
    
    Args:
        schema: The API geometry schema
        
    Returns:
        A GeometricRegion instance (Circle, Polygon, or Rectangle)
        
    Raises:
        ValueError: If no geometry type is provided or schema is invalid
    """
    if schema.circle is not None:
        return Circle(
            center=schema.circle.center,
            radius=schema.circle.radius
        )
    elif schema.polygon is not None:
        return Polygon(vertices=schema.polygon.vertices)
    elif schema.rectangle is not None:
        return Rectangle(vertices=schema.rectangle.vertices)
    else:
        raise ValueError("No geometry type provided in schema")


def rectangle_from_schema(schema: RectangleSchema) -> Rectangle:
    """
    Convert a RectangleSchema to a domain Rectangle.
    
    Args:
        schema: The API rectangle schema
        
    Returns:
        A Rectangle instance
    """
    return Rectangle(vertices=schema.vertices)
