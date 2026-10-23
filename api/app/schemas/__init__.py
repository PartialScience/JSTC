"""
Schemas package for API request/response models.
"""
from .geometry_schemas import (
    CircleSchema,
    RectangleSchema,
    PolygonSchema,
    GeometrySchema,
)
from .component_schemas import (
    MaterialSchema,
    UniformTurnProfileSchema,
    TurnProfileSchema,
    CircularCrossSectionSchema,
    RectangularCrossSectionSchema,
    CrossSectionSchema,
    BoundaryConditionTypeSchema,
    BoundaryConditionSchema,
)
from .coil_schemas import (
    SecondaryConductorSchema,
    PrimarySchema,
    ToploadSchema,
    GroundedConductorSchema,
    SimulatableTeslaCoilSchema,
)
from .matrix_schemas import MatrixBundleSchema
from .analysis_schemas import (
    MatricesRequest,
    AnalyzeRequest,
    SecondaryOutputs,
    EigenModesOutputs,
    PrimaryOutputs,
    CouplingOutputs,
    CoupledOutputs,
    AnalysisResponse,
    ImpedanceRequest,
    ImpedancePoint,
    ImpedanceResponse,
    DriveRequest,
    DriveResponse,
    SpiceRequest,
    SpiceResponse,
    FieldRequest,
    FieldResponse,
)

__all__ = [
    # Geometry
    "CircleSchema",
    "RectangleSchema",
    "PolygonSchema",
    "GeometrySchema",
    # Components
    "MaterialSchema",
    "UniformTurnProfileSchema",
    "TurnProfileSchema",
    "CircularCrossSectionSchema",
    "RectangularCrossSectionSchema",
    "CrossSectionSchema",
    "BoundaryConditionTypeSchema",
    "BoundaryConditionSchema",
    # Coil
    "SecondaryConductorSchema",
    "PrimarySchema",
    "ToploadSchema",
    "GroundedConductorSchema",
    "SimulatableTeslaCoilSchema",
    # Matrices
    "MatrixBundleSchema",
    # Analysis
    "MatricesRequest",
    "AnalyzeRequest",
    "SecondaryOutputs",
    "EigenModesOutputs",
    "PrimaryOutputs",
    "CouplingOutputs",
    "CoupledOutputs",
    "AnalysisResponse",
    "ImpedanceRequest",
    "ImpedancePoint",
    "ImpedanceResponse",
    "DriveRequest",
    "DriveResponse",
    "SpiceRequest",
    "SpiceResponse",
    "FieldRequest",
    "FieldResponse",
]
