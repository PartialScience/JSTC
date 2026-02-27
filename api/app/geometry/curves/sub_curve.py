"""
A wrapper that restricts an existing ParametricCurve to a sub-range [t1, t2].
"""

from app.geometry.curves.base import ParametricCurve
from typing import List, Tuple


class SubCurve(ParametricCurve):
    """
    A parametric curve that represents a portion of another curve,
    restricted to the parameter range [t1, t2].

    The parameter domain of the SubCurve is [t1, t2] (i.e. the same
    parameterization as the parent curve, just clamped to the sub-range).
    """

    def __init__(self, parent_curve: ParametricCurve, t1: float, t2: float) -> None:
        if t1 >= t2:
            raise ValueError(f"t1 ({t1}) must be less than t2 ({t2})")
        if t1 < parent_curve.t_min or t2 > parent_curve.t_max:
            raise ValueError(
                f"Sub-range [{t1}, {t2}] must be within the parent curve's "
                f"range [{parent_curve.t_min}, {parent_curve.t_max}]"
            )
        self._parent_curve = parent_curve
        self._t1 = t1
        self._t2 = t2

    @property
    def parent_curve(self) -> ParametricCurve:
        """The original curve this sub-curve is derived from."""
        return self._parent_curve

    @property
    def t_min(self) -> float:
        return self._t1

    @property
    def t_max(self) -> float:
        return self._t2

    def point_at(self, t: float) -> tuple[float, ...]:
        return self._parent_curve.point_at(t)

    def distance_to_curve_for_range(self, point: tuple[float, ...], t1: float, t2: float) -> float:
        """Delegate to the parent curve's range-based distance computation."""
        return self._parent_curve.distance_to_curve_for_range(point, t1, t2)

    def bounding_box_for_range(self, t1: float, t2: float) -> List[Tuple[float, float]]:
        """Delegate to the parent curve's range-based bounding box computation."""
        return self._parent_curve.bounding_box_for_range(t1, t2)
