# Regression tests

Run from the application folder with the application dependencies installed:

```text
python -m unittest discover -s tests
```

The UI tests require a desktop session and Tk. On Windows, the bundled runtime also needs its Tcl/Tk library paths configured. When running the entire suite, collect garbage on the main thread after each test to keep destroyed Tk objects out of worker-thread garbage collection.

## Added edge cases (October 12, 2026)

- Transient invalid-argument errors at every winner-file replacement: coordinates, metadata, configuration, polar, and replay script.
- Failure while creating a temporary file, failure while flushing to disk, and persistent replacement failure.
- Previous file preservation, temporary-file cleanup, and winning CSV-row retention when export fails.
- Unicode filenames, repeated replacement, and empty file contents.
- Size & Fit starting values outside the range, non-finite values, and values absent from discrete choices; rejected before calling the solver.
- Closing both function tabs cancels refresh callbacks; manual refresh does not create duplicate timers.

The wider suite covers geometry, units, ground effect, height constraints, refinement, parallel/serial consistency, cancellation, airfoil libraries, transition/stall settings, PDF export, layout, and dropdown scrolling.

A separate real-solver smoke check runs NACA 0012 at two element angles with 60 panels and Re 300,000, then checks saved winner metadata and coordinate JSON. Automated tests mostly use deterministic solver fixtures; these checks do not establish aerodynamic accuracy against experiments or CFD.
