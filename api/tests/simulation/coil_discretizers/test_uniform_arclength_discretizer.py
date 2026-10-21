"""
Tests for UniformArcLengthDiscretizer.

The discretizer's contract: interior slice boundaries sit EXACTLY on
integer-turn boundaries (located by the turn profile's exact inverse),
chosen nearest the uniform-arc-length targets, strictly increasing, spanning
[t_min, t_max]. Cutting on whole turns is what keeps the L/m segment
grouping and the C-matrix tent nodes coincident, and makes a grouping
collapse (slices outnumbering turns) impossible by construction.
"""
import pytest

from app.models.coil_models import (
    CurveSecondaryConductorSpec,
    LinearSecondaryConductorSpec,
)
from app.models.materials import Material
from app.models.turn_profiles import GradedTurns, UniformTurns
from app.geometry import CatmullRomSpline
from app.simulation.coil_discretizers.uniform_arclength_discretizer import (
    UniformArcLengthDiscretizer,
)


def _uniform_secondary(turns=100.0, length=10.0):
    return LinearSecondaryConductorSpec(
        material=Material.COPPER,
        turns=UniformTurns(turns),
        start=(1.0, 0.0),
        end=(1.0, length),
        wire_dia=0.02,
    )


def _graded_secondary():
    """Densely wound at the bottom (80 turns in the first fifth), sparse
    above (20 turns over the remaining four fifths)."""
    return LinearSecondaryConductorSpec(
        material=Material.COPPER,
        turns=GradedTurns(points=((0.0, 0.0), (0.2, 80.0), (1.0, 100.0))),
        start=(1.0, 0.0),
        end=(1.0, 10.0),
        wire_dia=0.02,
    )


def _spline_secondary():
    path = CatmullRomSpline(points=((2.0, 0.0), (2.6, 5.0), (2.0, 10.0)))
    return CurveSecondaryConductorSpec(
        material=Material.COPPER,
        turns=UniformTurns(60.0),
        wire_dia=0.02,
        path=path,
    )


class TestGetSlices:
    @pytest.mark.parametrize("order", [1, 2, 5, 30])
    def test_count_endpoints_and_monotonicity(self, order):
        sec = _uniform_secondary()
        slices = UniformArcLengthDiscretizer.get_slices(sec, order)
        assert len(slices) == order + 1
        assert slices[0] == sec.curve.t_min
        assert slices[-1] == sec.curve.t_max
        assert all(b > a for a, b in zip(slices[:-1], slices[1:]))

    def test_interior_boundaries_are_integer_turns(self):
        for sec in (_uniform_secondary(), _graded_secondary(), _spline_secondary()):
            slices = UniformArcLengthDiscretizer.get_slices(sec, 7)
            for t in slices[1:-1]:
                n = sec.turn_fxn(t)
                assert n == pytest.approx(round(n), abs=1e-9), (
                    f"interior slice at t={t} sits at fractional turn {n}"
                )

    def test_uniform_winding_gives_uniform_arc_length(self):
        """When the order divides the turn count, the turn-boundary snap
        lands exactly on the uniform-arc-length targets."""
        sec = _uniform_secondary(turns=100.0, length=10.0)
        slices = UniformArcLengthDiscretizer.get_slices(sec, 4)
        for a, b in zip(slices[:-1], slices[1:]):
            assert sec.curve.arc_length_between(a, b) == pytest.approx(2.5, abs=1e-9)

    def test_near_uniform_when_not_divisible(self):
        """Non-divisible turn counts snap to the nearest whole turn: slice
        lengths stay within half a turn pitch of uniform."""
        sec = _uniform_secondary(turns=10.0, length=10.0)
        order = 4
        pitch = 1.0  # length / turns
        slices = UniformArcLengthDiscretizer.get_slices(sec, order)
        target = 10.0 / order
        for a, b in zip(slices[:-1], slices[1:]):
            assert abs(sec.curve.arc_length_between(a, b) - target) <= 0.5 * pitch + 1e-9

    def test_graded_winding_slices_follow_arc_length_not_turns(self):
        """With 80% of turns in the first 20% of the height, uniform
        ARC-LENGTH targets put most slice boundaries in the dense band's
        complement - the discretizer divides the geometry, not the turns."""
        sec = _graded_secondary()
        slices = UniformArcLengthDiscretizer.get_slices(sec, 5)
        # Uniform arclength targets: 2, 4, 6, 8. Dense band ends at 2.0.
        interior = slices[1:-1]
        assert sum(1 for t in interior if t > 2.0) >= 3

    def test_order_exceeding_turns_rejected(self):
        sec = _uniform_secondary(turns=10.0)
        with pytest.raises(ValueError, match="exceeds the secondary's total turn count"):
            UniformArcLengthDiscretizer.get_slices(sec, 30)

    def test_order_equal_to_turns_gives_one_turn_per_slice(self):
        sec = _uniform_secondary(turns=10.0, length=10.0)
        slices = UniformArcLengthDiscretizer.get_slices(sec, 10)
        assert len(slices) == 11
        for k, t in enumerate(slices[:-1]):
            assert sec.turn_fxn(t) == pytest.approx(k, abs=1e-9)

    def test_grouping_matches_tent_nodes(self):
        """The whole point of the turn-boundary convention: the segment
        grouping derived from the slices is exact and has exactly one group
        per slice."""
        from app.simulation.distributed_element_matrices.turn_sampling import (
            secondary_turn_points,
            segment_start_indices,
        )
        for sec in (_uniform_secondary(turns=24.0), _graded_secondary()):
            order = 6
            slices = UniformArcLengthDiscretizer.get_slices(sec, order)
            pts = secondary_turn_points(sec)
            idx = segment_start_indices(sec, tuple(slices), len(pts))
            assert len(idx) == order
            assert idx[0] == 0
