import tempfile
from pathlib import Path
import tkinter as tk
import unittest
from geometric_constraints import check_heights, validate_groups
from grouped_search import parameter_blocks
from app import App
import wing_optimizer as w
import test_optimizer as fixtures

class LengthConstraintTests(unittest.TestCase):
    def test_length_uses_rightmost_position_and_selected_elements(self):
        g=[[(0,0),(.6,.1)],[(.8,0),(1.2,.1)]]
        group=dict(elements=[1],max_length=600,unit="mm")
        self.assertAlmostEqual(check_heights(g,1,[group])["limit_right_x_m_1"],.6)
        with self.assertRaisesRegex(ValueError,"rightmost"):
            check_heights(g,1,[dict(group,elements=[2])])
        check_heights(g,1,[dict(group,elements=[2],enabled=False)])
        with self.assertRaises(ValueError):
            check_heights(g,1,[group,dict(elements=[1],max_height=50,unit="mm")])

    def test_validation_and_disabled_groups(self):
        c=dict(elements=[{}],search=dict(mode="free"),height_constraints=[dict(elements=[1],max_length=600,unit="mm")])
        validate_groups(c)
        self.assertEqual(c["height_constraints"][0]["measurement"],"right_x")
        for value in (0,-1,float("nan")):
            c["height_constraints"][0]["max_length"]=value
            with self.assertRaises(ValueError):validate_groups(c)
        c["height_constraints"][0]["enabled"]=False
        with self.assertRaisesRegex(ValueError,"Enable"):validate_groups(c)
        self.assertEqual(parameter_blocks({"chord_1":[1]},[dict(elements=[99],enabled=False)]),[["chord_1"]])

    def test_ui_roundtrip_and_both_preview_lines(self):
        root=tk.Tk();root.withdraw()
        try:
            app=App(root,function="sizing")
            groups=[dict(elements=[1],max_length=600,unit="mm"),dict(elements=[1],max_height=200,unit="mm"),dict(elements=[2],max_length="",unit="mm",enabled=False)]
            app.constraints.set(groups)
            saved=app.constraints.get();app.constraints.set(saved)
            self.assertEqual(app.constraints.get(),saved)
            app.scene_height_limits=saved;app.scene_reference=1
            app.geometry=[[(0,0),(.5,.1),(0,0)]];app.draw()
            self.assertTrue(app.canvas.find_withtag("length-limit"))
            self.assertTrue(app.canvas.find_withtag("height-ceiling"))
        finally:root.destroy()

    def test_length_only_workflow_rejects_before_solver_and_exports(self):
        c=dict(elements=[dict(profile="0012",chord=dict(min=.2,max=.4),incidence_deg=0)],reference_chord_m=.4,
            panels_per_element=40,alpha_deg=0,search=dict(mode="free",workers=1),simulation=dict(reynolds=300000),
            height_constraints=[dict(elements=[1],max_length=.3,unit="m")])
        with tempfile.TemporaryDirectory() as folder:
            solver=fixtures.WorkflowTests.FakeSolver()
            result=w.run(c,Path(folder)/"run",solver=solver,progress=lambda _:None)
            self.assertLessEqual(result["best"]["limit_right_x_m_1"],.3+1e-12)
            self.assertGreater(result["rejected_geometries"],0)
            self.assertEqual(len(solver.ids),result["successful_geometries"])
            self.assertIn("Rightmost point",(Path(folder)/"run/report.html").read_text())

    def test_first_leading_edge_is_origin_after_rotation_and_ground_flip(self):
        from ground_effect import orient_geometry
        for angle in (-25,0,30):
            profile=w.naca4("2412",40)
            # Also exercise an offset leading-edge point, rather than assuming
            # that every imported/resampled profile has exact zero coordinates.
            shifted=[(x+.01,y+.02) for x,y in profile]
            g=w.build_geometry([shifted,profile],[.4,.15],dict(incidence_1=angle,incidence_2=35,gap_2=.1,overlap_2=.05),.4)
            self.assertAlmostEqual(g[0][20][0],0)
            oriented=orient_geometry(g,.4,dict(ground_effect=True,flip_for_downforce=True,clearance_m=.03))
            self.assertAlmostEqual(oriented[0][20][0],0)
            self.assertAlmostEqual(g[1][20][0],(g[0][0][0]+g[0][-1][0])/2-.05)
