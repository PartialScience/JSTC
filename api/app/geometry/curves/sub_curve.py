"""
A wrapper that restricts an existing UnitSpeedCurve to a sub-range [t1, t2].
"""
from dataclasses import dataclass

import numpy as np

from app.geometry.curves.base import UnitSpeedCurve


@dataclass(frozen=True)
class SubCurve(UnitSpeedCurve):
    """
    A portion of a unit-speed curve restricted to the parameter range
    [t1, t2], in the SAME parameterization as the parent. Because the
    parent's parameter is arc length, a sub-range of it is automatically
    unit speed as well, so the contract is inherited for free.
    """

    parent_curve: UnitSpeedCurve
    t1: float
    t2: float

    def __post_init__(self):
        if not isinstance(self.parent_curve, UnitSpeedCurve):
            raise TypeError(
                "SubCurve requires a unit-speed parent; got "
                f"{type(self.parent_curve).__name__}"
            )
        if self.t1 >= self.t2:
            raise ValueError(f"t1 ({self.t1}) must be less than t2 ({self.t2})")
        if self.t1 < self.parent_curve.t_min or self.t2 > self.parent_curve.t_max:
            raise ValueError(
                f"Sub-range [{self.t1}, {self.t2}] must be within the parent "
                f"curve's range [{self.parent_curve.t_min}, {self.parent_curve.t_max}]"
            )

    @property
    def t_min(self) -> float:
        return self.t1

    @property
    def t_max(self) -> float:
        return self.t2

    def point_at(self, t: float) -> tuple[float, float]:
        return self.parent_curve.point_at(t)

    def points_at(self, ts) -> np.ndarray:
        """Batched ``point_at``: same parameterization as the parent, so
        this forwards wholesale and keeps the parent's vectorized path."""
        return self.parent_curve.points_at(np.clip(np.asarray(ts, dtype=float), self.t1, self.t2))

    def derivative_at(self, t: float) -> tuple[float, float]:
        return self.parent_curve.derivative_at(t)

    def curvature_at(self, t: float) -> float:
        return self.parent_curve.curvature_at(t)

    def max_abs_curvature(self) -> float:
        """The parent's bound is valid (if conservative) for any sub-range."""
        return self.parent_curve.max_abs_curvature()

    def closest_parameter_in_range(
        self, point: tuple[float, float], t1: float, t2: float
    ) -> float:
        lo = max(t1, self.t1)
        hi = min(t2, self.t2)
        return self.parent_curve.closest_parameter_in_range(point, lo, hi)

    def _restrict(self, params: tuple[float, ...]) -> tuple[float, ...]:
        """Slice a parent sampling (which includes t1 and t2 exactly) down
        to this sub-range."""
        return tuple(t for t in params if self.t1 <= t <= self.t2)

    def sample_params(
        self,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        """Sample the parent with the sub-range endpoints forced, then keep
        the slice between them: every kept interval is a full interval of
        the parent's sampling, so the chord tolerance carries over exactly."""
        parent_params = self.parent_curve.sample_params(
            max_chord_error, include=(self.t1, self.t2, *include)
        )
        return self._restrict(parent_params)

    def sample_params_for_offset(
        self,
        offset: float,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        parent_params = self.parent_curve.sample_params_for_offset(
            offset, max_chord_error, include=(self.t1, self.t2, *include)
        )
        return self._restrict(parent_params)

    def canonical(self) -> tuple:
        return ("sub", self.parent_curve.canonical(), self.t1, self.t2)
