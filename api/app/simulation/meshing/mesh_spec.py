"""
Neutral mesh specification consumed by AxisymmetricMesher backends.

A MeshSpec is plain data: the rectangular axisymmetric domain plus
conductor holes described as sampled boundary polygons. All knowledge of
curves, coils, and discretization lives upstream (the geometry layer and
the solver that builds the spec); all knowledge of mesh generators lives
downstream (the mesher backends). This is the seam that keeps backends
swappable.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ConductorHole:
    """One conductor, excluded from the field domain as a hole.

    Attributes:
        vertices: Boundary polygon of the conductor's (r, z) cross section,
            ordered along the boundary (either orientation), implicitly
            closed. Produced by BoundaryLoop.sample_polygon.
        mesh_size: Target element size on this conductor's boundary, in the
            same length units as the domain.
    """

    vertices: Tuple[Tuple[float, float], ...]
    mesh_size: float

    def __post_init__(self):
        if len(self.vertices) < 3:
            raise ValueError(
                f"Conductor polygon needs at least 3 vertices, got {len(self.vertices)}"
            )
        if self.mesh_size <= 0:
            raise ValueError(f"mesh_size must be positive, got {self.mesh_size}")


@dataclass(frozen=True)
class MeshSpec:
    """The full meshing problem for the axisymmetric (r, z) half-plane.

    The field domain is the rectangle [0, r_max] x [0, z_max] minus the
    conductor holes. Conductors may touch or cross the domain edges (e.g.
    a topload disc reaching the r=0 axis); the boolean subtraction in the
    backend handles the overlap.

    Attributes:
        r_max: Radial extent of the domain (> 0).
        z_max: Vertical extent of the domain (> 0).
        conductors: Conductor holes, in an order the caller remembers -
            the resulting MeshedGeometry reports boundary attributes
            parallel to this tuple.
        wall_mesh_size: Target element size on the domain walls and axis.
        size_grading: Transition distance over which the fine conductor
            element size grows to the coarse wall size, as a fraction of the
            larger domain extent. Smaller = fewer elements (coarser far
            field); larger = smoother transition (more elements). The mesh
            stays fine at every conductor surface regardless, so this trades
            far-field resolution for speed. Default 0.08.
    """

    r_max: float
    z_max: float
    conductors: Tuple[ConductorHole, ...]
    wall_mesh_size: float
    size_grading: float = 0.08

    def __post_init__(self):
        if self.r_max <= 0 or self.z_max <= 0:
            raise ValueError(
                f"Domain extents must be positive, got r_max={self.r_max}, z_max={self.z_max}"
            )
        if self.wall_mesh_size <= 0:
            raise ValueError(f"wall_mesh_size must be positive, got {self.wall_mesh_size}")
        if self.size_grading <= 0:
            raise ValueError(f"size_grading must be positive, got {self.size_grading}")
