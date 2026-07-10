from enum import Enum
from app.models.coil_models import TeslaCoilSpec
from dataclasses import dataclass, field


class BoundaryConditionType(Enum):
    """Type of boundary condition for electromagnetic simulation."""
    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"


@dataclass(frozen=True)
class BoundaryCondition:
    """Boundary condition specification for simulation domain walls.

    Frozen so it can participate in the lru_cache keys of the solvers.
    """
    bc_type: BoundaryConditionType = BoundaryConditionType.DIRICHLET
    value: float = 0.0


@dataclass(kw_only=True)
class SimulatableTeslaCoil(TeslaCoilSpec):
    """Tesla coil specification extended with simulation domain boundaries and boundary conditions."""

    r_max: float
    """Maximum radial extent of the simulation domain"""

    z_max: float
    """Maximum vertical extent of the simulation domain"""

    unit_scale: float = 1.0
    """Meters per geometry unit (e.g. 0.0254 for a coil specified in inches).

    All geometry (coil spec, r_max/z_max) shares one unit system; the
    solvers return matrices in geometric units and the simulation facade
    applies unit_scale together with the physical constants exactly once:
    L = mu_0 * unit_scale * L_geo,  C = 2*pi*epsilon_0 * unit_scale * C_geo.
    """

    discretization_order: int = 30
    """Number of virtual conductors to break the secondary coil into for matrix calculations"""

    bc_bottom: BoundaryCondition = field(default_factory=BoundaryCondition)
    """Boundary condition applied at the bottom (z=0) of the simulation domain."""

    bc_top: BoundaryCondition = field(default_factory=BoundaryCondition)
    """Boundary condition applied at the top (z=z_max) of the simulation domain."""

    bc_right: BoundaryCondition = field(default_factory=BoundaryCondition)
    """Boundary condition applied at the right boundary (r=r_max) of the simulation domain."""

