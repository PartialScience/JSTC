"""
Piecewise tangent-continuous unit-speed curve.
"""
import math
from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Sequence, Tuple

import numpy as np

from app.geometry.curves.base import UnitSpeedCurve
from app.geometry.curves.continuations import CurveContinuation


@dataclass(frozen=True)
class C1PiecewiseCurve(UnitSpeedCurve):
    """A chain of unit-speed pieces joined with position AND tangent
    continuity.

    The name is exact, not aspirational: under the unit-speed contract both
    one-sided derivatives at a junction are unit tangents, so matching
    tangent DIRECTION (G1) is the same as matching the derivative - the
    composite is a continuously differentiable (C1) unit-speed curve.
    Curvature may still jump at junctions, exactly as the Catmull-Rom
    spline's does at its knots; everything downstream (offset regions,
    sampling, solvers) already tolerates that.

    C0/C1 are VALIDATED here at construction - the geometry layer owns its
    invariants even for hand-assembled pieces. The supported way to build a
    chain is ``from_continuations``, where the constraints hold by
    construction (each continuation inherits its junction state; see
    curves/continuations.py for the explicit contract).

    The name ``PiecewiseCurve`` is deliberately left unclaimed for any
    future composite WITHOUT the continuity guarantee (which could never be
    a winding centerline - kinked envelopes break OffsetRegion - but might
    serve other geometry some day).

    The parameter domain is [0, total length]; piece k covers the
    sub-interval starting at the sum of the preceding lengths.
    """

    pieces: Tuple[UnitSpeedCurve, ...]

    #: Cumulative arc length at each piece boundary (len = n_pieces + 1).
    _s0: Tuple[float, ...] = field(init=False, repr=False, compare=False, default=())

    #: Junction tolerances, relative to the total length: positions must
    #: coincide and tangent directions agree to within these.
    _POS_RTOL = 1e-9
    _ANGLE_TOL = 1e-9

    def __post_init__(self):
        if len(self.pieces) < 1:
            raise ValueError("C1PiecewiseCurve needs at least one piece")
        for p in self.pieces:
            if not isinstance(p, UnitSpeedCurve):
                raise TypeError(
                    f"Every piece must be unit-speed; got {type(p).__name__}"
                )
            if isinstance(p, C1PiecewiseCurve):
                raise TypeError(
                    "Nested piecewise curves are not supported; flatten the "
                    "pieces into one chain."
                )

        s0 = [0.0]
        for p in self.pieces:
            s0.append(s0[-1] + p.length)
        total = s0[-1]

        pos_tol = max(self._POS_RTOL * total, 1e-15)
        for k in range(len(self.pieces) - 1):
            a, b = self.pieces[k], self.pieces[k + 1]
            pa = a.point_at(a.t_max)
            pb = b.point_at(b.t_min)
            gap = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
            if gap > pos_tol:
                raise ValueError(
                    f"Pieces {k} and {k + 1} do not join: endpoints are "
                    f"{gap:.3g} apart (C0 violation)."
                )
            ta = a.derivative_at(a.t_max)
            tb = b.derivative_at(b.t_min)
            cross = ta[0] * tb[1] - ta[1] * tb[0]
            dot = ta[0] * tb[0] + ta[1] * tb[1]
            if abs(cross) > self._ANGLE_TOL or dot <= 0:
                raise ValueError(
                    f"Pieces {k} and {k + 1} join with a kink: tangents "
                    f"{ta} vs {tb} (C1 violation). Build chains through "
                    "continuations so tangency holds by construction."
                )

        object.__setattr__(self, "_s0", tuple(s0))

    @classmethod
    def from_continuations(
        cls,
        first: UnitSpeedCurve,
        continuations: Sequence[CurveContinuation],
    ) -> "C1PiecewiseCurve":
        """Assemble a chain by propagation: each continuation is built from
        the previous piece's end point and end tangent, so C0/C1 hold by
        construction."""
        pieces = [first]
        for cont in continuations:
            prev = pieces[-1]
            pieces.append(
                cont.build(prev.point_at(prev.t_max), prev.derivative_at(prev.t_max))
            )
        return cls(pieces=tuple(pieces))

    # ------------------------------------------------------------------
    # Parameter bookkeeping
    # ------------------------------------------------------------------

    @property
    def t_min(self) -> float:
        return 0.0

    @property
    def t_max(self) -> float:
        return self._s0[-1]

    def _locate(self, t: float) -> tuple[int, float]:
        """Map a global arc length to (piece index, the piece's local t)."""
        t = min(max(t, 0.0), self._s0[-1])
        k = bisect_right(self._s0, t) - 1
        k = max(0, min(k, len(self.pieces) - 1))
        piece = self.pieces[k]
        return k, piece.t_min + (t - self._s0[k])

    def _to_global(self, k: int, local_t: float) -> float:
        return self._s0[k] + (local_t - self.pieces[k].t_min)

    # ------------------------------------------------------------------
    # Geometry: delegate to the owning piece
    # ------------------------------------------------------------------

    def point_at(self, t: float) -> tuple[float, float]:
        k, lt = self._locate(t)
        return self.pieces[k].point_at(lt)

    def points_at(self, ts) -> np.ndarray:
        """Batched ``point_at``: group the parameters by owning piece and
        forward each group to that piece's own ``points_at``, so a spline
        piece keeps its vectorized inversion."""
        ts = np.clip(np.asarray(ts, dtype=float), 0.0, self._s0[-1])
        ks = np.clip(
            np.searchsorted(self._s0, ts, side="right") - 1,
            0,
            len(self.pieces) - 1,
        )
        out = np.empty((ts.size, 2), dtype=float)
        for k in np.unique(ks):
            mask = ks == k
            piece = self.pieces[k]
            out[mask] = piece.points_at(piece.t_min + (ts[mask] - self._s0[k]))
        return out

    def derivative_at(self, t: float) -> tuple[float, float]:
        k, lt = self._locate(t)
        return self.pieces[k].derivative_at(lt)

    def curvature_at(self, t: float) -> float:
        k, lt = self._locate(t)
        return self.pieces[k].curvature_at(lt)

    def max_abs_curvature(self) -> float:
        return max(p.max_abs_curvature() for p in self.pieces)

    def closest_parameter_in_range(
        self, point: tuple[float, float], t1: float, t2: float
    ) -> float:
        """Exact global minimum: the best of each overlapping piece's own
        exact projection over its clipped sub-range."""
        t1 = max(t1, self.t_min)
        t2 = min(t2, self.t_max)
        best_t = t1
        best_d2 = None
        for k, piece in enumerate(self.pieces):
            lo_g = max(t1, self._s0[k])
            hi_g = min(t2, self._s0[k + 1])
            if hi_g < lo_g:
                continue
            lo = piece.t_min + (lo_g - self._s0[k])
            hi = piece.t_min + (hi_g - self._s0[k])
            lt = piece.closest_parameter_in_range(point, lo, hi)
            p = piece.point_at(lt)
            d2 = (p[0] - point[0]) ** 2 + (p[1] - point[1]) ** 2
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best_t = self._to_global(k, lt)
        return best_t

    # ------------------------------------------------------------------
    # Sampling: concatenate the pieces' exact samplers
    # ------------------------------------------------------------------

    def _concat_samples(self, per_piece) -> tuple[float, ...]:
        out: list[float] = [0.0]
        for k, params in enumerate(per_piece):
            for lt in params[1:]:  # drop each piece's head (== previous tail)
                out.append(self._to_global(k, lt))
        return tuple(out)

    def _local_includes(self, k: int, include: tuple[float, ...]) -> tuple[float, ...]:
        piece = self.pieces[k]
        lo, hi = self._s0[k], self._s0[k + 1]
        return tuple(
            piece.t_min + (t - lo) for t in include if lo < t < hi
        )

    def sample_params(
        self,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        return self._concat_samples(
            p.sample_params(max_chord_error, include=self._local_includes(k, include))
            for k, p in enumerate(self.pieces)
        )

    def sample_params_for_offset(
        self,
        offset: float,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        return self._concat_samples(
            p.sample_params_for_offset(
                offset, max_chord_error, include=self._local_includes(k, include)
            )
            for k, p in enumerate(self.pieces)
        )

    def canonical(self) -> tuple:
        return ("piecewise", tuple(p.canonical() for p in self.pieces))
