from .base_geometric_region import GeometricRegion
from app.geometry.curves.base import ParametricCurve
from typing import List

class OffsetRegion(
    GeometricRegion
):
    """
    A geometric region which contains all points within a set offset distance from a 
    parametric curve.
    """
   
    def __init__(self, curve: ParametricCurve, offset: float):
        """
        Initialize an offset region with a parametric curve and an offset distance.
        
        Args:
            curve: A ParametricCurve object representing the central curve of the region
            offset: A float representing the distance from the curve that defines the region
        """
        self._curve = curve
        self._offset = offset
    
    @property
    def offset(self) -> float:
        return self._offset
    
    @property
    def curve(self) -> ParametricCurve:
        return self._curve
   
    def contains(self, point: List[float]) -> bool:
        """
        Determine if a point is in the region by seeing if it is within 
        "offset" of the curve
        """
        return (self.curve.distance_to_curve(point) <= self.offset)

    def bounding_box(self) -> List[tuple[float, float]]:
        """
        Determine the bounding box of the offset region by taking the bounding box of the curve
        and expanding it by the offset in all directions.
        """
        curve_bounds = self.curve.bounding_box()
        return [(bound[0]-self.offset, bound[1]+self.offset) for bound in curve_bounds]