"""
Straight line segment, parameterized by arc length.
"""
from dataclasses import dataclass, field

from app.geometry.curves.base import UnitSpeedCurve


@dataclass(frozen=True)
class LineSegment(UnitSpeedCurve):
    """A straight segment from ``start`` to ``end``, parameterized by arc
    length: t runs over [0, |end - start|] and point_at(t) advances t
    geometry units along the segment. Every quantity is closed-form.
    """

    start: tuple[float, float]
    end: tuple[float, float]

    #: Derived (cached) quantities - excluded from equality/hashing.
    _length: float = field(init=False, repr=False, compare=False, default=0.0)
    _unit: tuple[float, float] = field(init=False, repr=False, compare=False, default=(0.0, 0.0))

    def __post_init__(self):
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0.0:
            raise ValueError("LineSegment start and end must differ")
        object.__setattr__(self, "_length", length)
        object.__setattr__(self, "_unit", (dx / length, dy / length))

    @property
    def t_min(self) -> float:
        return 0.0

    @property
    def t_max(self) -> float:
        return self._length

    def point_at(self, t: float) -> tuple[float, float]:
        return (
            self.start[0] + t * self._unit[0],
            self.start[1] + t * self._unit[1],
        )

    def derivative_at(self, t: float) -> tuple[float, float]:
        """Unit tangent - constant along the segment."""
        return self._unit

    def curvature_at(self, t: float) -> float:
        return 0.0

    def max_abs_curvature(self) -> float:
        return 0.0

    def closest_parameter_in_range(
        self, point: tuple[float, float], t1: float, t2: float
    ) -> float:
        """Exact closed form: the arc-length projection of the point onto
        the segment's direction, clamped to [t1, t2]."""
        t_hat = (
            (point[0] - self.start[0]) * self._unit[0]
            + (point[1] - self.start[1]) * self._unit[1]
        )
        return min(max(t_hat, t1), t2)

    def sample_params(
        self,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        """A chord of a line has zero deviation: the endpoints plus any
        interior include values are exact for every tolerance."""
        interior = sorted(t for t in set(include) if self.t_min < t < self.t_max)
        return (self.t_min, *interior, self.t_max)

    def sample_params_for_offset(
        self,
        offset: float,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        """The offset of a line is a parallel line - sampling is identical."""
        return self.sample_params(max_chord_error, include)

    def canonical(self) -> tuple:
        return ("line", tuple(self.start), tuple(self.end))
