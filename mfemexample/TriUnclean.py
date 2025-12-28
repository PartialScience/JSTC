## Example 1: Solving a simple diffusion problem using MFEM's Python interface
## This code was copied directly from the python MFEM README and is a port of the mfem C++ ex1 example.

import mfem.ser as mfem
#import mfem.par as mfem_par
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as tri
import argparse


################################## Classes

def make_pw_sigma(dim=2, alpha_rect=1e4, beta_circ=1e6):
    # Build constant 2x2 matrices
    K_bg = mfem.DenseMatrix(dim)
    K_bg.Assign(0.0)
    K_bg[0, 0] = 1.0
    K_bg[1, 1] = 1.0

    K_rect = mfem.DenseMatrix(dim)
    K_rect.Assign(0.0)
    K_rect[0, 0] = float(alpha_rect)   # suppress x-variation
    K_rect[1, 1] = 1.0

    K_circ = mfem.DenseMatrix(dim)
    K_circ.Assign(0.0)
    K_circ[0, 0] = float(beta_circ)    # nearly constant in circle
    K_circ[1, 1] = float(beta_circ)

    # Wrap as matrix constant coefficients
    C_bg   = mfem.MatrixConstantCoefficient(K_bg)
    C_rect = mfem.MatrixConstantCoefficient(K_rect)
    C_circ = mfem.MatrixConstantCoefficient(K_circ)

    # Piecewise by attribute (attr IDs: 1 background, 2 rectangle, 3 circle)
    Kpw = mfem.PWMatrixCoefficient(dim)
    Kpw.Set(1, C_bg)
    Kpw.Set(2, C_rect)
    Kpw.Set(3, C_circ)
    return Kpw


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

    parser.add_argument("--static-cond",
                        action="store_true",
                        help="Enable static condensation")

    parser.add_argument("--pa", action="store_true",
                        help="Partial assembly")

    parser.add_argument("--fa", action="store_true",
                        help="Full assembly")

    parser.add_argument("-d", "--device",
                        default="cpu",
                        help="Device configuration")

    parser.add_argument("--no-vis",
                        action="store_false",
                        dest="visualization",
                        help="Disable visualization")

    parser.add_argument("--algebraic-ceed",
                        action="store_true",
                        help="Use algebraic CEED")

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
static_cond = args.static_cond
pa = args.pa
fa = args.fa
device_config = args.device
visualization = args.visualization
algebraic_ceed = args.algebraic_ceed

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

# IMPORTANT: refresh attribute lists
mesh.SetAttributes()

eps = 1e-8

ip1 = mfem.IntegrationPoint()
ip1.Set(0.5, 0.0, 0.0, 0.0)  # midpoint on boundary segment

x = mfem.Vector(dim)

# compute vertex array once (Nx2 numpy array)
verts = np.array(mesh.GetVertexArray()).reshape(-1, mesh.Dimension())

for i in range(mesh.GetNBE()):
    be = mesh.GetBdrElement(i)

    # Try several ways to get the two vertex indices for the boundary segment.
    try:
        vids = be.GetVertices()
        # If vids behaves like a sequence (some builds), use it directly.
        if hasattr(vids, '__len__') and len(vids) >= 2:
            print("First works")
            v0, v1 = int(vids[0]), int(vids[1])
            X = 0.5 * (verts[v0] + verts[v1])
        else:
            print("second works")
            # Fallback: ask the element to fill an mfem.intArray (works with other bindings)
            vids_arr = mfem.intArray()
            be.GetVertices(vids_arr)
            v0, v1 = int(vids_arr[0]), int(vids_arr[1])
            X = 0.5 * (verts[v0] + verts[v1])
    except TypeError:
        print("third works")
        # Last-resort fallback: use the element transformation with a 1D integration point
        T = mesh.GetBdrElementTransformation(i)
        ip_bdr = mfem.IntegrationPoint()
        ip_bdr.Set([0.5], 1)   # 1D reference coordinate (midpoint of segment)
        Xv = mfem.Vector(mesh.Dimension())
        T.Transform(ip_bdr, Xv)
        X = np.array([float(Xv[j]) for j in range(mesh.Dimension())])

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

# Debug: print boundary attribute distribution and check left side (attr==4)
battrs = []
for i in range(mesh.GetNBE()):
    be = mesh.GetBdrElement(i)
    try:
        battrs.append(int(be.GetAttribute()))
    except Exception:
        # some bindings may require attribute property access
        battrs.append(int(be.Attribute))
from collections import Counter
print("Boundary attribute counts:", dict(Counter(battrs)))
print("Has left boundary (attr 4):", 4 in battrs)

print("bdr_attributes:", mesh.bdr_attributes.Size(),
      mesh.bdr_attributes.Min(), mesh.bdr_attributes.Max())

###################################### Finite Element Space

# Define the finite element function space
fec = mfem.H1_FECollection(1, mesh.Dimension())   # H1 order=1
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

"""
Note
-----
In order to represent a variable diffusion coefficient, you
must use a numba-JIT compiled function. For example:

>>> @mfem.jit.scalar
>>> def alpha(x):
>>>     return x+1.0
"""

###################################################### Linear Form

yval = 0.8
tol = 0.1
@mfem.jit.scalar
def rect_slice(x):
    # x is a numpy array-like of coordinates, x[0]=x, x[1]=y in 2D
    return 1.0 if (abs(x[1] - yval) < tol and x[0] <=  Rx + RectWidth and x[0] >= Rx ) else 0.0

b = mfem.LinearForm(fespace)
b.AddDomainIntegrator(mfem.DomainLFIntegrator(rect_slice))
b.Assemble()


##################################################### Bilinear Form

@mfem.jit.matrix(width=2, height=2)
def K(x):
    out = np.zeros((2,2))

    inRect = ( Rx <= x[0] <= Rx + RectWidth) and (Ry <= x[1] <= Ry + RectHeight)
    inCirc = (Cx - x[0])**2 + (Cy - x[1])**2 <= Rad**2

    if inRect:
        out[0, 0] = 10_000.0
        out[1, 1] = 1.0
    elif inCirc:
        out[0, 0] = 10_000.0
        out[1, 1] = 10_000.0
    else:
        out[0,0] = 1.0
        out[1,1] = 1.0

    # axisymmetric weight (match TeslaSlice1p_tri.cpp AxisymmetricSigma: multiply by r)
    r = x[0]
    out *= r

    return out


print(mfem.DiffusionIntegrator.__doc__)

#Kpw = make_pw_sigma(dim=2, alpha_rect=1e4, beta_circ=1e6)

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
print("Size of linear system: " + str(A.Height()))
print("||B||_2 =", B.Norml2())
print("X size:", X.Size(), "B size:", B.Size())
print("A dims:", A.Height(), A.Width())
print("Has PWMatrixCoefficient:", hasattr(mfem, "PWMatrixCoefficient"))
print("Has MatrixConstantCoefficient:", hasattr(mfem, "MatrixConstantCoefficient"))


import random
v = mfem.Vector(A.Height())
for i in range(v.Size()):
    v[i] = random.random() - 0.5
Av = mfem.Vector(A.Height())
A.Mult(v, Av)
q = v * Av   # dot product
print("v^T A v =", q)


AA = mfem.OperatorHandle2SparseMatrix(A)
try:
    diag = np.array(AA.GetDiag().GetDataArray())
    print("Matrix diag min/max:", diag.min(), diag.max())
except Exception:
    pass

X.SetSize(B.Size())
M = mfem.DSmoother(AA)
mfem.PCG(AA, M, B, X, 1, 200, 1e-12, 0.0)

a.RecoverFEMSolution(X, b, x)



########################################## Visualization using matplotlib


# # Extract vertices and solution as numpy arrays
# verts = np.array(mesh.GetVertexArray())
# sol = x.GetDataArray()

# # Plot the solution using matplotlib 
# triang = tri.Triangulation(verts[:,0], verts[:,1])

# fig, ax = plt.subplots()
# ax.set_aspect('equal')
# tpc = ax.tripcolor(triang, sol, shading='gouraud')
# fig.colorbar(tpc)
# plt.show()