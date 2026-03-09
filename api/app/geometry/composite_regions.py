"""A collection of regions derived from more basic geometric primitives, such as circles and polygons."""

from typing import List, Tuple
from dataclasses import dataclass
from .base_geometric_region import GeometricRegion

@dataclass(frozen=True)
class RegionUnion(GeometricRegion):
    """A region representing the union of multiple geometric regions."""
    regions: Tuple[GeometricRegion, ...]
    
    def contains(self, point: List[float]) -> bool:
        """Check if the point is contained in any of the constituent regions."""
        return any(region.contains(point) for region in self.regions)

    def bounding_box(self) -> List[Tuple[float, float]]:
        """Return the bounding box enclosing all constituent regions."""
        boxes = [region.bounding_box() for region in self.regions]
        ndim = len(boxes[0])
        return [
            (min(b[d][0] for b in boxes), max(b[d][1] for b in boxes))
            for d in range(ndim)
        ]
    
@dataclass(frozen=True)
class RegionIntersection(GeometricRegion):
    """A region representing the intersection of multiple geometric regions."""
    regions: Tuple[GeometricRegion, ...]
    
    def contains(self, point: List[float]) -> bool:
        """Check if the point is contained in all of the constituent regions."""
        return all(region.contains(point) for region in self.regions)

    def bounding_box(self) -> List[Tuple[float, float]]:
        """Return the bounding box of the intersection (tightest overlap of all constituent boxes)."""
        boxes = [region.bounding_box() for region in self.regions]
        ndim = len(boxes[0])
        return [
            (max(b[d][0] for b in boxes), min(b[d][1] for b in boxes))
            for d in range(ndim)
        ]

@dataclass(frozen=True)
class HorizontalSliceRegion(GeometricRegion):
    """A horizontal slice of a geometric region between two y-values."""
    region: GeometricRegion
    y_min: float
    y_max: float
    
    def contains(self, point: List[float]) -> bool:
        """Check if the point is contained in the region and within the horizontal slice."""
        return self.region.contains(point) and self.y_min <= point[1] <= self.y_max

    def bounding_box(self) -> List[Tuple[float, float]]:
        """Return the bounding box of the region clamped to the horizontal slice."""
        box = self.region.bounding_box()
        return [
            box[0],
            (max(box[1][0], self.y_min), min(box[1][1], self.y_max)),
        ]