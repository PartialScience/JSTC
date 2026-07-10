"""
Base class for all parametric curves
"""

from abc import ABC, abstractmethod
from bisect import insort

from scipy.integrate import quad
from scipy.optimize import minimize_scalar


class ParametricCurve(ABC):
    """Abstract base class for parametric curves.

    Concrete curves must implement ``t_min``/``t_max``, ``point_at`` and
    ``derivative_at``.  Everything else has a robust general implementation
    in terms of those four; concrete classes should override the general
    implementations wherever an exact/fast closed form exists (see
    ``LineSegment`` and ``CircularArc``).
    """

    #: Number of coarse samples used to bracket global minimizers in the
    #: general closest-point search. Enough to isolate the global minimum
    #: for any curve whose geometry varies on scales longer than
    #: (t_max - t_min) / _COARSE_SAMPLES.
    _COARSE_SAMPLES = 64

    @property
    @abstractmethod
    def t_min(self) -> float:
        """The minimum parameter value for the curve."""
        ...

    @property
    @abstractmethod
    def t_max(self) -> float:
        """The maximum parameter value for the curve."""
        ...

    @abstractmethod
    def point_at(self, t: float) -> tuple[float, ...]:
        """
        Get the point on the curve corresponding to the parameter t.

        Args:
            t: The parameter value

        Returns:
            A tuple of floats representing the coordinates of the point on the curve
        """
        ...

    @abstractmethod
    def derivative_at(self, t: float) -> tuple[float, ...]:
        """
        Get the derivative (tangent vector) of the curve at parameter t.

        Args:
            t: The parameter value

        Returns:
            A tuple of floats representing the components of the tangent vector
        """
        ...

    # ------------------------------------------------------------------
    # General implementations - override with closed forms where possible
    # ------------------------------------------------------------------

    def arc_length_between(self, t1: float, t2: float) -> float:
        """
        Compute the arc length of the curve between parameters t1 and t2.

        General implementation: numerical quadrature of the tangent
        magnitude.

        Args:
            t1: The start parameter value
            t2: The end parameter value

        Returns:
            The arc length of the curve between t1 and t2.
        """
        speed = lambda t: sum(d * d for d in self.derivative_at(t)) ** 0.5
        length, _ = quad(speed, t1, t2, limit=200)
        return length

    def closest_parameter_in_range(
        self, point: tuple[float, ...], t1: float, t2: float
    ) -> float:
        """
        Find the parameter of the point on the curve closest to *point*,
        restricted to the parameter range [t1, t2].

        General implementation: coarse global sampling to bracket the
        minimum, followed by bounded local refinement.

        Args:
            point: A tuple of floats representing the coordinates of the point
            t1: The start of the parameter range
            t2: The end of the parameter range

        Returns:
            The parameter t* in [t1, t2] minimizing |point - point_at(t)|
        """
        def dist_sq(t: float) -> float:
            p = self.point_at(t)
            return sum((a - b) ** 2 for a, b in zip(point, p))

        n = self._COARSE_SAMPLES
        ts = [t1 + (t2 - t1) * i / n for i in range(n + 1)]
        best_i = min(range(n + 1), key=lambda i: dist_sq(ts[i]))

        # Refine within the bracketing neighbors of the coarse winner
        lo = ts[max(best_i - 1, 0)]
        hi = ts[min(best_i + 1, n)]
        if lo == hi:
            return lo
        result = minimize_scalar(dist_sq, bounds=(lo, hi), method="bounded")
        # The coarse winner guards against a failed local refinement
        return result.x if result.fun <= dist_sq(ts[best_i]) else ts[best_i]

    def closest_parameter(self, point: tuple[float, ...]) -> float:
        """Find the parameter of the curve point closest to *point*.

        Delegates to closest_parameter_in_range over the full domain.
        """
        return self.closest_parameter_in_range(point, self.t_min, self.t_max)

    def distance_to_curve_for_range(
        self, point: tuple[float, ...], t1: float, t2: float
    ) -> float:
        """
        Provide the shortest distance from a given point to the portion of
        the curve restricted to the parameter range [t1, t2].

        General implementation: distance to the closest-parameter point.

        Args:
            point: A tuple of floats representing the coordinates of the point
            t1: The start of the parameter range
            t2: The end of the parameter range

        Returns:
            The shortest distance from the point to the curve over [t1, t2]
        """
        t_star = self.closest_parameter_in_range(point, t1, t2)
        p = self.point_at(t_star)
        return sum((a - b) ** 2 for a, b in zip(point, p)) ** 0.5

    def distance_to_curve(self, point: tuple[float, ...]) -> float:
        """
        Provide the shortest distance from a given point to the curve.

        Delegates to distance_to_curve_for_range over the full parameter domain.

        Args:
            point: A tuple of floats representing the coordinates of the point

        Returns:
            The shortest distance from the point to the curve
        """
        return self.distance_to_curve_for_range(point, self.t_min, self.t_max)

    def sample_params(
        self,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> tuple[float, ...]:
        """
        Sample parameter values such that the polyline through the sampled
        points deviates from the curve by at most *max_chord_error*.

        General implementation: recursive bisection - a segment [ta, tb] is
        split while the curve midpoint deviates from the chord midpoint by
        more than the tolerance.

        Args:
            max_chord_error: Maximum allowed distance between the curve and
                the chord of any sampled segment.
            include: Parameter values that must appear in the sample
                (e.g. discretization slice boundaries, so that no chord
                spans a value where downstream data has a kink).

        Returns:
            Sorted tuple of parameter values from t_min to t_max.
        """
        params = [self.t_min, self.t_max]
        for t in include:
            if self.t_min < t < self.t_max:
                insort(params, t)

        def chord_error(ta: float, tb: float) -> float:
            """Curve-to-chord deviation, probed at the 1/4, 1/2, 3/4 points.

            Probing three interior points (not just the midpoint) prevents
            symmetric curves - where the curve midpoint happens to lie on
            the chord - from defeating the refinement test.
            """
            pa, pb = self.point_at(ta), self.point_at(tb)
            err = 0.0
            for frac in (0.25, 0.5, 0.75):
                tp = ta + frac * (tb - ta)
                pp = self.point_at(tp)
                chord_pt = tuple(a + frac * (b - a) for a, b in zip(pa, pb))
                dev = sum((p - c) ** 2 for p, c in zip(pp, chord_pt)) ** 0.5
                err = max(err, dev)
            return err

        # Refine until every adjacent pair satisfies the chord tolerance.
        # min_step guards against runaway subdivision on degenerate input.
        min_step = (self.t_max - self.t_min) * 1e-6
        stack = list(zip(params[:-1], params[1:]))
        out: list[float] = [params[0]]
        while stack:
            ta, tb = stack.pop(0)
            if tb - ta > min_step and chord_error(ta, tb) > max_chord_error:
                tm = 0.5 * (ta + tb)
                stack.insert(0, (tm, tb))
                stack.insert(0, (ta, tm))
            else:
                out.append(tb)
        return tuple(out)
