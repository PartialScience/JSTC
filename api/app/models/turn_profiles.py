"""
Turn distributions and turn profiles.

Two layers, split so that the winding's parameter domain can never disagree
with its curve (the domain is derived, not specified):

``TurnDistribution``
    What a user/API specifies: how the turns are laid out along the winding,
    INDEPENDENT of the curve's length. Hashable frozen value objects.
    ``profile_over(length)`` instantiates the concrete profile on the
    curve's actual arc-length domain [0, length] - only the winding specs
    call it, with the length of their own curve.

``TurnProfile``
    The solver-facing cumulative turn count as a function of the arc-length
    parameter t, with an EXACT closed-form ``inverse``. Profiles are frozen
    dataclasses (structural equality and hashing -> real solver cache hits)
    that are callable, so they remain drop-in wherever a
    ``Callable[[float], float]`` is expected.

Every profile satisfies (and the model validation enforces):
  * strictly increasing over its domain,
  * zero at the curve start: profile(0) == 0.
These are the preconditions of every turn-inversion in the solvers.
"""
from abc import ABC, abstractmethod
from bisect import bisect_right
from dataclasses import dataclass
from typing import Tuple


# ---------------------------------------------------------------------------
# Distributions (curve-domain-free specifications)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TurnDistribution(ABC):
    """How turns are distributed along a winding, independent of its length."""

    @property
    @abstractmethod
    def total_turns(self) -> float:
        """Total number of turns the distribution lays down."""
        ...

    @abstractmethod
    def profile_over(self, length: float) -> "TurnProfile":
        """The cumulative turn profile over the arc-length domain [0, length]."""
        ...

    @abstractmethod
    def canonical(self) -> tuple:
        """JSON-serializable exact description (type tag + defining
        parameters), used for geometry fingerprints."""
        ...


@dataclass(frozen=True)
class UniformTurns(TurnDistribution):
    """Evenly wound: constant turn density along the curve."""

    turns: float

    def __post_init__(self):
        if self.turns <= 0:
            raise ValueError(f"turns must be positive, got {self.turns}")

    @property
    def total_turns(self) -> float:
        return self.turns

    def profile_over(self, length: float) -> "UniformTurnProfile":
        return UniformTurnProfile(total_turns=self.turns, t_max=length)

    def canonical(self) -> tuple:
        return ("uniform", self.turns)


@dataclass(frozen=True)
class GradedTurns(TurnDistribution):
    """Cumulative turn count specified at control points along the winding.

    ``points`` are (u, n) pairs: u is the normalized position along the
    curve (0 = start, 1 = end) and n the cumulative number of turns at that
    position. The profile interpolates linearly between points (piecewise
    constant turn density within each band). Constraints, validated here:

      * the first point is exactly (0, 0),
      * the last point has u == 1 (its n is the total turn count),
      * u and n are both strictly increasing.
    """

    points: Tuple[Tuple[float, float], ...]

    def __post_init__(self):
        pts = tuple((float(u), float(n)) for u, n in self.points)
        object.__setattr__(self, "points", pts)
        if len(pts) < 2:
            raise ValueError("GradedTurns needs at least 2 control points")
        if pts[0] != (0.0, 0.0):
            raise ValueError(f"The first control point must be (0, 0), got {pts[0]}")
        if pts[-1][0] != 1.0:
            raise ValueError(
                f"The last control point must sit at u = 1, got u = {pts[-1][0]}"
            )
        for (u0, n0), (u1, n1) in zip(pts[:-1], pts[1:]):
            if u1 <= u0:
                raise ValueError(
                    f"Control point positions must be strictly increasing: {u0} -> {u1}"
                )
            if n1 <= n0:
                raise ValueError(
                    "Cumulative turns must be strictly increasing (every "
                    f"winding is monotone): {n0} -> {n1}"
                )

    @property
    def total_turns(self) -> float:
        return self.points[-1][1]

    def profile_over(self, length: float) -> "PiecewiseLinearTurnProfile":
        return PiecewiseLinearTurnProfile(
            s_points=tuple(u * length for u, _ in self.points),
            n_points=tuple(n for _, n in self.points),
        )

    def canonical(self) -> tuple:
        return ("graded", self.points)


# ---------------------------------------------------------------------------
# Profiles (solver-facing, arc-length domain)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TurnProfile(ABC):
    """Cumulative turn count as a function of the arc-length parameter t."""

    @abstractmethod
    def __call__(self, t: float) -> float:
        """Cumulative turns from the curve start up to parameter t."""
        ...

    @abstractmethod
    def inverse(self, n: float) -> float:
        """The parameter t at which the cumulative count reaches n - the
        exact inverse of __call__ (defined for n in [0, total])."""
        ...


@dataclass(frozen=True)
class UniformTurnProfile(TurnProfile):
    """Evenly wound over [0, t_max]: turns accumulate linearly in arc length."""

    total_turns: float
    t_max: float

    def __post_init__(self):
        if self.total_turns <= 0:
            raise ValueError(f"total_turns must be positive, got {self.total_turns}")
        if self.t_max <= 0:
            raise ValueError(f"t_max must be positive, got {self.t_max}")

    def __call__(self, t: float) -> float:
        # Grouped so t == t_max gives exactly total_turns: (N * t) / t_max
        # can land a few ulp above N, and turn counting ceils this value.
        return self.total_turns * (t / self.t_max)

    def inverse(self, n: float) -> float:
        return self.t_max * n / self.total_turns


@dataclass(frozen=True)
class PiecewiseLinearTurnProfile(TurnProfile):
    """Cumulative turns interpolated linearly between (s, n) breakpoints.

    Exact per-span evaluation and inversion (both are linear solves). The
    breakpoints come from a GradedTurns distribution scaled to the curve's
    arc length, so s_points spans [0, L] and n_points [0, N], both strictly
    increasing (validated by GradedTurns).
    """

    s_points: Tuple[float, ...]
    n_points: Tuple[float, ...]

    def __call__(self, t: float) -> float:
        s, n = self.s_points, self.n_points
        if t <= s[0]:
            return n[0]
        if t >= s[-1]:
            return n[-1]
        i = bisect_right(s, t) - 1
        frac = (t - s[i]) / (s[i + 1] - s[i])
        return n[i] + frac * (n[i + 1] - n[i])

    def inverse(self, target: float) -> float:
        s, n = self.s_points, self.n_points
        if target <= n[0]:
            return s[0]
        if target >= n[-1]:
            return s[-1]
        i = bisect_right(n, target) - 1
        frac = (target - n[i]) / (n[i + 1] - n[i])
        return s[i] + frac * (s[i + 1] - s[i])


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

    def inverse(self, n: float) -> float:
        return self.base.inverse(n + self.base(self.t_shift))
