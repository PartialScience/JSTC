"""
SPICE export tests.

Without a SPICE engine in the test environment, correctness is checked by
round-trip: the netlist is parsed back into a CoupledSystem, which must
reproduce the original matrices AND the original coupled mode frequencies
(so the exported network is electrically equivalent, not just textually
plausible).
"""
import numpy as np
import pytest

from app.simulation.coupled.coupled_system import CoupledSystem, coupled_mode_frequencies
from app.simulation.coupled.spice_export import (
    export_spice_subcircuit,
    reconstruct_from_spice,
)


def _multi_segment_system(n=5, seed=0):
    """A small but non-trivial coupled system (SPD C and L, real coupling)."""
    rng = np.random.default_rng(seed)
    M = rng.standard_normal((n, n))
    C = M @ M.T + n * np.eye(n)
    M2 = rng.standard_normal((n, n))
    L = (M2 @ M2.T + n * np.eye(n)) * 1e-6
    A = np.eye(n) + np.diag([-1.0] * (n - 1), k=1)
    # coupling small enough to keep the bordered matrix PD
    Lp = 2e-5
    m = rng.uniform(0.02, 0.1, n) * np.sqrt(np.diag(L) * Lp)
    C = C * 1e-12
    return CoupledSystem(
        capacitance=C, inductance=L, connectivity=A, coupling=m,
        primary_inductance=Lp, tank_capacitance=5e-9,
    )


class TestNetlistStructure:
    def test_has_subckt_wrapper_and_ports(self):
        sys = _multi_segment_system(n=3)
        net = export_spice_subcircuit(sys, name="tc")
        assert ".subckt tc prim_in prim_gnd" in net
        assert ".ends tc" in net

    def test_element_counts(self):
        n = 4
        sys = _multi_segment_system(n=n)
        net = export_spice_subcircuit(sys)
        lines = [l for l in net.splitlines() if l and not l.startswith((".", "*"))]
        assert sum(l.startswith("Lseg") for l in lines) == n
        assert sum(l.startswith("Csh") for l in lines) == n
        assert any(l.startswith("Lprim") for l in lines)
        assert any(l.startswith("Ctank") for l in lines)

    def test_coupling_coefficients_physical(self):
        """Every K coefficient must lie strictly within (-1, 1)."""
        sys = _multi_segment_system(n=5)
        net = export_spice_subcircuit(sys)
        for line in net.splitlines():
            if line.startswith("K"):
                coeff = float(line.split()[-1])
                assert -1.0 < coeff < 1.0


class TestRoundTrip:
    @pytest.mark.parametrize("n", [1, 3, 5, 12])
    def test_matrices_reconstructed(self, n):
        sys = _multi_segment_system(n=n)
        net = export_spice_subcircuit(sys)
        back = reconstruct_from_spice(net)
        assert np.allclose(back.capacitance, sys.capacitance, rtol=1e-9)
        assert np.allclose(back.inductance, sys.inductance, rtol=1e-9)
        assert np.allclose(back.coupling, sys.coupling, rtol=1e-9)
        assert back.primary_inductance == pytest.approx(sys.primary_inductance)
        assert back.tank_capacitance == pytest.approx(sys.tank_capacitance)

    @pytest.mark.parametrize("n", [3, 8])
    def test_mode_frequencies_preserved(self, n):
        """The exported network is electrically equivalent: same modes."""
        sys = _multi_segment_system(n=n)
        back = reconstruct_from_spice(export_spice_subcircuit(sys))
        assert np.allclose(
            coupled_mode_frequencies(sys),
            coupled_mode_frequencies(back),
            rtol=1e-7,
        )
