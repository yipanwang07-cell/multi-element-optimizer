"""Check independence and configuration routing of the two function tabs."""
import json
import tkinter as tk
import unittest
from app import DesktopApp
import wing_optimizer as w

class FunctionTabTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk(); self.root.withdraw()
        self.desktop=DesktopApp(self.root)
    def tearDown(self):
        self.root.destroy()
    def test_separate_airfoils_modes_and_height_limits(self):
        d=self.desktop; a=d.panes["placement"]; b=d.panes["sizing"]
        self.assertEqual([d.tabs.tab(t,"text") for t in d.tabs.tabs()],["Adjust positions","Size & fit"])
        original=b.rows[0]["chord"].get()
        a.rows[0]["chord"].set("350")
        self.assertEqual(b.rows[0]["chord"].get(),original)
        self.assertIsNot(a.rows[0]["profile"],b.rows[0]["profile"])
        self.assertEqual(a.config()["search"]["mode"],"sequential")
        self.assertEqual(b.config()["search"]["mode"],"free")
        self.assertEqual(a.config()["height_constraints"],[])
        self.assertEqual(len(b.config()["height_constraints"]),2)
        self.assertFalse(a.constraints.frame.winfo_manager())
        self.assertEqual(b.constraints.frame.winfo_manager(),"pack")
        self.assertIsNot(a.messages,b.messages)
        self.assertIsNot(a.stop,b.stop)
        w.prepare(a.config(),a.base); w.prepare(b.config(),b.base)
    def test_loading_routes_without_overwriting_other_tab(self):
        d=self.desktop
        placement=d.panes["placement"]; sizing=d.panes["sizing"]
        placement.rows[0]["chord"].set("375")
        c=json.loads((w.EXAMPLES/"free_optimization_example.json").read_text())
        c["elements"][0]["chord"]={"min":200,"max":300}
        d.apply_config(c,w.ROOT)
        self.assertEqual(d.tabs.select(),str(d.frames["sizing"]))
        self.assertEqual(sizing.rows[0]["chord"].get(),"200:300")
        self.assertEqual(placement.rows[0]["chord"].get(),"375")
        sizing.rows[0]["profile"].set("NACA 0012")
        c=json.loads((w.EXAMPLES/"sequential_example.json").read_text())
        d.apply_config(c,w.ROOT)
        self.assertEqual(d.tabs.select(),str(d.frames["placement"]))
        self.assertEqual(sizing.rows[0]["profile"].get(),"NACA 0012")

if __name__=="__main__": unittest.main()
