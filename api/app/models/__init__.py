"""
Models package for JSTC API
"""

from .coil_models import (
    CoilComponent,
    ToploadSpec,
    GroundedConductorSpec,
    SecondaryConductorSpec,
    TeslaCoilSpec,
)

from .simulation_models import (
    BoundaryConditionType,
    BoundaryCondition,
    SimulatableTeslaCoil,
)

__all__ = [
    # Coil component classes
    'CoilComponent',
    'ToploadSpec',
    'GroundedConductorSpec',
    'SecondaryConductorSpec',
    'TeslaCoilSpec',
    # Simulation domain models
    'BoundaryConditionType',
    'BoundaryCondition',
    'SimulatableTeslaCoil',
]
