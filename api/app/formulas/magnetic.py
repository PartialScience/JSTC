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