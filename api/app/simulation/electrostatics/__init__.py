"""
Axisymmetric electrostatic FEM solves.

Implements the discrete side of docs/cmatrix_derivation.ipynb: r-weighted
Laplace solves with prescribed boundary potentials, and the Gram-matrix
charge extraction C_jk = U_j^T K U_k (no flux integration anywhere).
"""

from .axisymmetric import (
    ElectrostaticResult,
    solve_capacitance_gram_matrix,
    solve_electrostatics,
)

__all__ = [
    "ElectrostaticResult",
    "solve_capacitance_gram_matrix",
    "solve_electrostatics",
]
