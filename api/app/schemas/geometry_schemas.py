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


# ---------------------------------------------------------------------------
# Winding paths (centerlines in the (r, z) plane)
# ---------------------------------------------------------------------------

class LinePathSchema(BaseModel):
    """A straight centerline from start to end."""
    kind: Literal["line"] = "line"
    start: Tuple[float, float] = Field(..., description="Path start (r, z)")
    end: Tuple[float, float] = Field(..., description="Path end (r, z)")


class ArcPathSchema(BaseModel):
    """A circular-arc centerline (the minor arc through start and end).

    The SIGN of the radius picks the bend direction: positive bends left of
    the start->end direction (center on the left, CCW), negative bends
    right. |radius| must be at least half the chord length.
    """
    kind: Literal["arc"] = "arc"
    start: Tuple[float, float] = Field(..., description="Path start (r, z)")
    end: Tuple[float, float] = Field(..., description="Path end (r, z)")
    radius: float = Field(
        ..., description="Signed arc radius (positive bends left of travel)"
    )


class SplinePathSchema(BaseModel):
    """An interpolating centripetal Catmull-Rom spline through the points."""
    kind: Literal["spline"] = "spline"
    points: List[Tuple[float, float]] = Field(
        ..., min_length=2, description="Interpolation points (r, z), in order"
    )


PathSchema = Annotated[
    Union[LinePathSchema, ArcPathSchema, SplinePathSchema],
    Field(discriminator="kind"),
]
