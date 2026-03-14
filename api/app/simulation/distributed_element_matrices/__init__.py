"""
Distributed element matrices for discretized Tesla coil analysis.

When a continuous coil structure is discretized into N virtual conductor segments,
the electromagnetic coupling between segments is captured by distributed element
matrices:

- **Capacitance (C)**: Maxwell capacitance matrix relating node voltages to charges.
  Encodes self-capacitance and mutual capacitive coupling (including ground and
  topload effects) between each virtual conductor segment.

- **Inductance (L)**: Mutual inductance matrix relating loop currents to magnetic
  flux linkage. Encodes self-inductance and mutual inductive coupling between
  each virtual conductor segment.

These matrices, together with the connectivity matrix (A) from
``coil_discretizers.connectivity``, form the coupled LC eigenvalue
problem whose solutions yield the resonant mode structure of the coil.
"""

from .base import DistributedElementMatrixSolver
from .capacitance import CapacitanceMatrixSolver, FEMCapacitanceMatrixSolver
from .inductance import InductanceMatrixSolver, CoaxialRingInductanceLMatrixSolver

__all__ = [
    "DistributedElementMatrixSolver",
    "CapacitanceMatrixSolver",
    "FEMCapacitanceMatrixSolver",
    "InductanceMatrixSolver",
    "CoaxialRingInductanceLMatrixSolver",
]
