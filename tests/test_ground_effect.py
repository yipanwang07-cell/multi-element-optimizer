import json
import math
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
import wing_optimizer as w
from ground_effect import normalize_environment, orient_geometry, signed_result
import test_optimizer as fixtures

def config():
    return dict(length_unit="mm",reference_chord=400,alpha_deg=0,panels_per_element=40,
        elements=[dict(profile="4412",chord=400,incidence_deg=5)],
        environment=dict(ground_effect=True,flip_for_downforce=True,ground_clearance={"value":30,"unit":"mm"}),
        search=dict(mode="grid",max_geometries=1),simulation=dict(reynolds=300000,mach=0))

class GroundTests(unittest.TestCase):
    def test_reflection_and_minimum_clearance(self):
        c=config(); env=normalize_environment(c)
        g=[[(0,0),(1,.2),(1,0)],[(2,-.3),(3,-.2),(3,-.3)]]
        result=orient_geometry(g,.4,env)
        self.assertAlmostEqual(min(y for e in result for x,y in e)*.4,.03)
        for original,flipped in zip(g,result):
            self.assertAlmostEqual(abs(w.Polygon(original).area),abs(w.Polygon(flipped).area))
        c["environment"]["ground_effect"]=False
        result=orient_geometry(g,.4,normalize_environment(c))
        self.assertEqual(result[0],[(1,0),(1,-.2),(0,0)])
    def test_disabled_preserves_original_geometry(self):
        g=[[(0,1),(2,3),(4,0)]]
        self.assertEqual(orient_geometry(g,1,{}),g)
    def test_invalid_clearance_and_nonzero_offset(self):
        for height in (0,-1,float("nan")):
            c=config(); c["environment"]["ground_clearance"]=height
            with self.assertRaises(ValueError): w.prepare(c,w.ROOT)
        c=config(); c["alpha_deg"]=5
        with self.assertRaises(ValueError): w.prepare(c,w.ROOT)
    def test_downforce_objective_retains_signed_lift(self):
        rows=[signed_result(dict(cl=x,alpha=0,cd=.01,cm=0),dict(flip_for_downforce=True)) for x in (-1.,-2.,.5)]
        winner=max(rows,key=lambda r:r["cl"])
        self.assertEqual(winner["cl"],2.)
        self.assertEqual(winner["lift_cl"],-2.)
        self.assertEqual(signed_result(dict(cl=1),{})["cl"],1)
    def test_workflow_exports_real_ground_geometry_and_replay(self):
        class Solver(fixtures.WorkflowTests.FakeSolver):
            def analyze(self,g,settings,alphas,directory):
                self.assert_ground=settings["ground_effect"]
                self.geometry=g
                rows=super().analyze(g,settings,alphas,directory)
                for row in rows: row["cl"]=-1.5
                return rows
        with tempfile.TemporaryDirectory() as d:
            solver=Solver(); output=Path(d)/"run"
            result=w.run(config(),output,solver=solver,progress=lambda s:None)
            self.assertTrue(solver.assert_ground)
            self.assertAlmostEqual(min(y for e in solver.geometry for x,y in e)*.4,.03)
            self.assertEqual(result["best"]["cl"],1.5); self.assertEqual(result["best"]["lift_cl"],-1.5)
            self.assertIn("Ground (y=0)",(output/"best/geometry.svg").read_text())
            c=json.loads((output/"best/best_config.json").read_text())
            p,ch,r,axes,a,clear=w.prepare(c,output/"best")
            g=orient_geometry(w.build_geometry(p,ch,{n:v[0] for n,v in axes.items()},r),r,c["environment"])
            for first,second in zip(g[0],solver.geometry[0]):
                for x,y in zip(first,second): self.assertAlmostEqual(x,y)
    def test_ui_ground_preview_and_saved_units(self):
        from app import App
        root=tk.Tk(); root.withdraw()
        try:
            app=App(root); app.apply_config(config()); app.preview()
            self.assertTrue(app.canvas.find_withtag("ground"))
            self.assertTrue(app.canvas.find_withtag("ground-clearance"))
            self.assertAlmostEqual(min(y for e in app.geometry for x,y in e)*.4,.03)
            app.ground_unit.set("in"); app.change_ground_unit()
            self.assertAlmostEqual(float(app.ground_clearance.get())*.0254,.03)
            self.assertEqual(app.config()["environment"]["ground_clearance"]["unit"],"in")
            app.ground_enabled.set(False); app.flip_downforce.set(False); app.ground_options_changed()
            self.assertFalse(app.canvas.find_withtag("ground"))
        finally: root.destroy()

if __name__=="__main__": unittest.main()
