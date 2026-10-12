# Multi-element Optimizer

A Windows desktop application for designing and optimizing two-dimensional,
multi-element airfoil assemblies. Build a setup with up to five independently
sized airfoils, search their arrangement for maximum **Cl**, and export a complete
design record.

**Current aerodynamic backend: JavaFoil.** CFD cross-checks and a higher-fidelity
Euler + boundary-layer final-solution stage are future work, not current features.

## What it does

- **Adjust positions:** keep chords fixed and optimize element angles, slot gaps
  and overlaps.
- **Size & fit:** optimize chord lengths and placement within geometric bounds.
  Select any combination of elements and require their highest points to remain
  below a specified height above the reference plane or ground.
- Choose profiles from family-organized Selig, Eppler, Benzing, MSHD and other
  libraries, generate NACA four-digit sections, or import coordinate files.
  MSHD is explicitly marked as a figure-derived approximation.
- Enter lengths in m, cm, mm, inches or feet. Set element angles either absolutely
  or relative to the previous element; specify fixed values, ranges or lists.
- Enable inverted car orientation and JavaFoil's flat-ground model, with ground
  and clearance shown in the preview.
- Use coarse sweeps followed by fine refinement. Choose the sweep resolution and
  number of parallel JavaFoil processes, limited to available physical cores.
- Preview geometry, stop a run, inspect its history, and save results anywhere.

## Installation from source

The supported desktop environment is **64-bit Windows**, with **Python 3.11 or
newer including Tkinter**, and a **Java 17 JDK** (`java` and `javac` on PATH).
The repository contains source and airfoil data; it does not contain the bundled
Python/Java runtimes, downloaded JARs, personal run folders or research downloads.

From a terminal in the repository folder:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r docs\requirements.txt
.venv\Scripts\python.exe tools\setup.py --skip-python
.venv\Scripts\python.exe app\app.py
```

After setup, `Launch.cmd` opens the app using the virtual environment. In a local
portable installation it uses the bundled runtime instead.

Setup downloads JavaFoil from its official distribution and scripting libraries
from Maven Central. It builds a local compatibility copy that fixes modern Java
version detection and suppresses the startup age reminder, keeping the original
JAR intact. Aerodynamic calculations are unchanged by those compatibility fixes.
JavaFoil remains subject to its author's terms; it is not relicensed by this repo.

## Typical workflow

1. Open **Adjust positions** or **Size & fit** and add one to five airfoils.
2. Set dimensions, angle conventions and search ranges. For Size & fit, add
   height ceilings for the chosen elements. A fixed value locks a parameter.
3. Set wingspan and relative airspeed. Standard sea-level air is the default;
   advanced settings expose air properties, transition, panel count and overrides.
4. Optionally enable ground effect and flip the setup for downforce.
5. Preview the geometry, choose search fidelity and physical-core workers, then
   select **Optimize**. Use **Stop** to retain completed results from a partial run.
6. Select **Save design** and choose a destination folder.

Example configurations are in [examples](examples/). The detailed guide is in
[docs/README.md](docs/README.md).

## Search and aerodynamic conventions

The default coarse step is one tenth of each continuous parameter range. Fine
refinement searches **winner +/- 2.5% of the full parameter range width**, clipped
to the original bounds. Fine-step size is user-defined as a percentage of that
same range width (default 0.25%). For a 100-300 mm range, a 200 mm winner is refined
from 195 to 205 mm in 0.5 mm steps. Explicit discrete lists are not subdivided.

Size & fit searches joint combinations within selected height groups, in the
order **chords, angles, slot gaps, overlaps**. Each stage carries its best valid
solution into the next stage. Intersections, clearance and height ceilings are
checked before a solver run. Later passes revisit coupled parameters.

There is no simulation-count cap. Search stops on the implemented local
convergence checks, the configured sweep-round limit, or user cancellation.
This is a bounded local search; it does not guarantee a global maximum.
Independent candidates run in separate JavaFoil processes. On Windows each
process is pinned to a selected physical core; short batches can use fewer
workers than requested.

The objective is always displayed as **Cl**. In normal orientation it is
upward-positive; with the downforce flip it is downward-positive. Signed lift
and downforce coefficients are also retained. A fixed reference chord keeps
coefficient comparisons consistent while chords change.

Reynolds number uses airspeed and chord: `Re = density * speed * chord / viscosity`.
Wingspan controls JavaFoil's approximate aspect-ratio correction, not the Reynolds
length scale. Set the advanced aspect-ratio override to zero for a 2D section
comparison. Ground effect is a flat-ground mirror model; it does not model a
complete car, rotating wheels or three-dimensional diffuser flow.

## Saved results

Each run retains geometry, configuration, coefficients, solver cases and search
history. **Save design** creates a new folder without replacing existing files:

- PDF with the winning coefficients, geometry, dimensions, settings and numerical
  surface-data tables.
- Two **3840 x 2160 PNG** graphs: surface pressure coefficient and surface velocity.
  Both also appear in the PDF.
- CSV files for pressure, velocity, setup dimensions and sweep results.
- CAD geometry, input profiles and a replayable winning configuration.
- Native JavaFoil surface exports and a reproduced winning polar.

Pressure/velocity contours, flow lines and a separate top-three validation solver
are not included in this release. Historical runs from a retired backend remain
on disk, but must be rerun with JavaFoil before exporting in this version.

## Accuracy and validation

JavaFoil provides fast panel/boundary-layer estimates with empirical stall and
finite-span corrections. Narrow slots, strong separation and maximum-lift
conditions can exceed this model's useful range. More search iterations do not
by themselves increase aerodynamic fidelity. Treat the output as a design
candidate requiring independent verification.

The automated suite checks geometry, units, height ceilings, refinement windows,
parallel execution, cancellation, UI behavior and exports. These software checks
are distinct from aerodynamic validation. See [validation notes](docs/VALIDATION.md).

To run the suite on Windows:

```powershell
$env:PYTHONPATH = "$PWD\app"
$env:PYTHONUTF8 = "1"
.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py" -v
```

## Future plans

### Cross-reference results with CFD

- Build reproducible single- and multi-element benchmark cases, including ground
  clearance, slot-gap and overlap sweeps, before trusting maximum-Cl predictions.
- Export matching geometries and operating conditions to an independent viscous
  CFD workflow, starting with 2D RANS and selected 3D wing/car configurations.
- Match Reynolds number, reference dimensions, angle conventions and boundary
  conditions. For ground cases, specify moving-ground treatment and domain extent.
  Compare 2D section coefficients without a finite-span correction.
- Perform mesh, domain and convergence studies. Compare Cl, Cd, Cm, surface Cp,
  separation locations and wake behavior; record discrepancies and uncertainty.
- Cross-check shortlisted designs, including near-optimal alternatives, rather
  than validating only a potentially misleading single peak. Add experimental
  comparisons where suitable data are available.

### Increase final-solution fidelity with Euler + boundary-layer solvers

- Retain JavaFoil for fast exploration, then evaluate a small shortlist using a
  genuine Euler flow solver coupled to an integral boundary-layer model.
- Support interacting elements, wakes and ground boundaries consistently in the
  outer-flow and viscous coupling. Add transition prediction and separation
  diagnostics with explicit convergence and applicability checks.
- Introduce surface/volume mesh refinement and solver-tolerance studies for final
  candidates. Rank only converged, comparable solutions and preserve each solver's
  original results and failure reasons.
- Compare the new solver against the CFD benchmarks before treating it as a
  fidelity improvement. Euler + boundary-layer coupling does not replace viscous
  CFD for strongly separated flow or establish reliable stall prediction alone.
- Once verified, add pressure contours, velocity contours and streamlines to the
  final report, clearly identifying the solver, mesh and solution quality.

These are planned development milestones, not implemented capabilities or claims
of validated accuracy.

## Project layout

| Folder | Contents |
| --- | --- |
| `app/` | Desktop UI, geometry, optimization, JavaFoil adapter and reporting |
| `assets/airfoils/` | Coordinate library and provenance |
| `examples/` | Ready-to-load configurations |
| `tests/` | Automated regression tests |
| `tools/` | Setup, launch helpers and Java compatibility source |
| `docs/` | User guide, validation notes and upstream geometry reference |
| `runtime/`, `runs/` | Local generated dependencies/results; excluded from Git |

## Credits and licensing

Geometry generation reimplements and extends Nick Morse's
[MultiElementWingGenerator](https://github.com/nick-morse/MultiElementWingGenerator).
Its MIT notice and original geometry script are retained in `docs/reference/`.
The application source is distributed under the [MIT license](LICENSE), preserving
upstream attribution.

The simulation backend is Martin Hepperle's
[JavaFoil](https://www.mh-aerotools.de/airfoils/jf_applet.htm); see its
[multi-element documentation](https://www.mh-aerotools.de/airfoils/jf_multi.htm).
JavaFoil and other dependencies retain their own licenses and terms. Third-party
airfoil coordinates are documented separately in
[coordinate sources](assets/airfoils/SOURCES.md) and `assets/airfoils/library.json`;
the application's MIT license does not override those data sources' terms.
