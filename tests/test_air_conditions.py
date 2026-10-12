import json
import math
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from air_conditions import normalize_conditions,air_properties
import wing_optimizer as w
import test_optimizer as fixtures

def physical():
    return dict(wingspan={"value":1500,"unit":"mm"},relative_airspeed={"value":72,"unit":"km/h"})

class AirConditionTests(unittest.TestCase):
    def test_standard_air_reynolds_mach_and_span(self):
        s=normalize_conditions(physical(),.4)
        rho,mu,a=air_properties({})
        self.assertAlmostEqual(rho,1.225,delta=.0001)
        self.assertAlmostEqual(mu,1.7893e-5,delta=1e-9)
        self.assertAlmostEqual(s["reynolds"],rho*20*.4/mu)
        self.assertAlmostEqual(s["mach"],20/a)
        self.assertEqual(s["aspect_ratio"],3.75)
        self.assertAlmostEqual(s["reference_area_m2"],.6)
        changed=physical(); changed["wingspan"]={"value":3000,"unit":"mm"}
        normalize_conditions(changed,.4)
        self.assertAlmostEqual(changed["reynolds"],s["reynolds"])
        self.assertEqual(changed["aspect_ratio"],7.5)
    def test_speed_and_chord_update_re_and_override_can_be_cleared(self):
        s=physical();normalize_conditions(s,.4); original=s["reynolds"]
        s["relative_airspeed"]["value"]=144;normalize_conditions(s,.4)
        self.assertAlmostEqual(s["reynolds"],original*2)
        normalize_conditions(s,.2);self.assertAlmostEqual(s["reynolds"],original)
        s.update(reynolds_override=123456,mach_override=0,aspect_ratio_override=0)
        normalize_conditions(s,.4); self.assertEqual(s["reynolds"],123456); self.assertEqual(s["aspect_ratio"],0)
        s.pop("reynolds_override");normalize_conditions(s,.4)
        self.assertAlmostEqual(s["reynolds"],original*2)
    def test_custom_atmosphere_and_invalid_inputs(self):
        rho,mu,a=air_properties(dict(temperature_c=30,pressure_pa=95000))
        self.assertLess(rho,1.225); self.assertGreater(mu,1.7893e-5)
        for key,value in (("relative_airspeed",0),("wingspan",0),("temperature_c",-273.15),("pressure_pa",-1),("viscosity_override",0)):
            s=physical();s[key]=value
            with self.assertRaises(ValueError): normalize_conditions(s,.4)
        legacy=dict(reynolds=300000,mach=0)
        self.assertEqual(normalize_conditions(legacy,.4),dict(reynolds=300000,mach=0))
    def test_workflow_saves_element_reynolds_and_conditions(self):
        c=dict(length_unit="mm",reference_chord=400,elements=[
            dict(profile="0012",chord=400,incidence_deg=0),
            dict(profile="0012",chord=100,incidence_deg=0,gap_length=40,overlap_length=0)],
            alpha_deg=0,panels_per_element=40,simulation=physical(),search=dict(mode="grid",max_geometries=1))
        with tempfile.TemporaryDirectory() as d:
            result=w.run(c,Path(d)/"run",solver=fixtures.WorkflowTests.FakeSolver(),progress=lambda s:None)
            best=result["best"]
            self.assertAlmostEqual(best["reynolds_1"],best["reference_reynolds"])
            self.assertAlmostEqual(best["reynolds_2"],best["reference_reynolds"]*.25)
            saved=json.loads((Path(d)/"run/best/best_config.json").read_text())
            w.prepare(saved,Path(d)/"run/best")
            self.assertAlmostEqual(saved["simulation"]["reynolds"],best["reference_reynolds"])
    def test_ui_advanced_collapsed_units_and_overrides(self):
        from app import DesktopApp
        root=tk.Tk();root.withdraw()
        try:
            desktop=DesktopApp(root);app=desktop.panes["placement"]
            self.assertFalse(app.advanced_frame.winfo_manager())
            c=app.config();self.assertIn("relative_airspeed",c["simulation"])
            self.assertNotIn("reynolds_override",c["simulation"])
            original=c["simulation"]["reynolds"]
            app.flight_inputs.speed_unit.set("km/h");app.flight_inputs.convert("speed")
            self.assertAlmostEqual(float(app.flight_inputs.speed.get()),72)
            self.assertAlmostEqual(app.config()["simulation"]["reynolds"],original)
            app.flight_inputs.span_unit.set("m");app.flight_inputs.convert("span")
            self.assertAlmostEqual(float(app.flight_inputs.span.get()),1.5)
            app.toggle_advanced();self.assertEqual(app.advanced_frame.winfo_manager(),"pack")
            app.settings["reynolds"].set("123456")
            self.assertEqual(app.config()["simulation"]["reynolds"],123456)
            app.toggle_advanced();self.assertFalse(app.advanced_frame.winfo_manager())
            self.assertEqual(app.config()["simulation"]["reynolds"],123456)
            app.settings["reynolds"].set("")
            self.assertAlmostEqual(app.config()["simulation"]["reynolds"],original)
        finally:root.destroy()

if __name__=="__main__":unittest.main()
