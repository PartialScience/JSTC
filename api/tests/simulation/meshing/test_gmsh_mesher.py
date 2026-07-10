"""
Tests for the GmshMesher backend and its MFEM conversion.

These exercise the full path: region boundary loops -> sampled polygons ->
MeshSpec -> gmsh (OCC boolean) -> in-memory MFEM mesh with attribute
registry. Assertions are geometric (areas, coordinates, closure) rather
than mesh-internal, so any conforming backend would pass.
"""
import math
import threading

import pytest

from app.geometry import Circle, LineSegment, OffsetRegion
from app.simulation.meshing import ConductorHole, GmshMesher, MeshSpec, MeshedGeometry


CHORD_TOL = 1e-3


def _hole_from_region(region, mesh_size):
    (loop,) = region.boundary_loops()
    return ConductorHole(
        vertices=tuple(loop.sample_polygon(CHORD_TOL)),
        mesh_size=mesh_size,
    )


def _total_mesh_area(mesh):
    return sum(mesh.GetElementVolume(i) for i in range(mesh.GetNE()))


def _bdr_vertices_by_attr(mesh, attr):
    """All vertex coordinates of boundary elements carrying *attr*."""
    verts = []
    for i in range(mesh.GetNBE()):
        if mesh.GetBdrAttribute(i) == attr:
            for v in mesh.GetBdrElement(i).GetVerticesArray():
                verts.append(tuple(mesh.GetVertexArray(v)))
    return verts


@pytest.fixture(scope="module")
def simple_meshed() -> tuple[MeshSpec, MeshedGeometry]:
    """A 10x10 domain with one circular conductor hole."""
    spec = MeshSpec(
        r_max=10.0,
        z_max=10.0,
        conductors=(
            _hole_from_region(Circle(center=(5.0, 5.0), radius=1.0), mesh_size=0.2),
        ),
        wall_mesh_size=2.0,
    )
    return spec, GmshMesher().mesh(spec)


class TestSimpleDomain:
    def test_produces_2d_mesh(self, simple_meshed):
        _, geo = simple_meshed
        assert geo.mesh.Dimension() == 2
        assert geo.mesh.GetNE() > 0
        assert geo.mesh.GetNBE() > 0

    def test_mesh_area_is_domain_minus_hole(self, simple_meshed):
        _, geo = simple_meshed
        expected = 10.0 * 10.0 - math.pi * 1.0 ** 2
        assert _total_mesh_area(geo.mesh) == pytest.approx(expected, rel=1e-3)

    def test_wall_attributes_lie_on_walls(self, simple_meshed):
        spec, geo = simple_meshed
        for x, y in _bdr_vertices_by_attr(geo.mesh, geo.axis_attr):
            assert x == pytest.approx(0.0, abs=1e-9)
        for x, y in _bdr_vertices_by_attr(geo.mesh, geo.bottom_attr):
            assert y == pytest.approx(0.0, abs=1e-9)
        for x, y in _bdr_vertices_by_attr(geo.mesh, geo.right_attr):
            assert x == pytest.approx(spec.r_max, abs=1e-9)
        for x, y in _bdr_vertices_by_attr(geo.mesh, geo.top_attr):
            assert y == pytest.approx(spec.z_max, abs=1e-9)

    def test_conductor_attribute_lies_on_circle(self, simple_meshed):
        _, geo = simple_meshed
        (conductor_attr,) = geo.conductor_attrs
        verts = _bdr_vertices_by_attr(geo.mesh, conductor_attr)
        assert len(verts) > 10
        for x, y in verts:
            r = math.hypot(x - 5.0, y - 5.0)
            assert r == pytest.approx(1.0, abs=5 * CHORD_TOL)

    def test_all_boundary_elements_classified(self, simple_meshed):
        _, geo = simple_meshed
        known = {geo.axis_attr, geo.bottom_attr, geo.right_attr, geo.top_attr,
                 *geo.conductor_attrs}
        for i in range(geo.mesh.GetNBE()):
            assert geo.mesh.GetBdrAttribute(i) in known

    def test_conductor_boundary_is_finer_than_walls(self, simple_meshed):
        """Element size control: conductor boundary edges must be much
        shorter than wall edges."""
        _, geo = simple_meshed

        def edge_lengths(attr):
            lengths = []
            for i in range(geo.mesh.GetNBE()):
                if geo.mesh.GetBdrAttribute(i) == attr:
                    v = geo.mesh.GetBdrElement(i).GetVerticesArray()
                    (x1, y1), (x2, y2) = geo.mesh.GetVertexArray(v[0]), geo.mesh.GetVertexArray(v[1])
                    lengths.append(math.hypot(x2 - x1, y2 - y1))
            return lengths

        (conductor_attr,) = geo.conductor_attrs
        max_conductor = max(edge_lengths(conductor_attr))
        max_wall = max(edge_lengths(geo.right_attr))
        assert max_conductor < 0.5
        assert max_wall > 2 * max_conductor


class TestCoilLikeDomain:
    """A stadium-shaped winding hole plus a toroid section, like a real coil."""

    @pytest.fixture(scope="class")
    def coil_meshed(self):
        winding = OffsetRegion(
            curve=LineSegment((2.26925, 23.0), (2.26925, 44.8085)),
            offset=0.020101 / 2,
        )
        toroid = Circle(center=(7.375, 48.8085), radius=3.125)
        spec = MeshSpec(
            r_max=100.0,
            z_max=150.0,
            conductors=(
                ConductorHole(
                    vertices=tuple(winding.boundary_loops()[0].sample_polygon(2e-4)),
                    mesh_size=0.02,
                ),
                _hole_from_region(toroid, mesh_size=0.5),
            ),
            wall_mesh_size=20.0,
        )
        return spec, GmshMesher().mesh(spec)

    def test_meshes_with_two_conductors(self, coil_meshed):
        _, geo = coil_meshed
        assert len(geo.conductor_attrs) == 2
        assert geo.mesh.GetNE() > 0

    def test_winding_and_toroid_attrs_are_disjoint_and_placed(self, coil_meshed):
        _, geo = coil_meshed
        winding_attr, toroid_attr = geo.conductor_attrs
        for x, y in _bdr_vertices_by_attr(geo.mesh, winding_attr):
            assert abs(x - 2.26925) < 0.05 and 22.9 < y < 44.95
        for x, y in _bdr_vertices_by_attr(geo.mesh, toroid_attr):
            assert math.hypot(x - 7.375, y - 48.8085) == pytest.approx(3.125, abs=0.01)

    def test_area_excludes_both_conductors(self, coil_meshed):
        _, geo = coil_meshed
        stadium = 21.8085 * 0.020101 + math.pi * (0.020101 / 2) ** 2
        toroid = math.pi * 3.125 ** 2
        expected = 100.0 * 150.0 - stadium - toroid
        assert _total_mesh_area(geo.mesh) == pytest.approx(expected, rel=1e-4)


class TestEdgeTouchingConductor:
    """A conductor crossing the axis (like the JavaTC topload disc) must
    mesh via the boolean cut, with the overlap removed."""

    def test_disc_touching_axis(self):
        # Thin plate from r=-0.5 (past the axis) to r=8.25 - crossing r=0
        plate = ConductorHole(
            vertices=((-0.5, 48.0), (8.25, 48.0), (8.25, 48.1), (-0.5, 48.1)),
            mesh_size=0.5,
        )
        spec = MeshSpec(r_max=20.0, z_max=60.0, conductors=(plate,), wall_mesh_size=5.0)
        geo = GmshMesher().mesh(spec)
        # Domain area minus only the part of the plate inside the domain
        expected = 20.0 * 60.0 - 8.25 * 0.1
        assert _total_mesh_area(geo.mesh) == pytest.approx(expected, rel=1e-4)
        # The plate's boundary curves must carry the conductor attribute
        (conductor_attr,) = geo.conductor_attrs
        verts = _bdr_vertices_by_attr(geo.mesh, conductor_attr)
        assert len(verts) > 0
        for x, y in verts:
            assert 47.99 < y < 48.11 and x <= 8.26


class TestOffMainThread:
    """Regression: under a server (FastAPI) sync endpoints run in a worker
    threadpool. gmsh.initialize() installs a SIGINT handler, and
    signal.signal() only works on the main thread - so meshing off the main
    thread must not raise 'signal only works in main thread'."""

    def test_mesh_generates_in_a_worker_thread(self):
        spec = MeshSpec(
            r_max=10.0,
            z_max=10.0,
            conductors=(
                _hole_from_region(Circle(center=(5.0, 5.0), radius=1.0), mesh_size=0.5),
            ),
            wall_mesh_size=3.0,
        )
        result: dict = {}

        def worker():
            try:
                geo = GmshMesher().mesh(spec)
                result["elements"] = geo.mesh.GetNE()
            except Exception as exc:  # noqa: BLE001 - capture for assertion
                result["error"] = exc

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        assert "error" not in result, f"meshing off main thread raised: {result.get('error')}"
        assert result["elements"] > 0

    def test_signal_handler_restored_after_meshing(self):
        """The signal.signal patch must be undone once meshing completes."""
        import signal

        original = signal.signal
        spec = MeshSpec(
            r_max=10.0,
            z_max=10.0,
            conductors=(
                _hole_from_region(Circle(center=(5.0, 5.0), radius=1.0), mesh_size=0.5),
            ),
            wall_mesh_size=3.0,
        )
        GmshMesher().mesh(spec)
        assert signal.signal is original


class TestSpecValidation:
    def test_rejects_bad_domain(self):
        with pytest.raises(ValueError):
            MeshSpec(r_max=0.0, z_max=1.0, conductors=(), wall_mesh_size=1.0)

    def test_rejects_tiny_polygon(self):
        with pytest.raises(ValueError):
            ConductorHole(vertices=((0, 0), (1, 0)), mesh_size=0.1)

    def test_rejects_conductor_outside_domain(self):
        outside = ConductorHole(
            vertices=((50.0, 50.0), (51.0, 50.0), (51.0, 51.0), (50.0, 51.0)),
            mesh_size=0.5,
        )
        spec = MeshSpec(r_max=10.0, z_max=10.0, conductors=(outside,), wall_mesh_size=2.0)
        with pytest.raises(ValueError):
            GmshMesher().mesh(spec)
