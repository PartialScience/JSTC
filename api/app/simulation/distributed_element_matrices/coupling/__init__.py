"""
Primary-secondary magnetic coupling solvers.

The coupling vector m (m_k = mutual inductance between the primary and
virtual-conductor segment k of the secondary) is the new quantity the
coupled primary-secondary model introduces: it borders the secondary's
L matrix into the full inductance matrix [[L, m], [m^T, L_p]] of the
combined system.
"""

from .base import MutualCouplingSolver
from .coaxial_ring_solver import (
    CoaxialRingMutualCouplingSolver,
    primary_geometric_self_inductance,
    primary_voltage_profile,
)

__all__ = [
    "MutualCouplingSolver",
    "CoaxialRingMutualCouplingSolver",
    "primary_geometric_self_inductance",
    "primary_voltage_profile",
]
