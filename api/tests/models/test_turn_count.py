"""
Regression tests for float-noise-immune turn counting.

A winding's total turn count is evaluated as ``turn_fxn(curve.t_max)``,
where the profile's t_max and the curve's t_max are the same length
computed through different float expressions. Non-associative rounding
can leave the product a few ulp above the exact integer (e.g.
1400 * 0.37 / 0.37 == 1400.0000000000002), and a bare ceil then invents
a phantom extra turn. Downstream, the phantom turn became a duplicate
sampling ring coincident with the winding end and a divergent ring
mutual inductance (a 132 kHz coil reported 1.9 kHz).

Run with: pytest tests/models/test_turn_count.py -v
"""
import pytest

from app.models.coil_models import LinearSecondaryConductorSpec
from app.models.materials import Material
from app.models.turn_profiles import UniformTurns, UniformTurnProfile


def _secondary(z_end: float, turns: float = 1400) -> LinearSecondaryConductorSpec:
    """The bug-report coil: 1400 turns on a vertical line from z=0.3."""
    return LinearSecondaryConductorSpec(
        material=Material.COPPER,
        turns=UniformTurns(turns),
        start=(0.065, 0.3),
        end=(0.065, z_end),
        wire_dia=0.000212,
    )


class TestTurnCountFloatNoise:
    @pytest.mark.parametrize("z_end", [0.65, 0.66, 0.67, 0.68, 0.70, 1.21])
    def test_integer_turn_totals_stay_integer(self, z_end):
        """z_end 0.67, 0.70, 1.21 used to ceil 1400 turns up to 1401."""
        assert _secondary(z_end).total_turns == 1400

    def test_fractional_turns_still_round_up(self):
        """Genuine fractional turns keep the documented ceil behavior."""
        assert _secondary(0.67, turns=1400.5).total_turns == 1401
        assert _secondary(0.67, turns=1399.01).total_turns == 1400

    def test_uniform_profile_exact_at_winding_end(self):
        """The profile evaluated at its own t_max is exactly total_turns."""
        length = 0.67 - 0.3  # == 0.37000000000000005
        profile = UniformTurnProfile(total_turns=1400, t_max=length)
        assert profile(length) == 1400.0
