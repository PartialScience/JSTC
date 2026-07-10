"""
Conductor cross-section shapes.

A CrossSection describes the (r, z)-plane profile of a wound conductor -
round wire by default, rectangular for ribbon/strap conductors. It owns
the two facts the solvers need:

  * region_at(center): the GeometricRegion the conductor occupies when a
    turn is centered at a point - consumed by the electrostatic mesher.
  * gmd: the geometric mean distance of the section, which replaces the
    physical radius in ring self-inductance formulas - consumed by the
    magnetics solvers.

Complexity lives in the concrete classes (the arc-length pattern): adding
a new section shape means providing its region and its GMD, nothing else.
"""
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple

from app.geometry.regions.base_geometric_region import GeometricRegion
from app.geometry.regions.simple_regions import Circle, Rectangle


@dataclass(frozen=True)
class CrossSection(ABC):
    """Abstract conductor cross-section profile."""

    @abstractmethod
    def region_at(self, center: Tuple[float, float]) -> GeometricRegion:
        """The region occupied by the conductor centered at *center*."""
        ...

    @property
    @abstractmethod
    def gmd(self) -> float:
        """Geometric mean distance of the section from itself.

        Used as the effective radius in ring self-inductance formulas
        (uniform current distribution - the DC/low-frequency convention):
        L_geo = R * (ln(8R / gmd) - 2).
        """
        ...

    @property
    @abstractmethod
    def max_extent(self) -> float:
        """Largest linear dimension of the section (mesh sizing hint)."""
        ...


@dataclass(frozen=True)
class CircularCrossSection(CrossSection):
    """A round conductor of the given diameter.

    GMD of a solid disc with uniform current is a * e^(-1/4) (Maxwell),
    which reproduces the classic uniform-current ring formula
    L = R (ln(8R/a) - 1.75) when substituted into ln(8R/gmd) - 2.
    """

    diameter: float

    def __post_init__(self):
        if self.diameter <= 0:
            raise ValueError(f"diameter must be positive, got {self.diameter}")

    def region_at(self, center: Tuple[float, float]) -> Circle:
        return Circle(center=center, radius=self.diameter / 2)

    @property
    def gmd(self) -> float:
        return (self.diameter / 2) * math.exp(-0.25)

    @property
    def max_extent(self) -> float:
        return self.diameter


@dataclass(frozen=True)
class RectangularCrossSection(CrossSection):
    """A rectangular (ribbon/strap) conductor.

    Attributes:
        width: Radial extent of the section.
        height: Axial extent of the section.

    GMD of a rectangle with uniform current is approximately
    0.2235 * (width + height) (Rosa & Grover 1912, Formulas and Tables
    for the Calculation of Mutual and Self-Inductance).
    """

    width: float
    height: float

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"width and height must be positive, got {self.width} x {self.height}"
            )

    def region_at(self, center: Tuple[float, float]) -> Rectangle:
        cr, cz = center
        w2, h2 = self.width / 2, self.height / 2
        return Rectangle(vertices=(
            (cr - w2, cz - h2),
            (cr + w2, cz - h2),
            (cr + w2, cz + h2),
            (cr - w2, cz + h2),
        ))

    @property
    def gmd(self) -> float:
        return 0.2235 * (self.width + self.height)

    @property
    def max_extent(self) -> float:
        return max(self.width, self.height)
