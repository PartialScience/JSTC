"""
Pydantic schemas for geometric shapes in API requests.

These mirror the domain geometry classes (app.geometry) as a discriminated
union keyed on ``kind`` - the shape that produces the cleanest tagged-union
types in a generated TypeScript client.
"""
from typing import List, Literal, Tuple, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated


class CircleSchema(BaseModel):
    """A circular (r, z) cross section - a toroid when revolved off-axis."""
    kind: Literal["circle"] = "circle"
    center: Tuple[float, float] = Field(..., description="Center point (r, z)")
    radius: float = Field(..., gt=0, description="Radius")


class RectangleSchema(BaseModel):
    """A rectangular region defined by exactly 4 vertices."""
    kind: Literal["rectangle"] = "rectangle"
    vertices: List[Tuple[float, float]] = Field(
        ..., min_length=4, max_length=4,
        description="Four (r, z) vertices, in boundary order",
    )


class PolygonSchema(BaseModel):
    """A general polygon defined by >= 3 vertices."""
    kind: Literal["polygon"] = "polygon"
    vertices: List[Tuple[float, float]] = Field(
        ..., min_length=3, description="(r, z) vertices, in boundary order",
    )


GeometrySchema = Annotated[
    Union[CircleSchema, RectangleSchema, PolygonSchema],
    Field(discriminator="kind"),
]
