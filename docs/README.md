# Multi-element Optimizer - user guide

For installation requirements and source setup, see the [project README](../README.md).
After setup, launch with `Launch.cmd` from the repository root.
The local portable build also supports the bundled runtime.

## Airfoils, families and units

Each element has linked Family and Profile dropdowns. Select Benzing, Selig, Eppler, Motorsport, Wortmann, Comparison or NACA, then select a profile from that family. Library preview opens the searchable outline/source browser. Browse DAT imports a custom Selig-order coordinate file.

There are 83 installed offline coordinate profiles plus generated NACA four-digit choices. See [the sourced catalog](../assets/airfoils/SOURCES.md). MSHD is explicitly marked figure-derived: it is an approximate recovery of the original thesis's vector outline, not an author-supplied numeric DAT. This qualification remains in saved provenance and reports.

Each element has its own length unit: m, cm, mm, in or ft. Chord, vertical gap and overlap use that element's unit. Thus a main element may use millimetres while a flap uses inches. The Reference length unit controls reference chord, minimum surface clearance, bounding-box dimensions .

Changing a unit converts the entered numbers and range endpoints to preserve physical dimensions. Changing the reference unit also converts elements still using the previous default; independently selected units remain independent.

Imported airfoil x/y coordinates are normalized before chord scaling. Their original length units therefore cancel; the entered physical chord determines the final dimensions.

## Angle modes

Every element after the first can use:

- Absolute: the entered angle is measured from the body/reference x-axis.
- Relative: the entered angle is added to the previous element's resolved absolute body angle.

The first element always uses absolute mode. Relative angles accumulate until a later element uses absolute mode and starts a new reference.

Example: element 1 at 5 degrees absolute, element 2 at 10 degrees relative, element 3 at 20 degrees absolute, element 4 at -7 degrees relative gives resolved body angles 5, 15, 20 and 13 degrees.

Positive angles rotate the leading-edge-to-trailing-edge line clockwise: nose up, trailing edge down for positive lift. The separate Reference-axis AoA offset rotates the complete assembly relative to the freestream; keep it at 0 for direct element-angle input. Effective aerodynamic AoA equals resolved body angle plus this offset. The offset is retained to support earlier configurations and optional complete-assembly polar studies.

## Entering ranges

Type a single value, a range, or a list:

    15
    0:20
    10,15,20

Angles are degrees. Gap and overlap ranges are physical lengths in the row's selected unit, not fractions of chord. A 5:25 gap in an mm row means 5 to 25 mm. No step entry is needed. A min:max range receives 10 initial intervals, giving 11 endpoint-inclusive samples.

The old min:max:step syntax remains supported for grid/random studies. In sequential mode, continuous range sweeps begin with 10 intervals regardless of the supplied legacy step. Explicit comma-separated lists are discrete allowed choices and are not continuously interpolated.

Chord is a fixed scalar for each element. Angles, gaps and overlaps are sweep parameters.

## Placement convention

The first leading edge is at (0,0). Each later leading edge is positioned relative to the preceding element's trailing-edge midpoint:

    next_LE_x = previous_TE_x - physical_overlap
    next_LE_y = previous_TE_y - physical_vertical_gap

Offsets use the assembly's fixed body axes, not the preceding element's rotated axes. Positive overlap moves the next element forward; negative overlap creates horizontal separation. Positive vertical gap places the next leading edge below the preceding trailing edge.

Vertical gap is a placement offset. It is not the shortest distance between the two airfoil surfaces. The program separately measures actual surface clearance for every pair and rejects intersection, containment, contact and insufficient clearance.

The optional box constrains assembly width and height in the body frame. It does not auto-size a flap or constrain the geometry after the reference-axis rotation. Thickness follows the chosen profile and chord. Simulation remains two-dimensional; span and endplates are not modeled.

## Sequential sweep — the default

The requested parameter order is:

1. Element 1 angle.
2. Gap between elements 1 and 2.
3. Overlap of element 2.
4. Element 2 angle.
5. Gap between elements 2 and 3.
6. Overlap of element 3.
7. Continue through the remaining elements, ending with the last element's angle.

Only one parameter changes at a time. Other parameters are held at their latest selected values. The initial configuration uses each continuous range's midpoint, or the middle choice of a discrete list.

Both optimization modes first sweep continuous parameters at 1/10 of their full ranges, then refine within ±2.5% of the full parameter range around each winning value, with user-set percentage steps (default 0.25%). There is no repeated subdivision. Equal scores retain the current point, preventing drift across numerically flat polars.

After a full pass, the program checks neighboring parameter values with all other parameters at the FINAL configuration. If a neighbor improves Cl, earlier parameters are revisited in another ordered pass. This handles interactions between elements.

A completed local check means no tested single-parameter neighbor improved Cl beyond the chosen Cl tolerance. It is a bounded coordinate local maximum at the selected range-based resolution, not proof of a continuous/global maximum. Boundary maxima are flagged so the ranges can be expanded.

Stopping outcomes are explicit:

- Bounded coordinate local maximum: final neighboring checks passed.
- Evaluation budget: the evaluation limit was reached; convergence is not claimed.
- Pass limit: the allowed passes ended; convergence is not claimed.
- Cancelled: completed results are retained.

There is no evaluation cap, including when loading legacy configurations. Cached configurations are not simulated again. Maximum sweep rounds can be adjusted in the desktop settings. Step sizes are set in each function's Simulation fidelity tab. Defaults are range/10 for coarse sweeps and 0.25% of the full parameter range for fine steps within a ±2.5% window. Legacy refinement limits and angle/length tolerances do not change these step sizes. Advanced search.cl_tolerance defaults to 0.0001.

Grid and random modes remain available. Grid tests every discrete combination and refuses a grid larger than the budget. Random samples a reproducible subset without replacement. Their completed states do not claim sequential local convergence.

## Running a study

1. Select families/profiles, enter chords and choose each element's unit.
2. Set absolute/relative angle modes and angle ranges.
3. Enter physical vertical-gap and overlap ranges for each later element.
4. Set reference chord, Reynolds number, Mach number, surface clearance and search limits.
5. Preview geometry to inspect the midrange setup and resolved angles.
6. Run optimization. The Geometry & progress tab shows each parameter sweep in physical units.
7. Stop and retain results if needed, or open the saved report after completion.

The setup tab scrolls to keep all element cards and settings accessible on smaller screens.

## Configuration and command line

The default desktop example is sequential_example.json. Earlier example.json and fsae_example.json retain their grid settings and remain readable.

    python app/wing_optimizer.py --config sequential_example.json
    python app/wing_optimizer.py --config sequential_example.json --preview --output preview
    python app/wing_optimizer.py --config sequential_example.json --output runs/my_search

Simulation output directories must be new to avoid overwrite. Default run names include a timestamp. Ctrl+C stops gracefully.

A new-format element looks like:

    {
      "profile": "S1223",
      "length_unit": "mm",
      "chord": 140,
      "angle_mode": "relative",
      "incidence_deg": {"min": 10, "max": 30},
      "gap_length": {"min": 5, "max": 25},
      "overlap_length": {"min": 0, "max": 20}
    }

Physical quantities can explicitly override the row's unit:

    "chord": {"value": 4, "unit": "in"}
    "gap_length": {"min": 0.25, "max": 0.75, "unit": "in"}

A scalar length string such as "4 in" is accepted in JSON. Desktop fields use the unit dropdown and numeric entries.

Global physical fields include reference_chord, minimum_clearance_length and bounding_box_lengths, using the top-level length_unit unless an explicit quantity unit is supplied. Legacy chord_m, reference_chord_m, gap/overlap fractions, minimum_clearance fractions and bounding_box fractions still work. New fields take precedence and populate those internal normalized keys automatically.

All angles use incidence_deg and per-element angle_mode. Legacy configurations default to absolute mode. The existing alpha_deg field specifies the reference-axis AoA offset or its optional uniform polar range.

Simulation settings include reynolds, mach, transition_model, transition_upper/lower, roughness, timeout_seconds, java and javafoil_dir. Transition fractions of 1.0 allow natural transition; the wrapper converts them to JavaFoil's percentage interface. The stall model is selectable: 0 = Calcfoil, 1 = Eppler (default), 2 = None.

## Coefficient reference

All geometry is divided by the SAME fixed reference_chord_m before it reaches JavaFoil:

    Cl = lift per unit span / (0.5 * density * velocity^2 * reference_chord)
    Re_reference = velocity * reference_chord / kinematic_viscosity

The program never independently normalizes each assembly to its bounding box. This keeps Cl comparisons meaningful as gap/overlap/angles change. JavaFoil adjusts Reynolds number for each element's local chord. Moment coefficients refer to (x/cref,y/cref)=(0.25,0).

The objective maximizes signed Cl. Downforce or absolute lift would require a deliberately different objective/convention.

## Saved results

- report.html: physical lengths, entered/resolved angles, search status and geometry.
- results.csv: every simulated coefficient, entered angle parameters, resolved absolute body angles, normalized placement parameters and explicit gap_m_N/overlap_m_N physical values.
- evaluations.csv: every unique attempted geometry and its success/rejection/failure.
- sweep_trace.jsonl: parameter order, coarse/refinement levels, candidate values, Cl, cache hits and final neighboring checks.
- summary.json: best observed result, counts, stopping reason, local checks and range-based resolution.
- search_history.svg: for sequential mode, evaluated Cl and best Cl so far against evaluation index.
- lift_curves.svg: reference-offset polars in grid/random mode; sequential history for backward-compatible file naming.
- config.json: rerunnable study; imported source coordinates are copied into input/.
- provenance.json and input_profiles.json: coordinate sources, unit/angle conventions, exact normalized profiles and solver JAR hashes.
- cases/g.../: solver input, geometry exported back by JavaFoil, raw polar, script and log.
- best/best_config.json: winning scalar inputs with original physical units and angle modes preserved.
- best/best.json: winning coefficients and parameters.
- best/coordinates_m.csv and element_N_solidworks.xyz: physical body-frame geometry in metres for CAD.
- best/javafoil_geometry.txt: normalized solver geometry with multielement separators.
- best/geometry.svg: body geometry.
- best/geometry_at_best_alpha.svg and coordinates_at_best_alpha_m.json: geometry at the winning reference-axis offset.
- best/polar.txt: winning raw polar.

## Validation and aerodynamic limits

Run all regression tests:

    python -m unittest discover -s . -p "test*.py" -v

The suite covers source profiles, unit conversion, mixed-unit configuration loading, chained absolute/relative angles, CLI previews, family menus, variable-count element editor controls, collisions, saved geometry, sequential order, 11-sample coarse sweeps, a single fine stage, coupled-parameter revisits, caching, cancellation and unlimited evaluations and boundary outcomes.

Actual JavaFoil checks are saved in runs/units_relative_sequential_validation. The 21-point coarse sweep used a 400 mm main element and a 4 inch second element, with a relative angle. Its final angles were 1 degree absolute and 11 degrees absolute (10 degrees relative); the physical slot placement was preserved. The winning saved configuration can reproduce the solver point.

JavaFoil uses coupled panel and boundary-layer calculations with an empirical stall correction. Closely spaced, strongly separated and high-lift flows require independent CFD or experimental validation. Geometry checks and local optimization do not establish physical accuracy or convergence of the aerodynamic model.

## Sources

The geometry workflow reimplements and extends Nick Morse's [MultiElementWingGenerator](https://github.com/nick-morse/MultiElementWingGenerator), MIT license; original source and license are retained in docs/reference/.

Martin Hepperle's [JavaFoil multielement documentation](https://www.mh-aerotools.de/airfoils/jf_multi.htm) provides the solver format, complete-element force selection, coefficient references and multielement stall-model guidance. JavaFoil is downloaded from its [official distribution](https://www.mh-aerotools.de/airfoils/jf_applet.htm), under its author's terms. Nashorn, ASM, Shapely and NumPy retain their own bundled license notices.

Exact coordinate sources and hashes are in ../assets/airfoils/library.json and [../assets/airfoils/SOURCES.md](../assets/airfoils/SOURCES.md).


## Free optimization with group height limits

Open **Size & fit**. This tab contains its own airfoil inputs, height limits, simulation settings, preview, and results.
Add any number of height limits, select the element numbers in each group, and enter a maximum height and unit. For example: elements 1+2 at 200 mm and elements 3+4 at 200 mm. Groups can overlap or select nonadjacent elements.

Enter physical chord ranges as well as angle, gap, and overlap ranges in this tab (e.g. chord 100:300 in mm). Single values fix parameters. Set the reference-axis angle offset to 0; element angles support the existing absolute and relative choices. A fixed reference chord makes Cl comparable as element chords change. Reference Reynolds number is calculated from the relative airspeed and that reference chord; element Reynolds numbers scale with each element's actual chord.

The optimizer finds a feasible initial geometry using geometry-only trials, then sweeps all chords in element order, all element angles, all gaps, and all overlaps. The coarse stage uses 10 intervals for continuous ranges and carries each winner into the next parameter sweep. After all coarse sweeps, one fine stage revisits the parameters near their winners within ±2.5% of the full parameter range around their winners, with steps expressed as a percentage of that range. Further passes revisit coupled parameters and verify local neighbors. This is bounded local optimization; range limits and the configured sweep-round limit still apply.

Height is the absolute y coordinate of each selected airfoil's highest outline point, measured from y = 0 after orientation and ground-clearance placement. Intersections, clearance, optional overall box, and every selected-airfoil ceiling are checked before JavaFoil runs. Rejected candidates appear only in the rejection log and search trace; they cannot become a baseline or enter results.csv. Saved valid results include top-point heights above y = 0 and physical optimized chords. Best geometry and a replayable best_config.json are saved as usual. The trace records sweep_complete checkpoints with each winning baseline.

Load **free_optimization_example.json** for the four-element, two-height-group example.


## Two independent tools

- **Adjust positions**: choose any number of airfoils with fixed chord lengths, then optimize angles, gaps, and overlaps.
- **Size & fit**: choose any number of airfoils, set chord ranges and group height limits, then optimize size and placement.

Each function has its own airfoils, units, settings, preview, progress, and saved results. Loading a configuration opens the matching function without changing the other tab. The search mode is selected automatically. Use each function's Airfoils & settings section to enter inputs and Preview & results to view its output.


## Ground effect and car orientation

Both function tabs include optional **Ground effect** and **Flip for downforce** switches.
Flip mirrors the whole wing vertically. Ground effect activates JavaFoil's ground-plane model at y=0 and translates every candidate until its lowest point has the selected clearance. The clearance is adjustable in m, cm, mm, inches, or feet. Each candidate retains that closest-point clearance as its chords and angles change.

Preview shows the actual oriented geometry, a shaded ground surface, and the clearance arrow. Saved CAD coordinates and geometry previews use the same frame and ground height as the solver. Both switches default off and can be enabled separately.

With either switch enabled, set the whole-wing angle offset to zero and use the per-airfoil angle ranges. The UI resets the offset when a switch is enabled. This avoids JavaFoil's polar rotation about a point on the ground changing the intended clearance or causing ground intersections.

The optimization metric is always named Cl. When flipped, results.csv records Cl as the positive-downward optimization coefficient, lift_cl as the signed upward-positive lift coefficient, and downforce_cl as the downward-positive coefficient. Raw polar.txt retains JavaFoil's signed lift. The unflipped objective remains maximum upward lift. Absolute resolved angles in the results use the physical solver axes after reflection.

The model is a 2D flat-ground mirror approximation for airfoil sections, not a full car or diffuser simulation. See https://www.mh-aerotools.de/airfoils/jf_wig.htm for the official model description. Load ground_car_example.json for a single inverted wing 30 mm above the ground.



## Simple simulation settings

The main simulation panel has **Wingspan**, **Relative airspeed**, and a **Stall model** selector, with length and speed unit selectors. Airspeed supports m/s, km/h, mph and ft/s. Default ambient air is standard sea level, 15°C and 101,325 Pa, using dry-air density from the ideal-gas relation and dynamic viscosity from Sutherland's law.

Reference Re = density × relative airspeed × fixed reference chord / dynamic viscosity. Each element's Reynolds number uses its own chord; the solver's normalized coordinates provide this scaling automatically, including during chord sweeps. Wingspan is not the Reynolds length scale. It sets JavaFoil's approximate finite-wing aspect-ratio correction: AR = wingspan / fixed reference chord, corresponding to rectangular reference area = wingspan × reference chord.

Open **Advanced settings** to customize temperature, pressure, density, viscosity, speed of sound, Reynolds, Mach, or aspect ratio, along with reference length, separation, overall box limits, transition, roughness, timeout, and search limits. Blank override fields use calculated values. Aspect-ratio override 0 requests the original 2D section result. Closing the menu retains any overrides.

Calculated Mach, reference and element Reynolds numbers, and aspect ratio are saved in results.csv. Physical air conditions are stored in config.json and provenance.json, and the report lists wingspan and airspeed. Legacy CLI configs without physical speed/span inputs keep their original explicit Reynolds/Mach and 2D default. Opening a legacy config in the UI converts its reference Reynolds into equivalent airspeed.

Sources: https://www.grc.nasa.gov/WWW/K-12/airplane/reynolds.html and https://www.mh-aerotools.de/airfoils/jf_users_manual.htm.

The desktop interface uses a consistent light theme, spacious airfoil cards, a prominent Optimize action, collapsible advanced controls, and mouse-wheel scrolling. Both tools retain separate settings and results.

Small question-mark icons explain airfoil inputs, simulation terms, height limits, and advanced controls. Hover briefly over an icon or focus it with the keyboard. Explanations close when the pointer leaves, focus moves, or the control is hidden.


## Save an optimized design anywhere

After a run has a completed best design, click Save design and choose a destination directory. A uniquely named Wing_design folder is created; existing files are never replaced.

The PDF includes the winning JavaFoil coefficients, geometry, dimensions, original ranges, settings, ambient-air numbers, search outcome and surface-data tables. Export recalculates the saved winner to obtain matching surface distributions.

Two 3840 x 2160 PNG images are saved: surface pressure coefficient and surface velocity. Both appear in the PDF. Numerical CSVs and native JavaFoil XML preserve the samples at the original panel resolution. Contours and flow lines are not part of this release.

The folder includes self-contained geometry/best_config.json and input coordinates, geometry in CAD formats, the original configuration and full sweep data, and a reproduced winning polar. Save uses the recorded run, even if you have edited the form since optimization. Stop cancels an export and retains the original run.


Parallel computation: candidate geometries within a parameter sweep run in independent JavaFoil processes. Simulation fidelity > Parallel processes selects an explicit number from 1 to the available physical-core count (default up to four). Parameter order, coarse/fine resolution, and geometric constraints are preserved. Winners and CSV rows are committed in deterministic candidate order. Stop cancels all active solver processes. Actual speedup depends on the machine and number of independent candidates.


Unlimited evaluations: the evaluation cap has been removed, including limits in older saved configurations. Both Adjust positions and Size & fit finish coarse coordinate sweeps at range/10, then refine within ±2.5% of the full parameter range around the winning coordinate using the selected fine-step percentage of that range. Search ends when its local-neighbor checks pass, the configured sweep-round limit is reached, or Stop is pressed. The console shows one line per evaluated candidate: iteration number and parameter changes in the selected units. Rejections, solver failures, and full results remain in the run files.


Simulation fidelity
-------------------
Both Adjust positions and Size & fit include a Simulation fidelity tab with independent settings:
- Coarse sweep divisions: full parameter range divided by this number (default 10).
- Fine step (% of full parameter range): default 0.25%. For a 100–300 mm range and 200 mm winner, this uses 0.5 mm steps over 195–205 mm.
Fine-step percentage must be greater than 0 and less than 2.5. Fine candidates stay within winner ±2.5% of (maximum − minimum), clipped to the original bounds. All winners, including zero and negative values, use this same range-width reference. Explicit comma-separated choices are not subdivided. Larger coarse division counts and smaller fine-step percentages mean more simulations; there is no evaluation cap. Live examples show the resulting steps in degrees and millimetres. Restore defaults resets only these two controls.

Settings are saved as search.coarse_divisions and search.fine_step_percent; older setups without the percentage use 0.25%. The former fine_divisions setting is retired. Parallel evaluation and parameter order are preserved. These controls change the optimization sampling resolution; airfoil panel resolution remains in Advanced settings.


Physical-core workers: both Simulation fidelity tabs provide a read-only process-count selector. Windows topology detection selects one logical processor per available physical core; hyperthread siblings are excluded. Each JavaFoil process is pinned to one of the selected cores and its affinity is read back to verify it. Selected counts are not silently clamped. Each case saves process.json with its PID and verified CPU mask; summary.json records the chosen physical-core processors. A full batch launches the selected number of independent processes. Baseline evaluations, cached candidates, invalid geometries, and short final batches can use fewer. This Windows build enumerates cores available in the current processor group.


Size & fit now sweeps Cartesian combinations within each height group. For group [1,2], it tests chord_1 × chord_2, then angle_1 × angle_2, then the group's slot gaps and overlaps. The best valid combination becomes the next stage's baseline. Groups run in the order entered; elements outside groups are swept individually. Overlapping groups are allowed. Coarse passes are followed by joint fine refinement near the winners and joint local-neighbor checks. All groups, clearances, and bounds are checked before each simulation. Input ranges remain the design bounds; a single value deliberately fixes that parameter. New sizing airfoils start with a chord range.

The console uses one line per candidate, such as 'Iteration 42: coarse chord 1: 350 mm; chord 2: 120 mm'. It has a vertical scrollbar and retains the scroll position while you read earlier lines. No total or evaluation-count ceiling is shown or enforced. Height selectors display only currently added airfoils, and update when airfoils are added or removed.

An already-open Python window keeps the code it loaded at startup. Stop or finish an old run, close that window, then relaunch Final Multielement App/Launch.cmd to load updates.


Airfoil height ceilings: select airfoils and enter “Must not exceed height”. This is a horizontal ceiling measured above y = 0, not top-to-bottom size or combined group span. With ground effect, y = 0 is the ground; otherwise it is the geometry reference plane. Every point on every selected airfoil must be at or below the ceiling after all geometry transformations. Overlapping selections enforce all their ceilings. Preview displays the reference/ground plane and dashed ceiling lines. New numerical results use top_y_m_N for each airfoil and ceiling_top_y_m_N for the highest selected point per ceiling. Newly loaded setups use these ceiling semantics.

Fine windows are centered on the winning value at the start of each fine parameter or group sweep. The center and both clipped window boundaries are always included; the final edge interval may be shorter than the requested step. Negative and zero winners use the full parameter range, like positive winners. The recorded search result includes refinement_windows with the actual center, limits, step, and percentage reference.

Layout: Preview, Optimize, Stop, Open report, and Save design occupy a fixed action row below the tabs. The Simulation fidelity page scrolls independently so its contents cannot push the actions off-screen.

## Stall model selection

Both functions offer a **Stall model** dropdown in Simulation settings:
**Calcfoil**, **Eppler** (default), or **None** (no stall correction). These are all
three choices in the bundled JavaFoil version. The selection applies to every
sweep candidate and saved-design replay, and is retained in the configuration,
provenance and reports. Older configurations default to Eppler.

For JSON setups use `simulation.stall_model`: `0`, `1`, or `2`, respectively.
JavaFoil's [multi-element guidance](https://www.mh-aerotools.de/airfoils/jf_multi.htm)
generally prefers Eppler. Selecting None disables the empirical correction; it
does not make separated-flow or maximum-lift predictions more accurate.

## Transition models and live Reynolds estimates

Simulation settings expose all nine JavaFoil transition criteria: Eppler 1/2,
Michel 1/2, H12-Re(s), Granville, Drela e^n before/after 1991, and Arnal e^n.
The default is Eppler 1. All three stall models remain independently selectable.
JSON `simulation.transition_model` uses JavaFoil's actual IDs **1-9**, in that order.
The previous 0-3 restriction was incorrect; 0 is not a valid JavaFoil transition ID.
Older configurations without this setting retain the default of 1.

Dropdown guidance follows the [JavaFoil boundary-layer documentation](https://www.mh-aerotools.de/airfoils/jf_analysis_boundarylayer.htm):
Eppler 1/2: Re > 100,000; Michel 1/2: Re > 2,000,000; Granville: Re > 5,000,000.
The other entries say "Re guidance not published". These are recommendations,
not enforced bounds or evidence of accuracy at every Reynolds number.

The reference and per-airfoil Reynolds estimates update as airspeed, chord, units,
or air properties change. Chord ranges show minimum/maximum Reynolds values.
An advanced Reynolds override is displayed separately from the physical estimate;
per-element solver values then scale from that override. Invalid or incomplete
inputs clear the estimate instead of leaving a stale value. Temperature, pressure,
density and viscosity overrides are respected. Turbulence intensity is not a
Reynolds-number input.


## Selectable geometry limits in Size & fit

In **Geometry limits**, select **Height** or **Length**, tick the airfoils to constrain,
enter a value and unit, and use **Enable** to switch the row on or off. At least one
row must be enabled. Multiple rows can constrain overlapping groups of airfoils.

Height uses the highest y coordinate above the ground/reference plane. Length uses
the rightmost x coordinate from x = 0, not the individual chord or assembly width.
The preview shows horizontal and vertical limit lines. Both are checked on placed,
rotated geometry before invoking JavaFoil, including flipped ground-effect setups.
Disabled rows are retained in saved configurations but ignored by the search.

For compatibility, JSON stores both types in `height_constraints`. A height row uses
`max_height` and `measurement: "top_y"`; a length row uses `max_length` and
`measurement: "right_x"`. Both accept `elements`, `unit`, and `enabled` (default true).
Older height-only configurations continue to load unchanged.
