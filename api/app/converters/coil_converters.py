"""
Converters from coil schemas to domain models.
"""
from app.geometry import (
    CatmullRomSpline,
    CircularArc,
    CircularCrossSection,
    LineSegment,
    RectangularCrossSection,
    UnitSpeedCurve,
)
from app.models.coil_models import (
    CurvePrimarySpec,
    CurveSecondaryConductorSpec,
    GroundedConductorSpec,
    ToploadSpec,
)
from app.models.materials import Material
from app.models.simulation_models import (
    BoundaryCondition,
    BoundaryConditionType,
    SimulatableTeslaCoil,
)
from app.models.turn_profiles import GradedTurns, UniformTurns
from app.schemas.component_schemas import (
    CircularCrossSectionSchema,
    GradedTurnProfileSchema,
    RectangularCrossSectionSchema,
    UniformTurnProfileSchema,
)
from app.schemas.geometry_schemas import (
    ArcPathSchema,
    LinePathSchema,
    SplinePathSchema,
)
from .geometry_converters import geometry_from_schema


_MATERIALS = {"copper": Material.COPPER, "aluminum": Material.ALUMINUM}


def material_from_schema(schema) -> Material:
    return _MATERIALS[schema.value]


def turn_distribution_from_schema(schema):
    if isinstance(schema, UniformTurnProfileSchema):
        return UniformTurns(schema.total_turns)
    if isinstance(schema, GradedTurnProfileSchema):
        return GradedTurns(points=tuple(tuple(p) for p in schema.points))
    raise ValueError(f"Unknown turn profile schema: {type(schema).__name__}")


def path_from_schema(schema) -> UnitSpeedCurve:
    """Build the unit-speed winding centerline a path schema describes."""
    if isinstance(schema, LinePathSchema):
        return LineSegment(tuple(schema.start), tuple(schema.end))
    if isinstance(schema, ArcPathSchema):
        return CircularArc.from_endpoints(
            tuple(schema.start), tuple(schema.end), schema.radius
        )
    if isinstance(schema, SplinePathSchema):
        return CatmullRomSpline(points=tuple(tuple(p) for p in schema.points))
    raise ValueError(f"Unknown path schema: {type(schema).__name__}")


def cross_section_from_schema(schema):
    if isinstance(schema, CircularCrossSectionSchema):
        return CircularCrossSection(diameter=schema.diameter)
    if isinstance(schema, RectangularCrossSectionSchema):
        return RectangularCrossSection(width=schema.width, height=schema.height)
    raise ValueError(f"Unknown cross-section schema: {type(schema).__name__}")


def boundary_condition_from_schema(schema) -> BoundaryCondition:
    if schema is None:
        return BoundaryCondition()
    return BoundaryCondition(
        bc_type=BoundaryConditionType(schema.bc_type.value),
        value=schema.value,
    )


def secondary_from_schema(schema) -> CurveSecondaryConductorSpec:
    return CurveSecondaryConductorSpec(
        material=material_from_schema(schema.material),
        turns=turn_distribution_from_schema(schema.turn_fxn),
        path=path_from_schema(schema.path),
        wire_dia=schema.wire_dia,
    )


def primary_from_schema(schema) -> CurvePrimarySpec:
    return CurvePrimarySpec(
        material=material_from_schema(schema.material),
        turns=turn_distribution_from_schema(schema.turn_fxn),
        cross_section=cross_section_from_schema(schema.cross_section),
        path=path_from_schema(schema.path),
        tank_capacitance=schema.tank_capacitance,
        lead_length=schema.lead_length,
        lead_dia=schema.lead_dia,
    )


def topload_from_schema(schema) -> ToploadSpec:
    return ToploadSpec(
        material=material_from_schema(schema.material),
        shape=geometry_from_schema(schema.shape),
    )


def ground_from_schema(schema) -> GroundedConductorSpec:
    return GroundedConductorSpec(
        material=material_from_schema(schema.material),
        shape=geometry_from_schema(schema.shape),
    )


def coil_from_schema(schema) -> SimulatableTeslaCoil:
    """Convert a SimulatableTeslaCoilSchema to a domain SimulatableTeslaCoil."""
    return SimulatableTeslaCoil(
        secondary=secondary_from_schema(schema.secondary),
        primary=primary_from_schema(schema.primary) if schema.primary else None,
        toploads=tuple(topload_from_schema(t) for t in schema.toploads),
        grounds=tuple(ground_from_schema(g) for g in schema.grounds),
        r_max=schema.r_max,
        z_max=schema.z_max,
        unit_scale=schema.unit_scale,
        discretization_order=schema.discretization_order,
        bc_bottom=boundary_condition_from_schema(schema.bc_bottom),
        bc_top=boundary_condition_from_schema(schema.bc_top),
        bc_right=boundary_condition_from_schema(schema.bc_right),
    )
