"""Formuals pertaining to purley geometric calculations, such as lengths, areas, volumes, etc."""

import numpy as np

def conical_helix_arclength(r1: float, r2: float, h1: float, h2: float, n: float) -> float:
    """Compute the arc length of a conical helix
    
    Parameters:
    r1: radius at the bottom of the helix
    r2: radius at the top of the helix
    h1: height at the bottom of the helix
    h2: height at the top of the helix
    n: number of turns in the helix
    
    Returns:
    The arc length of the conical helix.
    
    References:
    1. Helical Curve:   https://mathworld.wolfram.com/Helix.html
    2. Flat Spiral:     https://mathworld.wolfram.com/ArchimedesSpiral.html
    3. Conical Spiral:  https://mathworld.wolfram.com/ConicalSpiral.html
    """
    p = (h2 - h1) / n  # pitch per turn
    
    dh = h2 - h1
    dr = r2 - r1
    
    if r1 == r2:
        # Special case: cylindrical helix
        return abs(dh * np.sqrt(1 + (2 * np.pi * r1 / p)**2) )
    elif h1 == h2:
        # Special case: flat spiral
        a = dr / (2 * np.pi * n)
        def s(t):
            """Arc length of flat spiral from base to t, where t = r * a"""
            return a * (t * np.sqrt(1 + t**2) + np.arcsinh(t)) / 2
        return abs(s(r2/a) - s(r1/a))
    else:
        # General case: conical helix
        a = 2 * np.pi * n / dh
        b = dr/dh
        t1 = r1 * dh / dr
        t2 = r2 * dh / dr
        def s(t):
            """Arc length of spiral from base to t, where t = r * dh / dr"""
            return  t * np.sqrt(1 + b**2 * (1 + a**2 * t**2))/2 + (1+b**2) * np.arcsinh(a*b*t / np.sqrt(1+b**2)) / (2*a*b)
        return abs(s(t2) - s(t1))

def helical_wire_length(curve, turn_fxn, min_samples: int = 2000) -> float:
    """Arc length of the helical wire whose centerline sweeps *curve* in
    the (r, z) plane while circling the axis per *turn_fxn*.

    Integrates sqrt(|dc|^2 + (2*pi*r*dn)^2) along the curve by dense
    trapezoid summation - fully general in the ParametricCurve
    abstraction, so any winding shape (cylinder, cone, flat spiral,
    saucer) is supported. Result is in the curve's geometry units.

    Parameters:
        curve: The winding centerline (a ParametricCurve).
        turn_fxn: Cumulative turns at parameter t.
        min_samples: Lower bound on integration samples (raised
            automatically to 20 per turn).
    """
    total_turns = float(turn_fxn(curve.t_max)) - float(turn_fxn(curve.t_min))
    n_samples = max(min_samples, int(20 * abs(total_turns)))
    ts = np.linspace(curve.t_min, curve.t_max, n_samples)
    points = np.array([curve.point_at(t) for t in ts])
    turns = np.array([turn_fxn(t) for t in ts])
    dr_dz = np.diff(points, axis=0)
    planar_sq = np.sum(dr_dz ** 2, axis=1)
    mean_r = 0.5 * (points[:-1, 0] + points[1:, 0])
    azimuthal = 2 * np.pi * mean_r * np.diff(turns)
    return float(np.sum(np.sqrt(planar_sq + azimuthal ** 2)))
