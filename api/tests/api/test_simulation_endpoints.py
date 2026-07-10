"""
Integration tests for the simulation endpoints.

The router functions are plain callables taking pydantic request models, so
these exercise the full path - schema -> convert -> facade -> solve/reuse
-> response - without needing an HTTP client. One FEM solve happens
(module-scoped) and every reuse test runs against that cached bundle.
"""
import copy

import pytest
from fastapi import HTTPException

from app.routers.simulation import analyze, compute_matrices, impedance, spice
from app.schemas import (
    AnalyzeRequest,
    ImpedanceRequest,
    MatricesRequest,
    SpiceRequest,
)
from tests.api.javatc_coil_schema import JAVATC_COIL_PAYLOAD


# JavaTC reference values (SI) for the endpoint-level checks
JAVATC = dict(
    f_res_hz=230.24e3, cdc_f=39.452e-12, lm_h=86.277e-6, k=0.129,
    primary_f_hz=225.17e3, topload_c_f=23.287e-12,
)


@pytest.fixture(scope="module")
def matrices_response():
    """One /matrices call (the slow FEM solve) shared by all reuse tests."""
    return compute_matrices(MatricesRequest.model_validate({"coil": JAVATC_COIL_PAYLOAD}))


class TestMatricesEndpoint:
    def test_returns_bundle(self, matrices_response):
        b = matrices_response
        assert b.discretization_order == 30
        assert len(b.nodal_capacitance) == 31          # (N+1)x(N+1)
        assert len(b.nodal_capacitance[0]) == 31
        assert len(b.inductance) == 30                 # NxN
        assert len(b.coupling) == 30                   # N (has primary)
        assert len(b.topload_charge) == 31
        assert b.geometry_fingerprint


class TestAnalyzeWithBundle:
    @pytest.fixture(scope="class")
    def response(self, matrices_response):
        req = AnalyzeRequest.model_validate({
            "coil": JAVATC_COIL_PAYLOAD,
            "bundle": matrices_response.model_dump(),
        })
        return analyze(req)

    def test_secondary_matches_javatc(self, response):
        sec = response.secondary
        assert sec.resonant_frequency == pytest.approx(JAVATC["f_res_hz"], rel=0.01)
        assert sec.dc_capacitance == pytest.approx(JAVATC["cdc_f"], rel=0.12)
        assert sec.topload_effective_capacitance == pytest.approx(
            JAVATC["topload_c_f"], rel=0.02
        )
        assert len(sec.eigen_frequencies) == 30

    def test_primary_and_coupling_present(self, response):
        assert response.primary is not None
        assert response.coupling is not None
        assert response.primary.resonant_frequency == pytest.approx(
            JAVATC["primary_f_hz"], rel=0.01
        )
        assert response.coupling.mutual_inductance == pytest.approx(
            JAVATC["lm_h"], rel=0.01
        )
        assert response.coupling.coupling_coefficient == pytest.approx(
            JAVATC["k"], rel=0.02
        )

    def test_eigenmodes_shapes_and_convention(self, response):
        """The modes section carries every voltage/current mode shape, with
        the grounded base node in the voltage profile and the sign fixed so
        each mode's top voltage is non-negative."""
        m = response.modes
        n = len(response.secondary.eigen_frequencies)  # 30
        assert m.frequencies == pytest.approx(response.secondary.eigen_frequencies)
        # voltage carries the grounded base node -> one extra sample
        assert len(m.voltage_positions) == n + 1
        assert len(m.current_positions) == n
        # Positions are arc length (m): 0 at the base, winding_length at the top,
        # strictly increasing; currents sit strictly inside that span.
        assert m.voltage_positions[0] == 0.0
        assert m.voltage_positions[-1] == pytest.approx(
            response.secondary.winding_length
        )
        assert all(b > a for a, b in zip(m.voltage_positions, m.voltage_positions[1:]))
        assert 0.0 < m.current_positions[0] < m.current_positions[-1] < m.voltage_positions[-1]
        assert len(m.voltage_modes) == n and len(m.current_modes) == n
        for vmode, imode in zip(m.voltage_modes, m.current_modes):
            assert len(vmode) == n + 1
            assert len(imode) == n
            assert vmode[0] == 0.0            # grounded base
            assert vmode[-1] >= 0.0           # sign convention: top V positive

    def test_echoes_bundle(self, response, matrices_response):
        """The response carries the bundle back so the client can keep
        reusing it."""
        assert response.bundle.geometry_fingerprint == matrices_response.geometry_fingerprint

    def test_coupled_split_brackets_uncoupled(self, response):
        """The coupled solve returns a split pair bracketing the primary
        (~225 kHz) and secondary (~230 kHz) resonances."""
        c = response.coupled
        assert c is not None
        assert c.split_lower < 225e3 < 235e3 < c.split_upper
        assert c.frequency_split == pytest.approx(c.split_upper - c.split_lower)
        assert len(c.mode_frequencies) >= 2


class TestImpedanceEndpoint:
    def test_sweep_peaks_near_secondary_resonance(self, matrices_response):
        freqs = [180e3 + i * 1e3 for i in range(120)]  # 180..300 kHz
        req = ImpedanceRequest.model_validate({
            "coil": JAVATC_COIL_PAYLOAD,
            "bundle": matrices_response.model_dump(),
            "frequencies_hz": freqs,
            "include_losses": True,
        })
        resp = impedance(req)
        assert len(resp.points) == len(freqs)
        peak = max(resp.points, key=lambda p: p.magnitude)
        assert 220e3 < peak.frequency_hz < 245e3
        # magnitude and components are consistent
        assert peak.magnitude == pytest.approx(
            (peak.resistance ** 2 + peak.reactance ** 2) ** 0.5
        )

    def test_requires_tank(self, matrices_response):
        payload = copy.deepcopy(JAVATC_COIL_PAYLOAD)
        payload["primary"]["tank_capacitance"] = 0.0
        req = ImpedanceRequest.model_validate({
            "coil": payload, "frequencies_hz": [230e3],
        })
        with pytest.raises(HTTPException) as exc:
            impedance(req)
        assert exc.value.status_code == 422


class TestSpiceEndpoint:
    def test_returns_subcircuit(self, matrices_response):
        req = SpiceRequest.model_validate({
            "coil": JAVATC_COIL_PAYLOAD,
            "bundle": matrices_response.model_dump(),
            "subcircuit_name": "mycoil",
        })
        resp = spice(req)
        assert ".subckt mycoil prim_in prim_gnd" in resp.netlist
        assert ".ends mycoil" in resp.netlist
        assert "Lprim" in resp.netlist and "Ctank" in resp.netlist


class TestBundleReuseSemantics:
    def test_cheap_param_change_reuses_bundle(self, matrices_response):
        """Changing unit_scale must NOT invalidate the bundle - it rescales
        the answers without a re-solve."""
        payload = copy.deepcopy(JAVATC_COIL_PAYLOAD)
        payload["unit_scale"] = 1.0  # was 0.0254; pure post-processing change
        req = AnalyzeRequest.model_validate({
            "coil": payload, "bundle": matrices_response.model_dump(),
        })
        response = analyze(req)  # must not raise
        # Geometric-unit answers now differ from the inches run; sanity: finite
        assert response.secondary.resonant_frequency > 0

    def test_stale_bundle_raises_409(self, matrices_response):
        """Changing geometry (r_max) makes the bundle stale -> 409."""
        payload = copy.deepcopy(JAVATC_COIL_PAYLOAD)
        payload["r_max"] = 120
        req = AnalyzeRequest.model_validate({
            "coil": payload, "bundle": matrices_response.model_dump(),
        })
        with pytest.raises(HTTPException) as exc:
            analyze(req)
        assert exc.value.status_code == 409

    def test_discretization_change_raises_409(self, matrices_response):
        payload = copy.deepcopy(JAVATC_COIL_PAYLOAD)
        payload["discretization_order"] = 20
        req = AnalyzeRequest.model_validate({
            "coil": payload, "bundle": matrices_response.model_dump(),
        })
        with pytest.raises(HTTPException) as exc:
            analyze(req)
        assert exc.value.status_code == 409


class TestAnalyzeWithoutBundle:
    def test_no_primary_coil(self):
        """A coil with no primary computes inline and returns null
        primary/coupling sections."""
        payload = copy.deepcopy(JAVATC_COIL_PAYLOAD)
        payload["primary"] = None
        # Coarsen the mesh so this inline FEM solve is quick
        req = AnalyzeRequest.model_validate({"coil": payload})
        response = analyze(req)
        assert response.primary is None
        assert response.coupling is None
        assert response.secondary.resonant_frequency > 0
        assert response.bundle.geometry_fingerprint
