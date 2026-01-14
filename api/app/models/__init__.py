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
    TeslaCoilSimulation,
)

__all__ = [
    # Coil component classes
    'CoilComponent',
    'ToploadSpec',
    'GroundedConductorSpec',
    'SecondaryConductorSpec',
    'TeslaCoilSpec',
    # Simulation classes
    'BoundaryConditionType',
    'BoundaryCondition',
    'SimulatableTeslaCoil',
    'TeslaCoilSimulation',
]
