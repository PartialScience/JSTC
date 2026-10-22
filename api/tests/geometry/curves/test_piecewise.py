"""
Unit tests for C1PiecewiseCurve.

The unit-speed and G1 properties (including across junctions) are covered
by the shared contract suite, which runs against the chain instances
registered below; this file tests the piecewise-specific behavior:
construction validation, propagation assembly, and parameter bookkeeping.
"""
import math

import pytest

from app.geometry import (
    ArcContinuation,
    C1PiecewiseCurve,
    CatmullRomSpline,
    CircularArc,
    LineContinuation,
    LineSegment,
    SplineContinuation,
)


def _line_arc_chain() -> C1PiecewiseCurve:
    """Vertical run into a rightward arc - the QCW-primary shape."""
    return C1PiecewiseCurve.from_continuations(
        LineSegment((2.0, 0.0), (2.0, 5.0)),
        [ArcContinuation(end=(4.0, 7.0))],
    )


def _full_chain() -> C1PiecewiseCurve:
    """Line -> arc -> line -> clamped spline: every continuation type."""
    return C1PiecewiseCurve.from_continuations(
        LineSegment((2.0, 0.0), (2.0, 5.0)),
        [
            ArcContinuation(end=(4.0, 7.0)),
            LineContinuation(length=2.0),
            SplineContinuation(points=((7.0, 8.0), (8.0, 6.0))),
        ],
    )


# Registered into the unit-speed contract suite via conftest.py
PIECEWISE_INSTANCES = [
    pytest.param(_line_arc_chain(), id="piecewise-line-arc"),
    pytest.param(_full_chain(), id="piecewise-all-continuations"),
]

# A clamped-start spline on its own must satisfy the curve contract too
CLAMPED_SPLINE_INSTANCES = [
    pytest.param(
        CatmullRomSpline(
            points=((2.0, 0.0), (3.0, 2.0), (2.5, 4.0)),
            start_tangent=(0.0, 1.0),
        ),
        id="spline-clamped-start",
    ),
]


class TestConstruction:
    def test_requires_at_least_one_piece(self):
        with pytest.raises(ValueError, match="at least one piece"):
            C1PiecewiseCurve(pieces=())

    def test_rejects_c0_violation(self):
        with pytest.raises(ValueError, match="C0"):
            C1PiecewiseCurve(pieces=(
                LineSegment((0.0, 0.0), (1.0, 0.0)),
                LineSegment((2.0, 0.0), (3.0, 0.0)),  # gap
            ))

    def test_rejects_kink(self):
        with pytest.raises(ValueError, match="C1"):
            C1PiecewiseCurve(pieces=(
                LineSegment((0.0, 0.0), (1.0, 0.0)),
                LineSegment((1.0, 0.0), (1.0, 1.0)),  # 90 degree corner
            ))

    def test_rejects_reversal(self):
        with pytest.raises(ValueError, match="C1"):
            C1PiecewiseCurve(pieces=(
                LineSegment((0.0, 0.0), (1.0, 0.0)),
                LineSegment((1.0, 0.0), (0.0, 0.0)),  # doubles straight back
            ))

    def test_rejects_nesting(self):
        with pytest.raises(TypeError, match="flatten"):
            C1PiecewiseCurve(pieces=(_line_arc_chain(),))

    def test_accepts_hand_assembled_smooth_pieces(self):
        """Validation passes genuinely smooth hand-built chains - the
        constructor checks invariants, it does not require continuations."""
        line = LineSegment((2.0, 0.0), (2.0, 5.0))
        arc = CircularArc(center=(4.0, 5.0), radius=2.0, angle_start=math.pi, angle_end=math.pi / 2)
        chain = C1PiecewiseCurve(pieces=(line, arc))
        assert chain.length == pytest.approx(5.0 + 2.0 * math.pi / 2)

    def test_structural_equality(self):
        assert _full_chain() == _full_chain()
        assert hash(_full_chain()) == hash(_full_chain())
        assert _full_chain() != _line_arc_chain()


class TestParameterization:
    def test_domain_is_total_arc_length(self):
        chain = _line_arc_chain()
        assert chain.t_min == 0.0
        assert chain.t_max == pytest.approx(sum(p.length for p in chain.pieces))

    def test_pieces_cover_their_subintervals(self):
        chain = _full_chain()
        s = 0.0
        for piece in chain.pieces:
            p_chain = chain.point_at(s + 0.5 * piece.length)
            p_piece = piece.point_at(piece.t_min + 0.5 * piece.length)
            assert p_chain == pytest.approx(p_piece, abs=1e-12)
            s += piece.length

    def test_junction_evaluates_consistently_from_both_sides(self):
        chain = _full_chain()
        s = chain.pieces[0].length
        below = chain.point_at(s - 1e-12)
        above = chain.point_at(s + 1e-12)
        assert below == pytest.approx(above, abs=1e-9)

    def test_includes_land_inside_the_owning_piece(self):
        chain = _full_chain()
        want = (chain.pieces[0].length / 2, chain.pieces[0].length + 0.3)
        params = chain.sample_params(0.05 * chain.length, include=want)
        for w in want:
            assert any(abs(p - w) < 1e-12 for p in params)


class TestCanonical:
    def test_nests_piece_canonicals(self):
        tag, pieces = _line_arc_chain().canonical()
        assert tag == "piecewise"
        assert pieces[0][0] == "line"
        assert pieces[1][0] == "arc"
