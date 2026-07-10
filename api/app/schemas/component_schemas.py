"""
Pydantic schemas for the building blocks of a coil: materials, turn
profiles, conductor cross-sections, and boundary conditions.
"""
from enum import Enum
from typing import Literal, Union

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
    """Evenly wound: turns ramp linearly in the curve parameter."""
    kind: Literal["uniform"] = "uniform"
    total_turns: float = Field(..., gt=0, description="Total number of turns")
    t_min: float = Field(0.0, description="Curve parameter at the start")
    t_max: float = Field(1.0, description="Curve parameter at the end")


# A union of one member is still written as an Annotated discriminated union
# so adding future profile kinds (e.g. density-graded) is a one-line change
# and the generated TS type is already a tagged union.
TurnProfileSchema = Annotated[
    Union[UniformTurnProfileSchema,],
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
