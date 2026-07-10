"""
Concurrency regression tests for the FEM solve path.

pypardiso routes through a process-global solver instance that is not
thread-safe; concurrent solves used to corrupt its shared state and segfault
the process. _solve_multi serializes the PARDISO call, so these must run
correctly (and not crash) under many threads.

If the serialization regresses these tests will not merely fail - they can
take down the whole test process (a C-level crash in MKL). That loud failure
is intentional: it is exactly the production failure mode we are guarding.
"""
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest
import scipy.sparse as sp

from app.simulation.electrostatics.axisymmetric import _solve_multi


def _spd_system(n: int, seed: int):
    """A distinct SPD system A x = b with a known solution x."""
    rng = np.random.default_rng(seed)
    M = rng.standard_normal((n, n))
    A = sp.csr_matrix(M @ M.T + n * np.eye(n))
    x = rng.standard_normal((n, 3))
    return A, A @ x, x


class TestSolveMultiConcurrency:
    def test_many_concurrent_distinct_solves_are_correct(self):
        # Distinct matrices maximize the chance that an unsynchronized shared
        # solver returns the wrong factorization's answer.
        systems = [_spd_system(300, seed) for seed in range(12)]

        def solve(i):
            A, b, x = systems[i]
            out = _solve_multi(A, b)
            return np.allclose(out.reshape(x.shape), x, rtol=1e-6)

        # Repeat to shake out races.
        for _ in range(4):
            with ThreadPoolExecutor(max_workers=8) as ex:
                oks = list(ex.map(solve, range(len(systems))))
            assert all(oks), "a concurrent solve returned the wrong result"


class TestFemPipelineConcurrency:
    """The full mesh->solve pipeline across threads (as the API serves it)."""

    def test_concurrent_capacitance_matches_serial(self):
        from app.models.simulation_models import SimulatableTeslaCoil
        from app.simulation.facade.simulation import TeslaCoilSimulation
        from tests.simulation.test_coils import JAVATC_EXAMPLE_COIL

        orders = [24, 28, 32, 36]

        def compute(order):
            coil = SimulatableTeslaCoil(**JAVATC_EXAMPLE_COIL, discretization_order=order)
            return order, np.array(
                TeslaCoilSimulation(coil).secondary.nodal_capacitance_matrix_geo
            )

        serial = {o: compute(o)[1] for o in orders}

        with ThreadPoolExecutor(max_workers=len(orders)) as ex:
            results = list(ex.map(lambda o: compute(o), orders))

        for order, C in results:
            ref = serial[order]
            assert C.shape == ref.shape
            assert np.allclose(C, ref, rtol=1e-6), (
                f"order {order}: concurrent result differs from serial"
            )
