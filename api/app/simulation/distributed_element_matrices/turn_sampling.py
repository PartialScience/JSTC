"""
Shared turn-sampling helpers for ring-based magnetic solvers.

Both the secondary inductance matrix and the primary-secondary coupling
vector model the secondary as a stack of coaxial rings - one per turn
boundary - grouped into virtual-conductor segments by the discretizer's
slice parameters. These helpers own that convention so the two solvers
group turns IDENTICALLY (a requirement for the coupled eigenproblem's
bordered inductance matrix to be consistent).
"""
from __future__ import annotations

from typing import Tuple

import numpy as np

from app.models.coil_models import SecondaryConductorSpec


def secondary_turn_points(
    secondary: SecondaryConductorSpec,
    samples_per_turn: int,
) -> np.ndarray:
    """(r, z) positions of the secondary's turn-boundary rings.

    Returns an (M+1) x 2 array, M = total_turns: the fencepost positions
    of every integer turn boundary along the winding, found by inverting
    turn_fxn with dense linear interpolation.

    Args:
        secondary: The secondary conductor specification.
        samples_per_turn: Density of the turn_fxn inversion sample.
    """
    curve = secondary.curve
    num_turns = secondary.total_turns

    n_samples = samples_per_turn * num_turns
    t_sample = np.linspace(curve.t_min, curve.t_max, n_samples)
    turn_sample = np.array([secondary.turn_fxn(t) for t in t_sample])

    target_turns = np.arange(1, num_turns, dtype=float)
    t_interp = np.interp(target_turns, turn_sample, t_sample)

    t_values = np.empty(num_turns + 1)
    t_values[0] = curve.t_min
    t_values[1:-1] = t_interp
    t_values[-1] = curve.t_max

    return np.array([curve.point_at(t) for t in t_values])


def segment_start_indices(
    secondary: SecondaryConductorSpec,
    slices: Tuple[float, ...],
    n_points: int,
) -> list[int]:
    """Turn-point index where each virtual-conductor segment begins.

    Maps each segment's STARTING slice parameter to its nearest turn
    index - the reduceat boundaries that group turn-level quantities into
    segment-level ones. The final slice (t_max) is deliberately excluded
    so the last group runs through the final turn (an (N+1)-th group
    would be spurious; see the inductance solver's downsampling).

    Args:
        secondary: The secondary conductor specification.
        slices: The N+1 slice parameters from the discretizer.
        n_points: Number of turn points being grouped (M+1).
    """
    return sorted(set(
        max(0, min(n_points - 1, round(secondary.turn_fxn(t))))
        for t in slices[:-1]
    ))
