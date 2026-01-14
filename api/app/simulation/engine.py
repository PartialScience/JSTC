from abc import ABC, abstractmethod
from typing import Tuple
from app.simulation.types import EigenFamily
from app.models.coil_models import ToploadSpec, GroundedConductorSpec, SecondaryConductorSpec

class TeslaCoilSimulationEngine(ABC):
    """Abstract base class for Tesla coil simulation engines."""
    
    @abstractmethod
    def compute_capacitance_matrix(self,
            secondary: SecondaryConductorSpec,
            toploads: Tuple[ToploadSpec, ...], 
            grounds: Tuple[GroundedConductorSpec, ...], 
            r_max: float, 
            z_max: float
        ) -> Tuple[Tuple[float, ...], ...]:
        """
        Compute and return the capacitance matrix for the Tesla coil system.
        
        Returns:
            A tuple of tuples representing the capacitance matrix
        """
        raise NotImplementedError
    
    @abstractmethod
    def compute_inductance_matrix(self,
            secondary: SecondaryConductorSpec,
            toploads: Tuple[ToploadSpec, ...], 
            grounds: Tuple[GroundedConductorSpec, ...], 
            r_max: float, 
            z_max: float
        ) -> Tuple[Tuple[float, ...], ...]:
        """
        Compute and return the inductance matrix for the Tesla coil system.
        
        Returns:
            A tuple of tuples representing the inductance matrix
        """
        raise NotImplementedError
        
    @abstractmethod
    def compute_connectivity_matrix(self) -> Tuple[Tuple[float, ...], ...]:
        """
        Compute and return the connectivity matrix for the Tesla coil system.
        
        Returns:
            A tuple of tuples representing the connectivity matrix
        """
        raise NotImplementedError
    
    @abstractmethod
    def compute_eigen_frequency_family(self,
            capacitance_matrix: Tuple[Tuple[float, ...], ...], 
            inductance_matrix: Tuple[Tuple[float, ...], ...], 
            connectivity_matrix: Tuple[Tuple[float, ...], ...]                               
        ) -> EigenFamily:
        """
        Compute and return the eigenfrequencies of the Tesla coil system.
        
        Returns:
            An EigenFamily instance containing eigenfrequencies and voltage eigenmodes.
        """
        raise NotImplementedError