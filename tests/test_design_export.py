import json
import tempfile
import threading
from pathlib import Path
import tkinter as tk
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import wing_optimizer as w
import test_optimizer as fixtures
from design_export import export_design,parse_distribution

class ExportSolver(fixtures.WorkflowTests.FakeSolver):
    def __init__(self,settings=None,stop=None):super().__init__()
    def analyze(self,g,settings,alphas,directory,surface_distributions=False,flow_field=False):
        rows=super().analyze(g,settings,alphas,directory)
        for kind,name in (("velocity ratio","velocity"),("pressure coefficient","pressure")):
            root=ET.Element("section-aerodynamics");ET.SubElement(root,"value").text=kind
            elements=ET.SubElement(root,"elements");case=ET.SubElement(ET.SubElement(root,"cases"),"case")
            for i,points in enumerate(g):
                coordinates=ET.SubElement(ET.SubElement(elements,"element"),"coordinates")
                values=ET.SubElement(case,"element",idx=str(i))
                for j,(x,y) in enumerate(points):
                    p=ET.SubElement(coordinates,"point")
                    ET.SubElement(p,"x").text=str(x);ET.SubElement(p,"y").text=str(y)
                    ET.SubElement(values,"value").text=str(1+j*.01 if name=="velocity" else -.1*j)
            ET.ElementTree(root).write(directory/(name+".xml"),encoding="utf-8",xml_declaration=True)
        if flow_field:
            text='VARIABLES=x y vx vy v Cp\nZONE T="Velocity", I=4, J=4\n'
            text+=''.join(f"{x} {y} 1 0 1 0\n" for x in [-1,0,1,2] for y in [-1,0,1,2])
            (directory/"flow_field.txt").write_text(text)
        return rows

def graph_stub(stage,*args): (stage/"graphs").mkdir()
def report_stub(stage,*args): (stage/"design_report.pdf").write_bytes(b"%PDF-1.4 test fixture")

class DesignExportTests(unittest.TestCase):
    def make_run(self,folder):
        c=dict(elements=[dict(profile="E423",chord_m=.4,incidence_deg=0),
                         dict(profile="S1223",chord_m=.1,incidence_deg=0,gap=.12,overlap=0)],
            reference_chord_m=.4,panels_per_element=40,alpha_deg=0,search=dict(mode="grid",max_geometries=1),
            simulation=dict(reynolds=300000,mach=0))
        run=folder/"run";w.run(c,run,solver=fixtures.WorkflowTests.FakeSolver(),progress=lambda s:None);return run
    def test_destination_folder_is_unique_portable_and_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run=self.make_run(root);parent=root/"chosen destination";parent.mkdir()
            (parent/"keep.txt").write_text("untouched")
            with patch("design_export.w.JavaFoil",ExportSolver),patch("design_report.create_graphs",graph_stub),patch("design_report.create_report",report_stub):
                first=export_design(run,parent);second=export_design(run,parent)
            self.assertNotEqual(first,second);self.assertEqual((parent/"keep.txt").read_text(),"untouched")
            self.assertTrue((first/"design_report.pdf").exists())
            self.assertTrue((first/"data/surface_distributions.csv").exists())
            self.assertFalse((first/"data/flow_field.csv").exists())
            self.assertFalse((first/"analysis/flow_field.txt").exists())
            self.assertFalse(list((first/"geometry").glob("*.svg")))
            self.assertTrue((first/"geometry/coordinates_m.csv").exists())
            for path in (first/"geometry/best_config.json",first/"data/config.json"):
                c=json.loads(path.read_text());w.prepare(c,path.parent)
                self.assertTrue(all((path.parent/e["profile"]).is_file() for e in c["elements"]))
            self.assertFalse(list(parent.glob("*.building")))
    def test_failed_export_removes_only_its_own_partial_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run=self.make_run(root);parent=root/"out";parent.mkdir();sentinel=parent/"keep.txt";sentinel.write_text("safe")
            with patch("design_export.w.JavaFoil",ExportSolver),patch("design_report.create_graphs",side_effect=RuntimeError("render failed")):
                with self.assertRaisesRegex(RuntimeError,"render failed"):export_design(run,parent)
            self.assertEqual(list(parent.iterdir()),[sentinel])
    def test_distribution_validation_rejects_wrong_graph_type(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);geometry=[w.naca4("0012",40)]
            ExportSolver().analyze(geometry,{},[0],folder/"analysis",True)
            with self.assertRaisesRegex(ValueError,"Unexpected distribution"):parse_distribution(folder/"analysis/velocity.xml","pressure coefficient",geometry)
    def test_native_subset_keeps_coordinates_and_values_paired(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/"analysis"
            geometry=[[(1,0),(.5,.1),(0,0),(.5,-.1),(1,0)]]
            ExportSolver().analyze(geometry,{},[0],folder,True)
            path=folder/"pressure.xml";tree=ET.parse(path)
            coordinates=tree.find("elements/element/coordinates")
            values=tree.find("cases/case/element")
            coordinates.remove(coordinates[2]);values.remove(values[2])
            tree.write(path,encoding="utf-8")
            rows,points=parse_distribution(path,"pressure coefficient",geometry,with_coordinates=True)
            self.assertEqual(points[0],[(1,0),(.5,.1),(.5,-.1),(1,0)])
            self.assertAlmostEqual(rows[0][2],-.3)
            coordinates[1].find("x").text="9"
            tree.write(path,encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"differs from the winner"):
                parse_distribution(path,"pressure coefficient",geometry)
    def test_rejects_missing_value_for_native_coordinate(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/"analysis";geometry=[w.naca4("0012",40)]
            ExportSolver().analyze(geometry,{},[0],folder,True)
            path=folder/"pressure.xml";tree=ET.parse(path)
            values=tree.find("cases/case/element");values.remove(values[0])
            tree.write(path,encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"coordinate/value count"):
                parse_distribution(path,"pressure coefficient",geometry)
    def test_retired_solver_result_requires_a_new_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);run=self.make_run(folder)
            summary=json.loads((run/"summary.json").read_text())
            summary["best"].update(solver="retired-backend",validated=True)
            (run/"summary.json").write_text(json.dumps(summary))
            with self.assertRaisesRegex(ValueError,"retired solver"):
                export_design(run,folder)
            self.assertFalse(list(folder.glob("Wing_design_*")))

    def test_save_button_can_be_canceled_and_reports_completion(self):
        from app import App
        root=tk.Tk();root.withdraw()
        try:
            app=App(root)
            run_temp=tempfile.TemporaryDirectory()
            self.addCleanup(run_temp.cleanup)
            app.output=self.make_run(Path(run_temp.name))
            with patch("app.filedialog.askdirectory",return_value=""):app.save_design()
            self.assertFalse(app.saving)
            with tempfile.TemporaryDirectory() as temporary:
                with patch("app.filedialog.askdirectory",return_value=temporary),patch("app.threading.Thread") as thread:
                    app.save_design();self.assertTrue(app.saving);thread.return_value.start.assert_called_once()
                app.messages.put(("saved",temporary));app.poll()
                self.assertFalse(app.saving);self.assertEqual(app.saved_design,Path(temporary))
        finally:root.destroy()

if __name__=="__main__":unittest.main()
