"""
Pydantic schemas for a full Tesla coil configuration.

Mirrors the domain models (app.models.coil_models,
app.models.simulation_models). The secondary and primary are represented
as a straight winding centerline plus a serializable turn profile, matching
LinearSecondaryConductorSpec / LinearPrimarySpec.
"""
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from .component_schemas import (
    BoundaryConditionSchema,
    CrossSectionSchema,
    MaterialSchema,
    TurnProfileSchema,
)
from .geometry_schemas import GeometrySchema


class LinearSecondaryConductorSchema(BaseModel):
    """A secondary wound along a straight (r, z) centerline."""
    material: MaterialSchema = Field(MaterialSchema.COPPER)
    turn_fxn: TurnProfileSchema = Field(..., description="Cumulative turn profile")
    start: Tuple[float, float] = Field(..., description="Winding start (r, z)")
    end: Tuple[float, float] = Field(..., description="Winding end (r, z)")
    wire_dia: float = Field(..., gt=0, description="Wire diameter")


class LinearPrimarySchema(BaseModel):
    """A primary wound along a straight (r, z) centerline."""
    material: MaterialSchema = Field(MaterialSchema.COPPER)
    turn_fxn: TurnProfileSchema = Field(..., description="Cumulative turn profile")
    cross_section: CrossSectionSchema = Field(..., description="Conductor cross-section")
    start: Tuple[float, float] = Field(..., description="Winding start (r, z)")
    end: Tuple[float, float] = Field(..., description="Winding end (r, z)")
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
    secondary: LinearSecondaryConductorSchema
    primary: Optional[LinearPrimarySchema] = None
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
