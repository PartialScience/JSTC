"""
Simulation router: the two-tier design that lets a frontend re-analyze in
milliseconds after cheap parameter changes.

    POST /simulation/matrices    coil            -> matrix bundle   (slow: FEM)
    POST /simulation/analyze     coil [+ bundle]  -> full analysis   (fast)
    POST /simulation/impedance   coil [+ bundle]  -> Z(w) sweep      (fast)
    POST /simulation/spice       coil [+ bundle]  -> SPICE netlist   (fast)

The client obtains a bundle from /matrices, caches it, and passes it back
to the fast endpoints while tweaking non-geometry parameters. A bundle
that no longer matches the coil's geometry yields 409, signalling the
client to re-fetch matrices.
"""
from typing import Tuple

from fastapi import APIRouter, HTTPException

from app.converters import (
    bundle_from_schema,
    bundle_to_schema,
    build_analysis_response,
    coil_from_schema,
)
from app.schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    ImpedancePoint,
    ImpedanceRequest,
    ImpedanceResponse,
    MatricesRequest,
    MatrixBundleSchema,
    FieldRequest,
    FieldResponse,
    SpiceRequest,
    SpiceResponse,
)
from app.simulation.facade.simulation import TeslaCoilSimulation

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _wire(coil_schema, bundle_schema) -> Tuple[TeslaCoilSimulation, MatrixBundleSchema]:
    """Build a simulation, reusing the given bundle or computing one inline.

    Returns the wired simulation and the bundle schema to echo back.
    Raises 409 if a supplied bundle does not match the coil geometry.
    """
    coil = coil_from_schema(coil_schema)
    if bundle_schema is not None:
        try:
            sim = TeslaCoilSimulation(coil, matrices=bundle_from_schema(bundle_schema))
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return sim, bundle_schema
    sim = TeslaCoilSimulation(coil)
    return sim, bundle_to_schema(sim.compute_matrix_bundle())


def _require_coupled(sim) -> None:
    """422 when the coil cannot support a coupled solve (no primary/tank)."""
    primary = sim.coil.primary
    if primary is None or primary.tank_capacitance <= 0:
        raise HTTPException(
            status_code=422,
            detail="A coupled solve requires a primary with tank_capacitance > 0",
        )


@router.post("/matrices", response_model=MatrixBundleSchema)
def compute_matrices(request: MatricesRequest) -> MatrixBundleSchema:
    """Compute the geometric matrix bundle for a coil (runs the FEM solve).

    The slow call (~seconds). Cache the returned bundle on the client and
    pass it back to the fast endpoints to avoid recomputing while adjusting
    non-geometry parameters.
    """
    coil = coil_from_schema(request.coil)
    sim = TeslaCoilSimulation(coil)
    return bundle_to_schema(sim.compute_matrix_bundle())


@router.post("/analyze", response_model=AnalysisResponse)
def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    """Full JavaTC-style analysis plus the coupled solve (splitting)."""
    sim, bundle_schema = _wire(request.coil, request.bundle)
    return build_analysis_response(sim, bundle_schema)


@router.post("/impedance", response_model=ImpedanceResponse)
def impedance(request: ImpedanceRequest) -> ImpedanceResponse:
    """Primary driving-point impedance sweep with the secondary installed.

    The complex impedance looking into the primary tank terminals at each
    requested frequency - the coupled-system feature that shows the split
    resonances as peaks. Requires a primary tank capacitance.
    """
    sim, bundle_schema = _wire(request.coil, request.bundle)
    _require_coupled(sim)
    z = sim.coupled.primary_input_impedance(
        request.frequencies_hz,
        include_losses=request.include_losses,
        include_tank=request.include_tank,
    )
    points = [
        ImpedancePoint(
            frequency_hz=f,
            resistance=zi.real,
            reactance=zi.imag,
            magnitude=abs(zi),
        )
        for f, zi in zip(request.frequencies_hz, z)
    ]
    return ImpedanceResponse(points=points, bundle=bundle_schema)


@router.post("/spice", response_model=SpiceResponse)
def spice(request: SpiceRequest) -> SpiceResponse:
    """Export the coupled system as a SPICE subcircuit.

    A network reproducing the coupled model's AC/transient behavior, for
    dropping the coil into a larger SPICE schematic. Requires a primary
    tank capacitance.
    """
    sim, bundle_schema = _wire(request.coil, request.bundle)
    _require_coupled(sim)
    netlist = sim.coupled.spice_netlist(name=request.subcircuit_name)
    return SpiceResponse(netlist=netlist, bundle=bundle_schema)


@router.post("/field", response_model=FieldResponse)
def field(request: FieldRequest) -> FieldResponse:
    """Operating electric or magnetic field on a regular (r, z) grid.

    Superposes precomputed basis fields (cached by geometry) with the phasor
    drive at the requested frequency and primary current, so re-rendering a
    new drive is fast. Requires a primary with a tank capacitance.
    """
    import numpy as np

    sim, bundle_schema = _wire(request.coil, request.bundle)
    _require_coupled(sim)

    if request.field_type == "electric":
        result = sim.field.electric_field(
            nr=request.grid_nr,
            nz=request.grid_nz,
            frequency_hz=request.frequency_hz,
            primary_current=request.primary_current,
            reference_mode=request.reference_mode,
            hot_end=request.hot_end,
        )
        quantity = "potential [V]"
    else:
        result = sim.field.magnetic_field(
            nr=request.grid_nr,
            nz=request.grid_nz,
            frequency_hz=request.frequency_hz,
            primary_current=request.primary_current,
        )
        quantity = "vector_potential [T*m]"

    values = result.values.reshape(-1)
    real = np.where(np.isfinite(values.real), values.real, 0.0)
    imag = np.where(np.isfinite(values.imag), values.imag, 0.0)
    return FieldResponse(
        field_type=result.kind,
        quantity=quantity,
        nr=result.grid.nr,
        nz=result.grid.nz,
        r_min=result.grid.r_min,
        r_max=result.grid.r_max,
        z_min=result.grid.z_min,
        z_max=result.grid.z_max,
        unit_scale=result.unit_scale,
        real=real.tolist(),
        imag=imag.tolist(),
        mask=result.mask.reshape(-1).tolist(),
        bundle=bundle_schema,
    )
