"""
Pydantic schemas for tesla coil components and full coil configuration.
"""
from pydantic import BaseModel, Field
from enum import Enum
from .geometry_schemas import GeometrySchema, RectangleSchema


class BoundaryConditionTypeSchema(str, Enum):
    """Schema for boundary condition types."""
    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"


class BoundaryConditionSchema(BaseModel):
    """Schema for a boundary condition."""
    bc_type: BoundaryConditionTypeSchema = Field(
        BoundaryConditionTypeSchema.DIRICHLET,
        description="Type of boundary condition (Dirichlet or Neumann)"
    )
    value: float = Field(0.0, description="Value for the boundary condition")


class ToploadSchema(BaseModel):
    """Schema for a topload component."""
    geometry: GeometrySchema = Field(..., description="Geometry of the topload")


class SecondaryConductorSchema(BaseModel):
    """Schema for a secondary conductor component."""
    geometry: RectangleSchema = Field(..., description="Rectangular geometry of the secondary conductor")


class GroundedConductorSchema(BaseModel):
    """Schema for a grounded conductor component."""
    geometry: GeometrySchema = Field(..., description="Geometry of the grounded conductor")


class TeslaCoilSchema(BaseModel):
    """
    Schema for a complete tesla coil configuration.
    
    This represents the JSON structure for API requests.
    """
    secondary: SecondaryConductorSchema = Field(..., description="The secondary conductor component")
    toploads: list[ToploadSchema] | None = Field(None, description="Optional list of topload components")
    grounds: list[GroundedConductorSchema] | None = Field(None, description="Optional list of grounded conductor components")


class SimulatableTeslaCoilSchema(BaseModel):
    """
    Schema for a tesla coil with simulation domain and boundary conditions.
    
    This represents a complete simulation setup.
    """
    r_max: float = Field(..., description="Maximum radial extent of the simulation domain", gt=0)
    z_max: float = Field(..., description="Maximum vertical extent of the simulation domain", gt=0)
    coil: TeslaCoilSchema = Field(..., description="The tesla coil configuration")
    bc_bottom: BoundaryConditionSchema | None = Field(
        None,
        description="Boundary condition for the bottom wall (default: Dirichlet with value 0)"
    )
    bc_top: BoundaryConditionSchema | None = Field(
        None,
        description="Boundary condition for the top wall (default: Dirichlet with value 0)"
    )
    bc_right: BoundaryConditionSchema | None = Field(
        None,
        description="Boundary condition for the right wall (default: Dirichlet with value 0)"
    )

