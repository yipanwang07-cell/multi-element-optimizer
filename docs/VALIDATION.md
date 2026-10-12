# Validation notes

Run the regression suite using the instructions in the root README.
It exercises geometry generation, imported coordinate handling, unit conversion,
angle conventions, ceiling constraints, grouped/local search, refinement,
physical-core workers, cancellation, UI controls and portable design exports.

Tests that use a synthetic solver verify workflow behavior, not aerodynamic
accuracy. A real JavaFoil smoke run and PDF export are also checked for this release.
The app currently has no independent CFD validation or Euler final-solution stage.
Those planned capabilities and their acceptance criteria are in the root README.

Local validation artifacts and historical research runs are excluded from the
public repository. Reproduce results on your own installation before relying on
them. JavaFoil compatibility changes affect startup checks only.
