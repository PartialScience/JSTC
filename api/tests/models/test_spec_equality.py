"""
Structural equality/hashing of the winding specs.

The solvers' lru_caches key on the frozen spec dataclasses, so two specs
built from identical inputs must be equal and hash equal. Derived geometry
(the offset region) compares by identity and is therefore excluded from the
dataclass comparison; these tests pin that contract so a future field can't
silently reintroduce identity semantics and defeat the caches.
"""
from app.models.coil_models import (
    LinearSecondaryConductorSpec,
    SecondaryConductorSegment,
)
from app.models.materials import Material
from app.models.turn_profiles import UniformTurns


def _make_secondary():
    return LinearSecondaryConductorSpec(
        material=Material.COPPER,
        turns=UniformTurns(100),
        start=(1.0, 0.0),
        end=(1.0, 10.0),
        wire_dia=0.05,
    )


def test_identical_secondaries_are_equal_and_hash_equal():
    a, b = _make_secondary(), _make_secondary()
    assert a == b
    assert hash(a) == hash(b)


def test_different_secondaries_are_unequal():
    a = _make_secondary()
    b = LinearSecondaryConductorSpec(
        material=Material.COPPER,
        turns=UniformTurns(100),
        start=(1.0, 0.0),
        end=(1.0, 11.0),  # different end point
        wire_dia=0.05,
    )
    assert a != b


def test_identical_segments_are_equal_and_hash_equal():
    seg_a = SecondaryConductorSegment(
        material=Material.COPPER,
        full_secondary=_make_secondary(),
        t1=0.25,
        t2=0.5,
        flatten_start=True,
        flatten_end=True,
    )
    seg_b = SecondaryConductorSegment(
        material=Material.COPPER,
        full_secondary=_make_secondary(),
        t1=0.25,
        t2=0.5,
        flatten_start=True,
        flatten_end=True,
    )
    assert seg_a == seg_b
    assert hash(seg_a) == hash(seg_b)
