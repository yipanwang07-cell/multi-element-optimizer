import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
from app import App
import wing_optimizer as w
from test_optimizer import config, WorkflowTests

class InterimPreviewTests(unittest.TestCase):
    def test_running_preview_uses_saved_snapshot_not_edited_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/"run"
            result=w.run(config(),out,solver=WorkflowTests.FakeSolver(),progress=lambda _:None)
            snapshot=json.loads((out/"best/best.json").read_text())
            self.assertEqual(snapshot["result"],result["best"])
            root=tk.Tk();root.withdraw()
            try:
                app=App(root);app.running=True;app.output=out
                with patch.object(app,"config",side_effect=AssertionError("Must not read edited inputs")):
                    app.preview()
                self.assertEqual(app.geometry,snapshot["preview_geometry"])
                self.assertEqual(app.scene_reference,snapshot["reference_chord_m"])
                self.assertIn("Best so far",app.status.get())
                self.assertTrue(app.running)
            finally:root.destroy()

    def test_no_result_and_unreadable_snapshot_do_not_interrupt_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root=tk.Tk();root.withdraw()
            try:
                app=App(root);app.running=True;app.output=Path(folder)
                app.preview()
                self.assertIn("Waiting",app.status.get())
                (app.output/"best").mkdir()
                (app.output/"best/best.json").write_text("invalid")
                app.preview()
                self.assertIn("being saved",app.status.get())
                self.assertTrue(app.running)
            finally:root.destroy()
