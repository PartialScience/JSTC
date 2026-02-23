from __future__ import annotations

from typing import TYPE_CHECKING, Tuple
import app.formulas as formulas
import numpy as np

if TYPE_CHECKING:
    from app.simulation.facade.simulation import TeslaCoilSimulation


class SecondaryView:
    """Lazy computed properties pertaining to the secondary coil."""

    def __init__(self, sim: TeslaCoilSimulation):
        self._sim = sim

    # -- Matrices ------------------------------------------------------------

    @property
    def capacitance_matrix(self) -> Tuple[Tuple[float, ...], ...]:
        """Maxwell mutual capacitance matrix C."""
        coil = self._sim.coil
        return self._sim._cap_solver.compute_capacitance_matrix(
            secondary=coil.secondary,
            toploads=coil.toploads,
            grounds=coil.grounds,
            discretization_order=coil.discretization_order,
            r_max=coil.r_max,
            z_max=coil.z_max,
        )

    @property
    def inductance_matrix(self) -> Tuple[Tuple[float, ...], ...]:
        """Mutual inductance matrix L."""
        coil = self._sim.coil
        return self._sim._ind_solver.compute_inductance_matrix(
            secondary=coil.secondary,
            discretization_order=coil.discretization_order,
        )

    @property
    def connectivity_matrix(self) -> Tuple[Tuple[float, ...], ...]:
        """Connectivity matrix A."""
        coil = self._sim.coil
        return self._sim._conn_solver.compute_connectivity_matrix(
            discretization_order=coil.discretization_order,
        )

    # -- Eigen analysis ------------------------------------------------------

    @property
    def eigen_frequencies(self) -> Tuple[float, ...]:
        """Eigenfrequencies sorted ascending."""
        return self._sim._eigen_solver.compute_eigen_frequencies(
            capacitance_matrix=self.capacitance_matrix,
            inductance_matrix=self.inductance_matrix,
            connectivity_matrix=self.connectivity_matrix,
        )

    @property
    def voltage_eigen_modes(self) -> Tuple[Tuple[float, ...], ...]:
        """Voltage eigenmodes corresponding to eigenfrequencies."""
        return self._sim._eigen_solver.compute_voltage_eigen_modes(
            capacitance_matrix=self.capacitance_matrix,
            inductance_matrix=self.inductance_matrix,
            connectivity_matrix=self.connectivity_matrix,
        )

    @property
    def current_eigen_modes(self) -> Tuple[Tuple[float, ...], ...]:
        """Current eigenmodes derived from voltage eigenmodes via I = -(j/w) L^-1 A^T V."""
        return self._sim._eigen_solver.compute_current_eigen_modes(
            capacitance_matrix=self.capacitance_matrix,
            inductance_matrix=self.inductance_matrix,
            connectivity_matrix=self.connectivity_matrix,
        )

    # -- Derived scalars -----------------------------------------------------

    @property
    def resonant_frequency(self) -> float:
        """Fundamental resonant frequency (lowest eigenfrequency)."""
        return self.eigen_frequencies[0]

    @property
    def coil_pitch(self) -> float:
        """Vertical distance between adjacent turns of the secondary coil."""
        coil = self._sim.coil
        return 1/coil.secondary.turns_per_height

    @property
    def conductor_length(self) -> float:
        """Total length of the conductor/wire making up the secondary coil."""
        (r1, h1) = self._sim.coil.secondary.start
        (r2, h2) = self._sim.coil.secondary.end
        n = self._sim.coil.secondary.turns
        return formulas.conical_helix_arclength(r1, r2, h1, h2, n)
    
    @property
    def dc_resistance(self) -> float:
        """DC resistance of the secondary coil."""
        # TODO: Probably move condutivity off of the coil spec. Not exactly sure where tho yet
        coil = self._sim.coil
        length = self.conductor_length
        conductivity = coil.secondary.conductivity
        wire_area = np.pi * (coil.secondary.wire_dia / 2) ** 2
        return length / (conductivity * wire_area)
        