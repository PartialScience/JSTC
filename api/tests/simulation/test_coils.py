"""
Test coil definitions for simulation tests.

Each entry defines a complete SimulatableTeslaCoil (minus discretization_order,
which is varied independently).  To add a new test case, append a
``pytest.param`` to ``TEST_COILS``.

The ``coil`` fixture in conftest.py consumes this list, so every coil is
automatically cross-produced with every discretization order and every solver.
"""
import pytest
from app.models.coil_models import LinearSecondaryConductorSpec, ToploadSpec, GroundedConductorSpec
from app.models.materials import Material
from app.geometry import Circle, Rectangle


# ---------------------------------------------------------------------------
# Test coil configurations
#
# Each dict maps directly to SimulatableTeslaCoil constructor kwargs.
# ``discretization_order`` is intentionally omitted — it is injected by the
# fixture so that each coil is tested at multiple resolutions.
# ---------------------------------------------------------------------------

# TODO: Add more test coils

TEST_COILS = [
    pytest.param(
        dict(
            secondary=LinearSecondaryConductorSpec(
                material=Material.COPPER,
                turn_fxn=lambda t: 895 * t,
                start=(2.26925, 23.0),
                end=(2.26925, 44.8085),
                wire_dia=0.020101,
            ),
            toploads=(
                ToploadSpec(material=Material.ALUMINUM, shape=Circle(center=(10.5, 48.8085), radius=3.125)),),
            grounds=(),
            r_max=100,
            z_max=150,
        ),
        id="javatc-example-coil",
    ),
]
