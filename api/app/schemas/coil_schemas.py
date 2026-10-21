"""
Pydantic schemas for a full Tesla coil configuration.

Mirrors the domain models (app.models.coil_models,
app.models.simulation_models). Each winding is a parametric centerline PATH
in the (r, z) plane (line / arc / spline) plus a serializable turn profile.
"""
from typing import List, Optional

from pydantic import BaseModel, Field

from .component_schemas import (
    BoundaryConditionSchema,
    CrossSectionSchema,
    MaterialSchema,
    TurnProfileSchema,
)
from .geometry_schemas import GeometrySchema, PathSchema


class SecondaryConductorSchema(BaseModel):
    """A secondary wound along a parametric (r, z) centerline path."""
    material: MaterialSchema = Field(MaterialSchema.COPPER)
    turn_fxn: TurnProfileSchema = Field(..., description="Turn distribution")
    path: PathSchema = Field(..., description="Winding centerline path")
    wire_dia: float = Field(..., gt=0, description="Wire diameter")


class PrimarySchema(BaseModel):
    """A primary wound along a parametric (r, z) centerline path."""
    material: MaterialSchema = Field(MaterialSchema.COPPER)
    turn_fxn: TurnProfileSchema = Field(..., description="Turn distribution")
    cross_section: CrossSectionSchema = Field(..., description="Conductor cross-section")
    path: PathSchema = Field(..., description="Winding centerline path")
    tank_capacitance: float = Field(0.0, ge=0, description="Tank capacitance (Farads)")
    lead_length: float = Field(0.0, ge=0, description="Connection lead length")
    lead_dia: float = Field(0.0, ge=0, description="Connection lead diameter")


class ToploadSchema(BaseModel):
    material: MaterialSchema = Field(MaterialSchema.ALUMINUM)
    shape: GeometrySchema = Field(..., description="(r, z) cross-section shape")


class GroundedConductorSchema(BaseModel):
    material: MaterialSchema = Field(MaterialSchema.COPPER)
    shape: GeometrySchema = Field(..., description="(r, z) cross-section shape")


class SimulatableTeslaCoilSchema(BaseModel):
    """A complete coil plus its simulation domain and boundary conditions."""
    secondary: SecondaryConductorSchema
    primary: Optional[PrimarySchema] = None
    toploads: List[ToploadSchema] = Field(default_factory=list)
    grounds: List[GroundedConductorSchema] = Field(default_factory=list)

    r_max: float = Field(..., gt=0, description="Radial extent of the domain")
    z_max: float = Field(..., gt=0, description="Vertical extent of the domain")
    unit_scale: float = Field(
        1.0, gt=0,
        description="Meters per geometry unit (e.g. 0.0254 for inches)",
    )
    discretization_order: int = Field(
        30, ge=2, description="Number of virtual conductor segments",
    )

    bc_bottom: Optional[BoundaryConditionSchema] = None
    bc_top: Optional[BoundaryConditionSchema] = None
    bc_right: Optional[BoundaryConditionSchema] = None
