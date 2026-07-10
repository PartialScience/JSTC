"""
Geometric matrix bundle and matrix providers.

The expensive-to-compute, geometry-only artifacts of a simulation (chiefly
the FEM capacitance matrix) are gathered into a GeometricMatrixBundle. The
bundle depends ONLY on geometry, discretization, boundary-condition TYPES
and mesh configuration - NOT on unit_scale, materials, tank capacitance or
lead geometry. So a client can compute it once (slow) and re-send it while
tweaking those cheap parameters, getting the full analysis back in
milliseconds.

A MatrixProvider is the seam that lets the facade read these matrices from
either source:

  * SolverMatrixProvider computes them lazily via the solvers (slow path,
    used by ``compute_matrix_bundle``).
  * BundleMatrixProvider returns a precomputed bundle (fast path, used
    when a client passes matrices back).

All matrices here are GEOMETRIC (solver-native units); the views apply
epsilon_0/mu_0/unit_scale.
"""
from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from app.models.simulation_models import SimulatableTeslaCoil
    from app.simulation.facade.simulation import TeslaCoilSimulation


Matrix = Tuple[Tuple[float, ...], ...]
Vector = Tuple[float, ...]


@dataclass(frozen=True)
class GeometricMatrixBundle:
    """The geometry-only matrices worth caching across requests.

    Attributes:
        nodal_capacitance: (N+1)x(N+1) geometric nodal capacitance matrix
            (includes the grounded base node t_0).
        topload_charge: length-(N+1) geometric topload charge per tent
            solve.
        inductance: NxN geometric segment inductance matrix.
        coupling: length-N geometric primary-secondary coupling vector
            (empty when the coil has no primary).
        discretization_order: N - stored so a reused bundle can be
            checked against the coil it is applied to.
        geometry_fingerprint: hash of every matrix-affecting input (see
            geometry_fingerprint); a client-held bundle is rejected if it
            does not match the coil passed to analysis.
    """

    nodal_capacitance: Matrix
    topload_charge: Vector
    inductance: Matrix
    coupling: Vector
    discretization_order: int
    geometry_fingerprint: str


def _canonical_region(region) -> object:
    """A JSON-safe canonical description of a GeometricRegion for hashing."""
    # Circle-like
    if hasattr(region, "center") and hasattr(region, "radius"):
        return ["circle", list(region.center), region.radius]
    # Polygon/Rectangle-like
    if hasattr(region, "vertices"):
        return ["polygon", [list(v) for v in region.vertices]]
    # Fallback: sample the boundary loops
    loops = region.boundary_loops()
    return ["loops", [
        [list(p) for p in loop.sample_polygon(1e-3)] for loop in loops
    ]]


def _canonical_curve(curve, n: int = 8) -> list:
    """Canonical sampling of a parametric curve (endpoints + interior)."""
    ts = [curve.t_min + (curve.t_max - curve.t_min) * i / n for i in range(n + 1)]
    return [list(curve.point_at(t)) for t in ts]


def _canonical_turn_fxn(turn_fxn, curve, n: int = 8) -> list:
    ts = [curve.t_min + (curve.t_max - curve.t_min) * i / n for i in range(n + 1)]
    return [float(turn_fxn(t)) for t in ts]


def geometry_fingerprint(
    coil: SimulatableTeslaCoil,
    cap_config: Tuple[Tuple[str, float], ...] = (),
) -> str:
    """Stable hash of every input the geometric matrices depend on.

    Deliberately EXCLUDES unit_scale, materials, tank_capacitance and lead
    geometry - the parameters a client may tweak without invalidating a
    cached bundle. Boundary-condition VALUES are excluded too (the C
    matrix grounds all walls regardless); only their TYPES matter.

    Args:
        coil: The simulatable coil.
        cap_config: The capacitance solver's effective mesh configuration
            (its accuracy dials change the matrices, so they change the
            fingerprint).
    """
    sec = coil.secondary
    payload = {
        "secondary": {
            "curve": _canonical_curve(sec.curve),
            "offset": sec.geometry.offset,
            "turns": _canonical_turn_fxn(sec.turn_fxn, sec.curve),
        },
        "toploads": [_canonical_region(t._geometry()) for t in coil.toploads],
        "grounds": [_canonical_region(g._geometry()) for g in coil.grounds],
        "domain": [coil.r_max, coil.z_max],
        "discretization_order": coil.discretization_order,
        "bc_types": [
            coil.bc_bottom.bc_type.value,
            coil.bc_right.bc_type.value,
            coil.bc_top.bc_type.value,
        ],
        "cap_config": [list(kv) for kv in cap_config],
    }
    if coil.primary is not None:
        prim = coil.primary
        payload["primary"] = {
            "curve": _canonical_curve(prim.curve),
            "turns": _canonical_turn_fxn(prim.turn_fxn, prim.curve),
            "cross_section": repr(prim.cross_section),
        }

    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


class MatrixProvider(ABC):
    """Source of the geometric matrices the views consume."""

    @abstractmethod
    def nodal_capacitance_geo(self) -> Matrix: ...

    @abstractmethod
    def topload_charge_geo(self) -> Vector: ...

    @abstractmethod
    def inductance_geo(self) -> Matrix: ...

    @abstractmethod
    def coupling_geo(self) -> Vector: ...


class SolverMatrixProvider(MatrixProvider):
    """Computes matrices lazily via the simulation's solvers (slow path)."""

    def __init__(self, sim: TeslaCoilSimulation):
        self._sim = sim

    def nodal_capacitance_geo(self) -> Matrix:
        return self._sim._cap_solver.nodal_capacitance_matrix(self._sim.coil)

    def topload_charge_geo(self) -> Vector:
        return self._sim._cap_solver.topload_charge_vector(self._sim.coil)

    def inductance_geo(self) -> Matrix:
        return self._sim._ind_solver.compute_matrix(self._sim.coil)

    def coupling_geo(self) -> Vector:
        if self._sim.coil.primary is None:
            return ()
        return self._sim._coupling_solver.coupling_vector(self._sim.coil)


class BundleMatrixProvider(MatrixProvider):
    """Returns a precomputed bundle (fast path). Validates the bundle
    against the coil it is applied to so a stale bundle cannot silently
    produce wrong results."""

    def __init__(self, bundle: GeometricMatrixBundle, coil: SimulatableTeslaCoil,
                 cap_config: Tuple[Tuple[str, float], ...] = ()):
        expected = geometry_fingerprint(coil, cap_config)
        if bundle.geometry_fingerprint != expected:
            raise ValueError(
                "Matrix bundle does not match the coil geometry it was "
                "applied to (geometry_fingerprint mismatch). Recompute the "
                "bundle via the matrices endpoint after changing geometry, "
                "discretization, boundary-condition types or mesh settings."
            )
        if bundle.discretization_order != coil.discretization_order:
            raise ValueError(
                f"Bundle discretization_order {bundle.discretization_order} "
                f"!= coil discretization_order {coil.discretization_order}"
            )
        self._bundle = bundle

    def nodal_capacitance_geo(self) -> Matrix:
        return self._bundle.nodal_capacitance

    def topload_charge_geo(self) -> Vector:
        return self._bundle.topload_charge

    def inductance_geo(self) -> Matrix:
        return self._bundle.inductance

    def coupling_geo(self) -> Vector:
        return self._bundle.coupling
