"""
Pydantic schemas for simulation requests and the analysis response.

Two endpoints, two request shapes:

  * MatricesRequest (coil only) -> MatrixBundleSchema  [slow: FEM solve]
  * AnalyzeRequest (coil + bundle) -> AnalysisResponse  [fast: linear algebra]

All response quantities are SI (Hz, H, F, Ohm, m, kg, s, degrees).
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from .coil_schemas import SimulatableTeslaCoilSchema
from .matrix_schemas import MatrixBundleSchema


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class MatricesRequest(BaseModel):
    """Request the geometric matrix bundle for a coil (the slow FEM path)."""
    coil: SimulatableTeslaCoilSchema


class AnalyzeRequest(BaseModel):
    """Request a full analysis, reusing a precomputed matrix bundle.

    The bundle must match the coil's geometry (its geometry_fingerprint is
    validated); a mismatch returns 409. Omit the bundle to have the server
    compute it inline (equivalent to calling the matrices endpoint first,
    but without returning the bundle to the client)."""
    coil: SimulatableTeslaCoilSchema
    bundle: Optional[MatrixBundleSchema] = None


# ---------------------------------------------------------------------------
# Response sections
# ---------------------------------------------------------------------------

class SecondaryOutputs(BaseModel):
    resonant_frequency: float
    eigen_frequencies: List[float]

    dc_inductance: float
    effective_series_inductance: float
    energy_inductance: float

    dc_capacitance: float
    effective_shunt_capacitance: float
    energy_capacitance: float
    topload_effective_capacitance: float

    winding_length: float
    conductor_length: float
    coil_pitch: float
    turns_per_length: float
    turn_spacing: float
    mean_diameter: float
    aspect_ratio: float
    inclination_degrees: float

    reactance_at_resonance: float
    skin_depth: float
    dc_resistance: float
    ac_resistance: float
    quality_factor: float
    wire_weight: float


class EigenModesOutputs(BaseModel):
    """The secondary's transmission-line eigenmodes: for every eigenfrequency,
    the voltage mode shape (nodal voltages along the winding) and the current
    mode shape (segment currents).

    Amplitudes are the raw eigenvector values (arbitrary overall scale), with
    only the physically-arbitrary eigenvector SIGN fixed to a convention
    (top-node voltage positive) so a mode does not flip between analyses.
    Positions are arc length in meters along the winding centerline, measured
    from the grounded base (0) to the top terminal (``winding_length``).

    The voltage profile includes the grounded base node (value 0 at arc length
    0), so ``voltage_positions`` has one more entry than ``current_positions``.
    """
    frequencies: List[float] = Field(
        ..., description="Eigenfrequencies (Hz), ascending; one per mode"
    )
    voltage_positions: List[float] = Field(
        ..., description="Arc length (m) along the winding for each voltage node"
    )
    current_positions: List[float] = Field(
        ..., description="Arc length (m) along the winding for each current segment"
    )
    voltage_modes: List[List[float]] = Field(
        ..., description="Per-mode nodal voltage shape (len == len(voltage_positions))"
    )
    current_modes: List[List[float]] = Field(
        ..., description="Per-mode segment current shape (len == len(current_positions))"
    )


class PrimaryOutputs(BaseModel):
    dc_inductance: float
    lead_inductance: float
    total_inductance: float
    resonant_frequency: Optional[float] = Field(
        None, description="Null when no tank capacitance is specified"
    )
    percent_detuned: Optional[float] = None
    wire_length: float
    coil_pitch: float
    turn_spacing: float
    dc_resistance: float


class CouplingOutputs(BaseModel):
    mutual_inductance: float
    coupling_coefficient: float
    half_cycles_for_energy_transfer: float
    energy_transfer_time: Optional[float] = Field(
        None, description="Null when the primary tank frequency is undefined"
    )


class CoupledOutputs(BaseModel):
    """Full coupled primary-secondary solve. Present only when the primary
    has a tank capacitance."""
    mode_frequencies: List[float] = Field(
        ..., description="Coupled resonant frequencies (Hz), ascending"
    )
    split_lower: float = Field(..., description="Lower split-pair frequency (Hz)")
    split_upper: float = Field(..., description="Upper split-pair frequency (Hz)")
    frequency_split: float = Field(..., description="Upper - lower (Hz)")


class AnalysisResponse(BaseModel):
    """Full JavaTC-style analysis. primary/coupling are null for a coil
    with no primary; coupled is null without a primary tank capacitance."""
    secondary: SecondaryOutputs
    modes: EigenModesOutputs = Field(
        ..., description="Voltage and current eigenmode shapes of the secondary"
    )
    primary: Optional[PrimaryOutputs] = None
    coupling: Optional[CouplingOutputs] = None
    coupled: Optional[CoupledOutputs] = None
    bundle: MatrixBundleSchema = Field(
        ..., description="The matrix bundle used (echo it back to reuse)"
    )


# ---------------------------------------------------------------------------
# Impedance sweep
# ---------------------------------------------------------------------------

class ImpedanceRequest(BaseModel):
    """Primary driving-point impedance sweep with the secondary installed.

    Reuses a matrix bundle (fast). Requires a primary tank capacitance.
    """
    coil: SimulatableTeslaCoilSchema
    bundle: Optional[MatrixBundleSchema] = None
    frequencies_hz: List[float] = Field(
        ..., min_length=1, description="Frequencies to evaluate (Hz)"
    )
    include_losses: bool = Field(
        False, description="Use AC/DC resistances so peaks are finite"
    )
    include_tank: bool = Field(
        True, description="Include the series tank capacitor (full LC input)"
    )


class ImpedancePoint(BaseModel):
    frequency_hz: float
    resistance: float = Field(..., description="Re(Z) [Ohm]")
    reactance: float = Field(..., description="Im(Z) [Ohm]")
    magnitude: float = Field(..., description="|Z| [Ohm]")


class ImpedanceResponse(BaseModel):
    points: List[ImpedancePoint]
    bundle: MatrixBundleSchema


# ---------------------------------------------------------------------------
# SPICE export
# ---------------------------------------------------------------------------

class SpiceRequest(BaseModel):
    """Export the coupled system as a SPICE subcircuit. Reuses a bundle."""
    coil: SimulatableTeslaCoilSchema
    bundle: Optional[MatrixBundleSchema] = None
    subcircuit_name: str = Field("teslacoil", description="SPICE .subckt name")


class SpiceResponse(BaseModel):
    netlist: str = Field(..., description="SPICE subcircuit text")
    bundle: MatrixBundleSchema


# ---------------------------------------------------------------------------
# Field visualization
# ---------------------------------------------------------------------------

class FieldRequest(BaseModel):
    """Operating electric or magnetic field on a regular (r, z) grid.

    Reuses a matrix bundle for the drive solve; the basis fields are cached
    server-side by geometry, so changing the drive re-renders fast. Requires
    a primary with a tank capacitance.
    """
    coil: SimulatableTeslaCoilSchema
    bundle: Optional[MatrixBundleSchema] = None
    field_type: Literal["electric", "magnetic"] = Field(
        "electric", description="Which field to compute"
    )
    frequency_hz: float = Field(..., gt=0, description="Sinusoidal drive frequency")
    primary_current: float = Field(
        1.0, description="Primary current magnitude [A] (drive amplitude)"
    )
    reference_mode: Literal["floating", "grounded"] = Field(
        "floating", description="Primary common-mode reference (E-field only)"
    )
    hot_end: Literal["inner", "outer"] = Field(
        "outer", description="Which primary end carries V_p (E-field only)"
    )
    grid_nr: int = Field(120, ge=8, le=400, description="Grid samples across r")
    grid_nz: int = Field(180, ge=8, le=600, description="Grid samples across z")


class FieldResponse(BaseModel):
    """A complex field sampled on a regular grid, row-major (z outer, r
    inner). The client reshapes ``real``/``imag`` to (nz, nr) and takes the
    gradient/curl (using unit_scale for metres) for E or B."""
    field_type: Literal["electric", "magnetic"]
    quantity: str = Field(
        ..., description="'potential [V]' (E) or 'vector_potential [T*m]' (B)"
    )
    nr: int
    nz: int
    r_min: float
    r_max: float
    z_min: float
    z_max: float
    unit_scale: float = Field(..., description="Metres per coil unit")
    real: List[float] = Field(..., description="Re(field), nr*nz row-major")
    imag: List[float] = Field(..., description="Im(field), nr*nz row-major")
    mask: List[bool] = Field(..., description="True where the field is defined")
    bundle: MatrixBundleSchema
