"""
Builds an AnalysisResponse from a wired TeslaCoilSimulation.
"""
import numpy as np

from app.schemas.analysis_schemas import (
    AnalysisResponse,
    CoupledOutputs,
    CouplingOutputs,
    EigenModesOutputs,
    PrimaryOutputs,
    SecondaryOutputs,
)
from app.schemas.matrix_schemas import MatrixBundleSchema


def _optional(fn):
    """Return fn() or None if it raises ValueError (e.g. a tank-frequency
    quantity requested on a primary with no tank capacitance)."""
    try:
        return fn()
    except ValueError:
        return None


def _secondary_outputs(sec) -> SecondaryOutputs:
    return SecondaryOutputs(
        resonant_frequency=sec.resonant_frequency,
        eigen_frequencies=list(sec.eigen_frequencies),
        dc_inductance=sec.dc_inductance,
        effective_series_inductance=sec.effective_series_inductance,
        energy_inductance=sec.energy_inductance,
        dc_capacitance=sec.dc_capacitance,
        effective_shunt_capacitance=sec.effective_shunt_capacitance,
        energy_capacitance=sec.energy_capacitance,
        topload_effective_capacitance=sec.topload_effective_capacitance,
        winding_length=sec.winding_length,
        conductor_length=sec.conductor_length,
        coil_pitch=sec.coil_pitch,
        turns_per_length=sec.turns_per_length,
        turn_spacing=sec.turn_spacing,
        mean_diameter=sec.mean_diameter,
        aspect_ratio=sec.aspect_ratio,
        inclination_degrees=sec.inclination_degrees,
        reactance_at_resonance=sec.reactance_at_resonance,
        skin_depth=sec.skin_depth,
        dc_resistance=sec.dc_resistance,
        ac_resistance=sec.ac_resistance,
        quality_factor=sec.quality_factor,
        wire_weight=sec.wire_weight,
    )


def _modes_outputs(sec) -> EigenModesOutputs:
    """The voltage/current eigenmode shapes, plot- and export-ready.

    Each row of ``voltage_eigen_modes`` is one mode's reduced nodal voltages
    (t_1..t_N, the grounded base t_0 dropped); ``current_eigen_modes`` gives
    the matching segment currents. The eigenvector sign is arbitrary, so we
    fix it per mode to make the top-node voltage positive (matching the
    fundamental-mode convention used for Les/Cee) - otherwise a mode would
    flip sign between runs. Amplitudes are otherwise left raw (unnormalized).
    """
    V = np.array(sec.voltage_eigen_modes, dtype=float)  # (M, N)
    I = np.array(sec.current_eigen_modes, dtype=float)  # (M, N)
    signs = np.where(V[:, -1] < 0, -1.0, 1.0)
    V = V * signs[:, None]
    I = I * signs[:, None]

    # Physical node positions: arc length (m) along the winding from the base.
    # The voltage profile prepends the grounded base node (0 V at s=0), so it
    # rides the full N+1 node arc lengths; currents sit at the segment
    # midpoints, i.e. between consecutive node arc lengths.
    node_s = np.array(sec.node_arclengths, dtype=float)  # length N+1
    voltage_positions = node_s.tolist()
    voltage_modes = [[0.0, *row] for row in V.tolist()]
    current_positions = ((node_s[:-1] + node_s[1:]) / 2.0).tolist()
    current_modes = I.tolist()

    return EigenModesOutputs(
        frequencies=list(sec.eigen_frequencies),
        voltage_positions=voltage_positions,
        current_positions=current_positions,
        voltage_modes=voltage_modes,
        current_modes=current_modes,
    )


def _primary_outputs(primary) -> PrimaryOutputs:
    return PrimaryOutputs(
        dc_inductance=primary.dc_inductance,
        lead_inductance=primary.lead_inductance,
        total_inductance=primary.total_inductance,
        resonant_frequency=_optional(lambda: primary.resonant_frequency),
        percent_detuned=_optional(lambda: primary.percent_detuned),
        wire_length=primary.wire_length,
        coil_pitch=primary.coil_pitch,
        turn_spacing=primary.turn_spacing,
        dc_resistance=primary.dc_resistance,
    )


def _coupling_outputs(coupling) -> CouplingOutputs:
    return CouplingOutputs(
        mutual_inductance=coupling.mutual_inductance,
        coupling_coefficient=coupling.coupling_coefficient,
        half_cycles_for_energy_transfer=coupling.half_cycles_for_energy_transfer,
        energy_transfer_time=_optional(lambda: coupling.energy_transfer_time),
    )


def _coupled_outputs(coupled) -> CoupledOutputs:
    modes = coupled.mode_frequencies
    lo, hi = coupled.split_frequencies
    return CoupledOutputs(
        mode_frequencies=list(modes),
        split_lower=lo,
        split_upper=hi,
        frequency_split=hi - lo,
    )


def build_analysis_response(sim, bundle_schema: MatrixBundleSchema) -> AnalysisResponse:
    """Assemble the full analysis response from a wired simulation.

    primary/coupling are null for a coil with no primary; coupled is null
    without a primary tank capacitance (the coupled solve needs it).
    """
    has_primary = sim.coil.primary is not None
    coupled = None
    if has_primary:
        coupled = _optional(lambda: _coupled_outputs(sim.coupled))
    return AnalysisResponse(
        secondary=_secondary_outputs(sim.secondary),
        modes=_modes_outputs(sim.secondary),
        primary=_primary_outputs(sim.primary) if has_primary else None,
        coupling=_coupling_outputs(sim.coupling) if has_primary else None,
        coupled=coupled,
        bundle=bundle_schema,
    )
