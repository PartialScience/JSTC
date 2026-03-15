from .base_material import MaterialProperties
from .copper import Copper
from .aluminum import Aluminum

from enum import Enum

class Material(Enum):
    """Enum representing different materials with their properties."""
    COPPER = Copper()
    ALUMINUM = Aluminum()

__all__ = [
	"MaterialProperties",
	"Material",
	"Copper",
	"Aluminum",
]
