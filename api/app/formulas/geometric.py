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