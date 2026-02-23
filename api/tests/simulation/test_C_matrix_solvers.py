"""
Universal physical-property tests for any capacitance matrix solver.

These tests run against every solver registered in the ``capacitance_matrix``
fixture in conftest.py.  They verify properties that MUST hold regardless of
the numerical method used:

  1. The matrix is square (NxN).
  2. The matrix is symmetric.
  3. Main-diagonal entries are positive.
  4. Off-diagonal entries are non-positive (negative or zero).
  5. The matrix is positive definite.

Run with: pytest tests/simulation/test_C_matrix_solvers.py -v
"""
import pytest
import numpy as np
from numpy.testing import assert_allclose

# These tests are run against every registered capacitance-matrix solver 
# See conftest.py for the parameterized fixture that these tests are run against
class TestCapacitanceMatrixProperties:
    """Physical-property tests that apply to all C-matrix implementations."""

    def test_is_square(self, capacitance_matrix):
        """The capacitance matrix must be square (NxN)."""
        C = np.array(capacitance_matrix)
        assert C.ndim == 2
        assert C.shape[0] == C.shape[1], (
            f"Expected square matrix, got shape {C.shape}"
        )

    def test_is_symmetric(self, capacitance_matrix):
        """The mutual capacitance matrix must be symmetric: C = Cᵀ."""
        C = np.array(capacitance_matrix)
        assert_allclose(C, C.T, atol=1e-12,
                        err_msg="Capacitance matrix is not symmetric")

    def test_positive_diagonal(self, capacitance_matrix):
        """Every main-diagonal entry (self-capacitance) must be positive."""
        C = np.array(capacitance_matrix)
        diag = np.diag(C)
        assert np.all(diag > 0), (
            f"Diagonal entries must all be positive, got {diag}"
        )

    def test_non_positive_off_diagonal(self, capacitance_matrix):
        """Off-diagonal entries (mutual capacitances) must be ≤ 0."""
        C = np.array(capacitance_matrix)
        N = C.shape[0]
        for i in range(N):
            for j in range(N):
                if i != j:
                    assert C[i, j] <= 0, (
                        f"C[{i},{j}] = {C[i,j]} should be non-positive"
                    )

    def test_positive_definite(self, capacitance_matrix):
        """The capacitance matrix must be positive definite (all eigenvalues > 0)."""
        C = np.array(capacitance_matrix)
        eigenvalues = np.linalg.eigvalsh(C)
        assert np.all(eigenvalues > 0), (
            f"Matrix is not positive definite; eigenvalues = {eigenvalues}"
        )
