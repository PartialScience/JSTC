from typing import Optional, List, Tuple
from enum import Enum
from app.models.coil_models import TeslaCoilSpec, ToploadSpec, GroundedConductorSpec, SecondaryConductorSpec
from typing import NamedTuple
import methodtools as mt
from dataclasses import dataclass, field
import numpy as np
from scipy import linalg

class BoundaryConditionType(Enum):
    """Type of boundary condition for electromagnetic simulation."""
    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"

@dataclass
class BoundaryCondition:
    """Boundary condition specification for simulation domain walls."""
    bc_type: BoundaryConditionType = BoundaryConditionType.DIRICHLET
    value: float = 0.0
        
@dataclass(kw_only=True)
class SimulatableTeslaCoil(TeslaCoilSpec):
    """Tesla coil specification extended with simulation domain boundaries and boundary conditions."""
    
    r_max: float
    """Maximum radial extent of the simulation domain"""
    
    z_max: float
    """Maximum vertical extent of the simulation domain"""
    
    discretization_order: int = 30
    """Number of virtual conductors to break the secondary coil into for matrix calculations"""
    
    bc_bottom: BoundaryCondition = field(default_factory=BoundaryCondition)
    """Boundary condition applied at the bottom (z=0) of the simulation domain."""
    
    bc_top: BoundaryCondition = field(default_factory=BoundaryCondition)
    """Boundary condition applied at the top (z=z_max) of the simulation domain."""
    
    bc_right: BoundaryCondition = field(default_factory=BoundaryCondition)
    """Boundary condition applied at the right boundary (r=r_max) of the simulation domain."""

@dataclass
class TeslaCoilSimulation:
    
    coil_geometry: SimulatableTeslaCoil
    
    _primary: Optional["TeslaCoilPrimarySimulation"] = field(default=None, init=False, repr=False)
    _secondary: Optional["TeslaCoilSecondarySimulation"] = field(default=None, init=False, repr=False)

    @property
    def primary(self):
        """Primary coil properties."""
        if self._primary is None:
            self._primary = TeslaCoilPrimarySimulation(self)
        return self._primary

    @property
    def secondary(self):
        """Secondary coil properties."""
        if self._secondary is None:
            self._secondary = TeslaCoilSecondarySimulation(self)
        return self._secondary

@dataclass
class TeslaCoilSecondarySimulation:
    """
    Computed tesla coil properties pertaining to the secondary coil
    
    These properties are grouped together for clarity and organization. 
    While they most logically pertain to the secondary coil, some
    still depend on entire tesla coil simulation setup, and primary coil 
    parameters. However they vary most heavily with secondary coil parameters.
    """
    parent: TeslaCoilSimulation
        
 
    @mt.lru_cache()
    @staticmethod
    def _ComputeCapacitanceMatrix(
        secondary: SecondaryConductorSpec, 
        toploads: Tuple[ToploadSpec, ...], 
        grounds: Tuple[GroundedConductorSpec, ...], 
        r_max: float, 
        z_max: float
    ) -> List[List[float]]:
        """
        Placeholder for capacitance matrix calculation method.
        
        Args are passed explicitly to allow for proper caching based on dependencies.
        Note: Tuples are used instead of lists to enable proper caching.
        """
        pass
    
    @property
    def CapacitanceMatrix(self):
        geometry = self.parent.coil_geometry
        return self._ComputeCapacitanceMatrix(
            geometry.secondary,
            geometry.toploads,
            geometry.grounds,
            self.parent.r_max,
            self.parent.z_max,
        )
    
    @mt.lru_cache()
    @staticmethod
    def _ComputeInductanceMatrix(
        secondary: SecondaryConductorSpec, 
        toploads: Tuple[ToploadSpec, ...], 
        grounds: Tuple[GroundedConductorSpec, ...], 
        r_max: float, 
        z_max: float
    ) -> List[List[float]]:
        """
        Placeholder for inductance matrix calculation method.
        
        Args are passed explicitly to allow for proper caching based on dependencies.
        Note: Tuples are used instead of lists to enable proper caching.
        """
        pass
    
    @property
    def InductanceMatrix(self):
        """Placeholder for inductance matrix calculation method."""
        pass
    
    @property
    def ConnectivityMatrix(self):
        """Placeholder for connectivity matrix calculation method."""
        pass
    
    @dataclass(frozen=True)
    class EigenFamily(NamedTuple):
        eigenvalues: List[float]
        eigenvectors: List[List[float]]
          
    @mt.lru_cache()
    @staticmethod
    def _eigenFrequencyFamily(
        capacitance_matrix: Tuple[Tuple[float, ...], ...], 
        inductance_matrix: Tuple[Tuple[float, ...], ...], 
        connectivity_matrix: Tuple[Tuple[float, ...], ...]
    ) -> "TeslaCoilSecondarySimulation.EigenFamily":
        """
        Solve the generalized eigenvalue problem for the system:
        ω² C V = -A L⁻¹ Aᵀ V
        
        Args:
            capacitance_matrix: Capacitance matrix (tuples for caching)
            inductance_matrix: Inductance matrix (tuples for caching)
            connectivity_matrix: Connectivity matrix (tuples for caching)
            
        Returns:
            EigenFamily with eigenfrequencies and voltage eigenmodes
        """
        # Convert tuples to numpy arrays
        C = np.array(capacitance_matrix)
        L = np.array(inductance_matrix)
        A = np.array(connectivity_matrix)
        
        # Compute the right-hand side matrix: -A L⁻¹ Aᵀ
        L_inv = linalg.inv(L)
        RHS = -A @ L_inv @ A.T
        
        # Solve generalized eigenvalue problem: ω² C V = RHS V
        # This is equivalent to: RHS V = ω² C V
        eigenvalues, eigenvectors = linalg.eig(RHS, C)
        
        # Extract real parts and compute frequencies from ω²
        # ω² is the eigenvalue, so ω = sqrt(eigenvalue)
        # f = ω / (2π)
        omega_squared = np.real(eigenvalues)
        omega = np.sqrt(np.abs(omega_squared))
        frequencies = omega / (2 * np.pi)
        
        # Sort by frequency (ascending)
        sorted_indices = np.argsort(frequencies)
        frequencies_sorted = frequencies[sorted_indices]
        eigenvectors_sorted = np.real(eigenvectors[:, sorted_indices])
        
        # Convert to lists for the return type
        freq_list = frequencies_sorted.tolist()
        eigvec_list = [eigenvectors_sorted[:, i].tolist() for i in range(eigenvectors_sorted.shape[1])]
        
        return TeslaCoilSecondarySimulation.EigenFamily(
            eigenvalues=freq_list,
            eigenvectors=eigvec_list
        )
    
    @property
    def EigenFrequencies(self):
        """Return the eigenfrequencies calculated from the eigenvalue problem."""
        eigen_family = self._eigenFrequencyFamily(
            tuple(tuple(row) for row in self.CapacitanceMatrix),
            tuple(tuple(row) for row in self.InductanceMatrix),
            tuple(tuple(row) for row in self.ConnectivityMatrix)
        )
        return eigen_family.eigenvalues
    
    @property
    def VoltageEigenModes(self):
        """Return the voltage eigenmodes calculated from the eigenvalue problem."""
        eigen_family = self._eigenFrequencyFamily(
            tuple(tuple(row) for row in self.CapacitanceMatrix),
            tuple(tuple(row) for row in self.InductanceMatrix),
            tuple(tuple(row) for row in self.ConnectivityMatrix)
        )
        return eigen_family.eigenvectors
    
    @property
    def CurrentEigenModes(self):
        """Placeholder for current eigenmodes calculation method."""
        pass
    
    @property
    def ResonantFrequency(self) -> float:
        return self.EigenFrequencies[0]

@dataclass    
class TeslaCoilPrimarySimulation:
    def __init__(self, parent: TeslaCoilSimulation):
        self.parent = parent
        
"""
TeslaCoilSimulation class design criteria: 

1.  Want to be able to read simulation properties off the class like
    sim.Secodary.ResonantFrequency
    
2.  Want to cache all computations, and only clear the cache for a given property
    when the value of one of its dependacies changes
    
3.  Want to have a clean way of dealing with units (any libraries for this?)
    * A decorator which specifies property units would be sick
    * Some proper unit classes would be also very good
    * And it would be esspesially nice if a library had all the built in converters I need
    * I think we should have the following for unit handeling: 
        a. Unit converter which takes in different unit options for 
    ? Or should we even have units, or should we try to convert to dimensionless quntites
        We should probably do this during the PDE solves at the very least
                
TODO: 

1.  Move the computation methods to a Simulator class and make these just data holders 

2. Create a simulator class that uses a proper dependency injection pattern

 
"""