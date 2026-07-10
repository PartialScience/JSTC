"""
The regular (r, z) sampling grid used by every field computation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass(frozen=True)
class FieldGrid:
    """A regular grid over the axisymmetric half-plane [0, r_max] x [0, z_max].

    The grid is row-major in z then r: point (iz, ir) is at
    (r_min + ir*dr, z_min + iz*dz). ``points`` is the (2, nr*nz) coordinate
    array in the byNODES layout the sampler expects (all r, then all z).
    """

    r_min: float
    r_max: float
    z_min: float
    z_max: float
    nr: int
    nz: int

    def __post_init__(self):
        if self.nr < 2 or self.nz < 2:
            raise ValueError("grid needs at least 2 points per axis")
        if self.r_max <= self.r_min or self.z_max <= self.z_min:
            raise ValueError("grid extents must be increasing")

    @property
    def r_coords(self) -> np.ndarray:
        return np.linspace(self.r_min, self.r_max, self.nr)

    @property
    def z_coords(self) -> np.ndarray:
        return np.linspace(self.z_min, self.z_max, self.nz)

    @property
    def shape(self) -> Tuple[int, int]:
        """(nz, nr) - the shape a flat field vector reshapes to."""
        return (self.nz, self.nr)

    def points(self) -> np.ndarray:
        """(2, nr*nz) sample coordinates, row 0 = r, row 1 = z, in row-major
        (z-outer, r-inner) order matching ``shape``."""
        rr, zz = np.meshgrid(self.r_coords, self.z_coords)  # (nz, nr)
        return np.vstack([rr.ravel(), zz.ravel()])

    @classmethod
    def over_domain(cls, r_max: float, z_max: float, nr: int, nz: int) -> "FieldGrid":
        """A grid spanning the full simulation domain from the axis."""
        return cls(r_min=0.0, r_max=r_max, z_min=0.0, z_max=z_max, nr=nr, nz=nz)
