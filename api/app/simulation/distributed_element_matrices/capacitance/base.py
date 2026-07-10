from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Tuple

from app.simulation.distributed_element_matrices.base import DistributedElementMatrixSolver

if TYPE_CHECKING:
    from app.models.simulation_models import SimulatableTeslaCoil


class CapacitanceMatrixSolver(DistributedElementMatrixSolver):
    """Abstract base class for capacitance matrix solvers.

    The capacitance object of this codebase is the NODAL (Galerkin)
    capacitance matrix over the winding's slice nodes t_0..t_N, derived in
    docs/cmatrix_derivation.ipynb: entry [j, k] is the hat-weighted charge
    at node j when the winding surface carries the tent potential profile
    of node k (topload riding node N; grounds and Dirichlet walls at 0).

    This is NOT the classical Maxwell matrix of isolated conductors - the
    tent (continuous) boundary data is what keeps every entry finite and
    convergent when the "conductors" are bands of one continuous winding.
    Consequences that differ from Maxwell matrices: adjacent off-diagonal
    entries may be positive, and the all-ones quadratic form equals the
    coil's DC capacitance exactly (partition of unity).

    Subclasses implement :meth:`nodal_capacitance_matrix` producing the
    full (N+1)x(N+1) matrix in GEOMETRIC units - multiply by
    2*pi*epsilon_0 and the meters-per-unit length scale for Farads.
    """

    def compute_matrix(
        self, coil: SimulatableTeslaCoil
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the grounded-reduced nodal capacitance matrix.

        Node 0 (the winding base, t_0) is held at 0 by the series
        connectivity convention (assumption 4 of
        SeriesConnectivityMatrixSolver), so its row and column are removed.
        The result is the NxN matrix (N = coil.discretization_order) that
        pairs with the series connectivity and inductance matrices in the
        eigenvalue problem.

        Parameters:
            coil: The full simulatable Tesla coil specification.

        Returns:
            An NxN tuple-of-tuples geometric capacitance matrix over the
            free nodes t_1..t_N.
        """
        nodal = self.nodal_capacitance_matrix(coil)
        return tuple(row[1:] for row in nodal[1:])

    @abstractmethod
    def nodal_capacitance_matrix(
        self, coil: SimulatableTeslaCoil
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the full nodal capacitance matrix, including node 0.

        The full matrix is the one whose quadratic forms have direct
        physical meaning (DC capacitance = all-ones form; field energy of
        any piecewise-linear voltage profile = (1/2) V^T C V).

        Parameters:
            coil: The full simulatable Tesla coil specification.

        Returns:
            An (N+1)x(N+1) tuple-of-tuples geometric capacitance matrix
            over the slice nodes t_0..t_N.
        """
        ...

    @abstractmethod
    def topload_charge_vector(
        self, coil: SimulatableTeslaCoil
    ) -> Tuple[float, ...]:
        """Geometric charge attributed to the topload group per unit solve.

        Entry k is the charge on ALL topload surfaces when the winding
        carries node k's tent profile (topload riding node N). By
        linearity, the topload charge under any nodal profile V is
        sum_k q_k V_k; dividing by the top voltage yields the topload's
        effective (in-situ, shielded) capacitance.

        Parameters:
            coil: The full simulatable Tesla coil specification.

        Returns:
            A length-(N+1) tuple, geometric units (multiply by
            2*pi*epsilon_0*scale for Coulombs-per-volt terms).
        """
        ...
