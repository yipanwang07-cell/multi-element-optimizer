"""Physical units, angle chains and ordered-local-sweep regression tests."""
import json
import csv
import io
from contextlib import redirect_stdout
from unittest.mock import patch
import airfoil_library as library
import math
from pathlib import Path
import tempfile
import threading
import tkinter as tk
import unittest
import wing_optimizer as w
from design_inputs import *
from coordinate_search import run_search,ordered_parameters
import test_optimizer as fixtures

def settings(): return dict(max_passes=15,max_refinements=5,angle_tolerance_deg=.001,length_tolerance_m=.00001,cl_tolerance=1e-9)

class UnitAngleTests(unittest.TestCase):
    def test_lengths(self):
        for value,unit,expected in [(400,"mm",.4),(40,"cm",.4),(1,"in",.0254),(1,"ft",.3048)]:
            self.assertAlmostEqual(length_m(value,unit),expected)
        self.assertAlmostEqual(length_m("2 in"),.0508)
        with self.assertRaises(ValueError): length_m(5,"yards")
        with self.assertRaises(ValueError): length_m(float("nan"))
    def test_ranges_without_step(self):
        points=w.values(dict(min=-3,max=7))
        self.assertEqual(len(points),11); self.assertEqual(points[0],-3); self.assertEqual(points[-1],7)
        self.assertEqual(w.values(dict(min=5,max=5)),[5])
    def test_mixed_units_and_gap_range(self):
        c=dict(length_unit="mm",reference_chord={"value":400,"unit":"mm"},minimum_clearance_length={"value":1,"unit":"mm"},
            elements=[dict(profile="0012",chord=400,length_unit="mm"),
                      dict(profile="0012",chord=4,length_unit="in",gap_length={"min":.25,"max":.5,"unit":"in"},overlap_length={"min":0,"max":10,"unit":"mm"})])
        p,chords,ref,axes,a,clearance=w.prepare(c,w.ROOT)
        self.assertAlmostEqual(chords[1],.1016); self.assertAlmostEqual(ref,.4)
        self.assertAlmostEqual(axes["gap_2"][0]*ref,.00635)
        self.assertAlmostEqual(clearance,.0025)
        migrated=ui_config(c)
        w.prepare(migrated,w.ROOT)
        self.assertAlmostEqual(migrated["elements"][1]["gap"]["min"]*ref,.00635)
    def test_relative_absolute_chain(self):
        params={f"incidence_{i}":v for i,v in enumerate([5,10,20,-7,3],1)}
        self.assertEqual(absolute_angles(params,["absolute","relative","absolute","relative","relative"]),[5,15,20,13,16])
        points=w.naca4("0012")
        params.update({f"{key}_{i}":.05 for i in range(2,6) for key in ("gap","overlap")})
        geom=w.build_geometry([points]*5,[1,.3,.3,.3,.3],params,1,["absolute","relative","absolute","relative","relative"])
        for i,angle in enumerate([5,15,20,13,16]):
            le=geom[i][60]; te=geom[i][0]
            self.assertAlmostEqual(math.degrees(math.atan2(te[1]-le[1],te[0]-le[0])),-angle)
    def test_cli_preview_resolves_relative_angle(self):
        with tempfile.TemporaryDirectory() as d:
            c=dict(elements=[dict(profile="0012",chord_m=1,incidence_deg=5),
                dict(profile="0012",chord_m=.3,incidence_deg=10,angle_mode="relative",gap=.05,overlap=.02)])
            configfile=Path(d)/"config.json"; output=Path(d)/"preview"
            configfile.write_text(json.dumps(c))
            with patch("sys.argv",["wing_optimizer.py","--config",str(configfile),"--preview","--output",str(output)]), redirect_stdout(io.StringIO()):
                w.main()
            geometry=json.loads((output/"coordinates_at_best_alpha_m.json").read_text())
            te=geometry[1][0]; le=geometry[1][60]
            self.assertAlmostEqual(math.degrees(math.atan2(te[1]-le[1],te[0]-le[0])),-15)

    def test_first_relative_rejected(self):
        c=dict(elements=[dict(profile="0012",chord_m=1,angle_mode="relative")])
        with self.assertRaisesRegex(ValueError,"no previous"): w.prepare(c,w.ROOT)
    def test_best_physical_config(self):
        c=json.loads((w.EXAMPLES/"sequential_example.json").read_text())
        w.prepare(c,w.ROOT)
        params=dict(incidence_1=5,incidence_2=10,gap_2=.04,overlap_2=.02)
        best=fixed_best_config(c,params,0,.4)
        _,_,_,axes,_,_=w.prepare(best,w.ROOT)
        self.assertEqual(axes["gap_2"],[.04]); self.assertEqual(axes["overlap_2"],[.02])
        self.assertEqual(best["elements"][1]["angle_mode"],"relative")

class LocalSweepTests(unittest.TestCase):
    def test_order_and_ten_intervals(self):
        axes=dict(incidence_1=[0,20],incidence_2=[10,30],gap_2=[.04,.08],overlap_2=[0,.02])
        events=[]
        def evaluate(p):
            return dict(cl=10-(p["incidence_1"]-6.3)**2-(p["incidence_2"]-17.6)**2-100*(p["gap_2"]-.06)**2-100*(p["overlap_2"]-.01)**2)
        result=run_search(axes,evaluate,set(axes),settings=settings(),trace=events.append)
        self.assertTrue(result["converged"])
        self.assertEqual(result["parameter_order"],["incidence_1","gap_2","overlap_2","incidence_2"])
        coarse=[e for e in events if e["phase"]=="coarse" and e["parameter"]=="incidence_1" and e["cycle"]==1]
        self.assertEqual(len(coarse),11)
        self.assertAlmostEqual(result["parameters"]["incidence_1"],6.3,delta=.02)
        self.assertTrue(all(c["passed"] for c in result["local_checks"]))
    def test_coupled_parameters_revisit(self):
        axes=dict(incidence_1=[-2,2],incidence_2=[-2,2],gap_2=[.1],overlap_2=[0])
        def evaluate(p):
            x=p["incidence_1"]; y=p["incidence_2"]
            return dict(cl=10-(x-y)**2-(y-1)**2)
        result=run_search(axes,evaluate,{"incidence_1","incidence_2"},settings=settings())
        self.assertTrue(result["converged"]); self.assertGreater(result["completed_passes"],1)
        self.assertAlmostEqual(result["parameters"]["incidence_1"],1,delta=.201)
    def test_boundary_maximum(self):
        result=run_search(dict(incidence_1=[0,10]),lambda p:dict(cl=p["incidence_1"]),{"incidence_1"},settings=settings())
        self.assertTrue(result["converged"]); self.assertEqual(result["parameters"]["incidence_1"],10)
        self.assertTrue(result["local_checks"][0]["at_boundary"])
    def test_invalid_and_cached_candidates(self):
        calls=[]
        def evaluate(p):
            calls.append(tuple(p.items()))
            return None if p["incidence_1"]<0 else dict(cl=-(p["incidence_1"]-2)**2)
        result=run_search(dict(incidence_1=[-4,4]),evaluate,{"incidence_1"},settings=settings())
        self.assertTrue(result["converged"])
        self.assertEqual(len(calls),len(set(calls)))
    def test_budget_does_not_claim_convergence(self):
        from coordinate_search import SearchBudget
        n=0
        def evaluate(p):
            nonlocal n
            n+=1
            if n>3: raise SearchBudget()
            return dict(cl=p["incidence_1"])
        result=run_search(dict(incidence_1=[0,10]),evaluate,{"incidence_1"},settings=settings())
        self.assertEqual(result["termination"],"evaluation_budget"); self.assertFalse(result["converged"])
    def test_stop(self):
        stop=threading.Event(); stop.set()
        result=run_search(dict(incidence_1=[0,10]),lambda p:dict(cl=1),{"incidence_1"},stop=stop)
        self.assertEqual(result["termination"],"cancelled")
    def test_legacy_sequential_cap_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            c=json.loads((w.EXAMPLES/"sequential_example.json").read_text())
            c["search"]["max_geometries"]=3
            result=w.run(c,Path(d)/"run",solver=fixtures.WorkflowTests.FakeSolver(),progress=lambda _:None)
            self.assertTrue(result["search"]["converged"])
            self.assertGreater(result["evaluated_geometries"],3)
            self.assertTrue((Path(d)/"run/sweep_trace.jsonl").exists())

class EditorTests(unittest.TestCase):
    def test_family_menus_and_units_preserve_dimensions(self):
        from app import App
        root=tk.Tk(); root.withdraw()
        try:
            app=App(root); row=app.rows[0]
            row["family"].set("Eppler"); app.change_family(row)
            choices=row["_profile_box"]["values"]
            self.assertTrue(all(library.find(x)["family"]=="Eppler" for x in choices))
            self.assertIn("E423",choices)
            before=w.prepare(app.config(),w.ROOT)[1][0]
            row["length_unit"].set("in"); app.change_row_unit(row)
            after=w.prepare(app.config(),w.ROOT)[1][0]
            self.assertAlmostEqual(before,after,places=8)
            app.global_unit.set("cm"); app.change_global_unit()
            after=w.prepare(app.config(),w.ROOT)[1][0]
            self.assertAlmostEqual(before,after,places=8)
            self.assertEqual(app.config()["search"]["mode"],"sequential")
            for _ in range(3): app.add()
            self.assertEqual(len(app.rows),5)
            root.update_idletasks()
            self.assertTrue(app.setup_canvas.bbox("all"))
        finally: root.destroy()

if __name__=="__main__":
    import airfoil_library as library
    unittest.main(verbosity=2)
