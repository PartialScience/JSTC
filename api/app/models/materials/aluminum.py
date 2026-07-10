from .base_material import MaterialProperties

class Aluminum(MaterialProperties):
    """Material properties for aluminum."""
    
    def conductivity(self, T: float) -> float:
        """Return the conductivity of aluminum at a given temperature T.
        
        Args:
            T: Temperature in Kelvin
        Returns:
            Conductivity in Siemens per meter (S/m)
        """
        # Empirical formula for aluminum conductivity as a function of temperature
        # σ(T) = σ0 / (1 + α * (T - T0))
        # where σ0 is the conductivity at reference temperature T0, and α is the temperature coefficient
        σ0 = 3.77e7  # Conductivity of aluminum at 20°C (293K) in S/m
        T0 = 293.15  # Reference temperature in Kelvin
        α = 0.00429  # Temperature coefficient for aluminum
                
        return σ0 / (1 + α * (T - T0))

    @property
    def density(self) -> float:
        """Mass density of aluminum in kg/m^3."""
        return 2700.0
