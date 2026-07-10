"""
End-to-end validation against JavaTC 13.6.

Runs the complete pipeline - geometry -> discretization -> FEM capacitance
matrix -> coaxial-ring inductance matrix -> eigen analysis - on the JavaTC
example coil and compares every fundamental output against the values in
docs/JavaTC Example Coil.txt.

Tolerances are chosen per quantity based on how directly the two codes
model it:

  * Wire length and pitch are pure geometry: near-exact.
  * Ldc sums the same ring-formula physics JavaTC uses: sub-percent.
  * f_res, Les, Ces, Lee, Cee exercise the full FEM + eigen pipeline;
    residual differences reflect JavaTC's grid-relaxation field solver
    vs our FEM, the ideal-vs-thin disc, and the axisymmetric ring
    approximation of the spiral primary.
  * Cdc is the most sensitive to how the grounded primary is represented
    (our model brackets JavaTC's value with/without it), hence the widest
    band.
  * R_dc differs by conductivity model (JavaTC uses AWG wire tables).

These tests are the accuracy contract of the project: do NOT loosen a
tolerance to make a regression pass.
"""
import pytest

from app.models.simulation_models import SimulatableTeslaCoil
from app.simulation.facade.simulation import TeslaCoilSimulation
from tests.simulation.test_coils import JAVATC_EXAMPLE_COIL


# JavaTC 13.6 consolidated output for the example coil
# (docs/JavaTC Example Coil.txt)
JAVATC = dict(
    f_res_hz=230.24e3,
    ldc_h=17.388e-3,
    les_h=17.230e-3,
    lee_h=17.808e-3,
    cdc_f=39.452e-12,
    ces_f=27.733e-12,
    cee_f=26.832e-12,
    wire_length_m=1063.4 * 0.3048,
    dc_resistance_ohm=27.0736,
    pitch_m=(21.8085 / 895) * 0.0254,
    # Tier 1/2 additions
    winding_length_m=21.81 * 0.0254,
    turns_per_inch=41.0,
    turn_spacing_m=0.00427 * 0.0254,
    aspect_ratio=4.81,
    inclination_deg=90.0,
    reactance_ohm=24925.0,
    skin_depth_m=6.34e-3 * 0.0254,       # see test comment - methods differ
    wire_weight_kg=1.3 * 0.45359237,
    topload_c_f=23.287e-12,
    ac_resistance_ohm=89.2104,
    quality_factor=279.0,
    # Tier 3: primary and coupling
    primary_ldc_h=25.713e-6,
    primary_lead_h=0.861e-6,
    primary_wire_m=25.89 * 0.3048,
    primary_rdc_ohm=4.3e-3,
    primary_spacing_m=0.25 * 0.0254,
    primary_f_hz=225.17e3,
    detuned_pct=2.2,
    lm_h=86.277e-6,
    coupling_k=0.129,
    half_cycles=7.75,
    transfer_time_s=17.03e-6,
)


@pytest.fixture(scope="module")
def simulation():
    """One full-pipeline simulation at the JavaTC-comparable resolution.

    Module-scoped: the FEM solve happens once and every assertion reads
    from the same cached matrices.
    """
    coil = SimulatableTeslaCoil(**JAVATC_EXAMPLE_COIL, discretization_order=30)
    return TeslaCoilSimulation(coil)


@pytest.fixture(scope="module")
def secondary_view(simulation):
    return simulation.secondary


class TestGeometryAndWire:
    def test_wire_length(self, secondary_view):
        assert secondary_view.conductor_length == pytest.approx(
            JAVATC["wire_length_m"], rel=0.001
        )

    def test_coil_pitch(self, secondary_view):
        assert secondary_view.coil_pitch == pytest.approx(JAVATC["pitch_m"], rel=0.001)

    def test_dc_resistance(self, secondary_view):
        assert secondary_view.dc_resistance == pytest.approx(
            JAVATC["dc_resistance_ohm"], rel=0.03
        )

    def test_winding_length(self, secondary_view):
        assert secondary_view.winding_length == pytest.approx(
            JAVATC["winding_length_m"], rel=0.001
        )

    def test_turns_per_length(self, secondary_view):
        assert secondary_view.turns_per_length * 0.0254 == pytest.approx(
            JAVATC["turns_per_inch"], rel=0.01
        )

    def test_turn_spacing(self, secondary_view):
        assert secondary_view.turn_spacing == pytest.approx(
            JAVATC["turn_spacing_m"], rel=0.01
        )

    def test_aspect_ratio(self, secondary_view):
        assert secondary_view.aspect_ratio == pytest.approx(
            JAVATC["aspect_ratio"], rel=0.005
        )

    def test_inclination(self, secondary_view):
        assert secondary_view.inclination_degrees == pytest.approx(
            JAVATC["inclination_deg"], abs=0.01
        )

    def test_wire_weight(self, secondary_view):
        # JavaTC prints one decimal (1.3 lbs), so the reference itself
        # carries ~4% quantization
        assert secondary_view.wire_weight == pytest.approx(
            JAVATC["wire_weight_kg"], rel=0.05
        )


class TestACLosses:
    def test_skin_depth(self, secondary_view):
        """Our value is the textbook 1/sqrt(pi*f*mu0*sigma) (5.34 mils at
        f_res); JavaTC prints 6.34 mils, an ~19% higher value from a
        different empirical constant. The loose band documents the method
        difference while still catching unit/order errors."""
        assert secondary_view.skin_depth == pytest.approx(
            JAVATC["skin_depth_m"], rel=0.20
        )

    def test_ac_resistance(self, secondary_view):
        assert secondary_view.ac_resistance == pytest.approx(
            JAVATC["ac_resistance_ohm"], rel=0.03
        )

    def test_quality_factor(self, secondary_view):
        assert secondary_view.quality_factor == pytest.approx(
            JAVATC["quality_factor"], rel=0.03
        )


class TestInductances:
    def test_ldc(self, secondary_view):
        assert secondary_view.dc_inductance == pytest.approx(JAVATC["ldc_h"], rel=0.01)

    def test_les(self, secondary_view):
        assert secondary_view.effective_series_inductance == pytest.approx(
            JAVATC["les_h"], rel=0.03
        )

    def test_lee(self, secondary_view):
        assert secondary_view.energy_inductance == pytest.approx(
            JAVATC["lee_h"], rel=0.03
        )


class TestCapacitances:
    def test_ces(self, secondary_view):
        assert secondary_view.effective_shunt_capacitance == pytest.approx(
            JAVATC["ces_f"], rel=0.03
        )

    def test_cee(self, secondary_view):
        assert secondary_view.energy_capacitance == pytest.approx(
            JAVATC["cee_f"], rel=0.03
        )

    def test_cdc(self, secondary_view):
        assert secondary_view.dc_capacitance == pytest.approx(
            JAVATC["cdc_f"], rel=0.12
        )


class TestToploadAndReactance:
    def test_topload_effective_capacitance(self, secondary_view):
        """DC-share attribution of the topload charge (the JavaTC
        definition - validated to 0.1% before this tolerance was set)."""
        assert secondary_view.topload_effective_capacitance == pytest.approx(
            JAVATC["topload_c_f"], rel=0.02
        )

    def test_reactance_at_resonance(self, secondary_view):
        assert secondary_view.reactance_at_resonance == pytest.approx(
            JAVATC["reactance_ohm"], rel=0.03
        )


class TestResonance:
    def test_fundamental_resonant_frequency(self, secondary_view):
        """The headline number: quarter-wave resonance vs JavaTC."""
        assert secondary_view.resonant_frequency == pytest.approx(
            JAVATC["f_res_hz"], rel=0.01
        )

    def test_lumped_equivalents_are_self_consistent(self, secondary_view):
        """Les*Ces and Lee*Cee must each resonate at f_res (this identity
        holds exactly in JavaTC's outputs too)."""
        import math
        f = secondary_view.resonant_frequency
        for L, C in (
            (secondary_view.effective_series_inductance,
             secondary_view.effective_shunt_capacitance),
            (secondary_view.energy_inductance,
             secondary_view.energy_capacitance),
        ):
            f_lc = 1.0 / (2 * math.pi * math.sqrt(L * C))
            assert f_lc == pytest.approx(f, rel=1e-6)

    def test_overtones_are_above_fundamental(self, secondary_view):
        freqs = secondary_view.eigen_frequencies
        assert freqs[0] < freqs[1] < freqs[2]


class TestPrimary:
    def test_dc_inductance(self, simulation):
        assert simulation.primary.dc_inductance == pytest.approx(
            JAVATC["primary_ldc_h"], rel=0.01
        )

    def test_lead_inductance(self, simulation):
        assert simulation.primary.lead_inductance == pytest.approx(
            JAVATC["primary_lead_h"], rel=0.005
        )

    def test_wire_length(self, simulation):
        assert simulation.primary.wire_length == pytest.approx(
            JAVATC["primary_wire_m"], rel=0.01
        )

    def test_dc_resistance(self, simulation):
        # JavaTC prints one decimal (4.3 mOhm): ~2.5% quantization in the
        # reference plus the conductivity-model difference
        assert simulation.primary.dc_resistance == pytest.approx(
            JAVATC["primary_rdc_ohm"], rel=0.06
        )

    def test_turn_spacing(self, simulation):
        assert simulation.primary.turn_spacing == pytest.approx(
            JAVATC["primary_spacing_m"], rel=0.01
        )

    def test_resonant_frequency(self, simulation):
        assert simulation.primary.resonant_frequency == pytest.approx(
            JAVATC["primary_f_hz"], rel=0.005
        )

    def test_percent_detuned(self, simulation):
        """Combines both resonance errors (our f_sec runs ~0.4% above
        JavaTC's), hence the absolute band."""
        assert simulation.primary.percent_detuned == pytest.approx(
            JAVATC["detuned_pct"], abs=0.5
        )


class TestCoupling:
    def test_mutual_inductance(self, simulation):
        assert simulation.coupling.mutual_inductance == pytest.approx(
            JAVATC["lm_h"], rel=0.01
        )

    def test_coupling_coefficient(self, simulation):
        assert simulation.coupling.coupling_coefficient == pytest.approx(
            JAVATC["coupling_k"], rel=0.02
        )

    def test_half_cycles(self, simulation):
        assert simulation.coupling.half_cycles_for_energy_transfer == pytest.approx(
            JAVATC["half_cycles"], rel=0.02
        )

    def test_energy_transfer_time(self, simulation):
        assert simulation.coupling.energy_transfer_time == pytest.approx(
            JAVATC["transfer_time_s"], rel=0.02
        )

    def test_bordered_matrix_positive_definite(self, simulation):
        """The combined [[L, m],[m^T, L_p]] matrix of the coupled system
        must be PD (physical coupling, k < 1)."""
        import numpy as np
        bordered = np.array(simulation.coupling.bordered_inductance_matrix)
        assert np.all(np.linalg.eigvalsh(bordered) > 0)


class TestCoupledSolve:
    """The full coupled solve - beyond JavaTC's independent resonators."""

    def test_split_pair_brackets_uncoupled_resonances(self, simulation):
        f_p = simulation.primary.resonant_frequency
        f_s = simulation.secondary.resonant_frequency
        lo, hi = simulation.coupled.split_frequencies
        # The two coupled modes straddle both uncoupled resonances
        assert lo < min(f_p, f_s)
        assert hi > max(f_p, f_s)

    def test_split_scales_with_coupling(self, simulation):
        """The fractional split is on the order of the coupling coefficient
        (k ~ 0.13 -> tens of kHz around ~230 kHz)."""
        k = simulation.coupling.coupling_coefficient
        lo, hi = simulation.coupled.split_frequencies
        f_mid = 0.5 * (lo + hi)
        fractional_split = (hi - lo) / f_mid
        assert 0.5 * k < fractional_split < 2.0 * k

    def test_impedance_peaks_in_band(self, simulation):
        import numpy as np
        f = np.linspace(200e3, 260e3, 400)
        Z = simulation.coupled.primary_input_impedance(f, include_losses=True)
        peak_f = f[int(np.argmax(np.abs(Z)))]
        assert 220e3 < peak_f < 245e3
