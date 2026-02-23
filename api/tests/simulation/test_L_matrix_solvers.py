"""
Universal physical-property tests for any inductance matrix solver.

These tests run against every solver registered in the ``inductance_matrix``
fixture in conftest.py.  They verify properties that MUST hold regardless of
the numerical method used:

  1. The matrix is square (N×N).
  2. The matrix is symmetric.
  3. Main-diagonal entries (self-inductance) are positive.
  4. The matrix is positive definite.

Run with: pytest tests/simulation/test_L_matrix_solvers.py -v
"""
import pytest
import numpy as np
from numpy.testing import assert_allclose


# These tests are run against every registered inductance-matrix solver 
# See conftest.py for the parameterized fixture that these tests are run against
class TestInductanceMatrixProperties:
    """Physical-property tests that apply to all L-matrix implementations."""

    def test_is_square(self, inductance_matrix):
        """The inductance matrix must be square (N×N)."""
        L = np.array(inductance_matrix)
        assert L.ndim == 2
        assert L.shape[0] == L.shape[1], (
            f"Expected square matrix, got shape {L.shape}"
        )

    def test_is_symmetric(self, inductance_matrix):
        """The mutual inductance matrix must be symmetric: L = Lᵀ."""
        L = np.array(inductance_matrix)
        assert_allclose(L, L.T, atol=1e-12,
                        err_msg="Inductance matrix is not symmetric")

    def test_positive_diagonal(self, inductance_matrix):
        """Every main-diagonal entry (self-inductance) must be positive."""
        L = np.array(inductance_matrix)
        diag = np.diag(L)
        assert np.all(diag > 0), (
            f"Diagonal entries must all be positive, got {diag}"
        )

    def test_positive_definite(self, inductance_matrix):
        """The inductance matrix must be positive definite (all eigenvalues > 0)."""
        L = np.array(inductance_matrix)
        eigenvalues = np.linalg.eigvalsh(L)
        assert np.all(eigenvalues > 0), (
            f"Matrix is not positive definite; eigenvalues = {eigenvalues}"
        )
