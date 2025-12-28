## This is a python version of the cpp file TeslaSlice1p_tri.cpp
## It solves a 2D axisymmetric conduction problem on a triangular mesh

import mfem.ser as mfem
#import mfem.par as mfem_par
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as tri
import argparse



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


###################################### Finite Element Space

# Define the finite element function space
fec = mfem.H1_FECollection(order, mesh.Dimension())   # H1 order=1
fespace = mfem.FiniteElementSpace(mesh, fec)

# Define the essential dofs
ess_tdof_list = mfem.intArray()

# If there are boundary attributes, make a marker array of length max_attr
if mesh.bdr_attributes.Size() > 0:
    ess_bdr = mfem.intArray(mesh.bdr_attributes.Max())
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

yval = 0.95
tol = 0.05
@mfem.jit.scalar
def rect_slice(x): #Puts voltage on part of coil
    return 1.0 if (abs(x[1] - yval) < tol and x[0] <=  Rx + RectWidth and x[0] >= Rx ) else 0.0

# Weight the RHS by radius r to be consistent with the axisymmetric
# bilinear form (we multiply K by r above). This avoids an inconsistent
# weak formulation that can hurt solver convergence.
@mfem.jit.scalar
def rect_slice_weighted(x):
    # replicate rect_slice logic and multiply by r (=x[0]) to avoid
    # nesting a numba coefficient inside another jitted function
    in_rect = (abs(x[1] - yval) < tol and x[0] <= Rx + RectWidth and x[0] >= Rx)
    return (1.0 * x[0]) if in_rect else 0.0

b = mfem.LinearForm(fespace)
b.AddDomainIntegrator(mfem.DomainLFIntegrator(rect_slice_weighted))
b.Assemble()


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


a = mfem.BilinearForm(fespace)
a.AddDomainIntegrator(mfem.DiffusionIntegrator(K))
a.Assemble()


print("bdr_attributes:", mesh.bdr_attributes.Size(), mesh.bdr_attributes.Min(), mesh.bdr_attributes.Max())


#################################################### Set up and solve



# Initialize a gridfunction to store the solution vector
x = mfem.GridFunction(fespace)
x.Assign(0.0)

# Form the linear system of equations (AX=B)
A = mfem.OperatorPtr()
B = mfem.Vector()
X = mfem.Vector()
a.FormLinearSystem(ess_tdof_list, x, b, A, X, B)


# Solve the system AX=B using PCG with a Gauss-Seidel preconditioner
AA = mfem.OperatorHandle2SparseMatrix(A)
X.SetSize(B.Size())
# Use Gauss-Seidel (GSSmoother) rather than DSmoother; GS is more robust
# for strong coefficient variation (e.g., near r=0 with axisymmetric weight)
M = mfem.GSSmoother(AA)
mfem.PCG(AA, M, B, X, 1, 200, 1e-12, 0.0)

# Diagnostics: compute and report residual norms to verify PCG behavior
Av = mfem.Vector(AA.Height())
AA.Mult(X, Av)             # Av = A * X
res = mfem.Vector(B.Size())
res.Assign(B)
res -= Av                 # res = B - A*X
print('||r||_2 =', res.Norml2())
# preconditioned residual inner product (B r, r)
z = mfem.Vector(res.Size())
M.Mult(res, z)
print('(M r, r) =', float(res * z))
print('||M r||_2 =', z.Norml2())


a.RecoverFEMSolution(X, b, x)



########################################## Visualization using matplotlib


# Extract vertices and solution as numpy arrays
if(visualization):
    verts = np.array(mesh.GetVertexArray())
    sol = x.GetDataArray()
 
    triang = tri.Triangulation(verts[:,0], verts[:,1])

    fig, ax = plt.subplots()
    ax.set_aspect('equal')
    tpc = ax.tripcolor(triang, sol, shading='gouraud')
    fig.colorbar(tpc)
    plt.show()