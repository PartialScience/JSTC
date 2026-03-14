import functools
from typing import Tuple

import numba
import numpy as np

from app.formulas.magnetic import coaxial_circle_geometric_mutual_inductance
from app.models.coil_models import SecondaryConductorSpec
from app.simulation.distributed_element_matrices.inductance.base import InductanceMatrixSolver


# ---------------------------------------------------------------------------
# Numba-accelerated matrix fill (compiled once on first call)
# ---------------------------------------------------------------------------


@numba.njit(parallel=True)
def _fill_inductance_matrix(r, z, wire_diameter, L):
    """Fill the symmetric inductance matrix in-place using the Maxwell formula.

    Computes only the upper triangle and mirrors to the lower triangle.
    Parallelised across rows via numba.prange.
    """
    n = len(r)
    for i in numba.prange(n):
        r1 = r[i]
        z1 = z[i]

        L[i, i] = coaxial_circle_geometric_mutual_inductance(
            r1, r1, 0.0, wire_diameter,
        )

        for j in range(i + 1, n):
            val = coaxial_circle_geometric_mutual_inductance(
                r1, r[j], z[j] - z1, wire_diameter,
            )
            L[i, j] = val
            L[j, i] = val


class CoaxialRingInductanceLMatrixSolver(InductanceMatrixSolver):
    """Computes the L matrix by modeling each turn as a coaxial ring.

    The full turn-by-turn mutual-inductance matrix is computed once (and
    cached), then downsampled to the requested discretization order using
    segment boundaries provided by the discretizer.

    Supported kwargs:
        turn_interpolation_density (int): Number of dense samples per turn
            used to invert ``turn_fxn`` via linear interpolation.
            Defaults to ``_DEFAULT_TURN_INTERPOLATION_DENSITY``, which
            gives sub-0.1% accuracy for smooth (monotonic) turn functions.
    """

    _DEFAULT_TURN_INTERPOLATION_DENSITY = 10

    @property
    def turn_interpolation_density(self) -> int:
        """Dense samples per turn for inverting ``turn_fxn``."""
        return self._kwargs.get(
            "turn_interpolation_density",
            self._DEFAULT_TURN_INTERPOLATION_DENSITY,
        )

    def geometric_inductance_matrix(
        self,
        secondary: SecondaryConductorSpec,
        discretization_order: int,
    ) -> Tuple[Tuple[float, ...], ...]:
        """Compute the geometric inductance matrix at the given discretization.

        Parameters:
            secondary: The specification of the secondary conductor.
            discretization_order: The number of discrete segments to use.

        Returns:
            An NxN tuple-of-tuples geometric inductance matrix
            (N = discretization_order).  The returned matrix elements have
            the same units as the coil geometry.  For example, if the coil
            spec is defined in inches, the matrix elements will also be in
            inches.  To convert to units of inductance (Henries), multiply
            by the permeability of free space μ₀.
        """
        slices = tuple(self.discretizer.get_slices(secondary, discretization_order))

        L_full = self._compute_full_turn_matrix(
            secondary, self.turn_interpolation_density
        )
        n = L_full.shape[0]

        # Map each slice boundary to the nearest turn index, then sum
        # rows/columns within each slice via reduceat.
        slice_indices = sorted(set(
            max(0, min(n - 1, round(secondary.turn_fxn(t))))
            for t in slices
        ))
        L = np.add.reduceat(
            np.add.reduceat(L_full, slice_indices, axis=0),
            slice_indices,
            axis=1,
        )

        return tuple(tuple(row) for row in L)

    @staticmethod
    @functools.lru_cache
    def _compute_full_turn_matrix(
        secondary: SecondaryConductorSpec,
        turn_interpolation_density: int,
    ) -> np.ndarray:
        """Cached full turn-by-turn inductance matrix.

        Models each turn as a discrete conducting ring and computes the
        pairwise mutual inductance between all rings.

        Parameters:
            secondary: The specification of the secondary conductor.
            turn_interpolation_density: Dense samples per turn for
                inverting ``turn_fxn`` via linear interpolation.

        Returns:
            An (M+1)x(M+1) array where M = total_turns, representing the
            geometric inductance matrix.  Multiply by μ₀ for units of
            inductance (Henries).
        """
        curve = secondary.curve
        num_turns = secondary.total_turns

        # Build a dense sample of turn_fxn and invert it to find the t
        # parameter for each integer turn boundary.
        n_samples = turn_interpolation_density * num_turns
        t_sample = np.linspace(curve.t_min, curve.t_max, n_samples)
        turn_sample = np.array([secondary.turn_fxn(t) for t in t_sample])

        target_turns = np.arange(1, num_turns, dtype=float)
        t_interp = np.interp(target_turns, turn_sample, t_sample)

        t_values = np.empty(num_turns + 1)
        t_values[0] = curve.t_min
        t_values[1:-1] = t_interp
        t_values[-1] = curve.t_max

        points = tuple(curve.point_at(t) for t in t_values)
        r = np.array([p[0] for p in points], dtype=np.float64)
        z = np.array([p[1] for p in points], dtype=np.float64)

        L = np.empty((len(r), len(r)), dtype=np.float64)
        _fill_inductance_matrix(r, z, secondary.wire_dia, L)
        return L