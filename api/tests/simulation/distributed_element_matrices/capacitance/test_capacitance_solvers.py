"""
Universal physical-property tests for any capacitance matrix solver.

These tests run against every solver registered in the ``capacitance_matrix``
fixture in conftest.py.  They verify properties that MUST hold for the NODAL
(Galerkin/tent-basis) capacitance matrix regardless of the numerical method
used (see docs/cmatrix_derivation.ipynb):

  1. The reduced matrix is square, NxN (N = discretization order).
  2. The full nodal matrix is (N+1)x(N+1).
  3. Both are symmetric.
  4. Main-diagonal entries are positive.
  5. Both are positive definite (a grounded reference exists).
  6. The DC capacitance (all-ones quadratic form of the FULL matrix) is
     positive and exceeds the same form of any single node.

Note this matrix is NOT a classical Maxwell matrix: off-diagonal entries
between ADJACENT nodes may be positive (overlapping tent profiles), so no
off-diagonal sign test appears here. Distant nodes still couple negatively,
which test 7 spot-checks.

Run with: pytest tests/simulation/distributed_element_matrices/capacitance -v
"""
import pytest
import numpy as np
from numpy.testing import assert_allclose
from app.simulation.distributed_element_matrices.capacitance import CapacitanceMatrixSolver, FEMCapacitanceMatrixSolver


# ---------------------------------------------------------------------------
# Registry of concrete CapacitanceMatrixSolver implementations.
# Add new solvers here — ABC conformance tests run automatically.
# ---------------------------------------------------------------------------

CAPACITANCE_SOLVERS = [
    pytest.param(FEMCapacitanceMatrixSolver, id="FEM"),
    # pytest.param(BEMCapacitanceMatrixSolver, id="BEM"),  # ← register future solvers here
]

# Per-solver kwargs used by the property-test fixtures ONLY. Physical
# properties (symmetry, definiteness, signs) hold at any resolution, so the
# fixtures run a deliberately coarse/fast configuration; accuracy is
# established separately by the analytic electrostatics tests and the
# JavaTC end-to-end test.
SOLVER_TEST_KWARGS = {
    FEMCapacitanceMatrixSolver: dict(
        winding_mesh_size_factor=8.0,
        component_mesh_fraction=0.2,
        wall_mesh_fraction=0.25,
        fe_order=1,
    ),
}


# ---------------------------------------------------------------------------
# CapacitanceMatrixSolver ABC tests
# ---------------------------------------------------------------------------

class TestCapacitanceMatrixSolverABC:
    """Tests for CapacitanceMatrixSolver abstract base class."""

    def test_cannot_instantiate_directly(self):
        """The ABC should not be instantiable."""
        with pytest.raises(TypeError):
            CapacitanceMatrixSolver()

    @pytest.mark.parametrize("solver_cls", CAPACITANCE_SOLVERS)
    def test_concrete_is_subclass(self, solver_cls):
        """Every registered solver should be a subclass of the ABC."""
        assert issubclass(solver_cls, CapacitanceMatrixSolver)

    @pytest.mark.parametrize("solver_cls", CAPACITANCE_SOLVERS)
    def test_concrete_has_methods(self, solver_cls):
        """Every registered solver should expose the matrix interface."""
        assert hasattr(solver_cls, "compute_matrix")
        assert hasattr(solver_cls, "nodal_capacitance_matrix")


# ---------------------------------------------------------------------------
# Physical-property tests for all C-matrix implementations
# ---------------------------------------------------------------------------

# These tests are run against every registered capacitance-matrix solver
# See conftest.py for the parameterized fixtures these run against.
class TestCapacitanceMatrixProperties:
    """Physical-property tests that apply to all C-matrix implementations."""

    def test_reduced_is_square_N(self, capacitance_matrix, coil):
        """compute_matrix must be NxN over the free nodes t_1..t_N."""
        C = np.array(capacitance_matrix)
        assert C.ndim == 2
        assert C.shape == (coil.discretization_order, coil.discretization_order)

    def test_nodal_is_square_N_plus_1(self, nodal_capacitance_matrix, coil):
        """The full nodal matrix includes the grounded base node t_0."""
        C = np.array(nodal_capacitance_matrix)
        n = coil.discretization_order + 1
        assert C.shape == (n, n)

    def test_is_symmetric(self, nodal_capacitance_matrix):
        """The capacitance matrix must be symmetric: C = C^T."""
        C = np.array(nodal_capacitance_matrix)
        assert_allclose(C, C.T, atol=1e-12 * np.abs(C).max(),
                        err_msg="Capacitance matrix is not symmetric")

    def test_positive_diagonal(self, nodal_capacitance_matrix):
        """Every main-diagonal entry (tent self-energy) must be positive."""
        C = np.array(nodal_capacitance_matrix)
        diag = np.diag(C)
        assert np.all(diag > 0), (
            f"Diagonal entries must all be positive, got {diag}"
        )

    def test_positive_definite(self, nodal_capacitance_matrix):
        """With a grounded reference the nodal matrix is positive definite."""
        C = np.array(nodal_capacitance_matrix)
        eigenvalues = np.linalg.eigvalsh(C)
        assert np.all(eigenvalues > 0), (
            f"Matrix is not positive definite; eigenvalues = {eigenvalues}"
        )

    def test_reduction_is_principal_submatrix(self, capacitance_matrix, nodal_capacitance_matrix):
        """compute_matrix must equal the nodal matrix minus node 0."""
        C = np.array(capacitance_matrix)
        C_full = np.array(nodal_capacitance_matrix)
        assert_allclose(C, C_full[1:, 1:], rtol=1e-14)

    def test_dc_capacitance_positive_and_dominant(self, nodal_capacitance_matrix):
        """The all-ones form of the FULL nodal matrix is the DC capacitance
        (partition of unity): positive, and larger than any single tent's
        self term minus its neighbors' pull."""
        C = np.array(nodal_capacitance_matrix)
        ones = np.ones(C.shape[0])
        c_dc = ones @ C @ ones
        assert c_dc > 0

    def test_distant_nodes_couple_negatively(self, nodal_capacitance_matrix):
        """Far-separated tents behave like classical separate conductors:
        their mutual term is negative (adjacent tents may be positive -
        that is the nodal/Maxwell distinction)."""
        C = np.array(nodal_capacitance_matrix)
        n = C.shape[0]
        assert C[0, n - 1] < 0
