"""
Schema <-> domain conversion tests (no HTTP, no FEM).

Validates that a frontend JSON payload parses and converts into exactly the
domain coil the solvers expect, and that the matrix bundle round-trips.
"""
import pytest

from app.converters import bundle_from_schema, bundle_to_schema, coil_from_schema
from app.models.coil_models import LinearPrimarySpec, LinearSecondaryConductorSpec
from app.models.materials import Material
from app.models.turn_profiles import UniformTurnProfile
from app.schemas import SimulatableTeslaCoilSchema
from app.schemas.matrix_schemas import MatrixBundleSchema
from app.simulation.facade.matrices import GeometricMatrixBundle
from tests.api.javatc_coil_schema import JAVATC_COIL_PAYLOAD


class TestCoilConversion:
    def test_payload_parses(self):
        schema = SimulatableTeslaCoilSchema.model_validate(JAVATC_COIL_PAYLOAD)
        assert schema.discretization_order == 30
        assert schema.secondary.turn_fxn.total_turns == 895
        # Discriminated unions resolve to concrete types
        assert schema.toploads[0].shape.kind == "circle"
        assert schema.toploads[1].shape.kind == "rectangle"
        assert schema.primary.cross_section.kind == "circular"

    def test_converts_to_domain(self):
        schema = SimulatableTeslaCoilSchema.model_validate(JAVATC_COIL_PAYLOAD)
        coil = coil_from_schema(schema)

        assert isinstance(coil.secondary, LinearSecondaryConductorSpec)
        assert coil.secondary.material is Material.COPPER
        assert isinstance(coil.secondary.turn_fxn, UniformTurnProfile)
        assert coil.secondary.total_turns == 895
        assert coil.unit_scale == pytest.approx(0.0254)

        assert isinstance(coil.primary, LinearPrimarySpec)
        assert coil.primary.total_turns == pytest.approx(8.438)
        assert coil.primary.cross_section.diameter == pytest.approx(0.25)

        assert len(coil.toploads) == 2
        assert coil.toploads[0].contains([7.375, 48.8085])  # inside the toroid

    def test_defaults_applied(self):
        """A minimal coil (no primary, no BCs) fills sensible defaults."""
        minimal = {
            "secondary": {
                "turn_fxn": {"kind": "uniform", "total_turns": 100},
                "start": [1.0, 0.0], "end": [1.0, 10.0], "wire_dia": 0.05,
            },
            "r_max": 50, "z_max": 50,
        }
        coil = coil_from_schema(SimulatableTeslaCoilSchema.model_validate(minimal))
        assert coil.primary is None
        assert coil.unit_scale == 1.0
        assert coil.discretization_order == 30
        assert coil.secondary.material is Material.COPPER


class TestBundleRoundTrip:
    def test_bundle_schema_round_trips(self):
        bundle = GeometricMatrixBundle(
            nodal_capacitance=((1.0, -0.5), (-0.5, 1.0)),
            topload_charge=(0.1, 0.2),
            inductance=((2.0,),),
            coupling=(0.3,),
            discretization_order=1,
            geometry_fingerprint="abc123",
        )
        schema = bundle_to_schema(bundle)
        assert isinstance(schema, MatrixBundleSchema)

        # Serialize as the API would, reparse, convert back
        reparsed = MatrixBundleSchema.model_validate(schema.model_dump())
        restored = bundle_from_schema(reparsed)

        assert restored == bundle
