"""
Axisymmetric electrostatic unit solves and Gram-matrix charge extraction.

The math implemented here is derived start-to-finish in
docs/cmatrix_derivation.ipynb. Summary:

  * PDE: Laplace in the (r, z) half-plane with the cylindrical measure,
    which in weak form is the r-weighted diffusion operator
    K[a,b] = integral( grad(psi_a) . grad(psi_b) * r ) dr dz.
  * One Dirichlet solve per requested boundary-potential pattern.
  * The *geometric* capacitance matrix is the K-inner-product Gram matrix
    of the solution DOF vectors:  C_geo[j,k] = U_j^T K U_k,
    using the UNCONSTRAINED K (its boundary rows encode the charge).
    Physical units: C_SI = 2*pi*epsilon_0 * scale * C_geo.

This module knows nothing about coils. Boundary data arrives as
{attribute: value} maps where a value is a constant or a callable (r, z)
-> potential; every essential attribute not present in a solve's map is
held at 0.

Linear algebra strategy: the operator never changes between solves, so the
constrained system is factorized once (scipy splu) and each solve is a
back-substitution. MFEM does the FE assembly and boundary projection;
scipy does the solving.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence, Union

import numpy as np
import mfem.ser as mfem
from scipy.sparse import csr_matrix, spmatrix
from scipy.sparse.linalg import splu

BoundaryValue = Union[float, Callable[[float, float], float]]

# pypardiso.spsolve routes through a process-global PyPardisoSolver instance
# that is NOT thread-safe: concurrent calls from different threads clobber
# its shared factorization state and segfault the whole process. Under a
# server (FastAPI runs sync endpoints in a threadpool) two overlapping FEM
# solves would hit exactly this. Serialize the call with a module-level lock.
# The throughput cost is negligible - PARDISO already uses every core per
# solve, so concurrent solves would only oversubscribe the CPU anyway.
_PARDISO_LOCK = threading.Lock()


def _solve_multi(A: spmatrix, B: np.ndarray) -> np.ndarray:
    """Solve ``A X = B`` for every column of B, reusing a single
    factorization of A.

    A is the (free-DOF) stiffness block: sparse, symmetric positive
    definite, and identical across all unit solves - so it is factored once
    and every right-hand side is a cheap back-substitution. Prefers PARDISO
    (Intel MKL: multithreaded, exploits symmetry) when installed, else falls
    back to SciPy's SuperLU. Both accept the full 2-D RHS in one call, so
    the N+1 solves run as a single batched operation rather than a Python
    loop.

    Thread-safety: the PARDISO path is serialized (see _PARDISO_LOCK).
    """
    Acsc = A.tocsc()
    try:
        import pypardiso
    except ImportError:
        # SuperLU factorizes into a fresh per-call object - already
        # thread-safe, no shared global state.
        return splu(Acsc).solve(B)
    with _PARDISO_LOCK:
        X = pypardiso.spsolve(Acsc, B)
    # pypardiso squeezes a single-column RHS to 1-D; keep it 2-D.
    return X.reshape(B.shape)


@dataclass
class ElectrostaticResult:
    """Result bundle of a batch of axisymmetric unit solves.

    Attributes:
        gram: The geometric capacitance Gram matrix,
            gram[j, k] = integral( grad(u_j) . grad(u_k) * r ) dr dz.
        group_charges: Per-conductor-group charge attribution, or None if
            no charge groups were requested. group_charges[g, s] is the
            geometric charge on group g's surfaces in solve s - the weak
            (reaction) extraction a(u_s, w_g) with w_g the indicator
            lifting of the group's boundary DOFs. Same units convention
            as the gram matrix (multiply by 2*pi*epsilon_0*scale, and by
            1 volt, for Coulombs).
    """

    gram: np.ndarray
    group_charges: Optional[np.ndarray]
    #: (n_solves, n_points) potential of each solve's field sampled at the
    #: requested world points, or None if no sample points were given.
    #: Points outside the field domain (inside a conductor, or off-mesh) are
    #: NaN and flagged False in ``sample_mask``.
    sampled_fields: Optional[np.ndarray] = None
    #: (n_points,) bool: True where the sample point is inside the domain.
    sample_mask: Optional[np.ndarray] = None


def _sample_on_grid(mesh, fes, solutions: np.ndarray, points: np.ndarray):
    """Interpolate each solution field at world points via GSLIB.

    Args:
        mesh: the solve mesh (nodes are ensured here for point location).
        fes: the H1 space the solutions live in.
        solutions: (n_solves, n_dofs) DOF vectors.
        points: (2, n_points) world coordinates, row 0 = r, row 1 = z.

    Returns:
        (sampled, mask): sampled is (n_solves, n_points) with NaN at points
        outside the domain; mask is (n_points,) True inside the domain.
    """
    mesh.EnsureNodes()
    n_points = points.shape[1]
    fp = mfem.FindPointsGSLIB()
    fp.Setup(mesh)
    # byNODES layout (all r, then all z) matches ordering flag 0.
    fp.FindPoints(mfem.Vector(points.flatten(order="C")), 0)
    codes = np.array(fp.GetCode().GetDataArray(), dtype=int)  # 2 = not found
    mask = codes != 2

    gf = mfem.GridFunction(fes)
    vals = mfem.Vector()
    sampled = np.empty((solutions.shape[0], n_points))
    for s in range(solutions.shape[0]):
        gf.GetDataArray()[:] = solutions[s]
        fp.Interpolate(gf, vals)
        sampled[s] = np.array(vals.GetDataArray())
    fp.FreeData()

    sampled[:, ~mask] = np.nan
    return sampled, mask


class _RadialCoefficient(mfem.PyCoefficient):
    """The cylindrical Jacobian weight r (the x-coordinate of the mesh)."""

    def EvalValue(self, x):
        return x[0]


class _CallableCoefficient(mfem.PyCoefficient):
    """Adapts a python callable (r, z) -> value to an MFEM coefficient."""

    def __init__(self, fn: Callable[[float, float], float]):
        super().__init__()
        self._fn = fn

    def EvalValue(self, x):
        return self._fn(x[0], x[1])


def _sparse_to_scipy(K: mfem.SparseMatrix) -> csr_matrix:
    """Zero-copy view of an MFEM SparseMatrix as scipy CSR (then copied)."""
    height = K.Height()
    width = K.Width()
    indptr = np.array(K.GetIArray(), copy=True)
    indices = np.array(K.GetJArray(), copy=True)
    data = np.array(K.GetDataArray(), copy=True)
    return csr_matrix((data, indices, indptr), shape=(height, width))


def _attr_marker(max_attr: int, attrs) -> mfem.intArray:
    """MFEM attribute marker array with 1 at each listed attribute."""
    marker = mfem.intArray(max_attr)
    marker.Assign(0)
    for a in attrs:
        marker[a - 1] = 1
    return marker


def solve_capacitance_gram_matrix(
    mesh: mfem.Mesh,
    dirichlet_attrs: Sequence[int],
    solves: Sequence[Mapping[int, BoundaryValue]],
    fe_order: int = 2,
) -> np.ndarray:
    """Convenience wrapper over solve_electrostatics returning only the
    Gram matrix. See solve_electrostatics for the full contract."""
    return solve_electrostatics(mesh, dirichlet_attrs, solves, fe_order).gram


def solve_electrostatics(
    mesh: mfem.Mesh,
    dirichlet_attrs: Sequence[int],
    solves: Sequence[Mapping[int, BoundaryValue]],
    fe_order: int = 2,
    charge_groups: Sequence[Sequence[int]] = (),
    sample_points: Optional[np.ndarray] = None,
) -> ElectrostaticResult:
    """
    Run one axisymmetric Laplace solve per boundary-potential pattern and
    return the geometric capacitance Gram matrix of the solutions, plus
    optional per-conductor-group charge attributions.

    Args:
        mesh: The meshed field domain (from an AxisymmetricMesher). The
            r = 0 axis and any boundary attribute NOT listed in
            *dirichlet_attrs* receive the natural (Neumann) condition.
        dirichlet_attrs: Every boundary attribute held at a prescribed
            potential in the solves - all conductors plus all Dirichlet
            walls. Attributes missing from a particular solve's map are
            held at 0 in that solve.
        solves: One map per unit solve: {boundary_attribute: potential},
            where the potential is a constant or a callable (r, z) -> value
            (e.g. a tent profile along a winding).
        fe_order: H1 element order. Order 2 is the accuracy sweet spot:
            the Gram extraction is an energy functional and converges at
            O(h^(2p)).
        charge_groups: Optional groups of boundary attributes (each a
            sequence of attrs from dirichlet_attrs) for which the per-solve
            surface charge is extracted - e.g. one group holding all
            topload attributes. Charges use the weak/reaction form (no
            flux integration), so they share the Gram matrix's accuracy.
        sample_points: Optional (2, n_points) world coordinates (row 0 = r,
            row 1 = z) at which to interpolate every solve's field, for
            field visualization. Returned in ``sampled_fields``.

    Returns:
        An ElectrostaticResult with the symmetric positive-definite Gram
        matrix (gram[j,k] = integral( grad(u_j) . grad(u_k) * r ) dr dz,
        in the mesh's length units - multiply by 2*pi*epsilon_0 and the
        meters-per-unit scale for Farads) and, when charge_groups were
        requested, the group charge matrix.

    Raises:
        ValueError: If no Dirichlet attribute exists (the potential would
            have no reference and the matrix would be singular - see the
            positive-definiteness caveat in the derivation notebook).
    """
    if not dirichlet_attrs:
        raise ValueError(
            "At least one Dirichlet boundary is required as the potential "
            "reference; an all-Neumann domain has a singular C matrix."
        )

    fec = mfem.H1_FECollection(fe_order, mesh.Dimension())
    fes = mfem.FiniteElementSpace(mesh, fec)
    max_attr = mesh.bdr_attributes.Max()

    # --- Assemble the r-weighted stiffness once, unconstrained ---
    r_coeff = _RadialCoefficient()
    form = mfem.BilinearForm(fes)
    form.AddDomainIntegrator(mfem.DiffusionIntegrator(r_coeff))
    form.Assemble()
    form.Finalize()
    K = _sparse_to_scipy(form.SpMat())

    # --- Essential (Dirichlet) DOFs ---
    ess_marker = _attr_marker(max_attr, dirichlet_attrs)
    ess_tdofs = mfem.intArray()
    fes.GetEssentialTrueDofs(ess_marker, ess_tdofs)
    ess = np.array(ess_tdofs.ToList(), dtype=np.int64)
    n_dofs = fes.GetNDofs()
    free = np.setdiff1d(np.arange(n_dofs, dtype=np.int64), ess)

    # --- Constrained operator blocks (same matrix for every solve) ---
    K_ff = K[np.ix_(free, free)].tocsc()
    K_fe = K[np.ix_(free, ess)]

    # --- Project each solve's Dirichlet data onto the boundary DOFs ---
    ess_values = np.zeros((len(solves), ess.size))
    grid_fn = mfem.GridFunction(fes)
    for s, boundary_values in enumerate(solves):
        grid_fn.Assign(0.0)
        for attr, value in boundary_values.items():
            if attr not in dirichlet_attrs:
                raise ValueError(
                    f"Solve {s} prescribes attribute {attr}, which is not "
                    "in dirichlet_attrs"
                )
            if callable(value):
                coeff = _CallableCoefficient(value)
            else:
                coeff = mfem.ConstantCoefficient(float(value))
            grid_fn.ProjectBdrCoefficient(coeff, _attr_marker(max_attr, [attr]))
        ess_values[s] = grid_fn.GetDataArray()[ess]

    # --- Solve all right-hand sides at once (one factorization) ---
    # K_ff X = -K_fe U_ess^T ; column s is the free-DOF field of solve s.
    rhs = -(K_fe @ ess_values.T)
    free_solution = _solve_multi(K_ff, np.asarray(rhs))

    solutions = np.zeros((len(solves), n_dofs))
    solutions[:, ess] = ess_values
    solutions[:, free] = free_solution.T

    # --- Gram extraction: C_geo = U K U^T (see notebook section 7) ---
    KU = K @ solutions.T
    C_geo = solutions @ KU
    # Enforce exact symmetry against floating-point asymmetry
    C_geo = 0.5 * (C_geo + C_geo.T)

    # --- Optional per-group charge attribution: Q[g, s] = w_g^T K u_s ---
    # w_g is the indicator lifting of group g's boundary DOFs, so the
    # product is simply the sum of the reaction vector K u_s over those
    # DOFs (see the derivation notebook's discrete mirror, section 7).
    group_charges = None
    if charge_groups:
        group_charges = np.empty((len(charge_groups), len(solves)))
        for g, attrs in enumerate(charge_groups):
            unknown = [a for a in attrs if a not in dirichlet_attrs]
            if unknown:
                raise ValueError(
                    f"Charge group {g} lists attributes {unknown} that are "
                    "not in dirichlet_attrs"
                )
            group_tdofs = mfem.intArray()
            fes.GetEssentialTrueDofs(_attr_marker(max_attr, attrs), group_tdofs)
            dofs = np.array(group_tdofs.ToList(), dtype=np.int64)
            group_charges[g] = KU[dofs, :].sum(axis=0)

    # --- Optional field sampling on a grid (for field visualization) ---
    sampled_fields = None
    sample_mask = None
    if sample_points is not None and sample_points.shape[1] > 0:
        sampled_fields, sample_mask = _sample_on_grid(
            mesh, fes, solutions, sample_points
        )

    return ElectrostaticResult(
        gram=C_geo,
        group_charges=group_charges,
        sampled_fields=sampled_fields,
        sample_mask=sample_mask,
    )
