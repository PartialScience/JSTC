"""
Shared turn-sampling helpers for ring-based magnetic solvers.

Both the secondary inductance matrix and the primary-secondary coupling
vector model the secondary as a stack of coaxial rings - one per turn
boundary - grouped into virtual-conductor segments by the discretizer's
slice parameters. These helpers own that convention so the two solvers
group turns IDENTICALLY (a requirement for the coupled eigenproblem's
bordered inductance matrix to be consistent).

Turn boundaries are located with the turn profile's EXACT closed-form
inverse, and the discretizer guarantees every slice boundary sits exactly
on an integer turn, so the grouping below is exact rather than
nearest-turn rounding.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np

from app.models.coil_models import SecondaryConductorSpec


def secondary_turn_points(secondary: SecondaryConductorSpec) -> np.ndarray:
    """(r, z) positions of the secondary's turn-boundary rings.

    Returns an (M+1) x 2 array, M = total_turns: the fencepost positions
    of every integer turn boundary along the winding, located by the turn
    profile's exact inverse.
    """
    curve = secondary.curve
    turn_fxn = secondary.turn_fxn
    num_turns = secondary.total_turns

    t_values = [curve.t_min]
    t_values += [turn_fxn.inverse(float(k)) for k in range(1, num_turns)]
    t_values.append(curve.t_max)
    return np.array([curve.point_at(t) for t in t_values])


def segment_start_indices(
    secondary: SecondaryConductorSpec,
    slices: Tuple[float, ...],
    n_points: int,
) -> list[int]:
    """Turn-point index where each virtual-conductor segment begins.

    Maps each segment's STARTING slice parameter to its turn index - the
    reduceat boundaries that group turn-level quantities into segment-level
    ones. The final slice (t_max) is deliberately excluded so the last
    group runs through the final turn.

    The discretizer cuts on integer turn boundaries, so the mapping is
    exact; a non-increasing result would mean the slices were produced by
    a discretizer violating that contract, and is rejected loudly rather
    than silently collapsing the matrix dimensions.
    """
    indices = [
        max(0, min(n_points - 1, round(secondary.turn_fxn(t))))
        for t in slices[:-1]
    ]
    if indices[0] != 0:
        raise ValueError(
            "The first slice must start at the winding base (turn 0); got "
            f"turn index {indices[0]}."
        )
    for a, b in zip(indices[:-1], indices[1:]):
        if b <= a:
            raise ValueError(
                "Slice boundaries must map to strictly increasing turn "
                f"indices, got {indices}. The discretizer must cut on "
                "whole-turn boundaries with at most one slice per turn."
            )
    return indices
