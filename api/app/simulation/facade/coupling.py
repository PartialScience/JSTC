from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

import numpy as np
from scipy.constants import mu_0

if TYPE_CHECKING:
    from app.simulation.facade.simulation import TeslaCoilSimulation


class CouplingView:
    """Primary-secondary magnetic coupling quantities.

    Belongs to neither coil alone: the coupling vector m borders the
    secondary's L matrix into the combined inductance matrix

        [[L,   m ],
         [m^T, L_p]]

    of the coupled system (the object a future coupled-mode solver and
    SPICE exporter consume). All values SI.
    """

    def __init__(self, sim: TeslaCoilSimulation):
        self._sim = sim

    @property
    def coupling_vector(self) -> Tuple[float, ...]:
        """m in Henries: entry k is the mutual inductance between the
        primary and secondary segment k."""
        coil = self._sim.coil
        m_geo = np.array(self._sim._matrices.coupling_geo())
        return tuple(float(v) for v in m_geo * mu_0 * coil.unit_scale)

    @property
    def mutual_inductance(self) -> float:
        """Lm in Henries: total primary-secondary mutual inductance
        (uniform secondary current), Lm = sum_k m_k."""
        return float(np.sum(self.coupling_vector))

    @property
    def coupling_coefficient(self) -> float:
        """k = Lm / sqrt(L_p * L_s), with both self-inductances at their
        DC (uniform current) values - the JavaTC/TSSP convention."""
        lm = self.mutual_inductance
        lp = self._sim.primary.dc_inductance
        ls = self._sim.secondary.dc_inductance
        return float(lm / np.sqrt(lp * ls))

    @property
    def bordered_inductance_matrix(self) -> Tuple[Tuple[float, ...], ...]:
        """The (N+1)x(N+1) combined inductance matrix [[L, m],[m^T, L_p]]
        in Henries. Symmetric positive-definite whenever the coupling is
        physical (k < 1) - the canonical magnetic object of the coupled
        primary-secondary model."""
        L = np.array(self._sim.secondary.inductance_matrix)
        m = np.array(self.coupling_vector).reshape(-1, 1)
        lp = np.array([[self._sim.primary.dc_inductance]])
        bordered = np.block([[L, m], [m.T, lp]])
        return tuple(tuple(float(x) for x in row) for row in bordered)

    # -- Energy transfer ----------------------------------------------------------

    @property
    def half_cycles_for_energy_transfer(self) -> float:
        """Number of RF half-cycles for complete primary->secondary
        energy transfer at the present coupling: 1/k."""
        return 1.0 / self.coupling_coefficient

    @property
    def energy_transfer_time(self) -> float:
        """Time for complete energy transfer in seconds:
        (half cycles) / (2 * f_avg), with f_avg the mean of the two
        resonant frequencies."""
        f_avg = 0.5 * (
            self._sim.primary.resonant_frequency
            + self._sim.secondary.resonant_frequency
        )
        return self.half_cycles_for_energy_transfer / (2.0 * f_avg)
