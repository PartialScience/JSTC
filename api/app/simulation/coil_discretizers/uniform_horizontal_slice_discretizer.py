from typing import Tuple
from api.app.simulation.coil_discretizers.base import CoilDiscretizer
from api.app.simulation.matrix_solvers.connectivity.series_solver import SeriesConnectivityMatrixSolver
from api.app.models.coil_models import SecondaryConductorSpec, SecondaryConductorSegment

class UniformHorizontalSliceDiscretizer(
    CoilDiscretizer,
    SeriesConnectivityMatrixSolver
):
    """A coil discretizer that divides the secondary conductor into uniform horizontal slices."""
    
    @staticmethod
    def discretize_conductor(
        secondary: SecondaryConductorSpec,
        discretization_order: int,
    ) -> Tuple[SecondaryConductorSegment]:
        """Discretize the secondary conductor into uniform horizontal slices."""
        height = secondary.get_geometry()
        slice_height = height / discretization_order
        
        segments = []
        for i in range(discretization_order):
            segment = SecondaryConductorSegment(
                start_height=i * slice_height,
                end_height=(i + 1) * slice_height,
                width=secondary.get_geometry().width
            )
            segments.append(segment)
        
        return tuple(segments)
