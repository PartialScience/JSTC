//                       MFEM Example 1 - Parallel Version
//
// Compile with: make ex1p
//
// Sample runs:  mpirun -np 4 ex1p -m ../data/square-disc.mesh
//               mpirun -np 4 ex1p -m ../data/star.mesh
//               mpirun -np 4 ex1p -m ../data/star-mixed.mesh
//               mpirun -np 4 ex1p -m ../data/escher.mesh
//               mpirun -np 4 ex1p -m ../data/fichera.mesh
//               mpirun -np 4 ex1p -m ../data/fichera-mixed.mesh
//               mpirun -np 4 ex1p -m ../data/toroid-wedge.mesh
//               mpirun -np 4 ex1p -m ../data/octahedron.mesh -o 1
//               mpirun -np 4 ex1p -m ../data/periodic-annulus-sector.msh
//               mpirun -np 4 ex1p -m ../data/periodic-torus-sector.msh
//               mpirun -np 4 ex1p -m ../data/square-disc-p2.vtk -o 2
//               mpirun -np 4 ex1p -m ../data/square-disc-p3.mesh -o 3
//               mpirun -np 4 ex1p -m ../data/square-disc-nurbs.mesh -o -1
//               mpirun -np 4 ex1p -m ../data/star-mixed-p2.mesh -o 2
//               mpirun -np 4 ex1p -m ../data/disc-nurbs.mesh -o -1
//               mpirun -np 4 ex1p -m ../data/pipe-nurbs.mesh -o -1
//               mpirun -np 4 ex1p -m ../data/ball-nurbs.mesh -o 2
//               mpirun -np 4 ex1p -m ../data/fichera-mixed-p2.mesh -o 2
//               mpirun -np 4 ex1p -m ../data/star-surf.mesh
//               mpirun -np 4 ex1p -m ../data/square-disc-surf.mesh
//               mpirun -np 4 ex1p -m ../data/inline-segment.mesh
//               mpirun -np 4 ex1p -m ../data/amr-quad.mesh
//               mpirun -np 4 ex1p -m ../data/amr-hex.mesh
//               mpirun -np 4 ex1p -m ../data/mobius-strip.mesh
//               mpirun -np 4 ex1p -m ../data/mobius-strip.mesh -o -1 -sc
//
// Device sample runs:
//               mpirun -np 4 ex1p -pa -d cuda
//               mpirun -np 4 ex1p -fa -d cuda
//               mpirun -np 4 ex1p -pa -d occa-cuda
//               mpirun -np 4 ex1p -pa -d raja-omp
//               mpirun -np 4 ex1p -pa -d ceed-cpu
//               mpirun -np 4 ex1p -pa -d ceed-cpu -o 4 -a
//               mpirun -np 4 ex1p -pa -d ceed-cpu -m ../data/square-mixed.mesh
//               mpirun -np 4 ex1p -pa -d ceed-cpu -m ../data/fichera-mixed.mesh
//             * mpirun -np 4 ex1p -pa -d ceed-cuda
//             * mpirun -np 4 ex1p -pa -d ceed-hip
//               mpirun -np 4 ex1p -pa -d ceed-cuda:/gpu/cuda/shared
//               mpirun -np 4 ex1p -pa -d ceed-cuda:/gpu/cuda/shared -m ../data/square-mixed.mesh
//               mpirun -np 4 ex1p -pa -d ceed-cuda:/gpu/cuda/shared -m ../data/fichera-mixed.mesh
//               mpirun -np 4 ex1p -m ../data/beam-tet.mesh -pa -d ceed-cpu
//
// Description:  This example code demonstrates the use of MFEM to define a
//               simple finite element discretization of the Poisson problem
//               -Delta u = 1 with homogeneous Dirichlet boundary conditions.
//               Specifically, we discretize using a FE space of the specified
//               order, or if order < 1 using an isoparametric/isogeometric
//               space (i.e. quadratic for quadratic curvilinear mesh, NURBS for
//               NURBS mesh, etc.)
//
//               The example highlights the use of mesh refinement, finite
//               element grid functions, as well as linear and bilinear forms
//               corresponding to the left-hand side and right-hand side of the
//               discrete linear system. We also cover the explicit elimination
//               of essential boundary conditions, static condensation, and the
//               optional connection to the GLVis tool for visualization.

#include "mfem.hpp"
#include <fstream>
#include <iostream>
#include <chrono>
#include "../fem/gslib.hpp"

using namespace std;
using namespace mfem;

class RegionShowCoeff : public Coefficient
{
public:
   virtual double Eval(ElementTransformation &T,
                       const IntegrationPoint &ip)
   {
      const int attr = T.Attribute;
      return attr;
   }
};

class RegionCoefficient : public Coefficient
{
public:
   virtual double Eval(ElementTransformation &T,
                       const IntegrationPoint &ip)
   {
      const int attr = T.Attribute;
      if (attr == 2 || attr == 3) { return 1.0; }  // rectangle + circle
      return 0.0;                     // background
   }
};

class CircleCoefficient : public Coefficient
{
public:
   virtual double Eval(ElementTransformation &T,
                       const IntegrationPoint &ip)
   {
      const int attr = T.Attribute;
      if (attr == 3) { return 1.0; }  // circle
      return 0.0;                     // background
   }
};

class RectSliceCoefficient : public Coefficient
{
public:
   double yval;
   double tol;
   RectSliceCoefficient(double yval_, double tol_) : yval(yval_), tol(tol_) {}
   
   virtual double Eval(ElementTransformation &T,
                       const IntegrationPoint &ip)
   {
      const int attr = T.Attribute;
	  Vector x(T.GetSpaceDim());
      T.Transform(ip, x);
      double y = x(1);  // x(0) = x, x(1) = y in 2D
	  
      if (attr == 2) { return 1.0 * (abs(y - yval) < tol ? 1.0 : 0.0  ); }  // rectangle
      return 0.0;                     // background
   }
};

class AnisotropicSigma : public MatrixCoefficient
{
public:
   AnisotropicSigma() : MatrixCoefficient(2) { }

   virtual void Eval(DenseMatrix &K,
                     ElementTransformation &T,
                     const IntegrationPoint &ip)
   {
      int attr = T.Attribute;
      K.SetSize(2);
      K = 0.0;

      if (attr == 2) // rectangle
      {
         double alpha = 1e4; // big number to suppress x-variation
         K(0,0) = alpha;     // weight on u_x
         K(1,1) = 1.0;       // weight on u_y
      }
      else if (attr == 3) // circle conductor region
      {
         // Make gradient expensive in all directions → nearly constant
         double beta = 1e6;
         K(0,0) = beta;
         K(1,1) = beta;
      }
      else // background
      {
         K(0,0) = 1.0;
         K(1,1) = 1.0;
      }
   }
};

class AxisymmetricSigma : public MatrixCoefficient
{
public:
   AxisymmetricSigma() : MatrixCoefficient(2) { }

   virtual void Eval(DenseMatrix &K,
                     ElementTransformation &T,
                     const IntegrationPoint &ip)
   {
      int attr = T.Attribute;
      K.SetSize(2);
      K = 0.0;
	  

      if (attr == 2) // rectangle
      {
         double alpha = 1e4; // big number to suppress x-variation
         K(0,0) = alpha;     // weight on u_x
         K(1,1) = 1.0;       // weight on u_y
      }
      else if (attr == 3) // circle conductor region
      {
         // Make gradient expensive in all directions → nearly constant
         double beta = 1e6;
         K(0,0) = beta;
         K(1,1) = beta;
      }
      else // background
      {
         K(0,0) = 1.0;
         K(1,1) = 1.0;
      }
	  Vector X(T.GetSpaceDim());
	  T.Transform(ip, X);
	  double r = X(0); // radius
	  K *= r;
	  
   }
};

double AverageOverAttr(const ParGridFunction &u, int attr_k)
{
   ParMesh *pmesh = u.ParFESpace()->GetParMesh();
   //const int dim = pmesh->Dimension();

   double num_local = 0.0;
   double den_local = 0.0;

   for (int e = 0; e < pmesh->GetNE(); e++)
   {
      if (pmesh->GetElement(e)->GetAttribute() != attr_k) { continue; }

      ElementTransformation *T = pmesh->GetElementTransformation(e);
      const FiniteElement *fe = u.ParFESpace()->GetFE(e);

      const IntegrationRule &ir =
         IntRules.Get(fe->GetGeomType(), 2*fe->GetOrder() + 2);

      Vector uvals(ir.GetNPoints());
      u.GetValues(e, ir, uvals);

      for (int q = 0; q < ir.GetNPoints(); q++)
      {
         const IntegrationPoint &ip = ir.IntPoint(q);
         T->SetIntPoint(&ip);
         const double w = ip.weight * T->Weight();   // dΩ weight
         num_local += w * uvals(q);
         den_local += w;
      }
   }

   double num = 0.0, den = 0.0;
   MPI_Allreduce(&num_local, &num, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
   MPI_Allreduce(&den_local, &den, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);

   return (den > 0.0) ? (num/den) : 0.0;
}


int main(int argc, char *argv[])
{
   //Start Timer
   auto start = chrono::high_resolution_clock::now();
	
	
   // 1. Initialize MPI and HYPRE.
   Mpi::Init();
   int num_procs = Mpi::WorldSize();
   int myid = Mpi::WorldRank();
   Hypre::Init();

   // 2. Parse command-line options.
   const char *mesh_file = "../data/star.mesh";
   int order = 1;
   bool static_cond = false;
   bool pa = false;
   bool fa = false;
   const char *device_config = "cpu";
   bool visualization = true;
   double RectHeight = 0.7;
   double RectWidth = 0.1;
   double Cx = 0.35, Cy = 1.2;
   double Rx = 0.1, Ry = 0.3;
   double Rad = 0.1;
   int NumSlices = 10;
 
   OptionsParser args(argc, argv);
   args.AddOption(&mesh_file, "-m", "--mesh",
                  "Mesh file to use.");
   args.AddOption(&order, "-o", "--order",
                  "Finite element order (polynomial degree) or -1 for"
                  " isoparametric space.");
   args.AddOption(&static_cond, "-sc", "--static-condensation", "-no-sc",
                  "--no-static-condensation", "Enable static condensation.");
   args.AddOption(&pa, "-pa", "--partial-assembly", "-no-pa",
                  "--no-partial-assembly", "Enable Partial Assembly.");
   args.AddOption(&fa, "-fa", "--full-assembly", "-no-fa",
                  "--no-full-assembly", "Enable Full Assembly.");
   args.AddOption(&device_config, "-d", "--device",
                  "Device configuration string, see Device::Configure().");
   args.AddOption(&visualization, "-vis", "--visualization", "-no-vis",
                  "--no-visualization",
                  "Enable or disable GLVis visualization.");
   args.AddOption(&RectHeight, "-rh", "--rect-height",
                  "Height of Rectangle");
   args.AddOption(&RectWidth, "-rw", "--rect-width",
                  "Width of Rectangle");
   args.AddOption(&Rx, "-rx", "--rect-x0",
                  "x0 coord of Rectangle");				  
   args.AddOption(&Ry, "-ry", "--rect-y0",
                  "y0 coord of Rectangle");		
   args.AddOption(&Rad, "-rad", "--radius",
                  "Radius of Circle");
   args.AddOption(&Cx, "-cx", "--circle-x0",
                  "x0 coord of Circle");				  
   args.AddOption(&Cy, "-cy", "--circle-y0",
                  "y0 coord of Circle");	
   args.AddOption(&NumSlices, "-ns", "--num-slices",
                  "Number of discretized wire wrappings");					  
   args.Parse();
   if (!args.Good())
   {
      if (myid == 0)
      {
         args.PrintUsage(cout);
      }
      return 1;
   }
   if (myid == 0)
   {
      args.PrintOptions(cout);
   }

   // 3. Enable hardware devices such as GPUs, and programming models such as
   //    CUDA, OCCA, RAJA and OpenMP based on command line options.
   Device device(device_config);
   if (myid == 0) { device.Print(); }

   // 4. Read the (serial) mesh from the given mesh file on all processors.  We
   //    can handle triangular, quadrilateral, tetrahedral, hexahedral, surface
   //    and volume meshes with the same code.
   int nx = 20;  // number of elements in x
   int ny = 40; // number of elements in y (taller domain)

   Mesh mesh = Mesh::MakeCartesian2D(
      nx, ny,
      Element::TRIANGLE,
      true,      // generate_edges
      1.0,       // width in x: [0,1]
      2.0        // height in y: [0,2]
   );
   mesh.EnsureNodes();
   int dim = mesh.Dimension();
   
   int n_ref_levels = 3;
   for (int level = 0; level < n_ref_levels; level++)
   {
      Array<int> el_to_refine;
      el_to_refine.Reserve(mesh.GetNE());

      for (int i = 0; i < mesh.GetNE(); i++)
      {
         ElementTransformation *T = mesh.GetElementTransformation(i);

         IntegrationPoint ip; ip.Set2(1.0/3.0, 1.0/3.0);
         Vector x(mesh.Dimension());
         T->Transform(ip, x);

         double xx = x(0), yy = x(1);

         // --- your geometric tests ---
         bool near_circle = false;
         {
            double dx = xx - Cx, dy = yy - Cy;
            double R = Rad, band = 0.08 - level*0.025;
            double r2 = dx*dx + dy*dy;
            double Rin = R - band, Rout = R + band;
            near_circle = (r2 >= Rin*Rin && r2 <= Rout*Rout);
         }

         bool near_rect = false;
         {
            double x0 = Rx, x1 = x0 + RectWidth, y0 = Ry, y1 = y0 + RectHeight;
            double pad = 0.04 - level*0.015;
            near_rect = (xx >= x0 - pad && xx <= x1 + pad &&
                         yy >= y0 - pad && yy <= y1 + pad);
         }

         if (near_circle || near_rect) { el_to_refine.Append(i); }
      }

      // Triangles: local refinement is typically kept conforming by propagation
      if (el_to_refine.Size() > 0)
      {
         mesh.GeneralRefinement(el_to_refine); // triangles: conforming refinement
      }
   } 
   mesh.EnsureNodes();
   

   for (int i = 0; i < mesh.GetNE(); i++)
   {
      ElementTransformation *T = mesh.GetElementTransformation(i);

      // center of the reference element: (1/3,1/3) for triangles
      IntegrationPoint ip;
      ip.Set2(1.0/3.0, 1.0/3.0);

      Vector x(dim);
      T->Transform(ip, x);
      double xx = x(0);
      double yy = x(1);

      int attr = 1; // background
   

      // 2) rectangle [0.2,0.3] x [0.3,1.2]
      if (xx >= Rx && xx <= Rx + RectWidth && yy >= Ry && yy <= Ry + RectHeight)
      {
         attr = 2;
      }

      // 3) circle centered at (0.5, 1.5) with radius 0.3
      double dx = xx - Cx;
      double dy = yy - Cy;
      if (dx*dx + dy*dy <= Rad*Rad)
      {
         attr = 3;
      }

      mesh.GetElement(i)->SetAttribute(attr);
   }
   
   //Set Boundary Attributes
   for (int i = 0; i < mesh.GetNBE(); i++)
   {
      Element *be = mesh.GetBdrElement(i);
      ElementTransformation *T = mesh.GetBdrElementTransformation(i);

      IntegrationPoint ip;
      //ip.Set1(0.5); // midpoint of the boundary edge

      Vector x(dim);
      T->Transform(ip, x);
      double xx = x(0);
      double yy = x(1);

      int battr = 0;
      const double eps = 1e-8;

      if (fabs(yy - 0.0) < eps)      { battr = 1; } // bottom
      else if (fabs(xx - 1.0) < eps) { battr = 2; } // right
      else if (fabs(yy - 2.0) < eps) { battr = 3; } // top
      else if (fabs(xx - 0.0) < eps) { battr = 4; } // left

      be->SetAttribute(battr);
   }
   
   // Update the internal attribute list
   mesh.SetAttributes();
   
   
   

   // 5. Refine the serial mesh on all processors to increase the resolution. In
   //    this example we do 'ref_levels' of uniform refinement. We choose
   //    'ref_levels' to be the largest number that gives a final mesh with no
   //    more than 10,000 elements.
   {
      int ref_levels =
         (int)floor(log(100000./mesh.GetNE())/log(2.)/dim);
      for (int l = 0; l < ref_levels; l++)
      {
         //mesh.UniformRefinement();
      }
   }

   // 6. Define a parallel mesh by a partitioning of the serial mesh. Refine
   //    this mesh further in parallel to increase the resolution. Once the
   //    parallel mesh is defined, the serial mesh can be deleted.
   ParMesh pmesh(MPI_COMM_WORLD, mesh);
   mesh.Clear();
   {
      int par_ref_levels = 2;
      for (int l = 0; l < par_ref_levels; l++)
      {
         //pmesh.UniformRefinement();
      }
   }
   
   

   // 7. Define a parallel finite element space on the parallel mesh. Here we
   //    use continuous Lagrange finite elements of the specified order. If
   //    order < 1, we instead use an isoparametric/isogeometric space.
   FiniteElementCollection *fec;
   bool delete_fec;
   if (order > 0)
   {
      fec = new H1_FECollection(order, dim);
      delete_fec = true;
   }
   else if (pmesh.GetNodes())
   {
      fec = pmesh.GetNodes()->OwnFEC();
      delete_fec = false;
      if (myid == 0)
      {
         cout << "Using isoparametric FEs: " << fec->Name() << endl;
      }
   }
   else
   {
      fec = new H1_FECollection(order = 1, dim);
      delete_fec = true;
   }
   ParFiniteElementSpace fespace(&pmesh, fec);
   HYPRE_BigInt size = fespace.GlobalTrueVSize();
   if (myid == 0)
   {
      cout << "Number of finite element unknowns: " << size << endl;
   }

   // 8. Determine the list of true (i.e. parallel conforming) essential
   //    boundary dofs. In this example, the boundary conditions are defined
   //    by marking all the external boundary attributes from the mesh as
   //    essential (Dirichlet) and converting them to a list of true dofs.

   Array<int> ess_tdof_list;
   Array<int> ess_bdr(pmesh.bdr_attributes.Max());
   ess_bdr = 0;
   if (pmesh.bdr_attributes.Size() > 0)
   {
      ess_bdr[0] = 1; // attr 1 -> bottom
      ess_bdr[1] = 1; // attr 2 -> right
      ess_bdr[2] = 1; // attr 3 -> top 
   }
   fespace.GetEssentialTrueDofs(ess_bdr, ess_tdof_list);


   // 9. Set up the parallel linear form b(.) which corresponds to the
   //    right-hand side of the FEM linear system, which in this case is
   //    (1,phi_i) where phi_i are the basis functions in fespace.
   ParLinearForm b(&fespace);
   ConstantCoefficient one(1.0);
   RegionCoefficient VoltsConst;
   CircleCoefficient CircleVolts;
   
   
   // 10. Define the solution vector x as a parallel finite element grid
   //     function corresponding to fespace. Initialize x with initial guess of
   //     zero, which satisfies the boundary conditions.
   ParGridFunction x(&fespace);
   x = 0.0;


   // 11. Set up the parallel bilinear form a(.,.) on the finite element space
   //     corresponding to the Laplacian operator -Delta, by adding the
   //     Diffusion domain integrator.
   ParBilinearForm a(&fespace);
   if (pa) { a.SetAssemblyLevel(AssemblyLevel::PARTIAL); }
   if (fa)
   {
      a.SetAssemblyLevel(AssemblyLevel::FULL);
      // Sort the matrix column indices when running on GPU or with OpenMP (i.e.
      // when Device::IsEnabled() returns true). This makes the results
      // bit-for-bit deterministic at the cost of somewhat longer run time.
      a.EnableSparseMatrixSorting(Device::IsEnabled());
   }
   
   
   AxisymmetricSigma sigma;   
   a.AddDomainIntegrator(new DiffusionIntegrator(sigma));

   // 12. Assemble the parallel bilinear form and the corresponding linear
   //     system, applying any necessary transformations such as: parallel
   //     assembly, eliminating boundary conditions, applying conforming
   //     constraints for non-conforming AMR, static condensation, etc.
   if (static_cond) { a.EnableStaticCondensation(); }
   a.Assemble();

   OperatorPtr A;
   Vector B, X;

   // 13. Solve the linear system A X = B.
   //     * With full assembly, use the BoomerAMG preconditioner from hypre.
   //     * With partial assembly, use Jacobi smoothing, for now.
   Solver *prec = NULL;
   prec = new HypreBoomerAMG;

   CGSolver cg(MPI_COMM_WORLD);
   cg.SetRelTol(1e-12);
   cg.SetMaxIter(2000);
   cg.SetPrintLevel(1);
   if (prec) { cg.SetPreconditioner(*prec); }
   

   // 14. Recover the parallel grid function corresponding to X. This is the
   //     local finite element solution on each processor.
   
   
   DenseMatrix C(NumSlices,NumSlices);                    // C matrix to fill up
   
   FindPointsGSLIB finder(MPI_COMM_WORLD);
   finder.Setup(pmesh);
   mfem::Vector point_pos(2*NumSlices), values(NumSlices);
   for (int j = 0; j < NumSlices; j++)
   {  point_pos[j] = Rx + RectWidth/2;
      point_pos[NumSlices + j] = Ry + RectHeight*(1 + 2*j)/20;
   }
   
   //Run simulation
   for(int i = 0; i < NumSlices; i++){
	   
	  b = 0.0;
	  RectSliceCoefficient RectVoltsSlice(Ry + RectHeight*(1 + 2*i)/2/NumSlices, RectHeight/NumSlices/2);
      b.AddDomainIntegrator(new DomainLFIntegrator(RectVoltsSlice));
      b.Assemble();
	  
	  a.FormLinearSystem(ess_tdof_list, x, b, A, X, B);
	  cg.SetOperator(*A);
      cg.Mult(B, X);
	  a.RecoverFEMSolution(X, b, x);
	   
      finder.Interpolate(point_pos, x, values, mfem::Ordering::byNODES);
   
      for(int j = 0; j<NumSlices; j++){
	     C(i,j) = values[j]; 
      }
	    
   }
   delete prec;
   
   //Print C matrix
   if(myid == 0){ 
      for(int i=0; i<NumSlices; i++){
	      for(int j=0; j<NumSlices; j++){
		     mfem::out << " " << C(i,j) << " "; 
	      }
		  mfem::out << " \n"; 
      }
   }
   
   
   //mfem::Vector evals;
   //mfem::DenseMatrix evecs;
   //C.Eigenvalues(evals, evecs);
   
   mfem::DenseMatrixEigensystem es(C);
   es.Eval();
   mfem::Vector &evals = es.Eigenvalues();
   mfem::DenseMatrix &evecs = es.Eigenvectors();
   if (myid == 0)
   {
      mfem::out << "Eigenvalues:\n";
      for (int k = 0; k < evals.Size(); k++)
      {
         mfem::out << "  lambda[" << k << "] = " << evals[k] << "\n";
      }

      mfem::out << "\nEigenvectors (columns):\n";
      for (int k = 0; k < evals.Size(); k++)
      {
         mfem::out << "v[" << k << "] = [";
         for (int i = 0; i < C.Height(); i++)
         {
            mfem::out << evecs(i,k) << (i+1 == C.Height() ? "" : ", ");
         }
         mfem::out << "]\n";
      }
   }

   //End timer
   auto end = chrono::high_resolution_clock::now();
   std::chrono::duration<double> duration = end - start;
   double elapsed_seconds = duration.count();
   cout << "Execution time: " << elapsed_seconds << " seconds." << endl;   

   // 15. Save the refined mesh and the solution in parallel. This output can
   //     be viewed later using GLVis: "glvis -np <np> -m mesh -g sol".
   {
      ostringstream mesh_name, sol_name;
      mesh_name << "mesh." << setfill('0') << setw(6) << myid;
      sol_name << "sol." << setfill('0') << setw(6) << myid;

      ofstream mesh_ofs(mesh_name.str().c_str());
      mesh_ofs.precision(8);
      pmesh.Print(mesh_ofs);

      ofstream sol_ofs(sol_name.str().c_str());
      sol_ofs.precision(8);
      //x.Save(sol_ofs);
   }

   // 16. Send the solution by socket to a GLVis server.
   if (visualization)
   {
      char vishost[] = "localhost";
      int  visport   = 19916;
      socketstream sol_sock(vishost, visport);
      sol_sock << "parallel " << num_procs << " " << myid << "\n";
      sol_sock.precision(8);
      sol_sock << "solution\n" << pmesh << x << flush;
   }

   // 17. Free the used memory.
   if (delete_fec)
   {
      delete fec;
   }

   return 0;
}
