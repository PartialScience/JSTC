"""
Shared setup of the axisymmetric electrostatic problem for a coil: mesh the
domain, resolve the conductor boundary attributes, and build the winding
tent-basis Dirichlet patterns.

Both consumers of the FEM electrostatics use this:

  * the capacitance solver (tent solves -> Gram matrix), and
  * the field-visualization solver (the same tent basis plus the primary
    basis fields, sampled on a grid).

Keeping it in one place means the two always mesh identically and share the
tent construction, so a field render lines up exactly with the matrices.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Union

from app.models.coil_models import (
    GroundedConductorSpec,
    PrimarySpec,
    SecondaryConductorSpec,
    ToploadSpec,
)
from app.simulation.meshing import ConductorHole, GmshMesher, MeshSpec, MeshedGeometry

BoundaryValue = Union[float, Callable[[float, float], float]]


@dataclass
class CoilElectrostaticSetup:
    """The meshed electrostatic problem plus the winding tent basis.

    Attributes:
        geo: The meshed field domain with its boundary-attribute registry.
        dirichlet_attrs: Every essential (prescribed-potential) attribute -
            all conductors plus any Dirichlet walls.
        winding_attr: The secondary winding's boundary attribute.
        topload_attrs / ground_attrs / primary_attrs: Boundary attributes
            for each conductor group, in spec order.
        tent_solves: One Dirichlet map per winding node t_0..t_N: the tent
            profile on the winding (topload tied to the top node). These are
            the C-matrix solves; the field solver appends primary solves.
    """

    geo: MeshedGeometry
    dirichlet_attrs: Tuple[int, ...]
    winding_attr: int
    topload_attrs: Tuple[int, ...]
    ground_attrs: Tuple[int, ...]
    primary_attrs: Tuple[int, ...]
    tent_solves: List[Dict[int, BoundaryValue]]


def build_coil_electrostatic_setup(
    secondary: SecondaryConductorSpec,
    toploads: Tuple[ToploadSpec, ...],
    grounds: Tuple[GroundedConductorSpec, ...],
    primary: Optional[PrimarySpec],
    slices: Tuple[float, ...],
    r_max: float,
    z_max: float,
    dirichlet_walls: Tuple[bool, bool, bool],
    cfg: Dict[str, float],
) -> CoilElectrostaticSetup:
    """Mesh the coil and build the winding tent-basis Dirichlet patterns."""
    wire_dia = 2 * secondary.geometry.offset

    # --- Sample conductor boundaries into polygons ---
    winding_mesh_size = cfg["winding_mesh_size_factor"] * wire_dia
    (winding_loop,) = secondary.geometry.boundary_loops()
    winding_hole = ConductorHole(
        vertices=tuple(
            winding_loop.sample_polygon(winding_mesh_size / 10, include=slices)
        ),
        mesh_size=winding_mesh_size,
    )

    def component_hole(component) -> ConductorHole:
        (loop,) = component.boundary_loops()
        # Bounding box from fixed per-piece parameter sampling - a
        # chord-tolerance sample would need the feature size we are trying to
        # measure (and collapses small conductors entirely).
        probe = [
            piece.curve.point_at(
                piece.curve.t_min
                + (piece.curve.t_max - piece.curve.t_min) * i / 16
            )
            for piece in loop.pieces
            for i in range(17)
        ]
        width = max(p[0] for p in probe) - min(p[0] for p in probe)
        height = max(p[1] for p in probe) - min(p[1] for p in probe)
        size = max(min(width, height), wire_dia) * cfg["component_mesh_fraction"]
        return ConductorHole(
            vertices=tuple(loop.sample_polygon(size / 10)),
            mesh_size=size,
        )

    topload_holes = tuple(component_hole(t) for t in toploads)
    ground_holes = tuple(component_hole(g) for g in grounds)
    # The primary is one grounded cross-section per turn (electrostatically
    # near ground at secondary-resonance timescales). Kept as its own
    # conductor group so the field solver can energize the turns.
    primary_holes = (
        tuple(component_hole(region) for region in primary.ring_regions())
        if primary is not None else ()
    )

    # --- Mesh ---
    spec = MeshSpec(
        r_max=r_max,
        z_max=z_max,
        conductors=(winding_hole, *topload_holes, *ground_holes, *primary_holes),
        wall_mesh_size=max(r_max, z_max) * cfg["wall_mesh_fraction"],
        size_grading=cfg["size_grading"],
    )
    geo = GmshMesher().mesh(spec)

    nt, ng = len(toploads), len(grounds)
    winding_attr = geo.conductor_attrs[0]
    topload_attrs = geo.conductor_attrs[1:1 + nt]
    ground_attrs = geo.conductor_attrs[1 + nt:1 + nt + ng]
    primary_attrs = geo.conductor_attrs[1 + nt + ng:]

    # --- Essential boundaries: conductors + Dirichlet walls ---
    bottom_d, right_d, top_d = dirichlet_walls
    wall_attrs = (
        ((geo.bottom_attr,) if bottom_d else ())
        + ((geo.right_attr,) if right_d else ())
        + ((geo.top_attr,) if top_d else ())
    )
    dirichlet_attrs = (
        winding_attr, *topload_attrs, *ground_attrs, *primary_attrs, *wall_attrs
    )

    # --- Tent boundary profiles along the winding ---
    curve = secondary.curve
    projection_cache: Dict[Tuple[float, float], float] = {}

    def param_of(r: float, z: float) -> float:
        key = (r, z)
        t = projection_cache.get(key)
        if t is None:
            t = curve.closest_parameter(key)
            projection_cache[key] = t
        return t

    def tent(k: int) -> Callable[[float, float], float]:
        t_k = slices[k]
        t_lo = slices[k - 1] if k > 0 else None
        t_hi = slices[k + 1] if k < len(slices) - 1 else None

        def phi(r: float, z: float) -> float:
            t = param_of(r, z)
            if t <= t_k:
                if t_lo is None:
                    return 1.0
                return max(0.0, (t - t_lo) / (t_k - t_lo))
            if t_hi is None:
                return 1.0
            return max(0.0, (t_hi - t) / (t_hi - t_k))

        return phi

    top_node = len(slices) - 1
    tent_solves: List[Dict[int, BoundaryValue]] = []
    for k in range(len(slices)):
        boundary_values: Dict[int, BoundaryValue] = {winding_attr: tent(k)}
        if k == top_node:
            for attr in topload_attrs:
                boundary_values[attr] = 1.0
        tent_solves.append(boundary_values)

    return CoilElectrostaticSetup(
        geo=geo,
        dirichlet_attrs=dirichlet_attrs,
        winding_attr=winding_attr,
        topload_attrs=topload_attrs,
        ground_attrs=ground_attrs,
        primary_attrs=primary_attrs,
        tent_solves=tent_solves,
    )
