"""
Tests for primary-secondary mutual coupling solvers.
"""
import numpy as np
import pytest
from scipy.constants import mu_0

from app.models.simulation_models import SimulatableTeslaCoil
from app.simulation.coil_discretizers.uniform_arclength_discretizer import UniformArcLengthDiscretizer
from app.simulation.distributed_element_matrices.coupling import (
    CoaxialRingMutualCouplingSolver,
    MutualCouplingSolver,
    primary_geometric_self_inductance,
)
from app.simulation.distributed_element_matrices.inductance import CoaxialRingInductanceLMatrixSolver
from tests.simulation.test_coils import JAVATC_EXAMPLE_COIL


COUPLING_SOLVERS = [
    pytest.param(CoaxialRingMutualCouplingSolver, id="CoaxialRing"),
    # ← register future coupling solvers here
]


def _coil(order=10):
    return SimulatableTeslaCoil(**JAVATC_EXAMPLE_COIL, discretization_order=order)


def _solver(cls=CoaxialRingMutualCouplingSolver):
    return cls(discretizer=UniformArcLengthDiscretizer())


class TestMutualCouplingSolverABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            MutualCouplingSolver(discretizer=UniformArcLengthDiscretizer())

    @pytest.mark.parametrize("solver_cls", COUPLING_SOLVERS)
    def test_concrete_is_subclass(self, solver_cls):
        assert issubclass(solver_cls, MutualCouplingSolver)


class TestCouplingVector:
    def test_length_matches_discretization(self):
        for order in (10, 30):
            m = _solver().coupling_vector(_coil(order))
            assert len(m) == order

    def test_all_entries_positive(self):
        """Every secondary segment sits above and inside-out from the
        primary with aligned winding sense: all mutuals positive."""
        m = _solver().coupling_vector(_coil())
        assert all(v > 0 for v in m)

    def test_bottom_segment_couples_strongest(self):
        """The secondary segment nearest the primary plane dominates."""
        m = _solver().coupling_vector(_coil(order=30))
        assert m[0] == max(m)
        assert m[0] > 10 * m[-1]

    def test_total_mutual_independent_of_discretization(self):
        """Segment grouping only redistributes turn-level sums: Lm is
        exactly invariant under the discretization order."""
        lm_10 = sum(_solver().coupling_vector(_coil(10)))
        lm_50 = sum(_solver().coupling_vector(_coil(50)))
        assert lm_10 == pytest.approx(lm_50, rel=1e-12)

    def test_requires_primary(self):
        coil_kwargs = dict(JAVATC_EXAMPLE_COIL, primary=None)
        coil = SimulatableTeslaCoil(**coil_kwargs, discretization_order=10)
        with pytest.raises(ValueError):
            _solver().coupling_vector(coil)


class TestBorderedInductanceMatrix:
    def test_positive_definite(self):
        """[[L, m],[m^T, L_p]] must be PD - equivalent to k < 1, and the
        structural sanity check of the coupled-system model."""
        coil = _coil(order=30)
        d = UniformArcLengthDiscretizer()
        L = np.array(CoaxialRingInductanceLMatrixSolver(discretizer=d).compute_matrix(coil))
        m = np.array(_solver().coupling_vector(coil)).reshape(-1, 1)
        lp = primary_geometric_self_inductance(coil.primary)
        bordered = np.block([[L, m], [m.T, np.array([[lp]])]])
        eigenvalues = np.linalg.eigvalsh(bordered)
        assert np.all(eigenvalues > 0)

    def test_coupling_coefficient_below_unity(self):
        coil = _coil(order=30)
        d = UniformArcLengthDiscretizer()
        L = np.array(CoaxialRingInductanceLMatrixSolver(discretizer=d).compute_matrix(coil))
        lm = sum(_solver().coupling_vector(coil))
        lp = primary_geometric_self_inductance(coil.primary)
        k = lm / np.sqrt(lp * L.sum())
        assert 0 < k < 1


class TestPrimarySelfInductance:
    def test_positive_and_cached(self):
        coil = _coil()
        lp1 = primary_geometric_self_inductance(coil.primary)
        lp2 = primary_geometric_self_inductance(coil.primary)
        assert lp1 > 0
        assert lp1 == lp2

    def test_javatc_value(self):
        """Direct check against JavaTC's primary Ldc = 25.713 uH."""
        coil = _coil()
        lp = primary_geometric_self_inductance(coil.primary) * mu_0 * 0.0254
        assert lp == pytest.approx(25.713e-6, rel=0.01)
