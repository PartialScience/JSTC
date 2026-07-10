from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import numpy as np

from app.simulation.coupled import CoupledSystem, primary_driven_response
from app.simulation.facade.matrices import geometry_fingerprint
from app.simulation.fields import (
    FieldGrid,
    assemble_electrostatic_field,
    assemble_magnetic_field,
    compute_electrostatic_basis,
    compute_magnetic_basis,
)

if TYPE_CHECKING:
    from app.simulation.facade.simulation import TeslaCoilSimulation

ReferenceMode = Literal["floating", "grounded"]
HotEnd = Literal["inner", "outer"]


@dataclass
class FieldResult:
    """A complex operating field sampled on a regular (r, z) grid.

    Attributes:
        kind: 'electric' (values are potential phi [V]) or 'magnetic'
            (values are the azimuthal vector potential A_phi [T*m]).
        grid: the sampling grid (coordinates in coil units).
        values: (nz, nr) complex field values; NaN outside the domain.
        mask: (nz, nr) bool, True where the value is defined.
        unit_scale: metres per coil unit, so the client can differentiate
            in SI (E = -grad phi / unit_scale [V/m]; B from A_phi likewise).
    """

    kind: str
    grid: FieldGrid
    values: np.ndarray
    mask: np.ndarray
    unit_scale: float


class FieldView:
    """Operating electric and magnetic fields of the energized coil.

    Both are superpositions of precomputed basis fields (cached by geometry)
    weighted by the phasor drive solve, so re-rendering at a new frequency,
    current, or reference is instant. Requires a primary with a tank
    capacitance (the drive is the coupled solve)."""

    def __init__(self, sim: "TeslaCoilSimulation"):
        self._sim = sim

    def _system(self) -> CoupledSystem:
        coil = self._sim.coil
        if coil.primary is None or coil.primary.tank_capacitance <= 0:
            raise ValueError(
                "Field visualization requires a primary with tank_capacitance > 0"
            )
        sec = self._sim.secondary
        return CoupledSystem(
            capacitance=np.array(sec.capacitance_matrix),
            inductance=np.array(sec.inductance_matrix),
            connectivity=np.array(sec.connectivity_matrix),
            coupling=np.array(self._sim.coupling.coupling_vector),
            primary_inductance=self._sim.primary.total_inductance,
            tank_capacitance=coil.primary.tank_capacitance,
        )

    def _drive(self, frequency_hz: float, primary_current: complex):
        return primary_driven_response(
            self._system(),
            frequency_hz,
            primary_current=primary_current,
            secondary_resistance=self._sim.secondary.ac_resistance,
            primary_resistance=self._sim.primary.dc_resistance,
        )

    def electric_field(
        self,
        *,
        nr: int,
        nz: int,
        frequency_hz: float,
        primary_current: complex = 1.0,
        reference_mode: ReferenceMode = "floating",
        hot_end: HotEnd = "outer",
    ) -> FieldResult:
        coil = self._sim.coil
        grid = FieldGrid.over_domain(coil.r_max, coil.z_max, nr, nz)
        key = geometry_fingerprint(coil, self._sim._cap_config())
        basis = compute_electrostatic_basis(
            coil, grid, self._sim._discretizer, self._sim._cap_config(), key
        )
        drive = self._drive(frequency_hz, primary_current)
        phi = assemble_electrostatic_field(
            basis,
            drive.node_voltages,
            primary_voltage=drive.primary_voltage,
            reference_mode=reference_mode,
            hot_end=hot_end,
        )
        return FieldResult("electric", grid, phi, basis.mask, coil.unit_scale)

    def magnetic_field(
        self,
        *,
        nr: int,
        nz: int,
        frequency_hz: float,
        primary_current: complex = 1.0,
    ) -> FieldResult:
        coil = self._sim.coil
        grid = FieldGrid.over_domain(coil.r_max, coil.z_max, nr, nz)
        key = geometry_fingerprint(coil, self._sim._cap_config())
        basis = compute_magnetic_basis(coil, grid, self._sim._discretizer, key)
        drive = self._drive(frequency_hz, primary_current)
        a_phi = assemble_magnetic_field(
            basis, drive.segment_currents, primary_current=drive.primary_current
        )
        # A_phi is defined throughout the air region; conductor interiors are
        # a minor visual detail we keep (the loop kernel is finite off-ring).
        mask = np.ones(grid.shape, dtype=bool)
        return FieldResult("magnetic", grid, a_phi, mask, coil.unit_scale)
