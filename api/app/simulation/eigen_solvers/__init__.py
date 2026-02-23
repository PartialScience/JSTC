"""
A collection of objects for solving the eigen value problems which arise in the context of Tesla coil simulations. 
"""

from app.simulation.eigen_solvers.base import EigenSolverBase
from app.simulation.eigen_solvers.voltage_mode_solver import VoltageModeEigenSolver

__all__ = [
    "EigenSolverBase",
    "VoltageModeEigenSolver",
]
