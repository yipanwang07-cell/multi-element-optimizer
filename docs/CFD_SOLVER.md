# Optional 2D viscous CFD check

The fast optimization backend remains JavaFoil. After a sweep, use **Check best
with CFD** in either function's Results tab to analyze the saved winner using
SU2 8.5.0. This is an independent analysis, not an automatic replacement or
re-ranking of the JavaFoil sweep. No CFD accuracy claim follows from installation.

## Method and source code

- [SU2 source, pinned v8.5.0](https://github.com/su2code/SU2/tree/v8.5.0):
  incompressible Reynolds-averaged Navier–Stokes (`INC_RANS`), with SST 2003m
  turbulence closure, no-slip airfoil surfaces, and optional Langtry–Menter
  transition. Momentum and viscous stresses are solved throughout the mesh.
- [SST implementation](https://github.com/su2code/SU2/blob/v8.5.0/SU2_CFD/src/solvers/CTurbSSTSolver.cpp).
- [Transition implementation](https://github.com/su2code/SU2/blob/v8.5.0/SU2_CFD/src/solvers/CTransLMSolver.cpp).
- [Output definitions](https://github.com/su2code/SU2/blob/v8.5.0/SU2_CFD/src/output/CFlowIncOutput.cpp)
  supply pressure coefficient, wall shear and y+.
- [Gmsh](https://gmsh.info/) 4.15.0 generates a 2D domain with a hole for each
  airfoil and near-wall boundary-layer cells. Each mesher runs in its own process.
- [SU2's official airfoil tutorial](https://su2code.github.io/tutorials/Inc_Turbulent_NACA0012/)
  provides the incompressible setup and reference scaling conventions.

The adapter is original project code; it calls the upstream executables rather
than copying their numerical implementations into this MIT-licensed application.
SU2 retains its LGPL license and Gmsh its GPL license. Optional downloads include
upstream distribution/license metadata and are not committed to this repository.

## Why this method

JavaFoil's uncoupled panel/boundary-layer analysis and empirical stall correction
can produce unreliable results for large separated regions. SST RANS provides a
viscous flow-field calculation that can exhibit recirculation and wall-shear
reversal. Transition modelling is optional and uses 1% freestream turbulence in
this initial UI. JavaFoil's stall/transition dropdowns do not configure SU2.

Other sources reviewed:

- [MFOIL](https://websites.umich.edu/~kfid/codes.html): coupled panel/integral
  boundary-layer analysis, valuable for single-airfoil verification. It is not a
  drop-in multi-element ground-effect solver for this application.
- [NFoil](https://github.com/cayetanomarmur/NFoil): a Numba-accelerated MFOIL
  derivative; its public workflow is for single airfoils.
- [PyMISES](https://github.com/TechNektar/PyMISES): advertises Euler/boundary-layer
  coupling, but its own README lists comprehensive validation as planned. It was
  not adopted as a verified replacement based on those claims.

## Installation

Windows:

```powershell
python tools/setup_cfd.py
```

The installer downloads official SU2/Gmsh versions with pinned SHA-256 checksums.
Restart the app after installing. Other platforms can supply SU2 through the `SU2_CFD` environment
variable and install Gmsh, but are not tested by this Windows installer.

## Use and interpretation

1. Complete or stop an optimization with a saved best design.
2. Choose **Standard** or **Fine** and **Fully turbulent SST** or **SST + transition**.
3. Select **Check best with CFD**. Stop cancels the external process.
4. Review the separate HTML report, convergence history, surface CSV (Cp, skin
   friction, y+), and ParaView volume file retained in the run's `cfd_*` folder.
5. Repeat with a finer mesh and larger domain; compare coefficients and surface
   distributions. This check does not yet automate mesh-independence validation.

The geometry is normalized by the fixed reference chord. Density and velocity
are unity and viscosity is 1/Re, giving matching Reynolds number and consistent
2D coefficients. No aspect-ratio or empirical stall correction is applied.
The result's Cl follows the app's downforce sign convention; raw signed lift is
also retained. Ground is a slip/symmetry plane at y = 0, not a no-slip stationary
floor or a resolved moving-wall boundary layer.

The report checks residual reduction, final flow residuals, coefficient stability
and maximum y+. A completed process alone is not convergence. Non-converged results
are retained and prominently labelled; they do not replace the optimization winner.
Reverse wall-shear sample counts away from the first/last 5% of chord are indicators
of possible separation, not an accurate separated-area percentage or stall location.

Steady RANS may not converge for massive/unsteady separation. Such cases can need
URANS and additional validation. Wall y+, panel/surface resolution, domain size,
transition assumptions and turbulence model all require sensitivity checks. This
release has integration smoke tests, not experimental validation of multi-element
high-lift or ground-effect maxima.

## Verification

Run `python tools/smoke_cfd.py` for opt-in real solver integration checks:
a single NACA 0012 with transition and a two-element setup above the slip floor.
These short runs test meshing, solver execution, output diagnostics and failure
classification; they are deliberately not aerodynamic accuracy benchmarks.
The CFD job uses one CPU thread and runs separately from sweep worker settings.
