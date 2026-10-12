"""Library data, GUI and saved configuration regression checks."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
import airfoil_library as lib
import wing_optimizer as w
from library_dialog import LibraryDialog
from test_optimizer import config
import test_optimizer as fixtures

class LibraryTests(unittest.TestCase):
    def test_all_installed_profiles(self):
        entries=lib.airfoils()
        self.assertGreaterEqual(len(entries),80)
        self.assertEqual(len({e["id"] for e in entries}),len(entries))
        for entry in entries:
            with self.subTest(profile=entry["id"]):
                path=lib.resolve_profile(entry["id"],Path("unrelated"))
                self.assertEqual(path,lib.resolve_profile(entry["name"],Path("unrelated")))
                self.assertTrue(w.Polygon(w.profile(entry["id"],120,w.ROOT)).is_valid)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),entry["sha256"])
                self.assertTrue(entry["source_url"].startswith("http"))
    def test_named_aliases(self):
        for name,id in [("Selig S1223","s1223"),("Benzing Be 153-055","be153-055"),("e423","e423"),("MSHD","mshd")]:
            self.assertEqual(lib.find(name)["id"],id)
    def test_mshd_provenance(self):
        e=lib.find("MSHD")
        self.assertIn("figure-derived",e["name"])
        self.assertIn("approximation",e["method"])
        self.assertAlmostEqual(e["validation"]["max_thickness"],.129,delta=.005)
        self.assertAlmostEqual(e["validation"]["max_camber"],.138,delta=.01)
    def test_copied_coordinates_and_best_config(self):
        with tempfile.TemporaryDirectory() as d:
            c=config(); c["elements"]=[dict(profile="E423",chord_m=1,incidence_deg=0)]
            output=Path(d)/"run"
            w.run(c,output,solver=fixtures.WorkflowTests.FakeSolver(),progress=lambda _:None)
            copied=json.loads((output/"config.json").read_text())
            best=json.loads((output/"best/best_config.json").read_text())
            self.assertEqual(copied["profile_sources"][0]["id"],"e423")
            provenance=json.loads((output/"provenance.json").read_text())
            self.assertEqual(provenance["profile_sources"][0]["id"],"e423")
            self.assertEqual(copied["elements"][0]["profile"],"input/element_1.dat")
            self.assertEqual(best["elements"][0]["profile"],"../input/element_1.dat")
            a=w.prepare(c,w.ROOT)[0]
            self.assertEqual(a,w.prepare(copied,output)[0])
            self.assertEqual(a,w.prepare(best,output/"best")[0])
    def test_unavailable_profile_and_unsafe_path(self):
        with tempfile.TemporaryDirectory() as d:
            manifest=Path(d)/"library.json"
            data=dict(airfoils=[dict(id="missing",name="Missing",family="Test",status="needs_coordinates")])
            manifest.write_text(json.dumps(data))
            with patch.object(lib,"MANIFEST",manifest):
                with self.assertRaisesRegex(ValueError,"no verified coordinates"):
                    lib.resolve_profile("missing",w.ROOT)
                data["airfoils"][0].update(status="available",file="../outside.dat")
                manifest.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError,"stay inside"):
                    lib.resolve_profile("missing",w.ROOT)
    def test_search_dialog_and_editor(self):
        from app import App
        root=tk.Tk(); root.withdraw()
        try:
            app=App(root)
            app.rows[0]["profile"].set("E423")
            self.assertEqual(app.config()["elements"][0]["profile"],"E423")
            w.prepare(app.config(),w.ROOT)
            selected=[]
            dialog=LibraryDialog(root,selected.append)
            dialog.family.set("Selig"); dialog.query.set("S1223")
            root.update_idletasks()
            ids=dialog.tree.get_children()
            self.assertEqual(set(ids),{"s1223","s1223rtl"})
            dialog.tree.selection_set("s1223"); dialog.preview(); dialog.select()
            self.assertEqual(selected,["S1223"])
        finally: root.destroy()

if __name__=="__main__": unittest.main(verbosity=2)
