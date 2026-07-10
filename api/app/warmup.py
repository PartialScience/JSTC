"""
One-time warmup of the expensive native/JIT machinery.

The first FEM analysis in a fresh process pays a large one-off cost: Numba
compiles the inductance kernels, and MKL/gmsh/MFEM initialize. Running a
tiny throwaway solve at startup moves that cost off the first *real* request
- important behind a scale-to-zero host (Cloud Run / Fly), where every cold
start would otherwise hand a ~several-second first response to a user.
"""
from __future__ import annotations

import time


def run_warmup() -> float:
    """Run a minimal end-to-end analysis to trigger all lazy initialization.

    Returns the wall-clock seconds taken (for logging). Safe to call once at
    process startup; never raises out (a warmup failure must not stop the
    server from booting).
    """
    start = time.perf_counter()
    try:
        from app.models.coil_models import LinearSecondaryConductorSpec
        from app.models.materials import Material
        from app.models.simulation_models import SimulatableTeslaCoil
        from app.models.turn_profiles import UniformTurnProfile
        from app.simulation.facade.simulation import TeslaCoilSimulation

        # A trivially small coil: a short solenoid in a small domain at low
        # discretization order - exercises meshing, the FEM capacitance
        # solve (gmsh + MFEM + PARDISO) and the Numba inductance kernels.
        coil = SimulatableTeslaCoil(
            secondary=LinearSecondaryConductorSpec(
                material=Material.COPPER,
                turn_fxn=UniformTurnProfile(50),
                start=(1.0, 0.0),
                end=(1.0, 10.0),
                wire_dia=0.1,
            ),
            r_max=30.0,
            z_max=30.0,
            discretization_order=4,
            unit_scale=0.0254,
        )
        sim = TeslaCoilSimulation(coil)
        # Touch the full chain: capacitance (FEM), inductance (Numba), eigen.
        _ = sim.secondary.resonant_frequency
    except Exception:  # noqa: BLE001 - warmup must never block boot
        return -1.0
    return time.perf_counter() - start
