"""
Output bundle of an AxisymmetricMesher: the MFEM mesh plus the registry
mapping physical surfaces to MFEM boundary attributes.
"""
from dataclasses import dataclass
from typing import Tuple

import mfem.ser as mfem


@dataclass
class MeshedGeometry:
    """An MFEM mesh of the axisymmetric field domain, with named attributes.

    Boundary attribute conventions (MFEM attributes are 1-based ints):

        axis_attr:        the symmetry axis r = 0 (natural/Neumann boundary)
        bottom_attr:      the wall z = 0
        right_attr:       the wall r = r_max
        top_attr:         the wall z = z_max
        conductor_attrs:  one attribute per conductor hole, parallel to the
                          MeshSpec.conductors tuple that produced this mesh
    """

    mesh: mfem.Mesh
    axis_attr: int
    bottom_attr: int
    right_attr: int
    top_attr: int
    conductor_attrs: Tuple[int, ...]

    @property
    def wall_attrs(self) -> Tuple[int, int, int]:
        """The Dirichlet-capable wall attributes (bottom, right, top)."""
        return (self.bottom_attr, self.right_attr, self.top_attr)
