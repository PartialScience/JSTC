"""
Universal physical-property tests for any inductance matrix solver.

These tests run against every solver registered in the ``inductance_matrix``
fixture in conftest.py.  They verify properties that MUST hold regardless of
the numerical method used:

  1. The matrix is square (NxN).
  2. The matrix is symmetric.
  3. Main-diagonal entries (self-inductance) are positive.
  4. The matrix is positive definite.

Run with: pytest tests/simulation/matrix_solvers/inductance/test_inductance_solvers.py -v
"""
import math
import pytest
import numpy as np
from numpy.testing import assert_allclose
from app.models.coil_models import LinearSecondaryConductorSpec
from app.models.materials import Material
from app.models.simulation_models import SimulatableTeslaCoil
from app.simulation.coil_discretizers.uniform_arclength_discretizer import UniformArcLengthDiscretizer
from app.simulation.distributed_element_matrices.inductance import InductanceMatrixSolver, CoaxialRingInductanceLMatrixSolver


# ---------------------------------------------------------------------------
# Registry of concrete InductanceMatrixSolver implementations.
# Add new solvers here — ABC conformance tests run automatically.
# ---------------------------------------------------------------------------

INDUCTANCE_SOLVERS = [
    pytest.param(CoaxialRingInductanceLMatrixSolver, id="CoaxialRing"),
    # pytest.param(AnalyticalInductanceSolver, id="Analytical"),  # ← register future solvers here
]


# ---------------------------------------------------------------------------
# InductanceMatrixSolver ABC tests
# ---------------------------------------------------------------------------

class TestInductanceMatrixSolverABC:
    """Tests for InductanceMatrixSolver abstract base class."""

    def test_cannot_instantiate_directly(self):
        """The ABC should not be instantiable."""
        with pytest.raises(TypeError):
            InductanceMatrixSolver()

    @pytest.mark.parametrize("solver_cls", INDUCTANCE_SOLVERS)
    def test_concrete_is_subclass(self, solver_cls):
        """Every registered solver should be a subclass of the ABC."""
        assert issubclass(solver_cls, InductanceMatrixSolver)

    @pytest.mark.parametrize("solver_cls", INDUCTANCE_SOLVERS)
    def test_concrete_has_method(self, solver_cls):
        """Every registered solver should expose compute_matrix."""
        assert hasattr(solver_cls, "compute_matrix")


# ---------------------------------------------------------------------------
# Physical-property tests for all L-matrix implementations
# ---------------------------------------------------------------------------

# These tests are run against every registered inductance-matrix solver 
# See conftest.py for the parameterized fixture that these tests are run against
class TestInductanceMatrixProperties:
    """Physical-property tests that apply to all L-matrix implementations."""

    def test_is_square(self, inductance_matrix):
        """The inductance matrix must be square (NxN)."""
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


# ---------------------------------------------------------------------------
# Ideal-solenoid approximation test
# ---------------------------------------------------------------------------

# A long, thin solenoid (l/r = 50) so the ideal-solenoid formula L = N²πr²/l
# is a good approximation.  The discrete matrix sum converges to the ideal
# value as N increases; at N=200 the relative error from discretization is
# ~15 %, so a 20 % tolerance is used as a sanity check.
_SOLENOID_RADIUS = 1.0
_SOLENOID_LENGTH = 50.0
_SOLENOID_TURNS = 200
_SOLENOID_IDEALITY_TOL = 0.2

IDEAL_SOLENOID = LinearSecondaryConductorSpec(
    material=Material.COPPER,
    turn_fxn=lambda t: _SOLENOID_TURNS * t,
    start=(_SOLENOID_RADIUS, 0.0),
    end=(_SOLENOID_RADIUS, _SOLENOID_LENGTH),
    wire_dia=0.01,
)

IDEAL_SOLENOID_COIL = SimulatableTeslaCoil(
    secondary=IDEAL_SOLENOID,
    r_max=100,
    z_max=100,
    discretization_order=_SOLENOID_TURNS,
)


class TestInductanceMatrixSolenoidApproximation:
    """Verify that the total inductance (sum of all matrix elements) approximates
    the self-inductance of an ideal solenoid: L_geo = N² π r² / l."""

    @pytest.mark.parametrize("solver_cls", INDUCTANCE_SOLVERS)
    def test_sum_approximates_ideal_solenoid(self, solver_cls):
        """Sum of all L-matrix elements ≈ N²πr²/l for a long solenoid."""
        discretizer = UniformArcLengthDiscretizer()
        solver = solver_cls(discretizer=discretizer)

        L = solver.compute_matrix(IDEAL_SOLENOID_COIL)

        L_sum = sum(sum(row) for row in L)
        expected = _SOLENOID_TURNS ** 2 * math.pi * _SOLENOID_RADIUS ** 2 / _SOLENOID_LENGTH

        assert_allclose(L_sum, expected, rtol=_SOLENOID_IDEALITY_TOL,
                        err_msg=f"Matrix sum {L_sum:.4f} does not approximate "
                                f"ideal solenoid value {expected:.4f}")
