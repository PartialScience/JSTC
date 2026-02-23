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
To add a new solver         → add a pytest.param below and an elif branch
"""
import pytest
from app.models.simulation_models import SimulatableTeslaCoil
from app.simulation.C_matrix_solvers import FEMCapacitanceMatrixSolver
from app.simulation.L_matrix_solvers import IntegralInductanceLMatrixSolver
from tests.simulation.test_coils import TEST_COILS


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
# Coil fixture — one SimulatableTeslaCoil per TEST_COILS entry × disc. order
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

@pytest.fixture(params=[
    pytest.param("fem", id="FEM"),
    # pytest.param("bem", id="BEM"),  # ← register future solvers here
])
def capacitance_matrix(request, coil):
    """
    Compute and return a capacitance matrix from the parameterized solver.

    Skips automatically when the solver is still a placeholder (returns None).
    """
    if request.param == "fem":
        result = FEMCapacitanceMatrixSolver.compute_capacitance_matrix(
            secondary=coil.secondary,
            toploads=coil.toploads,
            grounds=coil.grounds,
            discretization_order=coil.discretization_order,
            r_max=coil.r_max,
            z_max=coil.z_max,
        )
    else:
        raise ValueError(f"Unknown capacitance solver: {request.param}")

    if result is None:
        pytest.skip(f"Capacitance solver '{request.param}' not yet implemented")

    return result


# ---------------------------------------------------------------------------
# Parameterized inductance-matrix fixture
# ---------------------------------------------------------------------------

@pytest.fixture(params=[
    pytest.param("integral", id="Integral"),
    # pytest.param("analytical", id="Analytical"),  # ← register future solvers here
])
def inductance_matrix(request, coil):
    """
    Compute and return an inductance matrix from the parameterized solver.

    Skips automatically when the solver is still a placeholder (returns None).
    """
    if request.param == "integral":
        result = IntegralInductanceLMatrixSolver.compute_inductance_matrix(
            secondary=coil.secondary,
            discretization_order=coil.discretization_order,
        )
    else:
        raise ValueError(f"Unknown inductance solver: {request.param}")

    if result is None:
        pytest.skip(f"Inductance solver '{request.param}' not yet implemented")

    return result
