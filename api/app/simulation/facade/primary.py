from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from scipy.constants import mu_0

if TYPE_CHECKING:
    from app.simulation.facade.simulation import TeslaCoilSimulation


class PrimaryView:
    """Lazy computed properties pertaining to the primary coil.

    All values are SI (H, Ohm, Hz, m, kg) unless the name says otherwise.
    Every property requires the coil to have a primary; accessing one on
    a primary-less coil raises ValueError.
    """

    #: Temperature used for material properties (matches SecondaryView).
    _AMBIENT_K = 293.15

    def __init__(self, sim: TeslaCoilSimulation):
        self._sim = sim

    @property
    def _spec(self):
        primary = self._sim.coil.primary
        if primary is None:
            raise ValueError("This coil has no primary specified")
        return primary

    # -- Magnetics --------------------------------------------------------------

    @property
    def dc_inductance(self) -> float:
        """Ldc of the primary winding in Henries (ring model with the
        cross-section's uniform-current GMD; fractional-turn weighted)."""
        from app.simulation.distributed_element_matrices.coupling import (
            primary_geometric_self_inductance,
        )

        coil = self._sim.coil
        return primary_geometric_self_inductance(self._spec) * mu_0 * coil.unit_scale

    @property
    def lead_inductance(self) -> float:
        """Self-inductance of the connection leads in Henries (straight
        round-wire formula). Zero when no lead is specified."""
        from app.formulas.magnetic import straight_wire_geometric_inductance

        spec = self._spec
        if spec.lead_length <= 0:
            return 0.0
        geo = straight_wire_geometric_inductance(spec.lead_length, spec.lead_dia)
        return geo * mu_0 * self._sim.coil.unit_scale

    @property
    def total_inductance(self) -> float:
        """Winding + lead inductance in Henries - the L of the tank."""
        return self.dc_inductance + self.lead_inductance

    # -- Resonance ----------------------------------------------------------------

    @property
    def resonant_frequency(self) -> float:
        """Primary tank resonant frequency in Hz:
        1 / (2*pi*sqrt((Lp + L_lead) * C_tank))."""
        spec = self._spec
        if spec.tank_capacitance <= 0:
            raise ValueError(
                "Primary resonant frequency requires tank_capacitance > 0"
            )
        return float(
            1.0 / (2 * np.pi * np.sqrt(self.total_inductance * spec.tank_capacitance))
        )

    @property
    def percent_detuned(self) -> float:
        """How far the secondary sits above the primary, in percent:
        100 * (f_secondary - f_primary) / f_primary. Positive means the
        secondary is tuned high (JavaTC prints this as '% high')."""
        f_p = self.resonant_frequency
        f_s = self._sim.secondary.resonant_frequency
        return float(100.0 * (f_s - f_p) / f_p)

    # -- Geometry and wire ----------------------------------------------------------

    @property
    def wire_length(self) -> float:
        """Total conductor length of the primary in meters."""
        from app.formulas.geometric import helical_wire_length

        spec = self._spec
        geo = helical_wire_length(spec.curve, spec.turn_fxn)
        return geo * self._sim.coil.unit_scale

    @property
    def coil_pitch(self) -> float:
        """Center-to-center turn spacing along the winding, in meters."""
        coil = self._sim.coil
        spec = self._spec
        curve = spec.curve
        length = curve.arc_length_between(curve.t_min, curve.t_max)
        return length * coil.unit_scale / spec.total_turns

    @property
    def turn_spacing(self) -> float:
        """Edge-to-edge gap between adjacent turns, in meters."""
        extent = self._spec.cross_section.max_extent * self._sim.coil.unit_scale
        return self.coil_pitch - extent

    @property
    def dc_resistance(self) -> float:
        """DC resistance of the primary conductor in Ohms.

        Uses the round-wire area for circular cross-sections and the
        rectangular area for ribbon conductors.
        """
        from app.geometry.cross_sections import CircularCrossSection, RectangularCrossSection

        coil = self._sim.coil
        spec = self._spec
        s = coil.unit_scale
        cs = spec.cross_section
        if isinstance(cs, CircularCrossSection):
            area = np.pi * (cs.diameter * s / 2) ** 2
        elif isinstance(cs, RectangularCrossSection):
            area = (cs.width * s) * (cs.height * s)
        else:
            raise NotImplementedError(
                f"No conductor area rule for {type(cs).__name__}"
            )
        conductivity = spec.material.value.conductivity(self._AMBIENT_K)
        return float(self.wire_length / (conductivity * area))
