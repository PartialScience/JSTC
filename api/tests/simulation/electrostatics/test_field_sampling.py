"""
Tests for grid sampling of solution fields (the field-visualization path).
Validated against the analytic coaxial potential phi = ln(b/r)/ln(b/a).
"""
import numpy as np
import pytest

from app.simulation.electrostatics import solve_electrostatics
from app.simulation.meshing import ConductorHole, GmshMesher, MeshSpec


@pytest.fixture(scope="module")
def coax():
    a, b, h = 1.0, 2.0, 4.0
    inner = ConductorHole(
        vertices=((-0.5, -1), (a, -1), (a, h + 1), (-0.5, h + 1)), mesh_size=0.1
    )
    spec = MeshSpec(r_max=b, z_max=h, conductors=(inner,), wall_mesh_size=0.1)
    geo = GmshMesher().mesh(spec)
    return geo, a, b, h


def test_sampled_field_matches_analytic_potential(coax):
    geo, a, b, h = coax
    (inner_attr,) = geo.conductor_attrs
    rs = np.linspace(1.05, 1.95, 12)
    pts = np.vstack([rs, np.full_like(rs, h / 2)])
    res = solve_electrostatics(
        geo.mesh, (inner_attr, geo.right_attr), ({inner_attr: 1.0},),
        sample_points=pts,
    )
    assert res.sampled_fields is not None
    assert res.sampled_fields.shape == (1, len(rs))
    expected = np.log(b / rs) / np.log(b / a)
    assert np.allclose(res.sampled_fields[0], expected, atol=1e-3)
    assert res.sample_mask.all()


def test_points_inside_conductor_are_masked(coax):
    geo, a, b, h = coax
    (inner_attr,) = geo.conductor_attrs
    # r = 0.5 is inside the inner conductor (r <= 1) -> not in the field domain.
    pts = np.array([[0.5, 1.5], [h / 2, h / 2]])
    res = solve_electrostatics(
        geo.mesh, (inner_attr, geo.right_attr), ({inner_attr: 1.0},),
        sample_points=pts,
    )
    assert not res.sample_mask[0]  # inside conductor
    assert res.sample_mask[1]  # in the field region
    assert np.isnan(res.sampled_fields[0, 0])
    assert np.isfinite(res.sampled_fields[0, 1])


def test_multiple_solves_sampled_together(coax):
    geo, a, b, h = coax
    (inner_attr,) = geo.conductor_attrs
    pts = np.array([[1.5], [h / 2]])
    res = solve_electrostatics(
        geo.mesh, (inner_attr, geo.right_attr),
        ({inner_attr: 1.0}, {inner_attr: 2.0}),
        sample_points=pts,
    )
    # Linearity: doubling the boundary value doubles the sampled potential.
    assert res.sampled_fields[1, 0] == pytest.approx(2 * res.sampled_fields[0, 0], rel=1e-9)


def test_no_sampling_by_default(coax):
    geo, a, b, h = coax
    (inner_attr,) = geo.conductor_attrs
    res = solve_electrostatics(geo.mesh, (inner_attr, geo.right_attr), ({inner_attr: 1.0},))
    assert res.sampled_fields is None
    assert res.sample_mask is None
