"""
Offset (parallel) curve of a unit-speed parent curve.
"""
from dataclasses import dataclass

from app.formulas.numerics import adaptive_cumulative_integral
from app.geometry.curves.base import ParametricCurve, UnitSpeedCurve


@dataclass(frozen=True)
class OffsetCurve(ParametricCurve):
    """
    The parallel curve at a signed offset distance from a unit-speed parent:

        offset_point(t) = parent(t) + offset * n_hat(t)

    where n_hat is the parent's unit LEFT normal (the unit tangent rotated
    +90 degrees CCW). A positive offset therefore lies to the left of the
    direction of travel, a negative offset to the right.

    THE DELIBERATE EXCEPTION to the unit-speed contract: this curve shares
    its parent's parameter domain, so a parameter value t refers to
    corresponding points on both curves. That correspondence is load-bearing
    (winding slice parameters land on both sides of the conductor boundary,
    and projections delegate to the parent), and it is mathematically
    incompatible with unit speed - the offset's speed is |1 - offset * k(t)|
    with k the parent's curvature. OffsetCurve is therefore a plain
    ParametricCurve and can never be used as a winding centerline.

    Validity requires |offset| below the parent's minimum radius of
    curvature (1 - offset*k > 0 everywhere); OffsetRegion validates this
    against the parent's max_abs_curvature at construction.

    With the unit-speed parent every quantity is exact:
        derivative  = (1 - offset*k) * T_hat   (Frenet, left-normal frame)
        curvature   = k / (1 - offset*k)
        arc length  = integral of (1 - offset*k) ds
    """

    parent: UnitSpeedCurve
    offset: float

    def __post_init__(self):
        if self.offset == 0:
            raise ValueError("Offset must be non-zero; use the parent curve instead")
        if not isinstance(self.parent, UnitSpeedCurve):
            raise TypeError(
                "OffsetCurve requires a unit-speed parent; got "
                f"{type(self.parent).__name__}"
            )

    @property
    def t_min(self) -> float:
        return self.parent.t_min

    @property
    def t_max(self) -> float:
        return self.parent.t_max

    def _unit_left_normal(self, t: float) -> tuple[float, float]:
        """The parent's unit tangent rotated +90 degrees CCW - exact, since
        a unit-speed parent's derivative is already the unit tangent."""
        dx, dy = self.parent.derivative_at(t)
        return (-dy, dx)

    def point_at(self, t: float) -> tuple[float, float]:
        px, py = self.parent.point_at(t)
        nx, ny = self._unit_left_normal(t)
        return (px + self.offset * nx, py + self.offset * ny)

    def derivative_at(self, t: float) -> tuple[float, float]:
        """Exact tangent via the Frenet frame: (1 - offset*k(t)) * T_hat."""
        tx, ty = self.parent.derivative_at(t)
        scale = 1.0 - self.offset * self.parent.curvature_at(t)
        return (scale * tx, scale * ty)

    def curvature_at(self, t: float) -> float:
        k = self.parent.curvature_at(t)
        return k / (1.0 - self.offset * k)

    def arc_length_between(self, t1: float, t2: float) -> float:
        """Exact integral of the offset speed (1 - offset*k) ds.

        For a constant-curvature parent (line, arc) this reduces to the
        closed form immediately; for a spline parent the parent's exact
        curvature is integrated with the owned adaptive Gauss-Legendre
        machinery (no elementary closed form exists).
        """
        k1 = self.parent.curvature_at(t1)
        k2 = self.parent.curvature_at(0.5 * (t1 + t2))
        if k1 == k2 == self.parent.curvature_at(t2):
            return (t2 - t1) * (1.0 - self.offset * k1)

        import numpy as np

        def speed(ts: "np.ndarray") -> "np.ndarray":
            return np.array(
                [abs(1.0 - self.offset * self.parent.curvature_at(float(t))) for t in np.atleast_1d(ts)]
            )

        _, cum = adaptive_cumulative_integral(speed, t1, t2, rel_tol=1e-10)
        return float(cum[-1])

    def closest_parameter_in_range(
        self, point: tuple[float, float], t1: float, t2: float
    ) -> float:
        """Delegate to the parent: within the offset's tube of validity
        (enforced at OffsetRegion construction) the normal projection onto
        the parent and onto the offset curve identify the same parameter."""
        return self.parent.closest_parameter_in_range(point, t1, t2)

    def sample_params(
        self,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        """Delegate to the parent's exact offset sampling - the parent knows
        its parallel curves (a line's offset is a line, an arc's an arc, a
        spline's follows from its curvature)."""
        return self.parent.sample_params_for_offset(
            self.offset, max_chord_error, include
        )

    def canonical(self) -> tuple:
        return ("offset", self.parent.canonical(), self.offset)
