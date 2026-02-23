from typing import Tuple, List
from app.models.coil_models import ToploadSpec, GroundedConductorSpec, SecondaryConductorSpec
import methodtools as mt
from abc import ABC, abstractmethod
from app.simulation.C_matrix_solvers import FEMCapacitanceMatrixSolver
from app.simulation.L_matrix_solvers import IntegralInductanceLMatrixSolver
from app.simulation.A_matrix_solvers import SeriesConnectivityMatrixSolver

class TeslaCoilMatrixSolver(ABC):

    @abstractmethod
    def get_capacitance_matrix(self) -> List[List[float]]:
        """
        Return the maxwell mutual capacitance matrix C for the Tesla coil system.
        
        The individual conductors in this matrix should represent discrete "virtual" 
        conductors that make up the entire secondary coil and topload system.
        
        The effects of the topload elements should all be lumped into the topmost conductor of the secondary coil.
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_inductance_matrix(self) -> List[List[float]]:
        """
        Return the mutual inductance matrix L for the Tesla coil system.
        
        The individual conductors in this matrix should represent discrete "virtual" 
        conductors that make up the entire secondary coil.
        """
        raise NotImplementedError   
    
    @abstractmethod
    def get_connectivity_matrix(self) -> List[List[float]]:
        """
        Return the connectivity matrix A for the Tesla coil system.
        
        This matrix defines how the individual virtual conductors are wired together electrically.
        """
        raise NotImplementedError

class FEMCIntegralIMatrixSolver(
    TeslaCoilMatrixSolver,
    FEMCapacitanceMatrixSolver,
    IntegralInductanceLMatrixSolver,
    SeriesConnectivityMatrixSolver
):
    """Concrete class implementation of TeslaCoilMatrixSolver using FEM for capacitance and integral method for inductance."""
    
    def __init__(self,
        secondary: SecondaryConductorSpec, 
        toploads: Tuple[ToploadSpec, ...], 
        grounds: Tuple[GroundedConductorSpec, ...], 
        r_max: float, 
        z_max: float
    ):
        self.secondary = secondary
        self.toploads = toploads
        self.grounds = grounds
        self.r_max = r_max
        self.z_max = z_max

    def get_capacitance_matrix(self) -> List[List[float]]:
        return self.compute_capacitance_matrix(
            self.secondary,
            self.toploads,
            self.grounds,
            self.r_max,
            self.z_max
        )
    
    def get_inductance_matrix(self) -> List[List[float]]:
        return self.compute_inductance_matrix(
            self.secondary
        )
    
    def get_connectivity_matrix(self) -> List[List[float]]:
        return self.compute_connectivity_matrix(
            self.secondary.discretization_order
        )