
from app.geometry.curves.base import ParametricCurve

class LineSegment(ParametricCurve):
    """
    Concrete parametric curve class for a line segment
    """
    
    def __init__(self, start: tuple[float, float], end: tuple[float, float]) -> None:
        """
        Initialize a line segment with start and end points.
        
        Args:
            start: A tuple of floats representing the coordinates of the start point
            end: A tuple of floats representing the coordinates of the end point
        """
        self.start = start
        self.end = end
    
    @property
    def t_min(self) -> float:
        """The minimum parameter value for the line segment."""
        return 0.0

    @property
    def t_max(self) -> float:
        """The maximum parameter value for the line segment."""
        return 1.0
    
    def point_at(self, t: float) -> tuple[float, float]:
        """Get the point on the line segment corresponding to the parameter t."""
        x = self.start[0] + t * (self.end[0] - self.start[0])
        y = self.start[1] + t * (self.end[1] - self.start[1])
        return (x, y)
    
    def derivative_at(self, t: float) -> tuple[float, float]:
        """Get the tangent vector of the line segment (constant for all t)."""
        return (self.end[0] - self.start[0], self.end[1] - self.start[1])
    
    def arc_length_between(self, t1: float, t2: float) -> float:
        """Compute the arc length of the line segment between parameters t1 and t2."""        
        # The length of the full line segment
        full_length = ((self.end[0] - self.start[0]) ** 2 + (self.end[1] - self.start[1]) ** 2) ** 0.5
        
        # The arc length between t1 and t2 is proportional to the difference in parameters
        return full_length * (t2 - t1)
    
    def distance_to_curve_for_range(self, point: tuple[float, float], t1: float, t2: float) -> float:
        """Provide the shortest distance from a given point to the line segment over [t1, t2]."""
        s1 = self.start
        s2 = self.end

        dx = s2[0] - s1[0]
        dy = s2[1] - s1[1]
        seg_len_sq = dx * dx + dy * dy

        # Degenerate segment (single point)
        if seg_len_sq == 0.0:
            return ((point[0] - s1[0]) ** 2 + (point[1] - s1[1]) ** 2) ** 0.5

        # Optimal t on the full line: t_hat = <p - s1, s2 - s1> / ||s2 - s1||^2
        t_hat = ((point[0] - s1[0]) * dx + (point[1] - s1[1]) * dy) / seg_len_sq

        # Project back to [t1, t2]
        t_star = min(max(t_hat, t1), t2)

        # Nearest point on the segment
        nearest = self.point_at(t_star)

        return ((point[0] - nearest[0]) ** 2 + (point[1] - nearest[1]) ** 2) ** 0.5