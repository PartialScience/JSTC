"""
Unit tests for the PrimarySpec model and its derived representations.
"""
import pytest

from app.geometry import Circle, CircularCrossSection
from app.models.coil_models import LinearPrimarySpec
from app.models.materials import Material
from app.models.turn_profiles import UniformTurnProfile


def _javatc_primary(**overrides):
    kwargs = dict(
        material=Material.COPPER,
        turn_fxn=UniformTurnProfile(8.438),
        cross_section=CircularCrossSection(diameter=0.25),
        tank_capacitance=0.0188e-6,
        lead_length=30.0,
        lead_dia=0.2,
        start=(3.75, 23.0),
        end=(7.969, 23.0),
    )
    kwargs.update(overrides)
    return LinearPrimarySpec(**kwargs)


class TestPrimarySpec:
    def test_total_turns_preserves_fraction(self):
        assert _javatc_primary().total_turns == pytest.approx(8.438)

    def test_one_ring_per_turn_including_fractional(self):
        assert len(_javatc_primary().ring_centers()) == 9

    def test_rings_at_turn_midpoints(self):
        """Uniform flat spiral 3.75 -> 7.969 over 8.438 turns: pitch
        0.5/turn, so turn k's ring sits at 3.75 + (k + 0.5) * 0.5 and the
        fractional last turn at the midpoint of [8, 8.438] turns."""
        centers = _javatc_primary().ring_centers()
        pitch = (7.969 - 3.75) / 8.438
        for k in range(8):
            r, z = centers[k]
            assert r == pytest.approx(3.75 + (k + 0.5) * pitch, abs=1e-6)
            assert z == pytest.approx(23.0)
        r_last, _ = centers[8]
        assert r_last == pytest.approx(3.75 + ((8 + 8.438) / 2) * pitch / 8.438 * 8.438, abs=1e-3)

    def test_ring_regions_are_cross_sections(self):
        regions = _javatc_primary().ring_regions()
        assert len(regions) == 9
        assert all(isinstance(r, Circle) for r in regions)
        assert all(r.radius == pytest.approx(0.125) for r in regions)

    def test_vertical_helical_primary(self):
        """The same spec type expresses a helical (vertical) primary."""
        helical = _javatc_primary(start=(4.0, 20.0), end=(4.0, 26.0),
                                  turn_fxn=UniformTurnProfile(6))
        centers = helical.ring_centers()
        assert len(centers) == 6
        assert all(r == pytest.approx(4.0) for r, _ in centers)
        assert centers[0][1] == pytest.approx(20.5)

    def test_rejects_degenerate_curve(self):
        with pytest.raises(ValueError):
            _javatc_primary(start=(4.0, 23.0), end=(4.0, 23.0))

    def test_hashable_for_solver_caching(self):
        assert hash(_javatc_primary()) is not None
