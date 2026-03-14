"""
Shared fixtures for simulation tests.

Fixture dependency graph::

    discretization_order          (parameterized: 10, 30, 50)
            │
            ▼
         coil                     (parameterized: test_coils.TEST_COILS)
            │                      → SimulatableTeslaCoil
            │
      ┌─────┴──────┐
      ▼             ▼
 capacitance    inductance        (parameterized: solver implementation)
   _matrix        _matrix          → Tuple[Tuple[float, ...], ...]

To add a new coil geometry  → edit tests/simulation/test_coils.py
To add a new solver         → add it to the registry in the corresponding test file
"""
import pytest
from app.models.simulation_models import SimulatableTeslaCoil
from app.simulation.coil_discretizers.uniform_arclength_discretizer import UniformArcLengthDiscretizer
from tests.simulation.test_coils import TEST_COILS
from tests.simulation.distributed_element_matrices.capacitance.test_capacitance_solvers import CAPACITANCE_SOLVERS
from tests.simulation.distributed_element_matrices.inductance.test_inductance_solvers import INDUCTANCE_SOLVERS


# ---------------------------------------------------------------------------
# Discretization order — varied independently of coil geometry
# ---------------------------------------------------------------------------

@pytest.fixture(
    params=[10, 30, 50], 
    ids=lambda x: f"N={x}"
)
def discretization_order(request):
    """Number of virtual conductors (varied across tests)."""
    return request.param


# ---------------------------------------------------------------------------
# Coil fixture — one SimulatableTeslaCoil per TEST_COILS entry x disc. order
# ---------------------------------------------------------------------------

@pytest.fixture(
    params=TEST_COILS,
)
def coil(request, discretization_order) -> SimulatableTeslaCoil:
    """
    Build a SimulatableTeslaCoil from the test_coils catalogue.

    ``discretization_order`` is injected separately so each coil
    is tested at every resolution.
    """
    return SimulatableTeslaCoil(
        **request.param,
        discretization_order=discretization_order,
    )


# ---------------------------------------------------------------------------
# Parameterized capacitance-matrix fixture
# ---------------------------------------------------------------------------

@pytest.fixture(params=CAPACITANCE_SOLVERS)
def capacitance_matrix(request, coil):
    """
    Compute and return a capacitance matrix from the parameterized solver.

    Skips automatically when the solver is still a placeholder (returns None).
    """
    solver_cls = request.param
    discretizer = UniformArcLengthDiscretizer()
    solver = solver_cls(discretizer=discretizer)
    result = solver.compute_capacitance_matrix(
        secondary=coil.secondary,
        toploads=coil.toploads,
        grounds=coil.grounds,
        discretization_order=coil.discretization_order,
        r_max=coil.r_max,
        z_max=coil.z_max,
    )

    if result is None:
        pytest.skip(f"Capacitance solver '{solver_cls.__name__}' not yet implemented")

    return result


# ---------------------------------------------------------------------------
# Parameterized inductance-matrix fixture
# ---------------------------------------------------------------------------

@pytest.fixture(params=INDUCTANCE_SOLVERS)
def inductance_matrix(request, coil):
    """
    Compute and return an inductance matrix from the parameterized solver.

    Skips automatically when the solver is still a placeholder (returns None).
    """
    solver_cls = request.param
    discretizer = UniformArcLengthDiscretizer()
    solver = solver_cls(discretizer=discretizer)
    result = solver.geometric_inductance_matrix(
        secondary=coil.secondary,
        discretization_order=coil.discretization_order,
    )

    if result is None:
        pytest.skip(f"Inductance solver '{solver_cls.__name__}' not yet implemented")

    return result
