"""
Wire-length weighting of the secondary's series resistance.

Equal arc-length slices hold different amounts of wire whenever the turn
density is nonuniform, so the per-segment resistances must follow each
segment's share of the WIRE length, not a uniform Rs/N split.
"""
import numpy as np
import pytest

from app.models.coil_models import LinearSecondaryConductorSpec
from app.models.materials import Material
from app.models.simulation_models import SimulatableTeslaCoil
from app.models.turn_profiles import GradedTurns, UniformTurns
from app.simulation.coupled.coupled_system import _segment_resistances
from app.simulation.facade.simulation import TeslaCoilSimulation


def _sim(turns):
    coil = SimulatableTeslaCoil(
        secondary=LinearSecondaryConductorSpec(
            material=Material.COPPER,
            turns=turns,
            start=(1.0, 0.0),
            end=(1.0, 10.0),
            wire_dia=0.02,
        ),
        r_max=30.0,
        z_max=30.0,
        discretization_order=5,
    )
    return TeslaCoilSimulation(coil)


def test_uniform_winding_gives_uniform_fractions():
    fractions = _sim(UniformTurns(100.0)).secondary.segment_wire_length_fractions
    assert len(fractions) == 5
    assert sum(fractions) == pytest.approx(1.0)
    for f in fractions:
        assert f == pytest.approx(0.2, rel=1e-3)


def test_graded_winding_front_loads_the_resistance():
    """80 of 100 turns in the bottom fifth: the first segment holds most of
    the wire, so it must carry most of the resistance."""
    turns = GradedTurns(points=((0.0, 0.0), (0.2, 80.0), (1.0, 100.0)))
    fractions = _sim(turns).secondary.segment_wire_length_fractions
    assert sum(fractions) == pytest.approx(1.0)
    assert fractions[0] > 0.5
    assert fractions[0] > 3 * fractions[-1]


def test_segment_resistances_helper():
    assert np.allclose(_segment_resistances(10.0, 4, None), 2.5)
    w = np.array([0.4, 0.3, 0.2, 0.1])
    assert np.allclose(_segment_resistances(10.0, 4, w), 10.0 * w)
    with pytest.raises(ValueError):
        _segment_resistances(10.0, 4, np.array([0.5, 0.5]))
    with pytest.raises(ValueError):
        _segment_resistances(10.0, 2, np.array([0.7, 0.6]))
