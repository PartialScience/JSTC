"""
Deliberate numerical building blocks for the geometry layer.

The curve classes implement every geometric quantity with exact math where
a closed form exists (lines, arcs, and their offsets are fully closed-form).
The helpers here exist for the few quantities that provably have no
elementary closed form - chiefly the arc length of a polynomial spline -
and are consumed as *owned, tested implementations by a specific class*,
never as silent generic fallbacks on a base class.

Everything here is deterministic and tolerance-controlled.
"""
from __future__ import annotations

from typing import Callable, Tuple

import numpy as np

# 15-point Gauss-Legendre nodes/weights on [-1, 1]: exact for polynomials up
# to degree 29, which comfortably covers the speed integrand of a cubic
# segment to machine precision once panels are small enough for the sqrt.
_GL_NODES, _GL_WEIGHTS = np.polynomial.legendre.leggauss(15)


def gauss_legendre_integral(f: Callable[[np.ndarray], np.ndarray], a: float, b: float) -> float:
    """Fixed 15-point Gauss-Legendre estimate of the integral of f over [a, b].

    f must accept a numpy array of evaluation points and return an array.
    """
    half = 0.5 * (b - a)
    mid = 0.5 * (a + b)
    return float(half * np.dot(_GL_WEIGHTS, f(mid + half * _GL_NODES)))


def adaptive_cumulative_integral(
    f: Callable[[np.ndarray], np.ndarray],
    a: float,
    b: float,
    rel_tol: float = 1e-12,
    max_depth: int = 30,
) -> Tuple[np.ndarray, np.ndarray]:
    """Adaptive cumulative integral of a positive integrand over [a, b].

    Subdivides until each panel's 15-point Gauss-Legendre estimate agrees
    with the sum of its two half-panel estimates to ``rel_tol`` (relative to
    the running total), then returns the panel grid and the cumulative
    integral at each grid point:

        x_breaks: increasing array starting at a and ending at b
        F_cum:    same length; F_cum[i] = integral of f from a to x_breaks[i]

    The returned grid is the natural breakpoint table for a monotone
    inversion of the cumulative function (see ``invert_cumulative``).

    Raises:
        ValueError: if the tolerance cannot be met within max_depth levels
            (an integrand far rougher than a spline speed - a bug upstream).
    """
    if b <= a:
        raise ValueError(f"Integration range must be increasing, got [{a}, {b}]")

    breaks: list[float] = [a]
    partials: list[float] = []

    # Scale for the relative tolerance: a first whole-range estimate.
    scale = abs(gauss_legendre_integral(f, a, b)) or 1.0

    def refine(lo: float, hi: float, whole: float, depth: int) -> None:
        mid = 0.5 * (lo + hi)
        left = gauss_legendre_integral(f, lo, mid)
        right = gauss_legendre_integral(f, mid, hi)
        if abs((left + right) - whole) <= rel_tol * scale:
            breaks.append(mid)
            partials.append(left)
            breaks.append(hi)
            partials.append(right)
            return
        if depth >= max_depth:
            raise ValueError(
                "adaptive_cumulative_integral failed to converge; integrand "
                "is rougher than any valid curve speed"
            )
        refine(lo, mid, left, depth + 1)
        refine(mid, hi, right, depth + 1)

    refine(a, b, gauss_legendre_integral(f, a, b), 0)

    x = np.array(breaks)
    F = np.concatenate([[0.0], np.cumsum(partials)])
    return x, F


def invert_cumulative(
    x_breaks: np.ndarray,
    F_cum: np.ndarray,
    target: float,
    f: Callable[[np.ndarray], np.ndarray],
    tol: float,
    max_iter: int = 60,
) -> float:
    """Solve F(x) = target for x, where F is the cumulative integral of the
    positive vectorized integrand ``f`` tabulated on (x_breaks, F_cum).

    Strategy: bracket by table lookup, then safeguarded Newton (falls back to
    bisection whenever a Newton step leaves the bracket). Converges to
    |F(x) - target| <= tol; since f is bounded away from zero for a regular
    curve, this bounds the x error by tol / min f.
    """
    target = float(np.clip(target, F_cum[0], F_cum[-1]))
    i = int(np.searchsorted(F_cum, target, side="right") - 1)
    i = max(0, min(i, len(x_breaks) - 2))
    lo, hi = float(x_breaks[i]), float(x_breaks[i + 1])
    F_lo = float(F_cum[i])

    # Current estimate from linear interpolation inside the bracket panel.
    span = float(F_cum[i + 1]) - F_lo
    x = lo if span == 0 else lo + (hi - lo) * (target - F_lo) / span

    for _ in range(max_iter):
        # Residual via one Gauss-Legendre panel from the bracket's left edge
        # (panels are already converged to the table tolerance).
        F_x = F_lo + (gauss_legendre_integral(f, lo, x) if x > lo else 0.0)
        err = F_x - target
        if abs(err) <= tol:
            return x
        if err > 0:
            hi = x
        else:
            lo, F_lo = x, F_x
        d = float(f(np.array([x]))[0])
        x_newton = x - err / d if d > 0 else None
        x = x_newton if x_newton is not None and lo < x_newton < hi else 0.5 * (lo + hi)
    return x


def invert_cumulative_many(
    x_breaks: np.ndarray,
    F_cum: np.ndarray,
    targets: np.ndarray,
    f: Callable[[np.ndarray], np.ndarray],
    tol: float,
    max_iter: int = 60,
) -> np.ndarray:
    """Vectorized ``invert_cumulative``: solve F(x_i) = target_i for every
    target at once, to the same tolerance and by the same safeguarded-Newton
    strategy. One call replaces len(targets) scalar solves, turning the
    per-iteration Gauss-Legendre residual into a single (n x 15) batch
    evaluation of ``f`` - the difference between milliseconds and seconds
    when a caller samples a spline densely (e.g. wire-length integration).
    """
    targets = np.clip(np.asarray(targets, dtype=float), F_cum[0], F_cum[-1])
    idx = np.clip(
        np.searchsorted(F_cum, targets, side="right") - 1, 0, len(x_breaks) - 2
    )
    lo = np.asarray(x_breaks, dtype=float)[idx]
    hi = np.asarray(x_breaks, dtype=float)[idx + 1]
    F_lo = np.asarray(F_cum, dtype=float)[idx]

    # Initial estimates from linear interpolation inside each bracket panel.
    span = np.asarray(F_cum, dtype=float)[idx + 1] - F_lo
    safe_span = np.where(span == 0.0, 1.0, span)
    x = np.where(span == 0.0, lo, lo + (hi - lo) * (targets - F_lo) / safe_span)

    done = np.zeros(targets.shape, dtype=bool)
    for _ in range(max_iter):
        # Residuals via one Gauss-Legendre panel per target from its
        # bracket's left edge (panels are already converged to the table
        # tolerance). half == 0 when x == lo, giving F_x == F_lo exactly.
        half = 0.5 * (x - lo)
        mid = 0.5 * (x + lo)
        nodes = mid[:, None] + half[:, None] * _GL_NODES[None, :]
        F_x = F_lo + half * (f(nodes.reshape(-1)).reshape(nodes.shape) @ _GL_WEIGHTS)
        err = F_x - targets

        done |= np.abs(err) <= tol
        if done.all():
            break
        live = ~done

        over = live & (err > 0)
        under = live & (err <= 0)
        hi = np.where(over, x, hi)
        F_lo = np.where(under, F_x, F_lo)
        lo = np.where(under, x, lo)

        d = f(x)
        safe_d = np.where(d > 0, d, 1.0)
        newton = x - err / safe_d
        ok = (d > 0) & (newton > lo) & (newton < hi)
        step = np.where(ok, newton, 0.5 * (lo + hi))
        x = np.where(live, step, x)
    return x
