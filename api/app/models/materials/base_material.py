from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum
from .copper import Copper
from .aluminum import Aluminum

class Material(Enum):
    """Enum representing different materials with their properties."""
    COPPER = Copper()
    ALUMINUM = Aluminum()

@dataclass(frozen=True)
class MaterialProperties(ABC):

    @abstractmethod
    def conductivity(self, T: float) -> float:
        """Return the conductivity of the material at a given temperature T.
        
        Args:
            T: Temperature in Kelvin
        Returns:
            Conductivity in Siemens per meter (S/m)
        """
        ...