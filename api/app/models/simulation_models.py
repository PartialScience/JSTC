from typing import Optional, List
from enum import Enum
from app.models.coil_models import TeslaCoil
from functools import cached_property
from typing import NamedTuple
from dataclasses import dataclass


class BoundaryConditionType(Enum):
    """Type of boundary condition for electromagnetic simulation."""
    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"


class BoundaryCondition:
    """Boundary condition specification for simulation domain walls."""
    
    def __init__(self, 
                 bc_type: BoundaryConditionType = BoundaryConditionType.DIRICHLET, 
                 value: float = 0.0):
        """
        Initialize a boundary condition.
        
        Args:
            bc_type: Type of boundary condition (Dirichlet or Neumann)
            value: Value for the boundary condition (default 0.0)
        """
        self.bc_type = bc_type
        self.value = value
        

class SimulatableTeslaCoil():
    """A Tesla coil combined with a simulaion domain given as an x and y min/max and optional boundary conditions"""
    def __init__(self,
        r_max: float,
        z_max: float,
        coil: TeslaCoil,
        bc_bottom: Optional[BoundaryCondition] = BoundaryCondition(),
        bc_top: Optional[BoundaryCondition] = BoundaryCondition(),
        bc_right: Optional[BoundaryCondition] = BoundaryCondition(),
    ):
        """
        Initialize a SimulatableTeslaCoil.
        
        Args:
            r_max: Maximum radial extent of the simulation domain
            z_max: Maximum vertical extent of the simulation domain
            coil: The TeslaCoil instance to simulate
            bc_bottom: Boundary condition for the bottom wall (default: Dirichlet with value 0)
            bc_top: Boundary condition for the top wall (default: Dirichlet with value 0)
            bc_right: Boundary condition for the right wall (default: Dirichlet with value 0)
        """
        self.coil = coil
        self.r_max = r_max
        self.z_max = z_max
        # Set default boundary conditions if not provided
        self.bc_bottom = bc_bottom
        self.bc_top = bc_top
        self.bc_right = bc_right

class TeslaCoilSimulaton:
    """
    Computed tesla coil properties
    """
    def __init__(self, coil: SimulatableTeslaCoil):
        self.coil = coil
  
    @property
    def secondary(self):
        """Secondary coil properties."""
        if self._secondary is None:
            self._secondary = TeslaCoilSecondarySimulaton(self)
        return self._secondary
    
    @property
    def primary(self):
        """Primary coil properties."""
        if self._primary is None:
            self._primary = TeslaCoilPrimarySimulaton(self)
        return self._primary
    

class TeslaCoilSecondarySimulaton:
    """
    Computed tesla coil properties pertaining to the secondary coil
    
    These properties are grouped together for clarity and organization. 
    While they most logically pertain to the secondary coil, some
    still depend on entire tesla coil simulation setup, and primary coil 
    parameters. However they vary most heavily with secondary coil parameters.
    """
    def __init__(self, parent: TeslaCoilSimulaton):
        self.parent = parent
    
    @cached_property
    def CapacitanceMatrix(self):
        """Placeholder for capacitance matrix calculation method."""
        pass
    
    @cached_property
    def InductanceMatrix(self):
        """Placeholder for inductance matrix calculation method."""
        pass
    
    @property
    def ConnectivityMatrix(self):
        """Placeholder for connectivity matrix calculation method."""
        pass
    
    class EigenFamily(NamedTuple):
        eigenvalues: List[float]
        eigenvectors: List[List[float]]
          
    @property
    def _eigenFrequencyFamily(self) -> EigenFamily:
        """Placeholder for eigenmode solver method."""
        pass
    
    @property
    def EigenFrequencies(self):
        """Return the eigenfrequencies calculated from the eigenvalue problem."""
        return self._eigenFrequencyFamily.eigenvalues
    
    @property
    def VoltageEigenModes(self):
        """Return the voltage eigenmodes calculated from the eigenvalue problem."""
        return self._eigenFrequencyFamily.eigenvectors
    
    @property
    def CurrentEigenModes(self):
        """Placeholder for current eigenmodes calculation method."""
        pass
    
    @property
    def ResonantFrequency(self) -> float:
        return self.EigenFrequencies[0]
    
    

    
        
class TeslaCoilPrimarySimulaton:
    def __init__(self, parent: TeslaCoilSimulaton):
        self.parent = parent
        
"""
TeslaCoilSimulaton class design criteria: 

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
                



 
"""