"""
Converters for tesla coil components from API schemas to domain models.
"""
from app.schemas import (
    ToploadSchema,
    SecondaryConductorSchema,
    GroundedConductorSchema,
    TeslaCoilSchema,
    BoundaryConditionSchema,
    SimulatableTeslaCoilSchema
)
from app.models.coil_models import (
    Topload,
    SecondaryConductor,
    GroundedConductor,
    TeslaCoilGeometry,
    BoundaryCondition,
    BoundaryConditionType,
    SimulatableTeslaCoil
)
from .geometry_converters import geometry_from_schema, rectangle_from_schema


def topload_from_schema(schema: ToploadSchema) -> Topload:
    """
    Convert a ToploadSchema to a domain Topload.
    
    Args:
        schema: The API topload schema
        
    Returns:
        A Topload instance with the appropriate geometry
    """
    geometry = geometry_from_schema(schema.geometry)
    return Topload(geometry=geometry)


def secondary_from_schema(schema: SecondaryConductorSchema) -> SecondaryConductor:
    """
    Convert a SecondaryConductorSchema to a domain SecondaryConductor.
    
    Args:
        schema: The API secondary conductor schema
        
    Returns:
        A SecondaryConductor instance
    """
    rectangle = rectangle_from_schema(schema.geometry)
    return SecondaryConductor(rectangle=rectangle)


def grounded_from_schema(schema: GroundedConductorSchema) -> GroundedConductor:
    """
    Convert a GroundedConductorSchema to a domain GroundedConductor.
    
    Args:
        schema: The API grounded conductor schema
        
    Returns:
        A GroundedConductor instance with the appropriate geometry
    """
    geometry = geometry_from_schema(schema.geometry)
    return GroundedConductor(geometry=geometry)


def coil_from_schema(schema: TeslaCoilSchema) -> TeslaCoilGeometry:
    """
    Convert a TeslaCoilSchema to a domain TeslaCoil.
    
    Args:
        schema: The API tesla coil schema
        
    Returns:
        A TeslaCoil instance with converted components
    """
    secondary = secondary_from_schema(schema.secondary)
    toploads = [topload_from_schema(tl) for tl in schema.toploads] if schema.toploads else None
    grounds = [grounded_from_schema(gnd) for gnd in schema.grounds] if schema.grounds else None
    return TeslaCoilGeometry(secondary=secondary, toploads=toploads, grounds=grounds)


def boundary_condition_from_schema(schema: BoundaryConditionSchema | None) -> BoundaryCondition:
    """
    Convert a BoundaryConditionSchema to a domain BoundaryCondition.
    
    Args:
        schema: The API boundary condition schema (None returns default)
        
    Returns:
        A BoundaryCondition instance
    """
    if schema is None:
        return BoundaryCondition()
    
    bc_type = BoundaryConditionType(schema.bc_type.value)
    return BoundaryCondition(bc_type=bc_type, value=schema.value)


def simulatable_coil_from_schema(schema: SimulatableTeslaCoilSchema) -> SimulatableTeslaCoil:
    """
    Convert a SimulatableTeslaCoilSchema to a domain SimulatableTeslaCoil.
    
    Args:
        schema: The API simulatable tesla coil schema
        
    Returns:
        A SimulatableTeslaCoil instance with converted components
    """
    coil = coil_from_schema(schema.coil)
    bc_bottom = boundary_condition_from_schema(schema.bc_bottom)
    bc_top = boundary_condition_from_schema(schema.bc_top)
    bc_right = boundary_condition_from_schema(schema.bc_right)
    
    return SimulatableTeslaCoil(
        r_max=schema.r_max,
        z_max=schema.z_max,
        coil=coil,
        bc_bottom=bc_bottom,
        bc_top=bc_top,
        bc_right=bc_right
    )
