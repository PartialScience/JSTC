"""
Gmsh-backed axisymmetric mesher.

Builds the field domain with the OpenCASCADE kernel: the domain rectangle
minus every conductor cross-section, subtracted in a single boolean cut.
Using a CAD boolean (rather than hole loops) means conductors may touch or
cross the domain edges - e.g. a topload disc reaching the r = 0 axis - and
overlapping same-potential conductors simply merge.

Gmsh's Python API is a process-global singleton and is not thread-safe.
All access is serialized behind a module-level lock and wrapped in
initialize/finalize so no state leaks between calls; callers never see any
of this.
"""
import contextlib
import math
import os
import signal
import threading

import numpy as np

from .base import AxisymmetricMesher
from .gmsh_to_mfem import extract_gmsh_data, gmsh_to_mfem
from .mesh_spec import MeshSpec
from .meshed_geometry import MeshedGeometry

# Gmsh is a process-global singleton: one mesh generation at a time.
_GMSH_LOCK = threading.Lock()


def _mesh_threads() -> int:
    """Thread count for gmsh, capped for multi-worker/small deployments."""
    for var in ("JSTC_MESH_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        raw = os.environ.get(var)
        if raw and raw.strip().isdigit():
            return max(1, int(raw))
    return os.cpu_count() or 1


@contextlib.contextmanager
def _suppress_signal_handling():
    """Neutralize signal.signal() for the duration of a gmsh call.

    gmsh.initialize() installs a SIGINT handler to make meshing
    Ctrl+C-interruptible, but signal.signal() only works on the main
    thread - and under a server (FastAPI) our sync endpoint runs in a
    worker threadpool, so gmsh raises "signal only works in main thread".
    A server neither needs nor wants gmsh to grab SIGINT, so we replace
    signal.signal with a no-op (returning None, so gmsh's save/restore
    becomes a no-op) for the duration. This runs inside _GMSH_LOCK, so no
    other thread races on the global patch.
    """
    original = signal.signal
    signal.signal = lambda *_args, **_kwargs: None  # type: ignore[assignment]
    try:
        yield
    finally:
        signal.signal = original

# Boundary attribute numbering (MFEM attributes are 1-based).
_AXIS_ATTR = 1
_BOTTOM_ATTR = 2
_RIGHT_ATTR = 3
_TOP_ATTR = 4
_FIRST_CONDUCTOR_ATTR = 5

#: Element (domain) attribute for the single field region.
_DOMAIN_ATTR = 1


class GmshMesher(AxisymmetricMesher):
    """Axisymmetric mesh generation backed by Gmsh's OCC kernel."""

    def mesh(self, spec: MeshSpec) -> MeshedGeometry:
        import gmsh

        with _GMSH_LOCK, _suppress_signal_handling():
            gmsh.initialize()
            try:
                gmsh.option.setNumber("General.Terminal", 0)
                # Multithreaded meshing (parallel Delaunay). Held under the
                # module lock, so only this mesh generation uses the threads.
                # Cap via env so a multi-worker / small-instance deployment
                # doesn't oversubscribe cores (workers x threads > cores).
                # Honors JSTC_MESH_THREADS, else OMP/MKL_NUM_THREADS, else all
                # cores (single-process dev default).
                gmsh.option.setNumber("General.NumThreads", _mesh_threads())
                gmsh.option.setNumber("Mesh.MaxNumThreads2D", _mesh_threads())
                gmsh.model.add("axisymmetric_domain")
                return self._build_and_mesh(gmsh, spec)
            finally:
                gmsh.finalize()

    # ------------------------------------------------------------------

    def _build_and_mesh(self, gmsh, spec: MeshSpec) -> MeshedGeometry:
        occ = gmsh.model.occ

        # --- Geometry: domain rectangle minus conductor surfaces ---
        domain = occ.addRectangle(0.0, 0.0, 0.0, spec.r_max, spec.z_max)

        hole_surfaces = []
        for conductor in spec.conductors:
            hole_surfaces.append((2, self._add_polygon_surface(occ, conductor.vertices)))

        if hole_surfaces:
            out, _ = occ.cut([(2, domain)], hole_surfaces,
                             removeObject=True, removeTool=True)
            surfaces = [tag for dim, tag in out if dim == 2]
            if not surfaces:
                raise ValueError("Boolean cut consumed the entire domain")
        else:
            surfaces = [domain]

        occ.synchronize()

        # --- Classify boundary curves and build physical groups ---
        curve_groups = self._classify_boundary_curves(gmsh, spec, surfaces)

        for attr, curves in curve_groups.items():
            if curves:
                gmsh.model.addPhysicalGroup(1, curves, attr)
        gmsh.model.addPhysicalGroup(2, surfaces, _DOMAIN_ATTR)

        conductor_attrs = tuple(
            _FIRST_CONDUCTOR_ATTR + i for i in range(len(spec.conductors))
        )
        for i, attr in enumerate(conductor_attrs):
            if not curve_groups.get(attr):
                raise ValueError(
                    f"Conductor {i} produced no boundary curves - is it "
                    "entirely outside the domain?"
                )

        # --- Mesh sizing via a distance-threshold size field ---
        # Each conductor gets a Distance->Threshold field: element size is
        # its mesh_size within DistMin of the surface, growing to the coarse
        # wall size by DistMax. A Min field combines them. This grades the
        # mesh far more efficiently than per-point sizes (which over-refine
        # the transition region and balloon the element count), cutting both
        # meshing and solve time without touching the near-field resolution
        # that sets accuracy.
        self._apply_size_field(gmsh, spec, curve_groups)

        gmsh.model.mesh.generate(2)

        # --- Convert to MFEM in memory ---
        data = extract_gmsh_data(gmsh)
        mesh = gmsh_to_mfem(**data)

        return MeshedGeometry(
            mesh=mesh,
            axis_attr=_AXIS_ATTR,
            bottom_attr=_BOTTOM_ATTR,
            right_attr=_RIGHT_ATTR,
            top_attr=_TOP_ATTR,
            conductor_attrs=conductor_attrs,
        )

    @staticmethod
    def _apply_size_field(gmsh, spec: MeshSpec, curve_groups: dict) -> None:
        """Set a distance-threshold background size field.

        For each conductor a Distance field measures the distance to its
        boundary curves; a Threshold field maps that to element size
        (mesh_size within DistMin, growing to the coarse wall size by
        DistMax). A Min field combines all conductors, so every point gets
        the finest applicable size. The walls/axis are left at the coarse
        wall size (the field's SizeMax), and point/curvature sizing is
        disabled so the field is authoritative.
        """
        field = gmsh.model.mesh.field
        transition = spec.size_grading * max(spec.r_max, spec.z_max)

        threshold_tags = []
        next_tag = 1
        for i, conductor in enumerate(spec.conductors):
            curves = curve_groups.get(_FIRST_CONDUCTOR_ATTR + i, [])
            if not curves:
                continue
            dist_tag = next_tag
            thr_tag = next_tag + 1
            next_tag += 2

            field.add("Distance", dist_tag)
            field.setNumbers(dist_tag, "CurvesList", curves)
            # Conductor boundaries are already fine polygons (many short
            # curves), so a handful of samples per curve resolves the
            # distance well; high sampling makes the field evaluation
            # (O(mesh_nodes x samples)) dominate meshing.
            field.setNumber(dist_tag, "Sampling", 3)

            field.add("Threshold", thr_tag)
            field.setNumber(thr_tag, "InField", dist_tag)
            field.setNumber(thr_tag, "SizeMin", conductor.mesh_size)
            field.setNumber(thr_tag, "SizeMax", spec.wall_mesh_size)
            # Hold the fine size within one element of the surface, then
            # grow to the wall size over the transition distance.
            field.setNumber(thr_tag, "DistMin", conductor.mesh_size)
            field.setNumber(thr_tag, "DistMax", transition)
            threshold_tags.append(thr_tag)

        if not threshold_tags:
            return

        min_tag = next_tag
        field.add("Min", min_tag)
        field.setNumbers(min_tag, "FieldsList", threshold_tags)
        field.setAsBackgroundMesh(min_tag)

        # The field is authoritative: disable competing size sources.
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

    @staticmethod
    def _add_polygon_surface(occ, vertices) -> int:
        """Add a closed polygon as an OCC plane surface, returning its tag."""
        point_tags = [occ.addPoint(x, y, 0.0) for x, y in vertices]
        n = len(point_tags)
        line_tags = [
            occ.addLine(point_tags[i], point_tags[(i + 1) % n]) for i in range(n)
        ]
        loop = occ.addCurveLoop(line_tags)
        return occ.addPlaneSurface([loop])

    def _classify_boundary_curves(self, gmsh, spec: MeshSpec, surfaces) -> dict:
        """Assign every boundary curve of the meshed domain to an attribute.

        Walls and the axis are recognized by their coordinates; every other
        boundary curve belongs to the conductor whose polygon it lies on
        (nearest polygon by curve-midpoint distance).
        """
        boundary = gmsh.model.getBoundary(
            [(2, s) for s in surfaces], combined=True, oriented=False
        )
        curves = [tag for dim, tag in boundary if dim == 1]

        # Coordinate tolerance for wall recognition, well below any feature
        tol = 1e-9 * max(spec.r_max, spec.z_max)

        groups: dict[int, list[int]] = {
            _AXIS_ATTR: [], _BOTTOM_ATTR: [], _RIGHT_ATTR: [], _TOP_ATTR: [],
        }
        for i in range(len(spec.conductors)):
            groups[_FIRST_CONDUCTOR_ATTR + i] = []

        # Probe every curve, classify walls/axis by coordinate, and defer
        # conductor curves for one vectorized nearest-polygon pass.
        conductor_curves: list[int] = []
        conductor_probes: list[list[tuple[float, float]]] = []
        for tag in curves:
            probes = self._probe_points(gmsh, tag)
            if all(abs(x) <= tol for x, _ in probes):
                groups[_AXIS_ATTR].append(tag)
            elif all(abs(y) <= tol for _, y in probes):
                groups[_BOTTOM_ATTR].append(tag)
            elif all(abs(x - spec.r_max) <= tol for x, _ in probes):
                groups[_RIGHT_ATTR].append(tag)
            elif all(abs(y - spec.z_max) <= tol for _, y in probes):
                groups[_TOP_ATTR].append(tag)
            else:
                conductor_curves.append(tag)
                conductor_probes.append(probes)

        if conductor_curves:
            nearest = self._nearest_conductors(spec, conductor_probes)
            for tag, idx in zip(conductor_curves, nearest):
                groups[_FIRST_CONDUCTOR_ATTR + int(idx)].append(tag)

        return groups

    @staticmethod
    def _probe_points(gmsh, curve_tag, n: int = 3):
        """Sample n interior points of a curve in (x, y)."""
        t0, t1 = gmsh.model.getParametrizationBounds(1, curve_tag)
        probes = []
        for i in range(1, n + 1):
            t = t0[0] + (t1[0] - t0[0]) * i / (n + 1)
            x, y, _ = gmsh.model.getValue(1, curve_tag, [t])
            probes.append((x, y))
        return probes

    @staticmethod
    def _nearest_conductors(spec: MeshSpec, curve_probes) -> np.ndarray:
        """Vectorized nearest-conductor assignment for many curves at once.

        curve_probes is one list of probe points per curve. A curve is
        assigned to the conductor minimizing its worst-probe distance to the
        conductor's boundary polygon. Same result as a per-curve
        point-to-segment search, but computed as batched NumPy over all
        curves and edges instead of ~10^5 Python calls.
        """
        n_probes = len(curve_probes[0])
        pts = np.asarray(curve_probes, dtype=float).reshape(-1, 2)  # (C*n_probes, 2)

        # Per-conductor: min distance from every probe to the polygon edges.
        per_conductor = np.empty((len(spec.conductors), pts.shape[0]))
        for i, conductor in enumerate(spec.conductors):
            verts = np.asarray(conductor.vertices, dtype=float)
            a = verts
            b = np.roll(verts, -1, axis=0)
            ab = b - a                                   # (E, 2)
            ab_len2 = np.einsum("ei,ei->e", ab, ab)
            ab_len2 = np.where(ab_len2 == 0.0, 1.0, ab_len2)
            ap = pts[:, None, :] - a[None, :, :]         # (P, E, 2)
            t = np.clip(np.einsum("pei,ei->pe", ap, ab) / ab_len2, 0.0, 1.0)
            proj = a[None, :, :] + t[:, :, None] * ab[None, :, :]
            per_conductor[i] = np.linalg.norm(pts[:, None, :] - proj, axis=2).min(axis=1)

        # Worst probe per curve, then the nearest conductor for that curve.
        per_conductor = per_conductor.reshape(len(spec.conductors), -1, n_probes)
        curve_dist = per_conductor.max(axis=2)           # (conductors, curves)
        return curve_dist.argmin(axis=0)
