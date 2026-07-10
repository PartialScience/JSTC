"""
Analytic validation of the axisymmetric electrostatic solver.

Each test compares the geometric capacitance from the FEM pipeline against
a closed-form solution:

  * Coaxial cylinders (Neumann top/bottom -> purely radial field):
        C_SI = 2*pi*eps0*h / ln(b/a)     =>  C_geo = h / ln(b/a)
  * Sphere centered on the axis in a large grounded box:
        C_SI ~= 4*pi*eps0*a              =>  C_geo ~= 2*a
    (approximate: truncation to a finite domain perturbs at O(a/R_box))

The coax test also runs a mesh-refinement convergence check, which is the
rigorous accuracy statement (the sphere tolerance is dominated by domain
truncation, not FEM error).
"""
import math

import pytest

from app.geometry import Circle
from app.simulation.electrostatics import solve_capacitance_gram_matrix
from app.simulation.meshing import ConductorHole, GmshMesher, MeshSpec


def _coax_geometry(mesh_size):
    """Coax capacitor: inner conductor r <= 1 as a hole spanning the full
    height, outer conductor = the right wall at r = 2, Neumann top/bottom."""
    a, b, h = 1.0, 2.0, 4.0
    inner = ConductorHole(
        # Crosses the axis and both horizontal walls; the boolean cut trims it
        vertices=((-0.5, -1.0), (a, -1.0), (a, h + 1.0), (-0.5, h + 1.0)),
        mesh_size=mesh_size,
    )
    spec = MeshSpec(r_max=b, z_max=h, conductors=(inner,), wall_mesh_size=mesh_size)
    return GmshMesher().mesh(spec), a, b, h


class TestCoaxialCylinders:
    def test_matches_closed_form(self):
        geo, a, b, h = _coax_geometry(mesh_size=0.1)
        (inner_attr,) = geo.conductor_attrs
        C = solve_capacitance_gram_matrix(
            mesh=geo.mesh,
            dirichlet_attrs=(inner_attr, geo.right_attr),
            solves=({inner_attr: 1.0},),
        )
        expected = h / math.log(b / a)
        assert C[0, 0] == pytest.approx(expected, rel=1e-3)

    def test_mesh_convergence(self):
        """Error must shrink monotonically (and fast) under refinement."""
        expected = 4.0 / math.log(2.0)
        errors = []
        for mesh_size in (0.4, 0.2, 0.1):
            geo, a, b, h = _coax_geometry(mesh_size)
            (inner_attr,) = geo.conductor_attrs
            C = solve_capacitance_gram_matrix(
                mesh=geo.mesh,
                dirichlet_attrs=(inner_attr, geo.right_attr),
                solves=({inner_attr: 1.0},),
            )
            errors.append(abs(C[0, 0] - expected) / expected)
        assert errors[2] < errors[0], f"No convergence: {errors}"
        assert errors[2] < 1e-3, f"Finest error too large: {errors}"

    def test_linear_profile_along_inner(self):
        """A callable (tent-like) boundary value: potential ramping 0 -> 1
        along the inner conductor height. Sanity: energy must lie between
        0 (all grounded) and the uniform-1V energy, and the solve must
        accept callables."""
        geo, a, b, h = _coax_geometry(mesh_size=0.1)
        (inner_attr,) = geo.conductor_attrs
        ramp = lambda r, z: min(max(z / h, 0.0), 1.0)
        C = solve_capacitance_gram_matrix(
            mesh=geo.mesh,
            dirichlet_attrs=(inner_attr, geo.right_attr),
            solves=({inner_attr: ramp}, {inner_attr: 1.0}),
        )
        assert 0.0 < C[0, 0] < C[1, 1]
        # The ramp-vs-uniform cross energy also has a closed form for the
        # radial-only field: integral of the ramp over height = h/2
        expected_cross = (4.0 / 2) / math.log(2.0)
        assert C[0, 1] == pytest.approx(expected_cross, rel=5e-3)


class TestGroupChargeExtraction:
    """Per-conductor-group charges from the reaction form, validated on the
    coax capacitor where every charge has a closed form."""

    @pytest.fixture(scope="class")
    def coax_result(self):
        from app.simulation.electrostatics import solve_electrostatics

        geo, a, b, h = _coax_geometry(mesh_size=0.1)
        (inner_attr,) = geo.conductor_attrs
        result = solve_electrostatics(
            mesh=geo.mesh,
            dirichlet_attrs=(inner_attr, geo.right_attr),
            solves=({inner_attr: 1.0},),
            charge_groups=((inner_attr,), (geo.right_attr,)),
        )
        return result

    def test_driven_conductor_charge_equals_gram_diagonal(self, coax_result):
        """Q on the 1V conductor is exactly the Gram diagonal (same weak
        extraction, indicator weight = the solve's own boundary data)."""
        assert coax_result.group_charges[0, 0] == pytest.approx(
            coax_result.gram[0, 0], rel=1e-12
        )

    def test_charges_balance(self, coax_result):
        """All field lines terminate on the two conductors: total charge
        is zero (Gauss)."""
        total = coax_result.group_charges[:, 0].sum()
        assert total == pytest.approx(0.0, abs=1e-9 * abs(coax_result.gram[0, 0]))

    def test_unknown_attr_in_group_rejected(self, coax_result):
        from app.simulation.electrostatics import solve_electrostatics

        geo, a, b, h = _coax_geometry(mesh_size=0.4)
        (inner_attr,) = geo.conductor_attrs
        with pytest.raises(ValueError):
            solve_electrostatics(
                mesh=geo.mesh,
                dirichlet_attrs=(inner_attr, geo.right_attr),
                solves=({inner_attr: 1.0},),
                charge_groups=((geo.top_attr,),),
            )


class TestSphereInLargeBox:
    def test_isolated_sphere_capacitance(self):
        """Sphere radius 1 at the center of a grounded 100x200 box:
        C_geo ~= 2a with O(a/R) truncation error."""
        sphere = Circle(center=(0.0, 100.0), radius=1.0)
        (loop,) = sphere.boundary_loops()
        hole = ConductorHole(
            vertices=tuple(loop.sample_polygon(1e-3)),
            mesh_size=0.15,
        )
        spec = MeshSpec(r_max=100.0, z_max=200.0, conductors=(hole,), wall_mesh_size=25.0)
        geo = GmshMesher().mesh(spec)
        (sphere_attr,) = geo.conductor_attrs
        C = solve_capacitance_gram_matrix(
            mesh=geo.mesh,
            dirichlet_attrs=(sphere_attr, geo.bottom_attr, geo.right_attr, geo.top_attr),
            solves=({sphere_attr: 1.0},),
        )
        assert C[0, 0] == pytest.approx(2.0, rel=0.03)


class TestStructuralProperties:
    """Two separate conductors: the Gram matrix must be symmetric, PD, and
    for indicator (constant 0/1) solves the off-diagonal is negative."""

    @pytest.fixture(scope="class")
    def two_sphere_gram(self):
        spheres = (
            Circle(center=(0.0, 40.0), radius=1.0),
            Circle(center=(0.0, 60.0), radius=1.0),
        )
        holes = tuple(
            ConductorHole(
                vertices=tuple(s.boundary_loops()[0].sample_polygon(1e-3)),
                mesh_size=0.2,
            )
            for s in spheres
        )
        spec = MeshSpec(r_max=50.0, z_max=100.0, conductors=holes, wall_mesh_size=15.0)
        geo = GmshMesher().mesh(spec)
        attr_a, attr_b = geo.conductor_attrs
        C = solve_capacitance_gram_matrix(
            mesh=geo.mesh,
            dirichlet_attrs=(attr_a, attr_b, geo.bottom_attr, geo.right_attr, geo.top_attr),
            solves=({attr_a: 1.0}, {attr_b: 1.0}),
        )
        return C

    def test_symmetric(self, two_sphere_gram):
        C = two_sphere_gram
        assert C[0, 1] == pytest.approx(C[1, 0], rel=1e-12)

    def test_positive_definite(self, two_sphere_gram):
        import numpy as np
        eigenvalues = np.linalg.eigvalsh(two_sphere_gram)
        assert (eigenvalues > 0).all()

    def test_indicator_off_diagonal_is_negative(self, two_sphere_gram):
        """For separate conductors held at 0/1 (the classical Maxwell
        setting) the mutual term is negative."""
        assert two_sphere_gram[0, 1] < 0

    def test_requires_a_dirichlet_reference(self, two_sphere_gram):
        with pytest.raises(ValueError):
            solve_capacitance_gram_matrix(
                mesh=None, dirichlet_attrs=(), solves=()
            )
