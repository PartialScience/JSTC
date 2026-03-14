from typing import Tuple, Callable
from app.simulation.coil_discretizers.base import CoilDiscretizer
from app.simulation.coil_discretizers.connectivity_matrices.series_solver import SeriesConnectivityMatrixSolver
from app.models.coil_models import SecondaryConductorSpec
from scipy.optimize import root_scalar

class UniformArcLengthDiscretizer(
    CoilDiscretizer,
    SeriesConnectivityMatrixSolver
):
    """A concrete coil discretizer that divides the secondary conductor into uniform arc length slices.
    
    The resulting discretization is compatible with a series connectivity matrix which is inherited 
    from the SeriesConnectivityMatrixSolver.
    """
    
    @staticmethod
    def get_slices(
        secondary: SecondaryConductorSpec,
        discretization_order: int,
    ) -> Tuple[Tuple[float, float]]:
        """
        Return discretization_order + 1 evenly spaced parameter values along the secondary conductor, 
        where the spacing is determined by arc length.
        """
        curve = secondary.curve
        total_length = curve.arc_length_between(curve.t_min, curve.t_max)
        slice_arc_length = total_length / discretization_order
        slices = [curve.t_min]
        for i in range(discretization_order - 1):
            result = root_scalar(
                lambda t, _t0=slices[i]: curve.arc_length_between(_t0, t) - slice_arc_length,
                method='bisect',
                bracket=(slices[i], curve.t_max),
                xtol=1e-10,
            )
            slices.append(result.root)
        slices.append(curve.t_max) # Manually add the last value to avoid root finding sign issues caused by floating point inaccuracies
        
        return tuple(slices)

    