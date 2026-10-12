import gc
import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
import wing_optimizer as w
import test_optimizer as fixtures
from app import DesktopApp
from air_conditions import reynolds_estimates, normalize_conditions
from transition_models import TRANSITION_MODELS, transition_model_id, transition_model_label, transition_model_name


class TransitionTests(unittest.TestCase):
    def tearDown(self):gc.collect()

    def test_all_ids_default_and_invalid(self):
        self.assertEqual(list(TRANSITION_MODELS),list(range(1,10)))
        for model in TRANSITION_MODELS:
            c=fixtures.config();c["simulation"]["transition_model"]=model
            w.prepare(c,w.ROOT)
            self.assertEqual(c["simulation"]["transition_model"],model)
        for model in (0,10,-1,True,1.5,"1",None):
            with self.subTest(model=model),self.assertRaises(ValueError):transition_model_id(model)
        c=fixtures.config();c["simulation"].pop("transition_model",None);w.prepare(c,w.ROOT)
        self.assertEqual(c["simulation"]["transition_model"],1)

    def test_reynolds_matches_solver_and_ranges(self):
        sim=dict(relative_airspeed=dict(value=72,unit="km/h"),wingspan=1.5,temperature_c=25)
        calculated,effective,elements=reynolds_estimates(sim,.4,[[.4],[.1,.2]])
        normalize_conditions(sim,.4)
        self.assertAlmostEqual(calculated,sim["reynolds"])
        self.assertAlmostEqual(elements[1][0],calculated/4)
        self.assertAlmostEqual(elements[1][1],calculated/2)
        sim["reynolds_override"]=100000
        physical,solver,elements=reynolds_estimates(sim,.4,[[.1,.2]])
        self.assertAlmostEqual(physical,calculated)
        self.assertEqual(solver,100000)
        self.assertEqual(elements,[(25000,50000)])

    def test_both_tabs_roundtrip_and_live_estimate(self):
        root=tk.Tk();root.withdraw()
        try:
            desktop=DesktopApp(root)
            for pane in desktop.panes.values():
                self.assertEqual(len(pane.flight_inputs.transition_model_box["values"]),9)
                self.assertNotIn("transition_model",pane.settings)
                for model in TRANSITION_MODELS:
                    pane.flight_inputs.transition_model.set(transition_model_label(model))
                    c=pane.config();self.assertEqual(c["simulation"]["transition_model"],model)
                    pane.apply_config(c)
                    self.assertEqual(pane.flight_inputs.transition_model.get(),transition_model_label(model))
                pane.flight_inputs.speed.set("20");pane.flight_inputs.speed_unit.set("m/s")
                pane.update_reynolds_estimate();before=pane.flight_inputs.reynolds_text.get()
                pane.flight_inputs.speed.set("40");pane.update_reynolds_estimate()
                self.assertNotEqual(before,pane.flight_inputs.reynolds_text.get())
                pane.rows[0]["chord"].set("100:200");pane.rows[0]["length_unit"].set("mm")
                pane.update_reynolds_estimate();self.assertIn(" to ",pane.flight_inputs.element_reynolds_text.get())
                pane.settings["reynolds"].set("100000");pane.update_reynolds_estimate()
                self.assertIn("Solver override: 100,000",pane.flight_inputs.reynolds_text.get())
                pane.flight_inputs.speed.set("");pane.update_reynolds_estimate()
                self.assertIn("enter valid",pane.flight_inputs.reynolds_text.get())
                self.assertEqual(pane.flight_inputs.element_reynolds_text.get(),"")
        finally:root.destroy()

    def test_saved_model_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            for model in TRANSITION_MODELS:
                c=fixtures.config();c["simulation"]["transition_model"]=model
                run=Path(directory)/str(model)
                w.run(c,run,solver=fixtures.WorkflowTests.FakeSolver(),progress=lambda _:None)
                self.assertEqual(json.loads((run/"best/best_config.json").read_text())["simulation"]["transition_model"],model)
                self.assertEqual(json.loads((run/"provenance.json").read_text())["transition_model"],transition_model_name(model))
