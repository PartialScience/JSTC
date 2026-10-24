"""
Tests for secondary turn sampling: ring fencepost placement and the
overlapping-turns warning.

Run with: pytest tests/simulation/distributed_element_matrices/test_turn_sampling.py -v
"""
import warnings

import numpy as np
import pytest

from app.models.coil_models import LinearSecondaryConductorSpec
from app.models.materials import Material
from app.models.turn_profiles import UniformTurns
from app.simulation.distributed_element_matrices.turn_sampling import secondary_turn_points


def _secondary(z_end: float = 0.67, turns: float = 1400, wire_dia: float = 0.000212):
    return LinearSecondaryConductorSpec(
        material=Material.COPPER,
        turns=UniformTurns(turns),
        start=(0.065, 0.3),
        end=(0.065, z_end),
        wire_dia=wire_dia,
    )


class TestSecondaryTurnPoints:
    def test_no_phantom_ring_at_float_noise_length(self):
        """Regression: z_end=0.67 used to yield 1402 fenceposts, the last
        two coincident to within 1e-16 (see tests/models/test_turn_count.py
        for the root cause)."""
        points = secondary_turn_points(_secondary())
        assert points.shape == (1401, 2)
        gaps = np.linalg.norm(np.diff(points, axis=0), axis=1)
        # Uniform pitch: every gap is one turn spacing, well above wire dia.
        assert gaps.min() == pytest.approx(0.37 / 1400, rel=1e-6)

    def test_clean_winding_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            secondary_turn_points(_secondary())

    def test_overlapping_turns_warn(self):
        """1400 turns of 0.5 mm wire over 0.37 m: pitch 0.264 mm < wire dia."""
        with pytest.warns(UserWarning, match="turns overlap"):
            secondary_turn_points(_secondary(wire_dia=0.0005))
