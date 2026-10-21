from typing import Tuple

from app.models.coil_models import SecondaryConductorSpec
from app.simulation.coil_discretizers.base import CoilDiscretizer
from app.simulation.coil_discretizers.connectivity_matrices.series_solver import SeriesConnectivityMatrixSolver


class UniformArcLengthDiscretizer(
    CoilDiscretizer,
    SeriesConnectivityMatrixSolver
):
    """Divides the secondary into slices of near-uniform arc length whose
    interior boundaries sit EXACTLY on whole-turn boundaries.

    Each interior slice boundary is the uniform-arc-length target snapped to
    the nearest integer-turn boundary (via the turn profile's exact
    inverse). Cutting on whole turns is the convention the magnetic solvers
    group rings by, so with this discretizer the L-matrix / coupling-vector
    segment grouping and the C-matrix tent nodes coincide exactly - and the
    grouping can never collapse (the historical shape-mismatch failure when
    slices outnumbered turns).

    The resulting discretization is compatible with a series connectivity
    matrix, inherited from SeriesConnectivityMatrixSolver.
    """

    @staticmethod
    def get_slices(
        secondary: SecondaryConductorSpec,
        discretization_order: int,
    ) -> Tuple[float, ...]:
        """Return discretization_order + 1 slice boundary parameters.

        Boundaries are [t_min, inverse(n_1), ..., inverse(n_{N-1}), t_max]
        with n_k strictly increasing integer turn counts chosen nearest the
        uniform-arc-length targets.

        Raises:
            ValueError: if discretization_order exceeds the secondary's
                total turn count - a winding cannot be cut finer than one
                turn per segment (the ring model has no sub-turn geometry).
        """
        if discretization_order < 1:
            raise ValueError(
                f"discretization_order must be >= 1, got {discretization_order}"
            )
        curve = secondary.curve
        turn_fxn = secondary.turn_fxn
        total_turns = secondary.total_turns  # integer ceil of the turn count
        if discretization_order > total_turns:
            raise ValueError(
                f"discretization_order ({discretization_order}) exceeds the "
                f"secondary's total turn count ({total_turns}). The "
                "discretizer cuts the winding on whole-turn boundaries (the "
                "magnetic ring model has no sub-turn geometry), so the order "
                "cannot exceed the number of turns."
            )

        span = curve.t_max - curve.t_min
        interior: list[int] = []
        prev = 0
        for k in range(1, discretization_order):
            t_target = curve.t_min + span * k / discretization_order
            n_k = round(turn_fxn(t_target))
            # Keep the integer turn boundaries strictly increasing while
            # leaving room for the remaining interior boundaries (all must
            # stay below the final turn).
            lower = prev + 1
            upper = (total_turns - 1) - (discretization_order - 1 - k)
            n_k = min(max(n_k, lower), upper)
            interior.append(n_k)
            prev = n_k

        return (
            curve.t_min,
            *(turn_fxn.inverse(float(n)) for n in interior),
            curve.t_max,
        )
