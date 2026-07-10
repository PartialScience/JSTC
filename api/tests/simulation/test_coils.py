"""
Test coil definitions for simulation tests.

Each entry defines a complete SimulatableTeslaCoil (minus discretization_order,
which is varied independently).  To add a new test case, append a
``pytest.param`` to ``TEST_COILS``.

The ``coil`` fixture in conftest.py consumes this list, so every coil is
automatically cross-produced with every discretization order and every solver.
"""
import pytest
from app.models.coil_models import (
    LinearPrimarySpec,
    LinearSecondaryConductorSpec,
    ToploadSpec,
)
from app.models.materials import Material
from app.models.turn_profiles import UniformTurnProfile
from app.geometry import Circle, CircularCrossSection, Rectangle


# ---------------------------------------------------------------------------
# Test coil configurations
#
# Each dict maps directly to SimulatableTeslaCoil constructor kwargs.
# ``discretization_order`` is intentionally omitted — it is injected by the
# fixture so that each coil is tested at multiple resolutions.
# ---------------------------------------------------------------------------

# The JavaTC example coil, as specified in docs/JavaTC Example Coil.txt.
# All dimensions in inches (unit_scale=0.0254).
#
# Topload: a toroid (minor dia 6.25, major OUTSIDE dia 21 -> tube radius
# 3.125 at centerline radius (21 - 6.25)/2 = 7.375) plus a disc
# (r = 0..8.25) at the same height. The disc is ideal (zero thickness) in
# JavaTC; here it is a 1/16 in plate, and its inner edge overshoots the
# axis slightly so the mesher's boolean cut trims it cleanly at r = 0.
#
# Primary: 8.438 turns of 0.25 in round conductor, r = 3.75 -> 7.969 at
# z = 23 (flat spiral). The PrimarySpec derives the axisymmetric
# representations the solvers consume: grounded cross-section rings for
# electrostatics (the primary sits near ground potential at
# secondary-resonance timescales - standard TSSP/JavaTC assumption) and
# coaxial rings for magnetics. Tank cap 0.0188 uF and 30 in of 0.2 in
# lead complete the primary resonant circuit.
_DISC_HALF_THICKNESS = 0.03125
JAVATC_EXAMPLE_COIL = dict(
    secondary=LinearSecondaryConductorSpec(
        material=Material.COPPER,
        turn_fxn=UniformTurnProfile(895),
        start=(2.26925, 23.0),
        end=(2.26925, 44.8085),
        wire_dia=0.020101,
    ),
    toploads=(
        ToploadSpec(
            material=Material.ALUMINUM,
            shape=Circle(center=(7.375, 48.8085), radius=3.125),
        ),
        ToploadSpec(
            material=Material.ALUMINUM,
            shape=Rectangle(vertices=(
                (-0.05, 48.8085 - _DISC_HALF_THICKNESS),
                (8.25, 48.8085 - _DISC_HALF_THICKNESS),
                (8.25, 48.8085 + _DISC_HALF_THICKNESS),
                (-0.05, 48.8085 + _DISC_HALF_THICKNESS),
            )),
        ),
    ),
    grounds=(),
    primary=LinearPrimarySpec(
        material=Material.COPPER,
        turn_fxn=UniformTurnProfile(8.438),
        cross_section=CircularCrossSection(diameter=0.25),
        tank_capacitance=0.0188e-6,
        lead_length=30.0,
        lead_dia=0.2,
        start=(3.75, 23.0),
        end=(7.969, 23.0),
    ),
    r_max=100,
    z_max=150,
    unit_scale=0.0254,
)

TEST_COILS = [
    pytest.param(JAVATC_EXAMPLE_COIL, id="javatc-example-coil"),
]
