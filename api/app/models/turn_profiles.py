"""
Turn profiles: serializable, hashable value objects for the cumulative
turn function of a winding.

A winding's ``turn_fxn`` gives the cumulative number of turns from the
start of its curve up to parameter ``t``. Historically this was a raw
lambda, which (a) cannot cross an API boundary and (b) hashes by identity,
defeating the solvers' ``lru_cache`` even for two identical coils. These
value objects fix both: they are frozen dataclasses (structural equality
and hashing -> real cache hits) that are also callable, so they remain
drop-in wherever a ``Callable[[float], float]`` is expected.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TurnProfile(ABC):
    """Cumulative turn count as a function of curve parameter t."""

    @abstractmethod
    def __call__(self, t: float) -> float:
        """Cumulative turns from the curve start up to parameter t."""
        ...


@dataclass(frozen=True)
class UniformTurnProfile(TurnProfile):
    """Evenly wound: turns accumulate linearly in the curve parameter.

    Over a curve parameterized on ``[t_min, t_max]`` (the default
    ``[0, 1]`` matches LineSegment-based windings), the cumulative count
    ramps linearly from 0 to ``total_turns``.
    """

    total_turns: float
    t_min: float = 0.0
    t_max: float = 1.0

    def __post_init__(self):
        if self.total_turns <= 0:
            raise ValueError(f"total_turns must be positive, got {self.total_turns}")
        if self.t_max <= self.t_min:
            raise ValueError("t_max must exceed t_min")

    def __call__(self, t: float) -> float:
        return self.total_turns * (t - self.t_min) / (self.t_max - self.t_min)


@dataclass(frozen=True)
class ShiftedTurnProfile(TurnProfile):
    """A base profile re-zeroed at ``t_shift``: ``base(t) - base(t_shift)``.

    Used to give a sub-segment of a winding a turn count relative to its
    own start while keeping the whole thing hashable (a segment carved
    from a coil stays cache-friendly).
    """

    base: TurnProfile
    t_shift: float

    def __call__(self, t: float) -> float:
        return self.base(t) - self.base(self.t_shift)
