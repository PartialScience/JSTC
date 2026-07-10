"""
AC resistance formulas: skin effect (exact Kelvin-function solution for a
round wire) and Medhurst's empirical proximity factor for solenoids.

References:
    Medhurst, R. G. (1947). "H.F. Resistance and Self-Capacitance of
    Single-Layer Solenoids," Wireless Engineer, Feb-Sep 1947.
    Applicable to coils of more than ~30 turns driven below their
    self-resonant frequency (accuracy ~3%).

    Skin effect: standard Kelvin-function solution for a solid round
    conductor, e.g. Ramo, Whinnery & Van Duzer, "Fields and Waves in
    Communication Electronics," section on conductors at high frequency.
"""
import math

import numpy as np
from scipy.special import ber, bei, berp, beip


def skin_effect_factor(wire_dia: float, skin_depth: float) -> float:
    """Ratio Rac/Rdc for an isolated solid round wire (skin effect only).

    Exact Kelvin-function solution:

        q = sqrt(2) * a / delta
        Rac/Rdc = (q/2) * (ber(q)*bei'(q) - bei(q)*ber'(q))
                        / (ber'(q)^2 + bei'(q)^2)

    with the high-frequency limit a/(2*delta) + 1/4. Both arguments must
    share the same length unit.

    Args:
        wire_dia: Conductor diameter.
        skin_depth: Skin depth at the frequency of interest.

    Returns:
        The skin-effect resistance multiplier (>= 1).
    """
    if wire_dia <= 0 or skin_depth <= 0:
        raise ValueError("wire_dia and skin_depth must be positive")

    a = wire_dia / 2.0
    q = math.sqrt(2.0) * a / skin_depth

    if q < 1e-3:
        # Series limit: 1 + q^4/48 - negligible; avoid 0/0 in the ratio
        return 1.0

    numerator = ber(q) * beip(q) - bei(q) * berp(q)
    denominator = berp(q) ** 2 + beip(q) ** 2
    return float((q / 2.0) * numerator / denominator)


# ---------------------------------------------------------------------------
# Medhurst proximity factor table.
# Rows: coil aspect ratio H/D (winding length / diameter).
# Columns: spacing ratio (turn pitch / wire diameter).
# Values: proximity multiplier Phi.
# ---------------------------------------------------------------------------

_MEDHURST_SPACING = np.array([1.00, 1.11, 1.25, 1.429, 1.667, 2.00, 2.50])
_MEDHURST_ASPECT = np.array([1.0, 2.0, 4.0, 6.0])
_MEDHURST_PHI = np.array([
    # spacing:  1.00  1.11  1.25  1.429 1.667 2.00  2.50
    [5.55, 4.10, 3.17, 2.47, 1.94, 1.67, 1.45],   # H/D = 1
    [4.10, 3.36, 2.74, 2.32, 1.98, 1.74, 1.50],   # H/D = 2
    [3.54, 3.05, 2.60, 2.27, 2.01, 1.78, 1.54],   # H/D = 4
    [3.31, 2.92, 2.60, 2.29, 2.03, 1.80, 1.56],   # H/D = 6
])


def medhurst_proximity_factor(spacing_ratio: float, aspect_ratio: float) -> float:
    """Medhurst's proximity-effect multiplier Phi for a single-layer
    solenoid, bilinearly interpolated from his published table.

    Args:
        spacing_ratio: Turn pitch (center to center) / wire diameter.
            Physical windings have >= 1; values outside the table range
            [1.0, 2.5] are clamped to the boundary (Phi varies slowly
            beyond it).
        aspect_ratio: Winding length / coil diameter (H/D). Clamped to
            the tabulated range [1, 6].

    Returns:
        The proximity multiplier Phi (>= 1 for all tabulated geometry).
    """
    if spacing_ratio <= 0 or aspect_ratio <= 0:
        raise ValueError("spacing_ratio and aspect_ratio must be positive")

    s = float(np.clip(spacing_ratio, _MEDHURST_SPACING[0], _MEDHURST_SPACING[-1]))
    h = float(np.clip(aspect_ratio, _MEDHURST_ASPECT[0], _MEDHURST_ASPECT[-1]))

    # Interpolate along spacing within each aspect row, then across rows
    per_row = np.array([
        np.interp(s, _MEDHURST_SPACING, row) for row in _MEDHURST_PHI
    ])
    return float(np.interp(h, _MEDHURST_ASPECT, per_row))
