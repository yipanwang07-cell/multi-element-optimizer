import csv
import json
import math
from pathlib import Path
import tempfile
import threading
import unittest
import wing_optimizer as w

def config():
    return json.loads((w.EXAMPLES/"example.json").read_text(encoding="utf-8-sig"))

class GeometryTests(unittest.TestCase):
    def test_naca(self):
        pts=w.naca4("0012")
        self.assertEqual(pts[0],pts[-1])
        self.assertAlmostEqual(max(y for x,y in pts),-min(y for x,y in pts))
        self.assertTrue(w.Polygon(pts).is_valid)
    def test_normalize(self):
        transformed=[(x*3+4,y*3-2) for x,y in w.rotate(w.naca4("2412"),12)]
        pts=w.normalize(transformed,120)
        self.assertAlmostEqual((pts[0][0]+pts[-1][0])/2,1,places=6)
        self.assertAlmostEqual((pts[0][1]+pts[-1][1])/2,0,places=6)
        self.assertTrue(w.Polygon(pts).is_valid)
    def test_placement(self):
        pts=w.naca4("0012")
        geom=w.build_geometry([pts,pts],[2,.5],dict(incidence_1=0,incidence_2=20,gap_2=.03,overlap_2=.05),2)
        self.assertAlmostEqual(geom[1][60][0],.95)
        self.assertAlmostEqual(geom[1][60][1],-.03)
        self.assertAlmostEqual(math.dist(geom[1][0],geom[1][60]),.25)
    def test_collision(self):
        large=[(0,0),(2,0),(2,2),(0,2)]; small=[(.5,.5),(1,.5),(1,1),(.5,1)]
        with self.assertRaises(ValueError): w.validate_geometry([large,small],0)
        with self.assertRaises(ValueError): w.validate_geometry([large,[(x+2.01,y) for x,y in large]],.02)
        with self.assertRaises(ValueError): w.validate_geometry([large],0,dict(width=1,height=3))
    def test_validation(self):
        c=config(); c["elements"]=[]
        with self.assertRaises(ValueError): w.prepare(c,w.ROOT)
        with self.assertRaises(ValueError): w.values(dict(min=0,max=1,step=.3))
        with self.assertRaises(ValueError): w.values(float("nan"))
        with self.assertRaises(ValueError): w.naca4("1012")
    def test_parser(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"polar.txt"
            p.write_text("alpha Cl Cd Cm\n0 1 .01 0\n2 2 .02 -.1\n")
            self.assertEqual(w.parse_polar(p,[0,2])[1]["cl"],2)
            p.write_text("0 1 .01 0\n2 nan .02 -.1\n")
            with self.assertRaises(RuntimeError): w.parse_polar(p,[0,2])
            p.write_text("0 1 .01 0\n0 2 .01 0\n")
            with self.assertRaises(RuntimeError): w.parse_polar(p,[0,2])
    def test_export(self):
        with tempfile.TemporaryDirectory() as d:
            geom=[w.naca4("0012"),[(x+1.1,y) for x,y in w.naca4("0012")]]
            w.export_geometry(Path(d),geom,2,5)
            self.assertEqual((Path(d)/"javafoil_geometry.txt").read_text().count("9999.9"),2)
            with (Path(d)/"coordinates_m.csv").open() as f:
                rows=list(csv.DictReader(f))
            self.assertEqual(float(rows[0]["x_m"]),2)

class WorkflowTests(unittest.TestCase):
    class FakeSolver:
        def __init__(self,stop=None):
            self.ids=[]; self.stop=stop
        def analyze(self,geom,settings,alphas,directory):
            directory.mkdir(parents=True); self.ids.append(directory.name)
            (directory/"polar.txt").write_text("fixture only")
            (directory/"run.jfscript").write_text("fixture only")
            if self.stop: self.stop.set()
            return [dict(alpha=a,cl=a,cd=.01,cm=0) for a in alphas]
    def test_grid_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/"run"; solver=self.FakeSolver()
            result=w.run(config(),output,solver=solver,progress=lambda s:None)
            self.assertEqual(result["successful_geometries"],8)
            self.assertEqual(result["best"]["cl"],18)
            self.assertEqual(len(set(solver.ids)),8)
            self.assertTrue((output/"best/coordinates_m.csv").exists())
            self.assertTrue((output/"report.html").exists())
            with (output/"results.csv").open() as f:
                self.assertEqual(len(list(csv.DictReader(f))),80)
    def test_random(self):
        with tempfile.TemporaryDirectory() as d:
            c=config(); c["search"].update(mode="random",sample_count=3)
            a,b=self.FakeSolver(),self.FakeSolver()
            w.run(c,Path(d)/"a",solver=a,progress=lambda s:None)
            w.run(c,Path(d)/"b",solver=b,progress=lambda s:None)
            self.assertEqual(a.ids,b.ids); self.assertEqual(len(set(a.ids)),3)
    def test_cancel(self):
        with tempfile.TemporaryDirectory() as d:
            stop=threading.Event()
            result=w.run(config(),Path(d)/"run",solver=self.FakeSolver(stop),stop=stop,progress=lambda s:None)
            self.assertTrue(result["cancelled"])
            self.assertEqual(result["successful_geometries"],1)
            self.assertIsNotNone(result["best"])
    def test_budget(self):
        c=config(); c["search"]["max_geometries"]=2
        with tempfile.TemporaryDirectory() as d:
            result=w.run(c,Path(d)/"run",solver=self.FakeSolver(),progress=lambda _:None)
            self.assertEqual(result["evaluated_geometries"],8)

class DesktopTests(unittest.TestCase):
    def test_editor(self):
        import tkinter as tk
        from app import App
        root=tk.Tk(); root.withdraw()
        try:
            app=App(root)
            initial=len(app.rows)
            for _ in range(6): app.add()
            self.assertEqual(len(app.rows),initial+6)
            w.prepare(app.config(),w.ROOT)
            app.remove(); self.assertEqual(len(app.rows),initial+5)
        finally: root.destroy()

if __name__=="__main__":
    unittest.main(verbosity=2)
