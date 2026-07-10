"""
Pydantic schema for the geometric matrix bundle.

This is the artifact a client caches and passes back to skip the expensive
FEM re-solve. It maps 1:1 to app.simulation.facade.matrices.
GeometricMatrixBundle.
"""
from typing import List

from pydantic import BaseModel, Field


class MatrixBundleSchema(BaseModel):
    """Geometry-only matrices (geometric units) plus their provenance.

    Treat this as an opaque token on the client: obtain it from the
    matrices endpoint, cache it, and send it back to the analyze endpoint.
    The geometry_fingerprint guards against applying it to a coil whose
    geometry has changed.
    """
    nodal_capacitance: List[List[float]] = Field(
        ..., description="(N+1)x(N+1) geometric nodal capacitance matrix"
    )
    topload_charge: List[float] = Field(
        ..., description="Length-(N+1) geometric topload charge per tent solve"
    )
    inductance: List[List[float]] = Field(
        ..., description="NxN geometric segment inductance matrix"
    )
    coupling: List[float] = Field(
        ..., description="Length-N geometric coupling vector (empty if no primary)"
    )
    discretization_order: int = Field(..., description="N")
    geometry_fingerprint: str = Field(
        ..., description="Hash of the geometry the bundle was computed for"
    )
