"""
Integration tests for the /simulation/drive endpoint: the operating-mode
phasor profiles along the secondary at a given drive.
"""
import math

import pytest
from fastapi import HTTPException

from app.routers.simulation import compute_matrices, drive
from app.schemas import DriveRequest, MatricesRequest
from tests.api.javatc_coil_schema import JAVATC_COIL_PAYLOAD


@pytest.fixture(scope="module")
def bundle():
    return compute_matrices(MatricesRequest.model_validate({"coil": JAVATC_COIL_PAYLOAD}))


def _drive(bundle, frequency_hz=220e3, primary_current=100.0):
    return drive(DriveRequest.model_validate({
        "coil": JAVATC_COIL_PAYLOAD,
        "bundle": bundle.model_dump(),
        "frequency_hz": frequency_hz,
        "primary_current": primary_current,
    }))


class TestShapes:
    def test_profile_shapes_and_conventions(self, bundle):
        r = _drive(bundle)
        n_nodes = len(r.voltage_positions)
        assert len(r.voltage_real) == len(r.voltage_imag) == n_nodes
        assert len(r.current_positions) == n_nodes - 1
        assert len(r.current_real) == len(r.current_imag) == n_nodes - 1
        # Grounded base node first, at arc length 0, pinned to 0 V
        assert r.voltage_positions[0] == pytest.approx(0.0)
        assert r.voltage_real[0] == 0.0 and r.voltage_imag[0] == 0.0
        # Current midpoints interleave the voltage nodes
        for s_mid, (a, b) in zip(
            r.current_positions, zip(r.voltage_positions[:-1], r.voltage_positions[1:])
        ):
            assert a < s_mid < b

    def test_voltage_magnitude_rises_to_the_top(self, bundle):
        """Near the fundamental the winding is a quarter-wave resonator:
        |V| grows monotonically-ish from base to top."""
        r = _drive(bundle)
        mags = [math.hypot(re, im) for re, im in zip(r.voltage_real, r.voltage_imag)]
        assert mags[-1] == max(mags)
        assert mags[-1] > 10 * mags[1]

    def test_linear_in_the_drive_current(self, bundle):
        a = _drive(bundle, primary_current=1.0)
        b = _drive(bundle, primary_current=100.0)
        va = math.hypot(a.voltage_real[-1], a.voltage_imag[-1])
        vb = math.hypot(b.voltage_real[-1], b.voltage_imag[-1])
        assert vb == pytest.approx(100.0 * va, rel=1e-9)

    def test_matches_the_field_view_drive(self, bundle):
        """The pane's profiles are the SAME solve the field view is seeded
        with - assert against the facade directly."""
        from app.converters import bundle_from_schema, coil_from_schema
        from app.simulation.facade.simulation import TeslaCoilSimulation
        from app.schemas.coil_schemas import SimulatableTeslaCoilSchema

        r = _drive(bundle, frequency_hz=225e3, primary_current=42.0)
        coil_schema = SimulatableTeslaCoilSchema.model_validate(JAVATC_COIL_PAYLOAD)
        sim = TeslaCoilSimulation(
            coil_from_schema(coil_schema), matrices=bundle_from_schema(bundle)
        )
        ref = sim.coupled.driven_response(225e3, primary_current=42.0)
        assert r.voltage_real[-1] == pytest.approx(float(ref.node_voltages[-1].real), rel=1e-12)
        assert r.current_real[0] == pytest.approx(float(ref.segment_currents[0].real), rel=1e-12)
        assert r.primary_voltage_imag == pytest.approx(float(ref.primary_voltage.imag), rel=1e-12)


class TestValidation:
    def test_requires_a_tank_capacitance(self, bundle):
        payload = {**JAVATC_COIL_PAYLOAD, "primary": {**JAVATC_COIL_PAYLOAD["primary"], "tank_capacitance": 0.0}}
        with pytest.raises(HTTPException) as exc:
            drive(DriveRequest.model_validate({
                "coil": payload, "frequency_hz": 220e3,
            }))
        assert exc.value.status_code == 422

    def test_rejects_nonpositive_inputs(self):
        for bad in ({"frequency_hz": 0.0}, {"frequency_hz": 2e5, "primary_current": 0.0}):
            with pytest.raises(Exception):
                DriveRequest.model_validate({"coil": JAVATC_COIL_PAYLOAD, **bad})
