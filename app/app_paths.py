"""Locations relative to the final application's root directory."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
EXAMPLES=ROOT/"examples"
VENDOR=ROOT/"runtime/vendor"
AIRFOILS=ROOT/"assets/airfoils"
