"""
Unit tests for the coil matrix solver classes.

Run with: pytest tests/simulation/test_coil_matrix_solvers.py -v
"""
import pytest
from app.simulation.coil_matrix_solvers import TeslaCoilMatrixSolver, FEMCIntegralIMatrixSolver
from app.models.coil_models import SecondaryConductorSpec, ToploadSpec, GroundedConductorSpec
from app.geometry import Circle


# ---------------------------------------------------------------------------
# Simple fixtures used only by the non-parameterized ABC / concrete tests
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_secondary():
    """A single secondary conductor spec for basic instantiation tests."""
    return SecondaryConductorSpec(
        start=(0.05, 0.0),
        end=(0.05, 0.5),
        wire_dia=0.001,
        turns=1000,
        conductivity=5.8e7,
    )


@pytest.fixture
def simple_topload():
    """A single topload spec for basic instantiation tests."""
    return ToploadSpec(shape=Circle(center=(0.0, 0.6), radius=0.1))


@pytest.fixture
def simple_ground():
    """A single grounded conductor spec for basic instantiation tests."""
    return GroundedConductorSpec(shape=Circle(center=(0.0, 0.0), radius=0.2))


# ---------------------------------------------------------------------------
# TeslaCoilMatrixSolver ABC tests
# ---------------------------------------------------------------------------

class TestTeslaCoilMatrixSolver:
    """Tests for TeslaCoilMatrixSolver abstract base class."""

    def test_cannot_instantiate_directly(self):
        """The ABC should not be instantiable."""
        with pytest.raises(TypeError):
            TeslaCoilMatrixSolver()

    def test_requires_all_three_methods(self):
        """A subclass missing any matrix getter should not be instantiable."""

        class MissingCapacitance(TeslaCoilMatrixSolver):
            def get_inductance_matrix(self):
                pass
            def get_connectivity_matrix(self):
                pass

        class MissingInductance(TeslaCoilMatrixSolver):
            def get_capacitance_matrix(self):
                pass
            def get_connectivity_matrix(self):
                pass

        class MissingConnectivity(TeslaCoilMatrixSolver):
            def get_capacitance_matrix(self):
                pass
            def get_inductance_matrix(self):
                pass

        with pytest.raises(TypeError):
            MissingCapacitance()
        with pytest.raises(TypeError):
            MissingInductance()
        with pytest.raises(TypeError):
            MissingConnectivity()

    def test_complete_subclass_instantiable(self):
        """A complete concrete subclass should be instantiable."""

        class Complete(TeslaCoilMatrixSolver):
            def get_capacitance_matrix(self):
                return []
            def get_inductance_matrix(self):
                return []
            def get_connectivity_matrix(self):
                return []

        solver = Complete()
        assert isinstance(solver, TeslaCoilMatrixSolver)


# ---------------------------------------------------------------------------
# FEMCIntegralIMatrixSolver tests
# ---------------------------------------------------------------------------

class TestFEMCIntegralIMatrixSolver:
    """Tests for FEMCIntegralIMatrixSolver concrete class."""

    def test_instantiation(self, simple_secondary, simple_topload, simple_ground):
        """Should be instantiable with required parameters."""
        solver = FEMCIntegralIMatrixSolver(
            secondary=simple_secondary,
            toploads=(simple_topload,),
            grounds=(simple_ground,),
            r_max=1.0,
            z_max=1.0,
        )
        assert solver.secondary is simple_secondary
        assert solver.toploads == (simple_topload,)
        assert solver.grounds == (simple_ground,)
        assert solver.r_max == 1.0
        assert solver.z_max == 1.0

    def test_is_instance_of_matrix_solver(self, simple_secondary, simple_topload, simple_ground):
        """Should be an instance of TeslaCoilMatrixSolver."""
        solver = FEMCIntegralIMatrixSolver(
            secondary=simple_secondary,
            toploads=(simple_topload,),
            grounds=(simple_ground,),
            r_max=1.0,
            z_max=1.0,
        )
        assert isinstance(solver, TeslaCoilMatrixSolver)

    def test_has_required_methods(self, simple_secondary, simple_topload, simple_ground):
        """Should expose all three matrix getter methods."""
        solver = FEMCIntegralIMatrixSolver(
            secondary=simple_secondary,
            toploads=(simple_topload,),
            grounds=(simple_ground,),
            r_max=1.0,
            z_max=1.0,
        )
        assert hasattr(solver, "get_capacitance_matrix")
        assert hasattr(solver, "get_inductance_matrix")
        assert hasattr(solver, "get_connectivity_matrix")

    def test_empty_toploads_and_grounds(self, simple_secondary):
        """Should work with empty topload and ground tuples."""
        solver = FEMCIntegralIMatrixSolver(
            secondary=simple_secondary,
            toploads=(),
            grounds=(),
            r_max=1.0,
            z_max=1.0,
        )
        assert solver.toploads == ()
        assert solver.grounds == ()
