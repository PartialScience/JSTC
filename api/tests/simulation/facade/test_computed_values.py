"""
Gating of assumption-bound outputs (Rac via Medhurst) and reason chaining.
"""
import pytest

from app.converters.analysis_converters import _computed
from app.geometry import CatmullRomSpline
from app.models.coil_models import (
    CurveSecondaryConductorSpec,
    LinearSecondaryConductorSpec,
)
from app.models.materials import Material
from app.models.simulation_models import SimulatableTeslaCoil
from app.models.turn_profiles import GradedTurns, UniformTurns
from app.simulation.facade.simulation import TeslaCoilSimulation
from app.simulation.types import NotComputable


def _sim(secondary):
    return TeslaCoilSimulation(SimulatableTeslaCoil(
        secondary=secondary,
        r_max=30.0,
        z_max=30.0,
        discretization_order=5,
    ))


def _solenoid(turns=UniformTurns(100.0)):
    return LinearSecondaryConductorSpec(
        material=Material.COPPER,
        turns=turns,
        start=(1.0, 0.0),
        end=(1.0, 10.0),
        wire_dia=0.02,
    )


def _spline_secondary():
    return CurveSecondaryConductorSpec(
        material=Material.COPPER,
        turns=UniformTurns(60.0),
        wire_dia=0.02,
        path=CatmullRomSpline(points=((2.0, 0.0), (2.6, 5.0), (2.0, 10.0))),
    )


def test_solenoid_rac_computed():
    sec = _sim(_solenoid()).secondary
    assert sec.ac_resistance > sec.dc_resistance
    assert sec.quality_factor > 0


def test_graded_solenoid_rac_not_computable():
    turns = GradedTurns(points=((0.0, 0.0), (0.5, 80.0), (1.0, 100.0)))
    sec = _sim(_solenoid(turns)).secondary
    with pytest.raises(NotComputable, match="uniform cylindrical solenoids"):
        _ = sec.ac_resistance


def test_spline_path_rac_not_computable_and_q_chains_reason():
    sec = _sim(_spline_secondary()).secondary
    with pytest.raises(NotComputable):
        _ = sec.ac_resistance
    with pytest.raises(NotComputable, match="depends on Rac"):
        _ = sec.quality_factor


def test_drive_resistance_falls_back_without_proximity():
    """Field/impedance solves still get a finite loss for parametric
    windings: Rdc x skin factor, proximity omitted."""
    sec = _sim(_spline_secondary()).secondary
    assert sec.drive_resistance >= sec.dc_resistance
    # And for a solenoid the drive resistance IS Rac
    sol = _sim(_solenoid()).secondary
    assert sol.drive_resistance == sol.ac_resistance


def test_computed_helper_reports_reasons():
    ok = _computed(lambda: 42.0)
    assert ok.value == 42.0 and ok.reason is None

    def boom():
        raise NotComputable("because physics")
    missing = _computed(boom)
    assert missing.value is None
    assert missing.reason == "because physics"
