from typing import Tuple
from api.app.simulation.coil_discretizers.base import CoilDiscretizer
from api.app.simulation.matrix_solvers.connectivity.series_solver import SeriesConnectivityMatrixSolver
from api.app.models.coil_models import SecondaryConductorSpec, SecondaryConductorSegment
from app.geometry import HorizontalSliceRegion


class UniformHorizontalSliceDiscretizer(
    CoilDiscretizer,
    SeriesConnectivityMatrixSolver
):
    """A concrete coil discretizer that divides the secondary conductor into uniform horizontal slices.
    
    The resulting discretization results in a series connectivity matrix which is inherited 
    from the SeriesConnectivityMatrixSolver.
    """
    
    @staticmethod
    def discretize_conductor(
        secondary: SecondaryConductorSpec,
        discretization_order: int,
    ) -> Tuple[SecondaryConductorSegment]:
        """Discretize the secondary conductor into uniform horizontal slices."""
        secondary_bounds = secondary.bounding_box
        if secondary_bounds.length != 2:
            raise ValueError("Secondary conductor geometry must be 2D.")
        (ymin, ymax) = secondary_bounds[1]
        slice_height = (ymax - ymin) / discretization_order
        coil_geometry = secondary.get_geometry()
        segments = tuple(
            SecondaryConductorSegment(
                geometry = HorizontalSliceRegion(
                    region = coil_geometry,
                    y_min = ymin + i * slice_height,
                    y_max = ymin + (i + 1) * slice_height
                )
            )
            for i in range(discretization_order)
        )
        return segments