from typing import Tuple
from app.simulation.eigen_solvers.base import EigenSolverBase
from app.simulation.types import EigenFamily
import numpy as np
from scipy import linalg
import methodtools as mt


class VoltageModeEigenSolver(EigenSolverBase):
    """Concrete eigen-analysis solver, which solves for voltage modes directly
    and derives current modes.

    Internally caches the shared eigenvalue decomposition so that
    ``compute_eigen_frequencies``, ``compute_voltage_eigen_modes``, and
    ``compute_current_eigen_modes`` all reuse the same work when called
    with identical (hashable) arguments.
    """

    # -- shared cached computation ------------------------------------------

    @mt.lru_cache()
    @staticmethod
    def _compute_eigen_family(
        capacitance_matrix: Tuple[Tuple[float, ...], ...],
        inductance_matrix: Tuple[Tuple[float, ...], ...],
        connectivity_matrix: Tuple[Tuple[float, ...], ...],
    ) -> EigenFamily:
        """
        Solve the generalized eigenvalue problem for the system:
        ω² C V = A L⁻¹ Aᵀ V

        Args:
            capacitance_matrix: Capacitance matrix (C)
            inductance_matrix: Inductance matrix (L)
            connectivity_matrix: Connectivity matrix (A)

        Returns:
            EigenFamily with eigenfrequencies (ω) and voltage eigenmodes (V)
        """
        C = np.array(capacitance_matrix)
        L = np.array(inductance_matrix)
        A = np.array(connectivity_matrix)

        L_inv = linalg.inv(L)
        RHS = A @ L_inv @ A.T

        eigenvalues, eigenvectors = linalg.eig(RHS, C)

        omega_squared = np.real(eigenvalues)
        omega = np.sqrt(omega_squared)
        frequencies = omega / (2 * np.pi)

        sorted_indices = np.argsort(frequencies)
        frequencies_sorted = frequencies[sorted_indices]
        eigenvectors_sorted = np.real(eigenvectors[:, sorted_indices])

        freq_list = frequencies_sorted.tolist()
        eigvec_list = [
            eigenvectors_sorted[:, i].tolist()
            for i in range(eigenvectors_sorted.shape[1])
        ]

        return EigenFamily(eigenvalues=freq_list, eigenvectors=eigvec_list)

    # -- public interface (all delegate to the cached family) ---------------

    @staticmethod
    def compute_eigen_frequencies(
        capacitance_matrix: Tuple[Tuple[float, ...], ...],
        inductance_matrix: Tuple[Tuple[float, ...], ...],
        connectivity_matrix: Tuple[Tuple[float, ...], ...],
    ) -> Tuple[float, ...]:
        family = VoltageModeEigenSolver._compute_eigen_family(
            capacitance_matrix, inductance_matrix, connectivity_matrix
        )
        return tuple(family.eigenvalues)

    @staticmethod
    def compute_voltage_eigen_modes(
        capacitance_matrix: Tuple[Tuple[float, ...], ...],
        inductance_matrix: Tuple[Tuple[float, ...], ...],
        connectivity_matrix: Tuple[Tuple[float, ...], ...],
    ) -> Tuple[Tuple[float, ...], ...]:
        family = VoltageModeEigenSolver._compute_eigen_family(
            capacitance_matrix, inductance_matrix, connectivity_matrix
        )
        return tuple(tuple(v) for v in family.eigenvectors)

    @mt.lru_cache()
    @staticmethod
    def compute_current_eigen_modes(
        capacitance_matrix: Tuple[Tuple[float, ...], ...],
        inductance_matrix: Tuple[Tuple[float, ...], ...],
        connectivity_matrix: Tuple[Tuple[float, ...], ...],
    ) -> Tuple[Tuple[float, ...], ...]:
        """
        Compute current eigenmodes: I = -(j/ω) L⁻¹ Aᵀ V

        Uses the eigenfrequencies and voltage modes from the shared family,
        then derives the current modes via the inductance matrix.
        """
        family = VoltageModeEigenSolver._compute_eigen_family(
            capacitance_matrix, inductance_matrix, connectivity_matrix
        )

        L = np.array(inductance_matrix)
        A = np.array(connectivity_matrix)
        L_inv = linalg.inv(L)
        A_T = A.T

        V = np.array(family.eigenvectors).T  # (num_nodes, num_modes)
        eigen_frequencies = family.eigenvalues

        num_modes = V.shape[1]
        I_modes = []

        for i in range(num_modes):
            omega = 2 * np.pi * eigen_frequencies[i]
            V_mode = V[:, i]
            I_mode = -(1j / omega) * L_inv @ A_T @ V_mode
            I_modes.append(np.real(I_mode).tolist())

        return tuple(tuple(mode) for mode in I_modes)
