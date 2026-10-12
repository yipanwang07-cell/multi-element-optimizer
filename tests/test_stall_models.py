import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
import wing_optimizer as w
import test_optimizer as fixtures
from app import DesktopApp
from stall_models import STALL_MODELS, stall_model_id


class StallModelTests(unittest.TestCase):
    def test_default_and_invalid_values(self):
        c=fixtures.config();w.prepare(c,w.ROOT)
        self.assertEqual(c["simulation"]["stall_model"],1)
        for value in (-1,3,True,1.5,"1",None):
            with self.subTest(value=value),self.assertRaises(ValueError):stall_model_id(value)

    def test_both_tabs_and_saved_settings(self):
        root=tk.Tk();root.withdraw()
        try:
            desktop=DesktopApp(root)
            for pane in desktop.panes.values():
                self.assertEqual(tuple(pane.flight_inputs.stall_model_box["values"]),tuple(STALL_MODELS.values()))
                for key,name in STALL_MODELS.items():
                    pane.flight_inputs.stall_model.set(name)
                    c=pane.config();self.assertEqual(c["simulation"]["stall_model"],key)
                    pane.apply_config(c)
                    self.assertEqual(pane.flight_inputs.stall_model.get(),name)
            desktop.panes["placement"].flight_inputs.stall_model.set("Calcfoil")
            self.assertEqual(desktop.panes["sizing"].flight_inputs.stall_model.get(),"None")
        finally:root.destroy()

    def test_saved_run_and_replay_keep_model(self):
        class RecordingSolver(fixtures.WorkflowTests.FakeSolver):
            def analyze(self,geometry,settings,alphas,directory):
                self.model=settings["stall_model"]
                return super().analyze(geometry,settings,alphas,directory)
        with tempfile.TemporaryDirectory() as temporary:
            for key,name in STALL_MODELS.items():
                c=fixtures.config();c["simulation"]["stall_model"]=key
                solver=RecordingSolver();run=Path(temporary)/str(key)
                w.run(c,run,solver=solver,progress=lambda _:None)
                self.assertEqual(solver.model,key)
                self.assertEqual(json.loads((run/"best/best_config.json").read_text())["simulation"]["stall_model"],key)
                self.assertEqual(json.loads((run/"provenance.json").read_text())["stall_model"],name)
                self.assertIn("Stall model: "+name,(run/"report.html").read_text(encoding="utf-8"))
