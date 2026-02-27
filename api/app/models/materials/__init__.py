from enum import Enum

from .base_material import MaterialProperties


class Material(Enum):
	"""Enum representing different materials with their properties."""

	COPPER = "copper"

__all__ = [
	"MaterialProperties",
	"Material",
]
