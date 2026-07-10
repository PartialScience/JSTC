"""
Tests for the coupled primary-secondary solve.

The core validations are analytic: a single-segment secondary tuned to the
primary is the textbook two-coupled-resonator problem, whose modes are
f0/sqrt(1 +/- k). This pins down every sign in the state matrix.
"""
import numpy as np
import pytest

from app.simulation.coupled.coupled_system import (
    CoupledSystem,
    coupled_mode_frequencies,
    primary_input_impedance,
)


def _tuned_pair(f0=100e3, k=0.1, Ls=1e-3, Lp=1e-3):
    """A 1-segment secondary and primary both tuned to f0, coupling k."""
    w0 = 2 * np.pi * f0
    Cs = 1 / (w0 ** 2 * Ls)
    Cp = 1 / (w0 ** 2 * Lp)
    m = k * np.sqrt(Ls * Lp)
    return CoupledSystem(
        capacitance=np.array([[Cs]]),
        inductance=np.array([[Ls]]),
        connectivity=np.array([[1.0]]),
        coupling=np.array([m]),
        primary_inductance=Lp,
        tank_capacitance=Cp,
    )


class TestFrequencySplitting:
    @pytest.mark.parametrize("k", [0.05, 0.1, 0.2, 0.35])
    def test_split_matches_analytic(self, k):
        f0 = 100e3
        sys = _tuned_pair(f0=f0, k=k)
        freqs = coupled_mode_frequencies(sys)
        expected = np.sort([f0 / np.sqrt(1 + k), f0 / np.sqrt(1 - k)])
        assert np.allclose(freqs, expected, rtol=1e-6)

    def test_two_modes_bracket_f0(self):
        f0 = 100e3
        freqs = coupled_mode_frequencies(_tuned_pair(f0=f0, k=0.15))
        assert freqs[0] < f0 < freqs[1]

    def test_larger_coupling_wider_split(self):
        f0 = 100e3
        narrow = coupled_mode_frequencies(_tuned_pair(f0=f0, k=0.05))
        wide = coupled_mode_frequencies(_tuned_pair(f0=f0, k=0.25))
        assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])


class TestDecouplingLimit:
    def test_zero_coupling_recovers_both_resonators(self):
        f0 = 100e3
        sys = _tuned_pair(f0=f0, k=0.0)
        freqs = coupled_mode_frequencies(sys)
        assert np.allclose(freqs, [f0, f0], rtol=1e-6)

    def test_detuned_uncoupled_gives_two_distinct(self):
        """m=0, primary and secondary at different frequencies -> the two
        independent resonances appear unchanged."""
        w = 2 * np.pi
        Ls = Lp = 1e-3
        Cs = 1 / ((w * 90e3) ** 2 * Ls)
        Cp = 1 / ((w * 110e3) ** 2 * Lp)
        sys = CoupledSystem(
            capacitance=np.array([[Cs]]), inductance=np.array([[Ls]]),
            connectivity=np.array([[1.0]]), coupling=np.array([0.0]),
            primary_inductance=Lp, tank_capacitance=Cp,
        )
        freqs = coupled_mode_frequencies(sys)
        assert np.allclose(freqs, [90e3, 110e3], rtol=1e-6)


class TestPrimaryInputImpedance:
    def test_lossless_winding_peaks_at_secondary_resonance(self):
        """Without the tank, the reflected secondary makes |Z| spike at the
        secondary resonance."""
        f0 = 100e3
        sys = _tuned_pair(f0=f0, k=0.1)
        f = np.linspace(90e3, 110e3, 5000)
        Z = primary_input_impedance(sys, f, include_tank=False)
        peak_f = f[np.argmax(np.abs(Z))]
        assert peak_f == pytest.approx(f0, rel=1e-3)

    def test_resistance_makes_peak_finite(self):
        sys = _tuned_pair()
        f = np.linspace(90e3, 110e3, 2000)
        z_lossless = np.abs(primary_input_impedance(sys, f, include_tank=False))
        z_lossy = np.abs(primary_input_impedance(
            sys, f, secondary_resistance=50.0, include_tank=False))
        assert z_lossy.max() < z_lossless.max()

    def test_tank_impedance_zero_crossings_at_modes(self):
        """With the tank included, the reactance crosses zero at the coupled
        modes (series-resonance condition)."""
        f0 = 100e3
        sys = _tuned_pair(f0=f0, k=0.12)
        modes = coupled_mode_frequencies(sys)
        f = np.linspace(85e3, 120e3, 20000)
        X = primary_input_impedance(sys, f, include_tank=True).imag
        sign_changes = f[:-1][np.diff(np.sign(X)) != 0]
        # Each mode should have a nearby reactance zero crossing
        for mode in modes:
            assert np.min(np.abs(sign_changes - mode)) < 200.0


class TestValidation:
    def test_rejects_bad_shapes(self):
        with pytest.raises(ValueError):
            CoupledSystem(
                capacitance=np.eye(3), inductance=np.eye(2),
                connectivity=np.eye(3), coupling=np.zeros(3),
                primary_inductance=1e-3, tank_capacitance=1e-9,
            )

    def test_rejects_nonpositive_tank(self):
        with pytest.raises(ValueError):
            CoupledSystem(
                capacitance=np.eye(2), inductance=np.eye(2),
                connectivity=np.eye(2), coupling=np.zeros(2),
                primary_inductance=1e-3, tank_capacitance=0.0,
            )
