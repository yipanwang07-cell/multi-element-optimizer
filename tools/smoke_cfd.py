"""Opt-in real SU2 integration smoke test, not an accuracy benchmark."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).absolute().parents[1]/"app"))
import wing_optimizer
from cfd_solver import validate_saved_design

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations",type=int,default=100)
    args=parser.parse_args()
    for name,ground,transition in (("single_transition",False,True),("multi_ground",True,False)):
        with tempfile.TemporaryDirectory(prefix="cfd-smoke-") as folder:
            run=Path(folder);(run/"best").mkdir()
            elements=[dict(profile="0012",chord=1,incidence_deg=0)]
            if ground:elements.append(dict(profile="0012",chord=.25,incidence_deg=10,gap=.1,overlap=.03))
            config=dict(length_unit="m",reference_chord=1,alpha_deg=0,panels_per_element=80,
                elements=elements,simulation=dict(reynolds=1e6,mach=0),
                environment=dict(ground_effect=ground,flip_for_downforce=ground,ground_clearance=.1))
            (run/"best/best_config.json").write_text(json.dumps(config))
            dest,result=validate_saved_design(run,dict(iterations=args.iterations,transition=transition),progress=print)
            assert (dest/"flow.vtu").is_file() and (dest/"report.html").is_file()
            assert len(result["surface_diagnostics"]["airfoils"])==len(elements)
            assert all(a["samples"]>0 for a in result["surface_diagnostics"]["airfoils"].values())
            assert result["aspect_ratio_correction"] is False
            assert not result["eligible_for_comparison"] or result["converged"]
            print(name,json.dumps(result),flush=True)

if __name__=="__main__":main()
