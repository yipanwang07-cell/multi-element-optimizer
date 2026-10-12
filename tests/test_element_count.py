"""Regression coverage for designs beyond the former five-element limit."""
import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
import wing_optimizer as w
from app import DesktopApp
from design_export import export_design
from test_design_export import ExportSolver
import test_optimizer as fixtures


def configuration(count=7):
    elements=[dict(profile="0012",chord_m=.2,incidence_deg=2)]
    elements += [dict(profile="0012",chord_m=.2,incidence_deg=2,gap=.2,overlap=-.2) for _ in range(count-1)]
    return dict(elements=elements,reference_chord_m=.2,panels_per_element=40,alpha_deg=0,
                search=dict(mode="grid",workers=1),simulation=dict(reynolds=300000,mach=0))


class ElementCountTests(unittest.TestCase):
    def test_twelve_elements_and_empty_input(self):
        c=configuration(12)
        profiles,chords,reference,axes,alphas,clearance=w.prepare(c,w.ROOT)
        geometry=w.build_geometry(profiles,chords,{k:v[0] for k,v in axes.items()},reference)
        w.validate_geometry(geometry,clearance)
        self.assertEqual(len(geometry),12)
        c["elements"]=[]
        with self.assertRaisesRegex(ValueError,"at least one"):
            w.prepare(c,w.ROOT)

    def test_both_editors_load_add_preview_and_select_seventh_element(self):
        root=tk.Tk();root.withdraw()
        try:
            desktop=DesktopApp(root)
            for mode,pane in desktop.panes.items():
                c=configuration()
                c["search"]["mode"]="free" if mode=="sizing" else "sequential"
                if mode=="sizing":
                    c["height_constraints"]=[dict(elements=[1,7],max_height=5,unit="m")]
                pane.apply_config(c)
                self.assertEqual(len(pane.rows),7)
                pane.add()
                self.assertEqual(len(pane.rows),8)
                self.assertEqual(len(pane.config()["elements"]),8)
                if mode=="sizing":
                    row=pane.constraints.rows[0]
                    self.assertEqual(len(row["selected"]),8)
                    self.assertTrue(row["selected"][6].get())
                    self.assertEqual(int(row["choices"].winfo_children()[6].grid_info()["row"]),1)
                profiles,chords,ref,axes,_,_=w.prepare(c,w.ROOT)
                pane.geometry=w.build_geometry(profiles,chords,{k:v[0] for k,v in axes.items()},ref)
                pane.draw()
                self.assertGreaterEqual(sum(pane.canvas.type(i)=="polygon" for i in pane.canvas.find_all()),7)
        finally:
            root.destroy()

    def test_seven_element_optimization_and_complete_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);run=root/"run"
            result=w.run(configuration(),run,solver=fixtures.WorkflowTests.FakeSolver(),progress=lambda _:None)
            self.assertIn("incidence_7",result["best"])
            with patch("design_export.w.JavaFoil",ExportSolver):
                saved=export_design(run,root)
            details=json.loads((saved/"export_details.json").read_text())
            self.assertEqual(details["element_count"],7)
            self.assertEqual(len(details["dimensions"]),7)
            self.assertTrue((saved/"design_report.pdf").is_file())
            self.assertEqual(len(list((saved/"graphs").glob("*.png"))),2)
