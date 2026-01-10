"""
Models package for JSTC API
"""

from .coil_models import (
    Topload, SecondaryConductor, GroundedConductor, TeslaCoil,
    BoundaryCondition, BoundaryConditionType, SimulatableTeslaCoil
)

__all__ = [
    'Topload',
    'SecondaryConductor',
    'GroundedConductor',
    'TeslaCoil',
    'BoundaryCondition',
    'BoundaryConditionType',
    'SimulatableTeslaCoil',
]
