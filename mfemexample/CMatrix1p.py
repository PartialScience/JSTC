## This is a python version of the cpp file TeslaSlice1p_tri.cpp
## It solves a 2D axisymmetric conduction problem on a triangular mesh


import mfem.par as mfem
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as tri
import argparse
from mpi4py import MPI

num_procs = MPI.COMM_WORLD.size
myid = MPI.COMM_WORLD.rank
smyid = '{:0>6d}'.format(myid)






################################## Arguments


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-m", "--mesh",
                        default="../data/star.mesh",
                        help="Mesh file")

    parser.add_argument("-o", "--order",
                        type=int,
                        default=1,
                        help="Finite element order")


    parser.add_argument("-d", "--device",
                        default="cpu",
                        help="Device configuration")

    parser.add_argument("--vis",
                        action="store_true",
                        dest="visualization",
                        help="Enable visualization")

    # Geometry parameters
    parser.add_argument("--rect-height", type=float, default=0.7)
    parser.add_argument("--rect-width",  type=float, default=0.1)

    parser.add_argument("--cx", type=float, default=0.35)
    parser.add_argument("--cy", type=float, default=1.2)

    parser.add_argument("--rx", type=float, default=0.1)
    parser.add_argument("--ry", type=float, default=0.3)

    parser.add_argument("--rad", type=float, default=0.1)

    parser.add_argument("--ns", type=int, default=10)

    return parser.parse_args()


args = parse_args()

mesh_file = args.mesh
order = args.order
device_config = args.device
visualization = args.visualization

RectHeight = args.rect_height
RectWidth  = args.rect_width
Cx, Cy = args.cx, args.cy
Rx, Ry = args.rx, args.ry
Rad = args.rad
NumSlices = args.ns

nx = 40
ny = 80


############################## Mesh


# Create a square mesh
mesh = mfem.Mesh.MakeCartesian2D( nx, ny,  mfem.Element.TRIANGLE, True, 1.0, 2.0)
mesh.EnsureNodes()
dim = mesh.Dimension()

#Integration Point
ip = mfem.IntegrationPoint()
ip.Set2(1.0/3.0, 1.0/3.0)
x = mfem.Vector(dim)

# Refine the mesh,but only near our circle and rectangle
n_ref_levels = 3
for level in range(n_ref_levels):
    el_to_refine = mfem.intArray()
    el_to_refine.Reserve(mesh.GetNE())

    # centroid in reference triangle: (1/3, 1/3)
    ip = mfem.IntegrationPoint()
    ip.Set2(1.0/3.0, 1.0/3.0)

    x = mfem.Vector(dim)
    for i in range(mesh.GetNE()):
        T = mesh.GetElementTransformation(i)
        T.Transform(ip, x)

        xx, yy = x[0], x[1]

        # --- geometric tests (same as C++) ---
        # near circle band
        dx = xx - Cx
        dy = yy - Cy
        band = 0.08 - level * 0.025
        Rin = Rad - band
        Rout = Rad + band
        r2 = dx*dx + dy*dy
        near_circle = (r2 >= Rin*Rin and r2 <= Rout*Rout)
        # near rectangle padded box
        x0, x1 = Rx, Rx + RectWidth
        y0, y1 = Ry, Ry + RectHeight
        pad = 0.04 - level * 0.015
        near_rect = (xx >= x0 - pad and xx <= x1 + pad and
                     yy >= y0 - pad and yy <= y1 + pad)
        if near_circle or near_rect:
            el_to_refine.Append(i)
        if el_to_refine.Size() > 0:
            mesh.GeneralRefinement(el_to_refine)

mesh.EnsureNodes()
mesh.UniformRefinement()
mesh.UniformRefinement()

# Set interior attributes
for i in range(mesh.GetNE()):
    T = mesh.GetElementTransformation(i)
    T.Transform(ip, x)
    xx, yy = x[0], x[1]
    attr = 1  # background

    # rectangle
    if (Rx <= xx <= Rx + RectWidth) and (Ry <= yy <= Ry + RectHeight):
        attr = 2

    # circle (overrides rectangle if overlap, same as your C++)
    dx, dy = xx - Cx, yy - Cy
    if dx*dx + dy*dy <= Rad*Rad:
        attr = 3

    mesh.GetElement(i).SetAttribute(attr)

mesh.SetAttributes()



# Set boundary attributes: 1=bottom, 2=right, 3=top, 4=left
# compute vertex array once (Nx2 numpy array)
verts = np.array(mesh.GetVertexArray()).reshape(-1, mesh.Dimension())
eps = 1e-8
for i in range(mesh.GetNBE()):
    be = mesh.GetBdrElement(i)

    vids_arr = mfem.intArray()
    be.GetVertices(vids_arr)
    v0, v1 = int(vids_arr[0]), int(vids_arr[1])
    X = 0.5 * (verts[v0] + verts[v1])

    xx, yy = float(X[0]), float(X[1])

    battr = 0
    if abs(yy - 0.0) < eps:
        battr = 1  # bottom
    elif abs(xx - 1.0) < eps:
        battr = 2  # right
    elif abs(yy - 2.0) < eps:
        battr = 3  # top
    elif abs(xx - 0.0) < eps:
        battr = 4  # left

    be.SetAttribute(battr)

mesh.SetAttributes()

pmesh = mfem.ParMesh(MPI.COMM_WORLD, mesh)

###################################### Finite Element Space

# Define the finite element function space
fec = mfem.H1_FECollection(order, pmesh.Dimension())   # H1 order=1
fespace = mfem.ParFiniteElementSpace(pmesh, fec)

# Define the essential dofs
ess_tdof_list = mfem.intArray()

# If there are boundary attributes, make a marker array of length max_attr
if pmesh.bdr_attributes.Size() > 0:
    ess_bdr = mfem.intArray(pmesh.bdr_attributes.Max())
    ess_bdr.Assign(0)

    # Mark attributes 1(bottom), 2(right), 3(top) as essential
    ess_bdr[0] = 1   # attr 1
    ess_bdr[1] = 1   # attr 2
    ess_bdr[2] = 1   # attr 3

    # Serial: Essential DOFs (not "true" DOFs)
    fespace.GetEssentialTrueDofs(ess_bdr, ess_tdof_list)
else:
    # no boundary attributes => no essential dofs
    pass
print("Num essential vdofs:", ess_tdof_list.Size())

###################################################### Linear Form

class WRS(mfem.PyCoefficient):
    def __init__(self, yval, tol):
        super().__init__()
        self.yval = yval
        self.tol = tol

    def EvalValue(self, x):
        in_rect = (abs(x[1] - yval) < tol and Rx <= x[0] <= Rx + RectWidth)
        return x[0] if in_rect else 0.02

b = mfem.ParLinearForm(fespace)   # To be set later


##################################################### Bilinear Form

@mfem.jit.matrix(width=2, height=2)
def K(x):
    out = np.zeros((2,2))

    inRect = ( Rx <= x[0] <= Rx + RectWidth) and (Ry <= x[1] <= Ry + RectHeight)
    inCirc = (Cx - x[0])**2 + (Cy - x[1])**2 <= Rad**2

    if inRect:
        out[0, 0] = 10_000.0    # Gradient in x direction == bad
        out[1, 1] = 1.0         # i.e. const in x direction
    elif inCirc:
        out[0, 0] = 10_000.0    # Gradient in any direction == bad
        out[1, 1] = 10_000.0    # i.e. circle is const
    else:
        out[0,0] = 1.0
        out[1,1] = 1.0

    # axisymmetric weight (match TeslaSlice1p_tri.cpp AxisymmetricSigma: multiply by r)
    r = x[0]
    out *= r

    return out


a = mfem.ParBilinearForm(fespace)
a.AddDomainIntegrator(mfem.DiffusionIntegrator(K))
a.Assemble()


print("bdr_attributes:", pmesh.bdr_attributes.Size(), pmesh.bdr_attributes.Min(), pmesh.bdr_attributes.Max())


#################################################### Set up and solve

finder = mfem.FindPointsGSLIB(MPI.COMM_WORLD)
finder.Setup(pmesh)

# point_pos holds x coords then y coords, length = 2*NumSlices
point_pos = mfem.Vector(2*NumSlices)
values    = mfem.Vector(NumSlices)

for j in range(NumSlices):
    point_pos[j]            = Rx + RectWidth/2.0
    point_pos[NumSlices + j] = Ry + RectHeight*(1.0 + 2.0*j)/20.0   # match your formula

# (Optional) C as a NumPy array if you want
C = np.zeros((NumSlices, NumSlices), dtype=float)

# --- Run simulation for each slice ---
# These are "output" objects FormLinearSystem fills in; in Python you typically
# predeclare them and reuse.
A = mfem.HypreParMatrix()  # holds the assembled/condensed operator
X = mfem.Vector()       # true-dof solution vector
B = mfem.Vector()       # true-dof RHS vector

# Initialize a parallel gridfunction to store the solution vector
x = mfem.ParGridFunction(fespace)
x.Assign(0.0)


a.FormLinearSystem(ess_tdof_list, x, b, A, X, B)


# Solve the system AX=B using PCG with a Gauss-Seidel preconditioner
M = mfem.HypreBoomerAMG(A)
cg = mfem.CGSolver(MPI.COMM_WORLD)
cg.SetRelTol(1e-12)
cg.SetMaxIter(2000)
cg.SetPrintLevel(1)
cg.SetPreconditioner(M)





for i in range(NumSlices):
    b.Assign(0.0)

    # Your custom coefficient: RectSliceCoefficient(center_y, half_thickness)
    yval = Ry + RectHeight*(1.0 + 2.0*i)/(2.0*NumSlices)     # center of slice (matches your C++)
    tol  = RectHeight/NumSlices/2.0

    rect_slice_weighted = WRS(yval = yval, tol = tol)

    # b.AddDomainIntegrator(new DomainLFIntegrator(RectVoltsSlice));
    b.AddDomainIntegrator(mfem.DomainLFIntegrator(rect_slice_weighted))
    b.Assemble()

    # a.FormLinearSystem(ess_tdof_list, x, b, A, X, B);
    a.FormLinearSystem(ess_tdof_list, x, b, A, X, B)

    cg.SetOperator(A)      # OperatorPtr -> Operator
    cg.Mult(B, X)

    a.RecoverFEMSolution(X, b, x)

    # finder.Interpolate(point_pos, x, values, mfem::Ordering::byNODES);
    finder.Interpolate(point_pos, x, values, mfem.Ordering.byNODES)

    for j in range(NumSlices):
        C[i, j] = values[j]

C = np.array(C, dtype=float)

# Use eigh if symmetric (recommended)
if np.allclose(C, C.T, rtol=1e-10, atol=1e-12):
    evals, evecs = np.linalg.eigh(C)   # evals ascending, evecs columns
else:
    evals, evecs = np.linalg.eig(C)    # possibly complex

# Sort by descending magnitude (or change to np.argsort(evals)[::-1] if you prefer)
idx = np.argsort(np.abs(evals))[::-1]
evals = evals[idx]
evecs = evecs[:, idx]

print("Eigenvalues (sorted):")
for k, lam in enumerate(evals):
    print(f"{k:2d}: {lam}")

# Print first few eigenvectors (optional)
k_print = min(3, evecs.shape[1])
for k in range(k_print):
    print(f"\nEigenvector {k} (lambda={evals[k]}):")
    print(evecs[:, k])


#x.Save('sol.'+smyid)
#pmesh.Print('mesh.'+smyid)



########################################## Visualization using matplotlib


n = evecs.shape[0]
s = np.arange(n)

for k in [0, 1]:
    plt.figure()
    plt.plot(s, evecs[:, k], marker="o")
    plt.xlabel("slice index")
    plt.ylabel("eigenvector component")
    plt.title(f"Eigenvector {k} (lambda={evals[k]:.6g})")
    plt.grid(True)
    plt.show()