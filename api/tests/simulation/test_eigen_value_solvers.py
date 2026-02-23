"""
Unit tests for the eigenvalue and eigencurrent solvers.

Test systems are defined in ``TEST_SYSTEMS`` and parameterized so that both
solvers are exercised against every (C, L, A) triple automatically.

Run with: pytest tests/simulation/test_eigen_value_solvers.py -v
"""
import pytest
import numpy as np
from dataclasses import dataclass
from numpy.testing import assert_allclose
from scipy import linalg
from app.simulation.eigen_value_solvers import EigenFrequencySolver, CurrentEigenModeSolver
from app.simulation.types import EigenFamily


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_nested_tuple(matrix):
    """Convert a 2-D numpy array to a tuple of tuples."""
    return tuple(tuple(float(entry) for entry in row) for row in matrix)


def _spd(N, seed):
    """Generate an NxN symmetric positive-definite matrix from a given seed."""
    rng = np.random.default_rng(seed)
    M = rng.standard_normal((N, N))
    return M @ M.T + N * np.eye(N)


def _series_A(N):
    """Standard series-connectivity matrix (upper bidiagonal)."""
    return np.eye(N) + np.diag([-1.0] * (N - 1), k=1)


@dataclass
class LCASystem:
    """A (C, L, A) matrix triple for eigenvalue solver testing."""
    C: np.ndarray
    L: np.ndarray
    A: np.ndarray


# ---------------------------------------------------------------------------
# Test systems — add new (C, L, A) triples here
# ---------------------------------------------------------------------------

TEST_SYSTEMS = [
    pytest.param(
        LCASystem(
            C=np.diag([1e-12, 2e-12]),
            L=np.diag([1e-6, 2e-6]),
            A=np.array([
                [ 1., -1.],
                [ 0.,  1.],
            ]),
        ),
        id="2x2-diagonal",
    ),
    pytest.param(
        LCASystem(
            C=np.eye(3),
            L=np.eye(3),
            A=np.eye(3),
        ),
        id="3x3-identity",
    ),
    pytest.param(
        LCASystem(
            C=_spd(30, seed=42),
            L=_spd(30, seed=99),
            A=_series_A(30),
        ),
        id="30x30-random-spd",
    ),
    pytest.param(
        LCASystem(
            C=_spd(50, seed=7),
            L=_spd(50, seed=13),
            A=_series_A(50),
        ),
        id="50x50-random-spd",
    ),
]


# ---------------------------------------------------------------------------
# Shared fixture — solves the eigenfrequency problem for each test system
# ---------------------------------------------------------------------------

@pytest.fixture(params=TEST_SYSTEMS)
def eigen_system(request):
    """
    Return (LCASystem, EigenFamily) for one test system.

    The EigenFamily is computed once per system by EigenFrequencySolver.
    """
    system: LCASystem = request.param
    result = EigenFrequencySolver.compute_eigen_frequency_family(
        capacitance_matrix=_to_nested_tuple(system.C),
        inductance_matrix=_to_nested_tuple(system.L),
        connectivity_matrix=_to_nested_tuple(system.A),
    )
    return system, result


# ---------------------------------------------------------------------------
# EigenFrequencySolver tests
# ---------------------------------------------------------------------------

class TestEigenFrequencySolver:
    """Tests for EigenFrequencySolver.compute_eigen_frequency_family."""

    def test_eigenvalue_equation(self, eigen_system):
        """
        Every (omega, V) pair must satisfy the generalized eigenvalue problem:

            A L^-1 A^T  V  =  omega^2  C V

        The solver reports f = omega / (2 pi), so we verify:
            (A L^-1 A^T) V  =  omega^2  C V.
        """
        system, result = eigen_system
        L_inv = linalg.inv(system.L)
        RHS_matrix = system.A @ L_inv @ system.A.T

        for freq, vec in zip(result.eigenvalues, result.eigenvectors):
            omega = 2 * np.pi * freq
            V = np.array(vec)

            lhs = RHS_matrix @ V
            rhs = (omega ** 2) * system.C @ V

            assert_allclose(lhs, rhs, atol=1e-8,
                            err_msg=f"Eigenvalue equation not satisfied for f={freq}")

    def test_frequencies_sorted_ascending(self, eigen_system):
        """Eigenfrequencies must be in non-decreasing order."""
        _, result = eigen_system
        freqs = list(result.eigenvalues)
        assert freqs == sorted(freqs), (
            f"Frequencies are not sorted ascending: {freqs}"
        )


# ---------------------------------------------------------------------------
# CurrentEigenModeSolver tests
# ---------------------------------------------------------------------------

class TestCurrentEigenModeSolver:
    """Tests for CurrentEigenModeSolver.find_current_modes_from_inductance."""

    def test_current_mode_equation(self, eigen_system):
        """
        Every current mode must satisfy:

            I = -(j/omega) L^-1 A^T V

        The real part of the RHS is compared against the solver output.
        """
        system, result = eigen_system
        L_inv = linalg.inv(system.L)
        A_T = system.A.T

        current_modes = CurrentEigenModeSolver.find_current_modes_from_inductance(
            inverse_inductance_matrix=_to_nested_tuple(L_inv),
            transpose_connectivity_matrix=_to_nested_tuple(A_T),
            eigen_frequencies=tuple(result.eigenvalues),
            voltage_eigenmodes=tuple(tuple(v) for v in result.eigenvectors),
        )

        V = np.array(result.eigenvectors).T  # (N, num_modes)

        for i, freq in enumerate(result.eigenvalues):
            omega = 2 * np.pi * freq
            expected = np.real(-(1j / omega) * L_inv @ A_T @ V[:, i])
            assert_allclose(current_modes[i], expected, rtol=1e-10,
                            err_msg=f"Current mode equation not satisfied for mode {i}")

    def test_current_modes_sorted_with_frequencies(self, eigen_system):
        """Current modes must correspond to the ascending-frequency ordering."""
        _, result = eigen_system
        freqs = list(result.eigenvalues)
        assert freqs == sorted(freqs)
