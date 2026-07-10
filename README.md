# JSTC

A modern re-write of the community-standard **JavaTC** Tesla-coil analysis
tool, pairing a FastAPI + finite-element physics backend with an interactive
React geometry editor.

---

## 1. Overview

JSTC computes the electrical behaviour of a Tesla coil from its geometry:
resonant frequency, the effective/energy inductance and capacitance pairs
(Les/Ces, Lee/Cee), DC values (Ldc, Cdc), topload capacitance, AC resistance
and Q, primary inductance and tuning, primary–secondary mutual inductance and
coupling coefficient, and the fully **coupled** response (frequency splitting,
the primary input-impedance Bode sweep, and a SPICE export of the coupled
network).

Where JavaTC uses closed-form approximations, JSTC solves the actual
electrostatics with the finite element method (FEM) on a mesh of the coil,
while keeping the classical lumped outputs so results can be cross-checked
against JavaTC directly. The project validates against JavaTC's published
example coil to within a few percent end-to-end
(`api/tests/simulation/test_javatc_e2e.py`).

The repository has three parts:

| Path | What it is |
|------|------------|
| [`api/`](api/) | Python / FastAPI backend: geometry, meshing, FEM/analytic solvers, and the HTTP API. |
| [`frontend/`](frontend/) | React + TypeScript app: an interactive `(r, z)` geometry editor (react-konva) and results dashboard. |
| [`docs/`](docs/) | The C-matrix derivation notebook and the JavaTC reference output used for validation. |

**Tech stack.** Backend: FastAPI, [gmsh](https://gmsh.info/) (meshing),
[PyMFEM](https://github.com/mfem/PyMFEM) (FEM), NumPy/SciPy, and Numba.
Frontend: React 18, TypeScript (strict), react-konva, Zustand, TanStack Query,
Recharts, Vitest + Playwright. Types flow end-to-end: the frontend's API types
are generated from the backend's OpenAPI schema.

---

## 2. Running the project full-stack locally

### Prerequisites

All development is done inside the provided **VS Code Dev Container**, which
builds PyMFEM from source and installs gmsh, Node, and the Python dependencies.

1. Install [Docker](https://www.docker.com/) and the VS Code
   [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
2. Open the repo in VS Code → `Ctrl/Cmd+Shift+P` → **Dev Containers: Reopen in
   Container**. The first build is slow (PyMFEM compiles); later launches are
   fast.

### Install the frontend dependencies (first time only)

```bash
npm run setup        # installs frontend/ node_modules
```

### Run both servers with one command

From the repo root:

```bash
npm run dev
```

This starts, via `concurrently`:

- **backend** — FastAPI/uvicorn on **:8420** (`api/main.py`)
- **frontend** — Vite dev server on **:5173**, which proxies `/simulation` and
  `/health` to the backend

Then open **http://localhost:5173**. Notes:

- Wait for `[api] Application startup complete` before running a calculation —
  the backend imports Numba/MFEM/gmsh (~10 s).
- The first **Run** on any geometry does the full FEM solve (tens of seconds).
  Cheap edits afterwards (materials, tank cap, unit scale) reuse the cached
  matrix bundle and return in milliseconds (see §5).
- `npm run dev` frees ports 5173/8420 first (`scripts/free-ports.mjs`) so a
  leftover process can't block startup. The API proxy target is overridable
  with `VITE_API_TARGET`.

### Useful commands

```bash
# backend (from api/)
python main.py                       # run standalone (with hot-reload)
python -m pytest                     # test suite

# frontend (from frontend/)
npm run test        # Vitest unit tests
npm run test:e2e    # Playwright end-to-end (mocked backend)
npm run typecheck   # tsc --noEmit
npm run lint
npm run build
npm run gen:api     # regenerate TS types from the backend OpenAPI schema
```

The interactive API docs are disabled by default; the OpenAPI schema is at
`http://localhost:8420/openapi.json`.

---

## 3. How Tesla coils are modeled

Every Tesla coil in JSTC is **axisymmetric**: the whole geometry is described in
the 2-D `(r, z)` half-plane and understood as the solid of revolution about the
`z` (vertical) axis. A circle drawn at `(r, z)` is really a *torus*; a vertical
line segment is a *cylinder*. The frontend renders the mirrored cross-section
(`±r`) so it reads like a real coil, but the model is the half-plane.

A coil (`SimulatableTeslaCoilSchema` on the wire, `SimulatableTeslaCoil` in the
domain, [`api/app/models/`](api/app/models/)) is:

- **Secondary** — the resonator. Modeled as a `ParametricCurve` centerline in
  `(r, z)` plus a `wire_dia` (giving an "offset region" — the wire cross-section
  swept along the curve) and a **turn function** `turn_fxn(t)`: the *cumulative*
  turn count along the curve. A straight vertical line is a classic solenoid; a
  slanted line is a conical coil; the turn function's derivative is the local
  winding density, so non-uniform winds are first-class. Turn functions are
  serializable value objects (e.g. `UniformTurnProfile`), so a coil round-trips
  through the API and is hashable for caching.
- **Toploads** — floating conductors at the top terminal (add capacitance).
  Each is a `material` + a shape (`Circle` → toroid, `Rectangle`/`Polygon` →
  ring/disc). Multiple toploads are a tuple; they're all tied to the top of the
  winding.
- **Grounds** — conductors held at 0 V (counterpoise, strike rail, nearby
  grounded objects). Same shape vocabulary as toploads.
- **Primary** — a curve + cross-section (`CircularCrossSection` for round wire,
  `RectangularCrossSection` for ribbon) + turn function, plus the tank
  capacitance and lead geometry. The primary is treated as sitting near ground
  potential on secondary-resonance timescales (the standard TSSP/JavaTC
  assumption), so for the electrostatics it **derives one grounded ring per
  turn**; for the magnetics it contributes coaxial rings. This keeps the
  capacitance solver ignorant of "what a primary is" — it just sees more
  grounded conductors.
- **Simulation domain** — `r_max`, `z_max` (a bounded box that approximates open
  space), per-wall boundary conditions, a `unit_scale` (meters per geometry
  unit — e.g. `0.0254` for inches), and `discretization_order` **N** (how many
  virtual segments the secondary is split into).

Geometry is built on a small, fully-tested library
([`api/app/geometry/`](api/app/geometry/)): `ParametricCurve` (line segments,
circular arcs, sub-curves, offset/parallel curves) and `GeometricRegion`
(circle, polygon, rectangle, offset region). Every region can produce its
**boundary loops** — closed sequences of parametric curves — which is the one
thing the mesher needs. Concrete curves override the generic implementations
with exact closed forms (arc length, closest point, adaptive sampling) where
they exist.

---

## 4. How the matrix solvers work

The secondary is discretized into **N virtual segments** (uniform arc-length
slicing). The physics is then captured by four matrices over those segments,
each produced by a swappable solver behind an abstract base class
([`api/app/simulation/`](api/app/simulation/)). Solvers return *geometric*
matrices (in the coil's length units, constants factored out); the facade
applies `ε₀`/`μ₀`/`unit_scale` exactly once (see §5).

### Inductance **L** (`distributed_element_matrices/inductance/`)

`CoaxialRingInductanceLMatrixSolver` models each turn of the secondary as a
coaxial circular ring and fills the full turn-by-turn mutual-inductance matrix
using the Maxwell/Rosa–Grover elliptic-integral formula (Numba-parallelized,
with the Kirchhoff self-inductance formula on the diagonal). It's computed once
per geometry and downsampled to the N segments.

### Capacitance **C** (`distributed_element_matrices/capacitance/` + `electrostatics/` + `meshing/`)

The capacitance matrix is where JSTC does real field solving. This is the
**nodal (tent-basis) Galerkin** capacitance matrix, derived start-to-finish in
[`docs/cmatrix_derivation.ipynb`](docs/cmatrix_derivation.ipynb). The pipeline:

1. **Mesh** — the secondary (one hole), toploads, grounds, and the primary's
   grounded rings are subtracted from the `(r, z)` domain with gmsh's
   OpenCASCADE kernel, producing an MFEM mesh with a boundary attribute per
   conductor (`meshing/`). Conductor surfaces are finely meshed, walls coarsely.
2. **Solve** — for each of the N+1 slice nodes, run one axisymmetric Laplace
   solve (r-weighted `DiffusionIntegrator`, order-2 H1 elements) whose boundary
   data is a **tent (hat) profile** on the winding: 1 at that node, ramping
   linearly to 0 at the neighbors. The topload rides the top node; grounds and
   Dirichlet walls are 0.
3. **Extract** — the capacitance entry is the *energy inner product* of two
   solution fields, `C_jk = Uⱼᵀ K Uₖ`, with the unconstrained stiffness matrix
   `K`. No surface-charge or flux integration — this form is symmetric and
   positive-definite by construction and super-convergent.

The tent basis (rather than piecewise-constant "Maxwell" indicators) is what
makes every matrix entry **finite and mesh-convergent**, and makes the DC
capacitance exact via a partition-of-unity argument. The same FEM solution also
yields the topload's induced charge per node (for its effective capacitance) at
no extra cost.

### Connectivity **A** (`coil_discretizers/connectivity_matrices/`)

The series connectivity matrix wires segment *n* to *n+1*, grounds the base
node, and lumps the topload into the top node — a fixed bidiagonal matrix.

### Mutual coupling **m** (`distributed_element_matrices/coupling/`)

For the coupled solve, `m` is the length-N vector of mutual inductances between
the primary and each secondary segment, computed with the same coaxial-ring
formula as **L**.

All solvers are pure functions of hashable inputs and cached with
`functools.lru_cache`, so identical geometry never recomputes.

---

## 5. Computing the core values from the matrices

The [`facade/`](api/app/simulation/facade/) wires a mutable coil to the cached
solvers and exposes the outputs as lazy properties. It first converts the
geometric matrices to SI **once**:

```
L [H] = μ₀ · unit_scale · L_geo        C [F] = 2π · ε₀ · unit_scale · C_geo
```

### Resonance and modes (`SecondaryView`)

The eigen solver solves the generalized eigenproblem for the transmission-line
ladder,

```
ω² C V = A L⁻¹ Aᵀ V,
```

giving the eigenfrequencies (the lowest is the quarter-wave **resonant
frequency**) and the voltage/current eigenmodes.

### Lumped equivalents (matched to JavaTC/TSSP definitions)

- **Ldc** = sum of all L entries (uniform DC current). **Cdc** = `𝟙ᵀ C 𝟙` on
  the full nodal matrix (whole coil equipotential — exact by partition of
  unity).
- **Les** (effective series inductance) from the fundamental mode:
  `V_top = ω·Les·I_base`. **Ces** = `1/(ω²·Les)` (resonates with Les).
- **Cee** (energy capacitance) = `VᵀCV / V_top²` — twice the field energy per
  top-volt². **Lee** = `1/(ω²·Cee)`.
- **Topload capacitance**, DC resistance, skin-effect **AC resistance** and
  **Q**, wire length/weight, and geometric ratios round out the secondary
  outputs.

### Primary and coupling

`PrimaryView` gives the primary's Ldc (coaxial rings) plus lead inductance, its
LC resonant frequency and percent-detune. `CouplingView` gives the mutual
inductance `Lm = Σ mₖ` and coupling coefficient `k = Lm/√(Lp·Ls)`.

### Coupled solve (`simulation/coupled/`)

The full system closes the secondary ladder, the bordered inductance matrix
`[[L, m], [mᵀ, Lp]]`, and the tank capacitor into one state-space model. From it:

- **Frequency splitting** — the coupled eigenmodes (the split pair around the
  operating point).
- **Primary input impedance** `Z(ω)` — a single linear solve per frequency,
  rendered in the app as a **Bode plot** (magnitude in dB + phase).
- **SPICE export** — the coupled network as a subcircuit (coupled inductors +
  the C-matrix capacitor network + tank), round-trip-verified to reproduce the
  coupled mode frequencies.

---

## The frontend, briefly

The React app is an interactive `(r, z)` cross-section editor: place a
secondary, primary, toploads, and grounds from the toolbar; drag endpoints,
vertices, radii, and wire diameters directly on the canvas; right-click to enter
exact values, add/delete vertices, or convert shape types; edit everything
numerically in the left sidebar. Ctrl+Z / Ctrl+Shift+Z undo/redo. All outputs
are always listed (values fill in on **Run**), with the impedance Bode sweep and
SPICE export below.

The expensive part — the FEM capacitance solve — is cached as an opaque
**matrix bundle**. On any change the frontend calls `/simulation/analyze` with
the cached bundle; if the geometry changed (detected by the bundle's
fingerprint, HTTP 409) it transparently refetches `/simulation/matrices` first.
This is why cheap parameter tweaks are instant while only geometry changes pay
the FEM cost.

---

## Validation & testing

- **Backend**: `cd api && python -m pytest` — unit tests for geometry, meshing,
  each solver (including analytic capacitance checks against coaxial cylinders
  and spheres), the coupled solver, and a full end-to-end comparison to
  JavaTC's example coil.
- **Frontend**: `npm run test` (Vitest units for the viewport transform, store,
  and geometry ops) and `npm run test:e2e` (Playwright, backend mocked).

See [`docs/cmatrix_derivation.ipynb`](docs/cmatrix_derivation.ipynb) for the
full capacitance-matrix derivation and `docs/JavaTC Example Coil.txt` for the
reference values.
