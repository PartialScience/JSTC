"""
Centripetal Catmull-Rom spline, reparameterized to unit speed.

The user-facing definition is the standard interpolating centripetal
Catmull-Rom curve through the given control points (knot exponent 1/2,
which provably produces no cusps or self-intersections within a segment -
Yuksel, Schaefer & Keyser 2011). Endpoint segments use reflected phantom
points (P_{-1} = 2 P_0 - P_1 and symmetrically at the far end), giving
natural, tangent-defined ends without extra user input. Collinear control
points reproduce an exactly straight centerline.

Internally each span is the exact cubic polynomial the Barry-Goldman
pyramid defines (recovered by evaluating at four nodes and solving the
4x4 Vandermonde system - exact for a cubic, no algebra to get wrong).
Everything polynomial is then closed-form: derivatives, curvature, and
closest-point projection (the distance-squared derivative is a quintic
whose roots come from the companion matrix).

The one quantity with no elementary closed form is arc length, so this
class owns its deliberate numerics (see app.formulas.numerics): a
Gauss-Legendre cumulative arc-length table per span, built once at
construction to a 1e-12 relative tolerance and cached on the instance, with
safeguarded-Newton inversion for the unit-speed parameter map. The shared
unit-speed contract tests verify the result like any other curve.
"""
import math
from dataclasses import dataclass, field
from typing import Tuple

import numpy as np

from app.formulas.numerics import (
    adaptive_cumulative_integral,
    gauss_legendre_integral,
    invert_cumulative,
)
from app.geometry.curves.base import UnitSpeedCurve

#: Local parameter error tolerance of the unit-speed inversion, relative to
#: the curve length.
_INVERT_REL_TOL = 1e-11


@dataclass(frozen=True)
class CatmullRomSpline(UnitSpeedCurve):
    """Interpolating centripetal Catmull-Rom spline through ``points``,
    parameterized by arc length: t in [0, total length].

    ``start_tangent`` (optional, a unit direction) clamps the curve's
    initial tangent - the continuation form used inside piecewise paths.
    The first span becomes the cubic Hermite with start derivative
    ``start_tangent * |P1 - P0|`` (the first chord's length - the
    deterministic magnitude convention, pinned by the golden fixture) and
    an end derivative matching the next span's start direction (C1 in the
    knot parameterization), or the natural end condition p''(1) = 0 when
    the clamped span is the only one. All other spans are unchanged
    centripetal Catmull-Rom.
    """

    points: Tuple[Tuple[float, float], ...]
    start_tangent: Tuple[float, float] | None = None

    # Derived, cached at construction - excluded from equality/hashing.
    _coeffs: np.ndarray = field(init=False, repr=False, compare=False, default=None)
    _tables: tuple = field(init=False, repr=False, compare=False, default=None)
    _seg_s0: np.ndarray = field(init=False, repr=False, compare=False, default=None)
    _length: float = field(init=False, repr=False, compare=False, default=0.0)

    def __post_init__(self):
        pts = tuple((float(p[0]), float(p[1])) for p in self.points)
        if len(pts) < 2:
            raise ValueError("CatmullRomSpline needs at least 2 points")
        for a, b in zip(pts[:-1], pts[1:]):
            if a == b:
                raise ValueError("Consecutive spline points must be distinct")
        object.__setattr__(self, "points", pts)
        if self.start_tangent is not None:
            tx, tz = float(self.start_tangent[0]), float(self.start_tangent[1])
            mag = math.hypot(tx, tz)
            if not math.isfinite(mag) or abs(mag - 1.0) > 1e-9:
                raise ValueError(
                    f"start_tangent must be a unit vector, got magnitude {mag}"
                )
            object.__setattr__(self, "start_tangent", (tx, tz))

        coeffs = _segment_coefficients(np.array(pts), self.start_tangent)
        object.__setattr__(self, "_coeffs", coeffs)

        # Per-segment cumulative arc-length tables (u-breakpoints, s values).
        tables = []
        seg_lengths = []
        for k in range(coeffs.shape[0]):
            speed = _speed_fn(coeffs[k])
            u_breaks, s_cum = adaptive_cumulative_integral(speed, 0.0, 1.0)
            tables.append((u_breaks, s_cum))
            seg_lengths.append(float(s_cum[-1]))
        seg_s0 = np.concatenate([[0.0], np.cumsum(seg_lengths)])
        object.__setattr__(self, "_tables", tuple(tables))
        object.__setattr__(self, "_seg_s0", seg_s0)
        object.__setattr__(self, "_length", float(seg_s0[-1]))

    # ------------------------------------------------------------------
    # Parameter bookkeeping
    # ------------------------------------------------------------------

    @property
    def t_min(self) -> float:
        return 0.0

    @property
    def t_max(self) -> float:
        return self._length

    def _locate(self, s: float) -> tuple[int, float]:
        """Map global arc length s -> (segment index, local parameter u)."""
        s = min(max(s, 0.0), self._length)
        k = int(np.searchsorted(self._seg_s0, s, side="right") - 1)
        k = max(0, min(k, len(self._tables) - 1))
        u_breaks, s_cum = self._tables[k]
        u = invert_cumulative(
            u_breaks,
            s_cum,
            s - self._seg_s0[k],
            _speed_fn(self._coeffs[k]),
            tol=_INVERT_REL_TOL * max(self._length, 1e-300),
        )
        return k, u

    def _s_of_u(self, k: int, u: float) -> float:
        """Global arc length at local parameter u of segment k."""
        u_breaks, s_cum = self._tables[k]
        i = int(np.searchsorted(u_breaks, u, side="right") - 1)
        i = max(0, min(i, len(u_breaks) - 2))
        speed = _speed_fn(self._coeffs[k])
        partial = gauss_legendre_integral(speed, float(u_breaks[i]), u) if u > u_breaks[i] else 0.0
        return float(self._seg_s0[k] + s_cum[i] + partial)

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    def point_at(self, t: float) -> tuple[float, float]:
        k, u = self._locate(t)
        x, y = _poly_eval(self._coeffs[k], u)
        return (float(x), float(y))

    def derivative_at(self, t: float) -> tuple[float, float]:
        """Unit tangent (the polynomial velocity, normalized)."""
        k, u = self._locate(t)
        dx, dy = _poly_eval_derivative(self._coeffs[k], u)
        mag = float(np.hypot(dx, dy))
        return (float(dx) / mag, float(dy) / mag)

    def curvature_at(self, t: float) -> float:
        k, u = self._locate(t)
        return _curvature_of(self._coeffs[k], u)

    def max_abs_curvature(self) -> float:
        """Upper bound on |curvature|, for offset validation.

        Curvature of a cubic span is a smooth rational function; its maximum
        is estimated by dense Chebyshev-node probing per span with a safety
        margin. This is a validation bound, not solver math - documented
        accordingly.
        """
        u_probe = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, 65)))
        worst = 0.0
        for k in range(self._coeffs.shape[0]):
            kap = np.abs([_curvature_of(self._coeffs[k], float(u)) for u in u_probe])
            worst = max(worst, float(kap.max()))
        return 1.1 * worst

    def closest_parameter_in_range(
        self, point: tuple[float, float], t1: float, t2: float
    ) -> float:
        """Global closest point via per-span polynomial root finding.

        On each span the squared distance to *point* is a degree-6
        polynomial in u, so its interior critical points are the real roots
        of a quintic (companion-matrix roots - exact to machine precision).
        The global minimum over [t1, t2] is the best of all spans' critical
        points plus the range endpoints.
        """
        t1 = max(t1, self.t_min)
        t2 = min(t2, self.t_max)
        k1, u1 = self._locate(t1)
        k2, u2 = self._locate(t2)

        best_t, best_d2 = t1, _dist_sq(self.point_at(t1), point)
        for cand_t in (t2,):
            d2 = _dist_sq(self.point_at(cand_t), point)
            if d2 < best_d2:
                best_t, best_d2 = cand_t, d2

        for k in range(k1, k2 + 1):
            u_lo = u1 if k == k1 else 0.0
            u_hi = u2 if k == k2 else 1.0
            if u_hi <= u_lo:
                continue
            cx, cy = self._coeffs[k][0], self._coeffs[k][1]
            # d/du |p(u) - q|^2 = 2 (p-q) . p' : quintic coefficients
            px = np.polynomial.polynomial.Polynomial(cx - np.array([point[0], 0, 0, 0]))
            py = np.polynomial.polynomial.Polynomial(cy - np.array([point[1], 0, 0, 0]))
            dpx, dpy = px.deriv(), py.deriv()
            quintic = px * dpx + py * dpy
            for root in quintic.roots():
                if abs(root.imag) > 1e-9:
                    continue
                u = float(root.real)
                if u_lo <= u <= u_hi:
                    x, y = _poly_eval(self._coeffs[k], u)
                    d2 = (x - point[0]) ** 2 + (y - point[1]) ** 2
                    if d2 < best_d2:
                        best_t, best_d2 = self._s_of_u(k, u), d2
        return best_t

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def sample_params(
        self,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        return self._sample(max_chord_error, include, offset=0.0)

    def sample_params_for_offset(
        self,
        offset: float,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        return self._sample(max_chord_error, include, offset=offset)

    def _sample(
        self, max_chord_error: float, include: tuple[float, ...], offset: float
    ) -> tuple[float, ...]:
        """Curvature-driven adaptive subdivision (in arc length s).

        A curve interval of length L and curvature bound kappa deviates from
        its chord by at most L^2 * kappa / 8 (circle-sagitta bound). For the
        parallel curve at signed offset a the interval length scales by
        (1 - a*kappa) and the curvature becomes kappa / (1 - a*kappa); both
        follow exactly from this curve's curvature. Intervals are split
        until the bound (with probe-based kappa estimation and a safety
        margin) meets the tolerance.
        """
        if max_chord_error <= 0:
            raise ValueError("max_chord_error must be positive")

        def interval_bound(s_a: float, s_b: float) -> float:
            ds = s_b - s_a
            probes = (s_a, 0.5 * (s_a + s_b), s_b)
            kap = 1.5 * max(abs(self.curvature_at(s)) for s in probes)
            if offset != 0.0:
                scale = max(abs(1.0 - offset * self.curvature_at(s)) for s in probes)
                ds = ds * scale
                kap = kap / max(1e-12, (1.0 - abs(offset) * kap / 1.5))
            return ds * ds * kap / 8.0

        # Seed with segment boundaries (curvature is only piecewise smooth)
        seeds = [float(s) for s in self._seg_s0]
        out: list[float] = [seeds[0]]
        min_step = self._length * 1e-9
        stack = list(zip(seeds[:-1], seeds[1:]))
        while stack:
            s_a, s_b = stack.pop(0)
            if s_b - s_a > min_step and interval_bound(s_a, s_b) > max_chord_error:
                mid = 0.5 * (s_a + s_b)
                stack.insert(0, (mid, s_b))
                stack.insert(0, (s_a, mid))
            else:
                out.append(s_b)

        interior = sorted(t for t in set(include) if self.t_min < t < self.t_max)
        if interior:
            merged = sorted(set(out) | set(interior))
            # Drop sampled points that crowd a forced include value
            final = [merged[0]]
            for v in merged[1:-1]:
                if v in interior or all(
                    abs(v - t) > min_step for t in interior
                ):
                    final.append(v)
            final.append(merged[-1])
            out = final
        return tuple(out)

    def canonical(self) -> tuple:
        if self.start_tangent is not None:
            return ("catmull-rom-clamped", self.points, self.start_tangent)
        return ("catmull-rom", self.points)


# ---------------------------------------------------------------------------
# Polynomial machinery (module-private)
# ---------------------------------------------------------------------------


def _segment_coefficients(
    pts: np.ndarray, start_tangent: tuple[float, float] | None = None
) -> np.ndarray:
    """Exact cubic coefficients of every centripetal Catmull-Rom span.

    Returns an (n_segments, 2, 4) array: coeffs[k, 0] are the x-polynomial
    coefficients (constant first) in the local parameter u in [0, 1] of
    span k, coeffs[k, 1] the y coefficients. With ``start_tangent`` set,
    span 0 is replaced by the clamped Hermite span (see CatmullRomSpline).
    """
    n = pts.shape[0]
    # Reflected phantom endpoints
    ext = np.vstack([2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2]])

    # Node evaluation points: exact cubic recovery via 4-point fit
    u_fit = np.array([0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0])
    V = np.vander(u_fit, 4, increasing=True)  # rows: [1, u, u^2, u^3]
    V_inv = np.linalg.inv(V)

    coeffs = np.empty((n - 1, 2, 4))
    for k in range(n - 1):
        quad = ext[k : k + 4]  # P_{k-1}, P_k, P_{k+1}, P_{k+2} (phantom-extended)
        # Centripetal knots (alpha = 1/2)
        d = np.sqrt(np.linalg.norm(np.diff(quad, axis=0), axis=1))
        tau = np.concatenate([[0.0], np.cumsum(d)])
        samples = np.array([
            _barry_goldman(quad, tau, tau[1] + u * (tau[2] - tau[1]))
            for u in u_fit
        ])  # (4, 2)
        coeffs[k, 0] = V_inv @ samples[:, 0]
        coeffs[k, 1] = V_inv @ samples[:, 1]

    if start_tangent is not None:
        coeffs[0] = _clamped_first_span(pts, coeffs, start_tangent)
    return coeffs


def _clamped_first_span(
    pts: np.ndarray, coeffs: np.ndarray, start_tangent: tuple[float, float]
) -> np.ndarray:
    """Hermite replacement for span 0 with a clamped start tangent.

    Start derivative: the unit tangent scaled by the first chord length.
    End derivative: the second span's start derivative rescaled to span 0's
    knot interval (C1 continuity in the knot parameterization) - or, for a
    single-span spline, the natural end condition p''(1) = 0.
    """
    p0, p1 = pts[0], pts[1]
    c = p1 - p0
    chord = float(np.hypot(c[0], c[1]))
    m0 = np.array([start_tangent[0] * chord, start_tangent[1] * chord])

    if pts.shape[0] > 2:
        # Next span's derivative at its local u = 0 is its linear coefficient
        m_next = np.array([coeffs[1, 0, 1], coeffs[1, 1, 1]])
        # Centripetal knot intervals of the two spans
        dt0 = math.sqrt(chord)
        dt1 = math.sqrt(float(np.hypot(pts[2][0] - p1[0], pts[2][1] - p1[1])))
        m1 = m_next * (dt0 / dt1)
    else:
        m1 = (3.0 * c - m0) / 2.0  # natural end: p''(1) = 0

    out = np.empty((2, 4))
    for axis in range(2):
        out[axis, 0] = p0[axis]
        out[axis, 1] = m0[axis]
        out[axis, 2] = 3.0 * c[axis] - 2.0 * m0[axis] - m1[axis]
        out[axis, 3] = -2.0 * c[axis] + m0[axis] + m1[axis]
    return out


def _barry_goldman(P: np.ndarray, tau: np.ndarray, t: float) -> np.ndarray:
    """Barry-Goldman pyramid evaluation of the Catmull-Rom span defined by
    the four points P with knots tau, at knot parameter t in [tau1, tau2]."""
    def lerp(a, b, ta, tb):
        if tb == ta:
            return a
        w = (t - ta) / (tb - ta)
        return (1 - w) * a + w * b

    A1 = lerp(P[0], P[1], tau[0], tau[1])
    A2 = lerp(P[1], P[2], tau[1], tau[2])
    A3 = lerp(P[2], P[3], tau[2], tau[3])
    B1 = lerp(A1, A2, tau[0], tau[2])
    B2 = lerp(A2, A3, tau[1], tau[3])
    return lerp(B1, B2, tau[1], tau[2])


def _poly_eval(c: np.ndarray, u: float) -> tuple[float, float]:
    x = c[0][0] + u * (c[0][1] + u * (c[0][2] + u * c[0][3]))
    y = c[1][0] + u * (c[1][1] + u * (c[1][2] + u * c[1][3]))
    return (x, y)


def _poly_eval_derivative(c: np.ndarray, u: float) -> tuple[float, float]:
    dx = c[0][1] + u * (2 * c[0][2] + 3 * u * c[0][3])
    dy = c[1][1] + u * (2 * c[1][2] + 3 * u * c[1][3])
    return (dx, dy)


def _poly_eval_second(c: np.ndarray, u: float) -> tuple[float, float]:
    return (2 * c[0][2] + 6 * u * c[0][3], 2 * c[1][2] + 6 * u * c[1][3])


def _curvature_of(c: np.ndarray, u: float) -> float:
    """Signed curvature (left-normal convention) - parameterization
    invariant, so evaluating in the polynomial parameter is exact."""
    dx, dy = _poly_eval_derivative(c, u)
    ddx, ddy = _poly_eval_second(c, u)
    speed_sq = dx * dx + dy * dy
    return float((dx * ddy - dy * ddx) / speed_sq ** 1.5)


def _speed_fn(c: np.ndarray):
    """Vectorized |p'(u)| for a span's coefficients."""
    def speed(u: np.ndarray) -> np.ndarray:
        u = np.asarray(u, dtype=float)
        dx = c[0][1] + u * (2 * c[0][2] + 3 * u * c[0][3])
        dy = c[1][1] + u * (2 * c[1][2] + 3 * u * c[1][3])
        return np.hypot(dx, dy)
    return speed


def _dist_sq(p: tuple[float, float], q: tuple[float, float]) -> float:
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
