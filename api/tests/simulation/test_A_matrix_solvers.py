"""
Unit tests for the connectivity matrix solver (A matrix).

Run with: pytest tests/simulation/test_A_matrix_solvers.py -v
"""
import pytest
from app.simulation.A_matrix_solvers import SeriesConnectivityMatrixSolver


class TestSeriesConnectivityMatrixSolver:
    """Tests for SeriesConnectivityMatrixSolver.compute_connectivity_matrix."""

    def test_dimension(self):
        """Matrix should be N x N for a given discretization order N."""
        for N in (2, 3, 5, 10):
            A = SeriesConnectivityMatrixSolver.compute_connectivity_matrix(N)
            assert len(A) == N, f"Expected {N} rows, got {len(A)}"
            for row in A:
                assert len(row) == N, f"Expected {N} cols, got {len(row)}"

    def test_diagonal_is_one(self):
        """All diagonal elements should be 1.0."""
        N = 5
        A = SeriesConnectivityMatrixSolver.compute_connectivity_matrix(N)
        for i in range(N):
            assert A[i][i] == 1.0, f"A[{i}][{i}] should be 1.0"

    def test_superdiagonal_is_minus_one(self):
        """Elements at A[i][i+1] should be -1.0 (series wiring)."""
        N = 5
        A = SeriesConnectivityMatrixSolver.compute_connectivity_matrix(N)
        for i in range(N - 1):
            assert A[i][i + 1] == -1.0, f"A[{i}][{i+1}] should be -1.0"

    def test_other_elements_are_zero(self):
        """All non-diagonal, non-superdiagonal elements should be 0.0."""
        N = 5
        A = SeriesConnectivityMatrixSolver.compute_connectivity_matrix(N)
        for i in range(N):
            for j in range(N):
                if i == j or j == i + 1:
                    continue
                assert A[i][j] == 0.0, f"A[{i}][{j}] should be 0.0, got {A[i][j]}"

    def test_returns_tuple_of_tuples(self):
        """Return type should be a tuple of tuples for hashability/caching."""
        A = SeriesConnectivityMatrixSolver.compute_connectivity_matrix(3)
        assert isinstance(A, tuple)
        for row in A:
            assert isinstance(row, tuple)

    def test_small_matrix_values(self):
        """Verify the full 3x3 connectivity matrix explicitly."""
        A = SeriesConnectivityMatrixSolver.compute_connectivity_matrix(3)
        expected = (
            (1.0, -1.0, 0.0),
            (0.0, 1.0, -1.0),
            (0.0, 0.0, 1.0),
        )
        assert A == expected

    def test_2x2_matrix(self):
        """Verify the 2x2 connectivity matrix."""
        A = SeriesConnectivityMatrixSolver.compute_connectivity_matrix(2)
        expected = (
            (1.0, -1.0),
            (0.0, 1.0),
        )
        assert A == expected

    def test_1x1_matrix(self):
        """A single conductor should produce [[1.0]]."""
        A = SeriesConnectivityMatrixSolver.compute_connectivity_matrix(1)
        assert A == ((1.0,),)

    def test_upper_triangular(self):
        """The connectivity matrix should be upper triangular (lower triangle is zero)."""
        N = 5
        A = SeriesConnectivityMatrixSolver.compute_connectivity_matrix(N)
        for i in range(N):
            for j in range(i):
                assert A[i][j] == 0.0, f"A[{i}][{j}] should be 0.0 (upper triangular)"
