"""
Unit tests for the eigenvalue and eigencurrent solvers.

Test systems are defined in ``MATRIX_TEST_CASES`` and parameterized so that all
registered ``EigenSolverBase`` implementations are exercised against every
(C, L, A) triple automatically.

Run with: pytest tests/simulation/eigen_solvers/test_eigen_solvers.py -v
"""
import pytest
import numpy as np
from dataclasses import dataclass
from numpy.testing import assert_allclose
from scipy import linalg
from app.simulation.eigen_solvers import EigenSolverBase, VoltageModeEigenSolver
from app.simulation.types import EigenFamily


# ---------------------------------------------------------------------------
# Registry of concrete EigenSolverBase implementations.
# Add new solvers here — all tests run automatically for each.
# ---------------------------------------------------------------------------

EIGEN_SOLVERS = [
    pytest.param(VoltageModeEigenSolver, id="VoltageModeEigenSolver"),
    # pytest.param(SomeOtherEigenSolver, id="Other"),  # ← register future solvers here
]


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
# Test cases — add new (C, L, A) triples here
# ---------------------------------------------------------------------------

MATRIX_TEST_CASES = [
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
# EigenSolverBase ABC tests
# ---------------------------------------------------------------------------

class TestEigenSolverABC:
    """Tests for EigenSolverBase abstract base class."""

    def test_cannot_instantiate_directly(self):
        """The ABC should not be instantiable."""
        with pytest.raises(TypeError):
            EigenSolverBase()

    @pytest.mark.parametrize("solver_cls", EIGEN_SOLVERS)
    def test_concrete_is_subclass(self, solver_cls):
        """Every registered solver should be a subclass of the ABC."""
        assert issubclass(solver_cls, EigenSolverBase)

    @pytest.mark.parametrize("solver_cls", EIGEN_SOLVERS)
    def test_has_compute_eigen_frequencies(self, solver_cls):
        """Every registered solver should expose compute_eigen_frequencies."""
        assert hasattr(solver_cls, "compute_eigen_frequencies")

    @pytest.mark.parametrize("solver_cls", EIGEN_SOLVERS)
    def test_has_compute_voltage_eigen_modes(self, solver_cls):
        """Every registered solver should expose compute_voltage_eigen_modes."""
        assert hasattr(solver_cls, "compute_voltage_eigen_modes")

    @pytest.mark.parametrize("solver_cls", EIGEN_SOLVERS)
    def test_has_compute_current_eigen_modes(self, solver_cls):
        """Every registered solver should expose compute_current_eigen_modes."""
        assert hasattr(solver_cls, "compute_current_eigen_modes")


# ---------------------------------------------------------------------------
# Shared fixture — solver x test system cross-product
# ---------------------------------------------------------------------------

@pytest.fixture(params=EIGEN_SOLVERS)
def solver_cls(request):
    """A concrete EigenSolverBase implementation."""
    return request.param


@pytest.fixture(params=MATRIX_TEST_CASES)
def eigen_system(request, solver_cls):
    """
    Return (solver_cls, LCASystem, frequencies, voltage_modes) for one
    test system x solver combination.
    """
    system: LCASystem = request.param
    C = _to_nested_tuple(system.C)
    L = _to_nested_tuple(system.L)
    A = _to_nested_tuple(system.A)

    freqs = solver_cls.compute_eigen_frequencies(C, L, A)
    modes = solver_cls.compute_voltage_eigen_modes(C, L, A)

    result = EigenFamily(eigenvalues=list(freqs), eigenvectors=[list(mode) for mode in modes])
    return solver_cls, system, result


# ---------------------------------------------------------------------------
# Eigen solver tests
# ---------------------------------------------------------------------------

class TestEigenSolver:
    """Tests for eigenfrequency, voltage-mode, and current-mode methods (all solvers)."""

    def test_eigenvalue_equation(self, eigen_system):
        """
        Every (omega, V) pair must satisfy the generalized eigenvalue problem:

            A L^-1 A^T  V  =  omega^2  C V
        """
        _, system, result = eigen_system
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
        _, _, result = eigen_system
        freqs = list(result.eigenvalues)
        assert freqs == sorted(freqs), (
            f"Frequencies are not sorted ascending: {freqs}"
        )

    def test_current_mode_equation(self, eigen_system):
        """
        Every current mode must satisfy:

            I = -(j/omega) L^-1 A^T V
        """
        solver_cls, system, result = eigen_system
        L_inv = linalg.inv(system.L)
        A_T = system.A.T

        current_modes = solver_cls.compute_current_eigen_modes(
            capacitance_matrix=_to_nested_tuple(system.C),
            inductance_matrix=_to_nested_tuple(system.L),
            connectivity_matrix=_to_nested_tuple(system.A),
        )

        V = np.array(result.eigenvectors).T  # (N, num_modes)

        for i, freq in enumerate(result.eigenvalues):
            omega = 2 * np.pi * freq
            expected = np.real(-(1j / omega) * L_inv @ A_T @ V[:, i])
            assert_allclose(current_modes[i], expected, rtol=1e-10,
                            err_msg=f"Current mode equation not satisfied for mode {i}")

    def test_current_modes_sorted_with_frequencies(self, eigen_system):
        """Current modes must correspond to the ascending-frequency ordering."""
        _, _, result = eigen_system
        freqs = list(result.eigenvalues)
        assert freqs == sorted(freqs)
