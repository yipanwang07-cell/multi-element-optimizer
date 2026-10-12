"""Run the optional CFD check on an existing run folder."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"app"))
import wing_optimizer
from cfd_solver import validate_saved_design

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run",type=Path)
    parser.add_argument("--fine",action="store_true")
    parser.add_argument("--transition",action="store_true")
    parser.add_argument("--iterations",type=int,default=3000)
    args=parser.parse_args()
    options=dict(iterations=args.iterations,transition=args.transition,surface_size=.008 if args.fine else .015,first_layer=5e-6 if args.fine else 1e-5,domain_chords=30 if args.fine else 20)
    path,result=validate_saved_design(args.run,options,progress=print)
    print(result["status"]);print(path/"report.html")
