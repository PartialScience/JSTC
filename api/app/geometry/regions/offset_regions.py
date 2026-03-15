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
   
    def __init__(self, curve: ParametricCurve, offset: float, flat_start: bool = False, flat_end: bool = False):
        """
        Initialize an offset region with a parametric curve and an offset distance.
        
        Args:
            curve: A ParametricCurve object representing the central curve of the region
            offset: A float representing the distance from the curve that defines the region
            flat_start: If True, the start endpoint cap is flat (perpendicular cut) instead of rounded
            flat_end: If True, the end endpoint cap is flat (perpendicular cut) instead of rounded
        """
        self._flat_start = flat_start
        self._flat_end = flat_end
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
        "offset" of the curve.
        
        When an end is set ot be flat, the rounded caps at the curve endpoints are
        replaced by flat cuts perpendicular to the tangent direction. A point
        near an endpoint is excluded if it falls on the outward side of the
        perpendicular plane through that endpoint.
        """
        if self.curve.distance_to_curve(point) > self.offset:
            return False
        
        if self._flat_start:
            # Start endpoint: reject points that are "before" the start plane
            start = self.curve.point_at(self.curve.t_min)
            tangent_start = self.curve.derivative_at(self.curve.t_min)
            dot_start = sum((p - s) * d for p, s, d in zip(point, start, tangent_start))
            if dot_start < 0:
                return False
        
        if self._flat_end:
            # End endpoint: reject points that are "past" the end plane
            end = self.curve.point_at(self.curve.t_max)
            tangent_end = self.curve.derivative_at(self.curve.t_max)
            dot_end = sum((p - e) * d for p, e, d in zip(point, end, tangent_end))
            if dot_end > 0:
                return False
        
        return True