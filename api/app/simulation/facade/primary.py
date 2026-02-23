from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.simulation.facade.simulation import TeslaCoilSimulation


class PrimaryView:
    """Lazy computed properties pertaining to the primary coil (placeholder)."""

    def __init__(self, sim: TeslaCoilSimulation):
        self._sim = sim
