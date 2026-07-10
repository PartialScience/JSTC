"""
Abstract interface for axisymmetric mesh generator backends.
"""
from abc import ABC, abstractmethod

from .mesh_spec import MeshSpec
from .meshed_geometry import MeshedGeometry


class AxisymmetricMesher(ABC):
    """Base class for mesh generator backends.

    A backend consumes a MeshSpec (plain polygons + sizes) and produces a
    MeshedGeometry (an mfem.Mesh with the attribute registry). Backends
    must be safe to call repeatedly from a single process; backends built
    on global-state libraries (e.g. Gmsh) must serialize access internally
    so that callers never need to know.
    """

    @abstractmethod
    def mesh(self, spec: MeshSpec) -> MeshedGeometry:
        """Generate a mesh of the field domain described by *spec*.

        Args:
            spec: The meshing problem.

        Returns:
            The meshed geometry with attribute registry.

        Raises:
            ValueError: If the spec describes an unmeshable configuration
                (e.g. a conductor entirely outside the domain).
        """
        ...
