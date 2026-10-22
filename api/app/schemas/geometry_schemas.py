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
    """A circular-arc centerline: the unique arc from ``start`` to ``end``
    passing through ``mid``.

    Three points on the arc (in traversal order) determine everything with
    no sign conventions: the circle, the bend direction, and whether the
    minor or major arc is taken. The points must not be collinear (a
    straight centerline is a line path).
    """
    kind: Literal["arc"] = "arc"
    start: Tuple[float, float] = Field(..., description="Path start (r, z)")
    mid: Tuple[float, float] = Field(
        ..., description="A point the arc passes through, between start and end"
    )
    end: Tuple[float, float] = Field(..., description="Path end (r, z)")


class SplinePathSchema(BaseModel):
    """An interpolating centripetal Catmull-Rom spline through the points."""
    kind: Literal["spline"] = "spline"
    points: List[Tuple[float, float]] = Field(
        ..., min_length=2, description="Interpolation points (r, z), in order"
    )


# The non-piecewise path kinds - also the only kinds allowed as the FIRST
# segment of a piecewise path (nesting is forbidden by construction).
SimplePathSchema = Annotated[
    Union[LinePathSchema, ArcPathSchema, SplinePathSchema],
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# Piecewise continuations: each carries ONLY its free parameters - the start
# point and start tangent are inherited from the previous segment, so
# tangent continuity holds by construction (see geometry/curves/continuations).
# ---------------------------------------------------------------------------

class LineFromSchema(BaseModel):
    """A straight segment continuing along the inherited tangent."""
    kind: Literal["line-from"] = "line-from"
    length: float = Field(..., gt=0, description="Segment length (the only free DOF)")


class ArcFromSchema(BaseModel):
    """An arc tangent to the inherited direction, ending at ``end``.

    The endpoint is the only free input; the tangent circle through it is
    unique (closed form), with sweeps beyond a semicircle included. An
    endpoint on the tangent line is rejected (straight ahead: use
    line-from; behind: no tangent circle exists).
    """
    kind: Literal["arc-from"] = "arc-from"
    end: Tuple[float, float] = Field(..., description="Arc endpoint (r, z)")


class SplineFromSchema(BaseModel):
    """A Catmull-Rom segment with its start tangent clamped to the
    inherited direction, interpolating the given points."""
    kind: Literal["spline-from"] = "spline-from"
    points: List[Tuple[float, float]] = Field(
        ..., min_length=1, description="Interpolation points (r, z), in order"
    )


ContinuationSchema = Annotated[
    Union[LineFromSchema, ArcFromSchema, SplineFromSchema],
    Field(discriminator="kind"),
]


class PiecewisePathSchema(BaseModel):
    """A tangent-continuous chain: a full first segment plus continuations
    that each inherit their start point and tangent from the previous one.

    The reduced continuation forms make a kinked chain unrepresentable -
    continuity is a property of the schema, not a validation afterthought.
    """
    kind: Literal["piecewise"] = "piecewise"
    first: SimplePathSchema = Field(..., description="The first segment (full description)")
    rest: List[ContinuationSchema] = Field(
        ...,
        min_length=1,
        # 20 segments total is far beyond any physical winding; the cap keeps
        # pairwise validation work (tube self-approach) bounded.
        max_length=19,
        description="Continuation segments, each built from the previous end",
    )


PathSchema = Annotated[
    Union[LinePathSchema, ArcPathSchema, SplinePathSchema, PiecewisePathSchema],
    Field(discriminator="kind"),
]
