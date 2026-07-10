"""Integration tests for POST /simulation/field."""
import numpy as np
import pytest

from app.routers.simulation import compute_matrices, field
from app.schemas import FieldRequest, MatricesRequest
from tests.api.javatc_coil_schema import JAVATC_COIL_PAYLOAD


@pytest.fixture(scope="module")
def bundle():
    return compute_matrices(
        MatricesRequest.model_validate({"coil": JAVATC_COIL_PAYLOAD})
    ).model_dump()


def _request(bundle, **overrides):
    body = {
        "coil": JAVATC_COIL_PAYLOAD,
        "bundle": bundle,
        "field_type": "electric",
        "frequency_hz": 214000,
        "primary_current": 100.0,
        "grid_nr": 30,
        "grid_nz": 45,
    }
    body.update(overrides)
    return FieldRequest.model_validate(body)


class TestFieldEndpoint:
    def test_electric_field_shape_and_content(self, bundle):
        resp = field(_request(bundle, field_type="electric"))
        assert resp.field_type == "electric"
        assert resp.nr == 30 and resp.nz == 45
        assert len(resp.real) == 30 * 45 == len(resp.imag) == len(resp.mask)
        mag = np.hypot(np.array(resp.real), np.array(resp.imag))
        # Peak potential is on the order of the operating top voltage (~10s kV).
        assert mag.max() > 1e4
        assert resp.unit_scale == pytest.approx(0.0254)

    def test_magnetic_field(self, bundle):
        resp = field(_request(bundle, field_type="magnetic"))
        assert resp.field_type == "magnetic"
        assert "vector_potential" in resp.quantity
        assert np.hypot(np.array(resp.real), np.array(resp.imag)).max() > 0

    def test_floating_and_grounded_differ(self, bundle):
        floating = field(_request(bundle, reference_mode="floating"))
        grounded = field(_request(bundle, reference_mode="grounded"))
        assert not np.allclose(floating.real, grounded.real)

    def test_current_scales_field_linearly(self, bundle):
        a = field(_request(bundle, primary_current=100.0))
        b = field(_request(bundle, primary_current=200.0))
        ra, rb = np.array(a.real), np.array(b.real)
        assert np.allclose(rb, 2 * ra, rtol=1e-6)

    def test_requires_primary_tank(self, bundle):
        from fastapi import HTTPException

        no_primary = {**JAVATC_COIL_PAYLOAD, "primary": None}
        with pytest.raises(HTTPException) as exc:
            field(FieldRequest.model_validate({
                "coil": no_primary, "frequency_hz": 200000,
            }))
        assert exc.value.status_code == 422
