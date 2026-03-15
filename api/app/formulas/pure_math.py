import math
import numba


@numba.njit(inline="always")
def ellipke(m: float):
    """Compute the complete elliptic integrals K(m) and E(m) simultaneously
    via a single arithmetic-geometric mean (AGM) pass.

    Parameters:
    m: the parameter (= k²), must satisfy 0 ≤ m < 1.

    Returns:
    (K, E) — the complete elliptic integrals of the first and second kind.
    """
    a = 1.0
    b = math.sqrt(1.0 - m)
    s = 0.5 * m
    twon = 1.0
    for _ in range(30):  # AGM converges in < 15 iterations for float64
        if abs(a - b) <= 1e-15 * a:
            break
        c = (a - b) * 0.5
        s += twon * c * c
        twon *= 2.0
        a_new = (a + b) * 0.5
        b = math.sqrt(a * b)
        a = a_new
    K = math.pi / (2.0 * a)
    E = K * (1.0 - s)
    return K, E
