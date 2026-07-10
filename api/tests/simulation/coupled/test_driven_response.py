"""
Tests for the phasor drive solve (the operating state the field
visualization superposes).
"""
import numpy as np
import pytest

from app.simulation.coupled.coupled_system import (
    CoupledSystem,
    primary_driven_response,
    primary_input_impedance,
)


def _system(n=6, seed=1):
    rng = np.random.default_rng(seed)
    M = rng.standard_normal((n, n))
    C = (M @ M.T + n * np.eye(n)) * 1e-12
    M2 = rng.standard_normal((n, n))
    L = (M2 @ M2.T + n * np.eye(n)) * 1e-6
    A = np.eye(n) + np.diag([-1.0] * (n - 1), k=1)
    Lp = 2e-5
    m = rng.uniform(0.02, 0.08, n) * np.sqrt(np.diag(L) * Lp)
    return CoupledSystem(
        capacitance=C, inductance=L, connectivity=A, coupling=m,
        primary_inductance=Lp, tank_capacitance=5e-9,
    )


class TestConsistency:
    def test_vp_over_ip_matches_winding_impedance(self):
        """V_p / I_p must equal the winding driving-point impedance (the
        include_tank=False impedance) at the same frequency - an independent
        derivation of the same quantity."""
        sys = _system()
        f = 180e3
        r = primary_driven_response(sys, f, primary_current=1.0)
        z_winding = primary_input_impedance(
            sys, np.array([f]), include_tank=False
        )[0]
        assert r.primary_voltage / r.primary_current == pytest.approx(z_winding, rel=1e-9)

    def test_with_losses_matches_lossy_impedance(self):
        sys = _system()
        f = 210e3
        r = primary_driven_response(
            sys, f, primary_current=2.0,
            secondary_resistance=40.0, primary_resistance=1.5,
        )
        z = primary_input_impedance(
            sys, np.array([f]), secondary_resistance=40.0,
            primary_resistance=1.5, include_tank=False,
        )[0]
        assert r.primary_voltage / r.primary_current == pytest.approx(z, rel=1e-9)

    def test_node_continuity(self):
        """The returned V and I satisfy j w C V = A I (nodal continuity)."""
        sys = _system()
        f = 150e3
        r = primary_driven_response(sys, f, primary_current=1.0)
        w = r.omega
        lhs = 1j * w * sys.capacitance @ r.node_voltages
        rhs = sys.connectivity @ r.segment_currents
        assert np.allclose(lhs, rhs, rtol=1e-9)


class TestLinearityAndShape:
    def test_scales_linearly_with_drive(self):
        sys = _system()
        f = 190e3
        r1 = primary_driven_response(sys, f, primary_current=1.0)
        r3 = primary_driven_response(sys, f, primary_current=3.0)
        assert np.allclose(r3.segment_currents, 3 * r1.segment_currents, rtol=1e-9)
        assert np.allclose(r3.node_voltages, 3 * r1.node_voltages, rtol=1e-9)
        assert r3.primary_voltage == pytest.approx(3 * r1.primary_voltage, rel=1e-9)

    def test_shapes(self):
        sys = _system(n=8)
        r = primary_driven_response(sys, 200e3)
        assert r.segment_currents.shape == (8,)
        assert r.node_voltages.shape == (8,)
        assert np.iscomplexobj(r.segment_currents)
        assert np.iscomplexobj(r.node_voltages)


class TestResonantBehavior:
    def test_secondary_voltage_peaks_near_a_coupled_mode(self):
        """Sweeping the drive, the secondary voltage magnitude is maximal near
        a coupled resonance (lightly damped so the peak is sharp)."""
        from app.simulation.coupled.coupled_system import coupled_mode_frequencies

        sys = _system()
        modes = coupled_mode_frequencies(sys)
        lower = modes[0]

        def vmag(f):
            r = primary_driven_response(
                sys, f, primary_current=1.0, secondary_resistance=0.5
            )
            return np.max(np.abs(r.node_voltages))

        # Sweep across all coupled modes; the peak coincides with whichever
        # mode couples strongest to the primary drive.
        sweep = np.linspace(modes.min() * 0.8, modes.max() * 1.2, 800)
        mags = np.array([vmag(f) for f in sweep])
        peak_f = sweep[np.argmax(mags)]

        nearest_mode_gap = np.min(np.abs(modes - peak_f)) / peak_f
        assert nearest_mode_gap < 0.03, "driven peak does not sit on a coupled mode"
        assert mags.max() > 20 * vmag(lower * 0.4)
