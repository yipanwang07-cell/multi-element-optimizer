import csv
import json
from pathlib import Path
import tempfile
import unittest
import tkinter as tk
import wing_optimizer as w
from coordinate_search import run_search
from geometric_constraints import check_heights, validate_groups, free_order, feasible_seed
import test_optimizer as fixtures

def config():
    return dict(length_unit="mm",reference_chord=400,minimum_clearance_length=1,alpha_deg=0,
        panels_per_element=40,elements=[
            dict(profile="0012",chord={"min":100,"max":500},incidence_deg=0),
            dict(profile="0012",chord=100,incidence_deg=0,gap_length=30,overlap_length=0)],
        height_constraints=[dict(elements=[1,2],max_height=25,unit="mm")],
        search=dict(mode="free",max_geometries=500,max_passes=2,max_refinements=2))

class FreeTests(unittest.TestCase):
    def test_ceiling_uses_top_coordinate_not_span(self):
        g=[[(0,0),(1,1)],[(0,-10),(1,-9)],[(0,2),(1,3)]]
        result=check_heights(g,.1,[dict(elements=[1,3],max_height=300,unit="mm")])
        self.assertAlmostEqual(result["ceiling_top_y_m_1"],.3)
        self.assertAlmostEqual(result["top_y_m_1"],.1)
        # Large separation below the ceiling is valid; a translated thin airfoil above it is not.
        check_heights(g,.1,[dict(elements=[1,2],max_height=100,unit="mm")])
        with self.assertRaisesRegex(ValueError,"highest point"):
            check_heights(g,.1,[dict(elements=[3],max_height=200,unit="mm")])
    def test_ceiling_after_ground_clearance_and_flip(self):
        from ground_effect import orient_geometry
        g=[[(0,0),(1,.1)],[(1,-.4),(2,-.3)]]
        oriented=orient_geometry(g,1,dict(ground_effect=True,flip_for_downforce=True,clearance_m=.05))
        check_heights(oriented,1,[dict(elements=[1],max_height=.15,unit="m")])
        with self.assertRaises(ValueError):
            check_heights(oriented,1,[dict(elements=[2],max_height=.2,unit="m")])
    def test_multiple_ceilings_and_reference_preview(self):
        from app import App
        root=tk.Tk();root.withdraw()
        try:
            app=App(root,function="sizing")
            app.geometry=[[(0,0),(1,.1),(0,0)]]
            app.scene_reference=1
            app.scene_environment=dict(ground_effect=False)
            app.scene_height_limits=[dict(elements=[1],max_height=200,unit="mm")]
            app.draw()
            self.assertTrue(app.canvas.find_withtag("height-ceiling"))
            self.assertTrue(app.canvas.find_withtag("height-reference"))
            with self.assertRaises(ValueError):
                check_heights(app.geometry,1,[dict(elements=[1],max_height=.2),dict(elements=[1],max_height=.05)])
        finally:root.destroy()
    def test_group_validation(self):
        c=config()
        for ids in ([],[0],[3],[1,1],[1.0]):
            c["height_constraints"][0]["elements"]=ids
            with self.assertRaises(ValueError): validate_groups(c)
        c["height_constraints"]=[]
        with self.assertRaises(ValueError): validate_groups(c)
    def test_range_units_and_ui_roundtrip(self):
        c=config(); c["elements"][0]["length_unit"]="in"; c["elements"][0]["chord"]={"min":4,"max":8}
        p,ch,r,axes,a,clear=w.prepare(c,w.ROOT)
        self.assertAlmostEqual(min(axes["chord_1"])*r,.1016)
        self.assertAlmostEqual(max(axes["chord_1"])*r,.2032)
        from design_inputs import ui_config
        self.assertEqual(ui_config(c)["elements"][0]["chord"],{"min":4,"max":8})
    def test_exact_order_and_baseline_carry(self):
        order=free_order(2)
        axes={n:[0.,1.] for n in order}
        events=[]
        result=run_search(axes,lambda p:dict(cl=sum(p.values())),set(),settings=dict(parameter_order=order,max_passes=1),trace=events.append)
        self.assertEqual(result["parameter_order"],["chord_1","chord_2","incidence_1","incidence_2","gap_2","overlap_2"])
        self.assertTrue(all(v==1 for v in result["parameters"].values()))
        coarse=[e for e in events if e["phase"]=="coarse"]
        self.assertTrue(all(e["parameters"]["chord_1"]==1 for e in coarse if e["parameter"]=="chord_2"))
    def test_seed_recovers_invalid_midpoint(self):
        axes={"chord_1":[.1,.3,.5],"incidence_1":[0.]}
        def valid(p):
            if p["chord_1"]>.15: raise ValueError()
        self.assertEqual(feasible_seed(axes,valid)["chord_1"],.1)
        with self.assertRaises(ValueError): feasible_seed(axes,lambda p: (_ for _ in ()).throw(ValueError()),limit=3)
    def test_constraints_before_solver_and_saved_chord(self):
        class Solver(fixtures.WorkflowTests.FakeSolver):
            def analyze(self,g,s,a,d):
                check_heights(g,.4,config()["height_constraints"])
                rows=super().analyze(g,s,a,d)
                for row in rows: row["cl"]=max(x for x,y in g[0])-min(x for x,y in g[0])
                return rows
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"run"
            result=w.run(config(),out,solver=Solver(),progress=lambda s:None)
            self.assertGreater(result["rejected_geometries"],0)
            with (out/"results.csv").open() as stream: rows=list(csv.DictReader(stream))
            self.assertTrue(all(float(r["ceiling_top_y_m_1"])<=.025000001 for r in rows))
            best=json.loads((out/"best/best_config.json").read_text())
            p,ch,ref,axes,a,clear=w.prepare(best,out/"best")
            geometry=w.build_geometry(p,ch,{n:v[0] for n,v in axes.items()},ref)
            check_heights(geometry,ref,best["height_constraints"])
            self.assertAlmostEqual(ch[0],result["best"]["chord_m_1"])
            self.assertTrue((out/"report.html").exists())
    def test_ui_free_mode_and_group_roundtrip(self):
        from app import App
        root=tk.Tk(); root.withdraw()
        try:
            app=App(root); app.apply_config(config())
            edited=app.config()
            self.assertEqual(edited["search"]["mode"],"free")
            self.assertEqual([g["elements"] for g in edited["height_constraints"]],[[1],[2]])
            self.assertEqual(edited["elements"][0]["chord"],{"min":100.,"max":500.})
        finally: root.destroy()
    def test_free_offset_rejected(self):
        c=config(); c["alpha_deg"]=5
        with self.assertRaises(ValueError): w.prepare(c,w.ROOT)
