"""
Meshing package: geometry-to-mesh conversion for axisymmetric FEM solves.

The pipeline is deliberately layered so every stage is a plain-data handoff:

    boundary loops (geometry pkg)  ->  MeshSpec (sampled polygons + sizes)
    MeshSpec  ->  AxisymmetricMesher backend  ->  MeshedGeometry
    MeshedGeometry = mfem.Mesh + boundary attribute registry

Backends are swappable behind AxisymmetricMesher; GmshMesher is the first.
"""

from .mesh_spec import ConductorHole, MeshSpec
from .meshed_geometry import MeshedGeometry
from .base import AxisymmetricMesher
from .gmsh_mesher import GmshMesher
from .gmsh_to_mfem import gmsh_to_mfem, extract_gmsh_data

__all__ = [
    "ConductorHole",
    "MeshSpec",
    "MeshedGeometry",
    "AxisymmetricMesher",
    "GmshMesher",
    "gmsh_to_mfem",
    "extract_gmsh_data",
]
