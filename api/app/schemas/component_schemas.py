"""
Pydantic schemas for the building blocks of a coil: materials, turn
profiles, conductor cross-sections, and boundary conditions.
"""
from enum import Enum
from typing import List, Literal, Tuple, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated


class MaterialSchema(str, Enum):
    """Conductor material (maps to app.models.materials.Material)."""
    COPPER = "copper"
    ALUMINUM = "aluminum"


# ---------------------------------------------------------------------------
# Turn profiles
# ---------------------------------------------------------------------------

class UniformTurnProfileSchema(BaseModel):
    """Evenly wound: constant turn density along the winding path.

    The profile's parameter domain is derived from the winding curve by the
    model itself, so the schema carries no domain fields.
    """
    kind: Literal["uniform"] = "uniform"
    total_turns: float = Field(..., gt=0, description="Total number of turns")


class GradedTurnProfileSchema(BaseModel):
    """Cumulative turn counts at control points along the winding.

    Each point is (u, n): u the normalized position along the path (0 =
    start, 1 = end) and n the cumulative turn count there. The first point
    must be (0, 0), the last must have u = 1 (its n is the total turn
    count), and both coordinates must be strictly increasing. Turns
    interpolate linearly between points (constant pitch within each band).
    """
    kind: Literal["graded"] = "graded"
    points: List[Tuple[float, float]] = Field(
        ..., min_length=2, description="(position u, cumulative turns) control points"
    )


TurnProfileSchema = Annotated[
    Union[UniformTurnProfileSchema, GradedTurnProfileSchema],
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# Conductor cross-sections
# ---------------------------------------------------------------------------

class CircularCrossSectionSchema(BaseModel):
    """Round conductor of a given diameter."""
    kind: Literal["circular"] = "circular"
    diameter: float = Field(..., gt=0)


class RectangularCrossSectionSchema(BaseModel):
    """Rectangular (ribbon/strap) conductor."""
    kind: Literal["rectangular"] = "rectangular"
    width: float = Field(..., gt=0, description="Radial extent")
    height: float = Field(..., gt=0, description="Axial extent")


CrossSectionSchema = Annotated[
    Union[CircularCrossSectionSchema, RectangularCrossSectionSchema],
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# Boundary conditions
# ---------------------------------------------------------------------------

class BoundaryConditionTypeSchema(str, Enum):
    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"


class BoundaryConditionSchema(BaseModel):
    """Boundary condition on a simulation-domain wall."""
    bc_type: BoundaryConditionTypeSchema = Field(
        BoundaryConditionTypeSchema.DIRICHLET,
        description="Dirichlet (fixed potential) or Neumann (zero normal field)",
    )
    value: float = Field(0.0, description="Potential value (Dirichlet only)")
