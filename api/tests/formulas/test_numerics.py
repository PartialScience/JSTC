"""invert_cumulative_many is BY CONTRACT the batched invert_cumulative:
same bracketing table, same safeguarded Newton, same tolerance. The suite
pins that equivalence on a representative spline-speed-like integrand."""
import numpy as np

from app.formulas.numerics import (
    adaptive_cumulative_integral,
    invert_cumulative,
    invert_cumulative_many,
)


def _speed(u):
    """A cubic-segment-like speed: smooth, positive, non-constant."""
    u = np.asarray(u, dtype=float)
    return np.hypot(1.0 + 0.8 * u - 1.2 * u**2, 0.4 - 1.5 * u + 2.1 * u**2)


def _table():
    return adaptive_cumulative_integral(_speed, 0.0, 1.0)


class TestInvertCumulativeMany:
    def test_matches_scalar_solver(self):
        """Every batched solution agrees with the scalar solver's."""
        x_breaks, F_cum = _table()
        total = float(F_cum[-1])
        tol = 1e-12 * total
        targets = np.linspace(0.0, total, 101)
        batched = invert_cumulative_many(x_breaks, F_cum, targets, _speed, tol=tol)
        scalar = np.array([
            invert_cumulative(x_breaks, F_cum, float(s), _speed, tol=tol)
            for s in targets
        ])
        assert np.max(np.abs(batched - scalar)) <= 1e-10

    def test_unsorted_and_repeated_targets(self):
        """Order independence: results pair with their targets, not with
        any assumed monotone sweep."""
        x_breaks, F_cum = _table()
        total = float(F_cum[-1])
        tol = 1e-12 * total
        targets = np.array([0.7, 0.1, 0.7, 0.0, 1.0, 0.33]) * total
        batched = invert_cumulative_many(x_breaks, F_cum, targets, _speed, tol=tol)
        for s, x in zip(targets, batched):
            assert abs(x - invert_cumulative(x_breaks, F_cum, float(s), _speed, tol=tol)) <= 1e-10

    def test_endpoints_and_clipping(self):
        """Targets at/beyond the table range clamp to the domain ends."""
        x_breaks, F_cum = _table()
        total = float(F_cum[-1])
        tol = 1e-12 * total
        batched = invert_cumulative_many(
            x_breaks, F_cum, np.array([-1.0, 0.0, total, total + 1.0]), _speed, tol=tol
        )
        assert abs(batched[0] - 0.0) <= 1e-12
        assert abs(batched[1] - 0.0) <= 1e-12
        assert abs(batched[2] - 1.0) <= 1e-10
        assert abs(batched[3] - 1.0) <= 1e-10

    def test_residuals_within_tolerance(self):
        """The defining property: |F(x_i) - target_i| <= tol for every i."""
        from app.formulas.numerics import gauss_legendre_integral

        x_breaks, F_cum = _table()
        total = float(F_cum[-1])
        tol = 1e-12 * total
        targets = np.linspace(0.0, total, 57)
        xs = invert_cumulative_many(x_breaks, F_cum, targets, _speed, tol=tol)
        for s, x in zip(targets, xs):
            # Evaluate F(x) the way the solver defines it: table value at the
            # bracket's left edge plus one converged GL panel.
            i = int(np.clip(np.searchsorted(x_breaks, x, side="right") - 1, 0, len(x_breaks) - 2))
            F_x = float(F_cum[i])
            if x > x_breaks[i]:
                F_x += gauss_legendre_integral(_speed, float(x_breaks[i]), float(x))
            assert abs(F_x - s) <= 2 * tol
