"""
Pydantic schemas for geometric shapes in API requests/responses.

These schemas represent the JSON structure for geometry data,
separate from the domain geometry classes.
"""
from typing import List, Union, Literal
from pydantic import BaseModel, Field


class CircleSchema(BaseModel):
    """Schema for a circle geometry."""
    center: List[float] = Field(..., description="Center point [x, y]", min_length=2, max_length=2)
    radius: float = Field(..., description="Radius of the circle", gt=0)


class PolygonSchema(BaseModel):
    """Schema for a polygon geometry."""
    vertices: List[List[float]] = Field(
        ..., 
        description="List of vertices, each as [x, y]",
        min_length=3
    )


class RectangleSchema(BaseModel):
    """Schema for a rectangle geometry."""
    vertices: List[List[float]] = Field(
        ..., 
        description="List of 4 vertices defining the rectangle, each as [x, y]",
        min_length=4,
        max_length=4
    )


class GeometrySchema(BaseModel):
    """
    Schema for any geometric shape.
    
    Uses a discriminated union to represent different shape types.
    Exactly one of the shape fields must be provided.
    """
    circle: CircleSchema | None = Field(None, description="Circle geometry")
    polygon: PolygonSchema | None = Field(None, description="Polygon geometry")
    rectangle: RectangleSchema | None = Field(None, description="Rectangle geometry")
    
    def model_post_init(self, __context) -> None:
        """Validate that exactly one geometry type is provided."""
        shapes_provided = sum([
            self.circle is not None,
            self.polygon is not None,
            self.rectangle is not None
        ])
        
        if shapes_provided != 1:
            raise ValueError("Exactly one geometry type must be provided")
