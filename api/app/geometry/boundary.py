"""
Boundary description of geometric regions: closed loops of parametric curves.

A region's boundary is expressed as one or more closed loops, each loop a
sequence of oriented curve pieces laid end to end. This is the contract that
connects the geometry layer to any mesh generator: a mesher consumes loops
sampled to polygons; the geometry layer owns the exact curve descriptions.
"""
from dataclasses import dataclass

from app.geometry.curves.base import ParametricCurve


@dataclass(frozen=True)
class BoundaryPiece:
    """One oriented segment of a boundary loop.

    The piece traverses its curve from t_min to t_max, or from t_max to
    t_min when ``reverse`` is True. Consecutive pieces of a loop must
    connect: each piece's end point is the next piece's start point.
    """

    curve: ParametricCurve
    reverse: bool = False

    @property
    def start_point(self) -> tuple[float, ...]:
        """First point of the piece in traversal order."""
        t = self.curve.t_max if self.reverse else self.curve.t_min
        return self.curve.point_at(t)

    @property
    def end_point(self) -> tuple[float, ...]:
        """Last point of the piece in traversal order."""
        t = self.curve.t_min if self.reverse else self.curve.t_max
        return self.curve.point_at(t)

    def sample_points(
        self,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> list[tuple[float, ...]]:
        """Sample the piece into an ordered list of points.

        Args:
            max_chord_error: Maximum curve-to-chord deviation (see
                ParametricCurve.sample_params).
            include: Parameter values that must be sampled exactly if they
                fall inside this piece's curve domain (values outside the
                domain are ignored, so a loop-wide list can be forwarded to
                every piece).

        Returns:
            Points in traversal order, including both endpoints.
        """
        params = self.curve.sample_params(max_chord_error, include=include)
        points = [self.curve.point_at(t) for t in params]
        if self.reverse:
            points.reverse()
        return points


@dataclass(frozen=True)
class BoundaryLoop:
    """A closed boundary: consecutive pieces connect, and the last piece's
    end point is the first piece's start point."""

    pieces: tuple[BoundaryPiece, ...]

    def sample_polygon(
        self,
        max_chord_error: float,
        include: tuple[float, ...] = (),
    ) -> list[tuple[float, float]]:
        """Sample the loop into a closed polygon.

        Junction points shared by consecutive pieces (and the loop-closing
        point) appear exactly once; the returned vertex list is implicitly
        closed (last vertex connects back to the first).

        Args:
            max_chord_error: Maximum curve-to-chord deviation.
            include: Parameter values forwarded to every piece (see
                BoundaryPiece.sample_points).

        Returns:
            Ordered polygon vertices, at least 3.
        """
        # Junctions between pieces coincide up to the numerical error of
        # the curve constructions (e.g. finite-difference normals), which
        # is many orders below any practical chord tolerance.
        join_tol = max_chord_error * 1e-3

        def same(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
            return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5 <= join_tol

        vertices: list[tuple[float, float]] = []
        for piece in self.pieces:
            pts = piece.sample_points(max_chord_error, include=include)
            if vertices and same(vertices[-1], pts[0]):
                pts = pts[1:]
            vertices.extend(pts)

        if len(vertices) > 1 and same(vertices[-1], vertices[0]):
            vertices.pop()

        if len(vertices) < 3:
            raise ValueError(
                f"Loop sampled to {len(vertices)} distinct vertices; "
                "a closed polygon needs at least 3"
            )
        return vertices

    def signed_area(self, max_chord_error: float) -> float:
        """Shoelace area of the sampled polygon.

        Positive for counter-clockwise loops, negative for clockwise.
        """
        poly = self.sample_polygon(max_chord_error)
        area = 0.0
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            area += x1 * y2 - x2 * y1
        return 0.5 * area
