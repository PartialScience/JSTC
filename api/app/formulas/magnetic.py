import math
import numba
from app.formulas.pure_math import ellipke


@numba.njit
def coaxial_circle_geometric_mutual_inductance(
    r1: float, r2: float, d: float, wire_diameter: float
) -> float:
    """Calculate the mutual, geometric inductance between two coaxial 
    circular conductors using the Maxwell Formula for coaxial inductance.
    
    When d=0 and r1=r2 (self-inductance of a single ring), the mutual
    formula diverges. In this case, the Kirchhoff formula for the self-
    inductance of a circular loop of finite wire cross-section is used
    instead.
    
    Compiled with numba.njit — callable from other @numba.njit functions
    and from regular Python code (accepts scalars only).
    
    Parameters:
    r1: radius of the first conductor
    r2: radius of the second conductor
    d: distance between circles along the common axis
    wire_diameter: diameter of the wire cross-section
    
    Returns:
    The geometric inductance of the two circular loops. The returned quantity will
    have the same units as r1, r2, and d. To get the inductance, multiply this quantity
    by the vacuum permeability constant μ0.
    
    References: 
    
    Rosa, E.B. & Grover, F.W. (1912). "Formulas and Tables for the 
    Calculation of Mutual and Self-Inductance," Bulletin of the Bureau of 
    Standards, Vol. 8, No. 1, p. 6, Formula [1].
    
    Link: https://nvlpubs.nist.gov/nistpubs/bulletin/08/nbsbulletinv8n1p1_A2b.pdf
    """
    if d == 0.0 and r1 == r2:
        wire_radius = wire_diameter / 2.0
        return r1 * (math.log(8.0 * r1 / wire_radius) - 2.0)

    k_sq = 4.0 * r1 * r2 / ((r1 + r2) ** 2 + d ** 2)
    k = math.sqrt(k_sq)
    K, E = ellipke(k_sq)
    return math.sqrt(r1 * r2) * ((2.0 / k - k) * K - 2.0 / k * E)

@numba.njit
def coaxial_ring_self_geometric_inductance(radius: float, gmd: float) -> float:
    """Geometric self-inductance of a single circular ring of conductor
    whose cross-section has the given geometric mean distance.

    L_geo = R * (ln(8R / gmd) - 2)

    With the uniform-current GMD of a round wire (a * e^-1/4) this
    reproduces the classic low-frequency formula R(ln(8R/a) - 1.75);
    passing the physical wire radius instead gives the surface-current
    (fully skin-limited) value. Multiply by mu_0 for Henries.

    References:
        Rosa & Grover (1912), Bulletin of the Bureau of Standards Vol. 8
        No. 1 - self-inductance of a circular ring.
    """
    return radius * (math.log(8.0 * radius / gmd) - 2.0)


def straight_wire_geometric_inductance(length: float, diameter: float) -> float:
    """Geometric self-inductance of a straight round wire (uniform
    current, low frequency):

    L_geo = (l / 2*pi) * (ln(4l / d) - 0.75)

    Multiply by mu_0 for Henries. This is the classic Rosa formula JavaTC
    uses for connection leads (its example lead - 30 in of 0.2 in
    conductor - evaluates to 0.861 uH, matching JavaTC's output exactly).

    References:
        Rosa, E.B. (1908). "The Self and Mutual Inductances of Linear
        Conductors," Bulletin of the Bureau of Standards Vol. 4, No. 2.
    """
    if length <= 0 or diameter <= 0:
        raise ValueError("length and diameter must be positive")
    return (length / (2.0 * math.pi)) * (math.log(4.0 * length / diameter) - 0.75)
