from dataclasses import dataclass
from abc import ABC, abstractmethod

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

    @property
    @abstractmethod
    def density(self) -> float:
        """Return the mass density of the material.

        Returns:
            Density in kilograms per cubic meter (kg/m^3)
        """
        ...
