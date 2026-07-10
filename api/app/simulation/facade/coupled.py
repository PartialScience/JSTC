from __future__ import annotations

from typing import TYPE_CHECKING, List, Sequence, Tuple

import numpy as np

from app.simulation.coupled import (
    CoupledSystem,
    coupled_mode_frequencies,
    export_spice_subcircuit,
    primary_input_impedance,
)

if TYPE_CHECKING:
    from app.simulation.facade.simulation import TeslaCoilSimulation


class CoupledView:
    """The full coupled primary-secondary solve.

    Unlike JavaTC's independent-resonator treatment, this closes the loop:
    the secondary capacitance ladder, the bordered inductance matrix and
    the primary tank capacitor form one system, exposing frequency
    splitting, the primary driving-point impedance, and a SPICE export.

    Requires a primary with a tank capacitance. All SI.
    """

    def __init__(self, sim: TeslaCoilSimulation):
        self._sim = sim

    def _system(self) -> CoupledSystem:
        coil = self._sim.coil
        if coil.primary is None:
            raise ValueError("The coupled solve requires a coil with a primary")
        if coil.primary.tank_capacitance <= 0:
            raise ValueError(
                "The coupled solve requires the primary to have a tank "
                "capacitance (primary.tank_capacitance > 0)"
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

    # -- Frequency splitting ---------------------------------------------------

    @property
    def mode_frequencies(self) -> Tuple[float, ...]:
        """All coupled resonant frequencies (Hz), ascending."""
        return tuple(float(f) for f in coupled_mode_frequencies(self._system()))

    @property
    def split_frequencies(self) -> Tuple[float, float]:
        """The fundamental split pair (lower, upper) in Hz - the two modes
        the primary/secondary pole-splitting produces around the operating
        point."""
        freqs = self.mode_frequencies
        return (freqs[0], freqs[1])

    @property
    def frequency_split(self) -> float:
        """Separation of the split pair, in Hz."""
        lo, hi = self.split_frequencies
        return hi - lo

    # -- Driving-point impedance -----------------------------------------------

    def primary_input_impedance(
        self,
        frequencies_hz: Sequence[float],
        *,
        include_losses: bool = False,
        include_tank: bool = True,
    ) -> List[complex]:
        """Complex impedance looking into the primary tank terminals, per
        frequency (Ohms), with the secondary installed.

        Args:
            frequencies_hz: Frequencies to evaluate.
            include_losses: Use the secondary AC resistance and primary DC
                resistance so resonance peaks are finite (else lossless).
            include_tank: Include the series tank capacitor (the full
                primary-LC input impedance). False gives the primary
                winding + reflected secondary only.
        """
        r_sec = self._sim.secondary.ac_resistance if include_losses else 0.0
        r_prim = self._sim.primary.dc_resistance if include_losses else 0.0
        z = primary_input_impedance(
            self._system(),
            np.asarray(frequencies_hz, dtype=float),
            secondary_resistance=r_sec,
            primary_resistance=r_prim,
            include_tank=include_tank,
        )
        return [complex(v) for v in z]

    # -- SPICE export ----------------------------------------------------------

    def spice_netlist(self, name: str = "teslacoil") -> str:
        """A SPICE subcircuit reproducing the coupled system's AC/transient
        behavior (ports: prim_in, prim_gnd)."""
        return export_spice_subcircuit(self._system(), name=name)
