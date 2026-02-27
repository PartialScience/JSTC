import math
from scipy.special import ellipk, ellipe


def coaxial_circle_geometric_mutual_inductance(r1: float, r2: float, d: float) -> float:
    """Calculate the mutual, geometric inductance between two coaxial 
    circular conductors using the Maxwell Formula for coaxial inductance.
    
    Parameters:
    r1: radius of the inner conductor
    r2: radius of the outer conductor
    d: distance between circles along the common axis
    
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
    k_sq = 4.0 * r1 * r2 / ((r1 + r2) ** 2 + d ** 2)
    k = math.sqrt(k_sq)

    K = ellipk(k_sq)  # Complete elliptic integral of the first kind  (parameter m = k²)
    E = ellipe(k_sq)  # Complete elliptic integral of the second kind (parameter m = k²)

    return math.sqrt(r1 * r2) * ((2.0 / k - k) * K - 2.0 / k * E)