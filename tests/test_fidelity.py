import tkinter as tk
import unittest
from coordinate_search import run_search,sweep_resolution
from app import DesktopApp

class FidelityTests(unittest.TestCase):
    def test_custom_steps_and_refinement_window(self):
        for mode in ("sequential","free"):
            events=[]
            result=run_search(dict(incidence_1=[0,20]),lambda p:dict(cl=-(p["incidence_1"]-5.05)**2),
                {"incidence_1"},settings=dict(mode=mode,coarse_divisions=4,fine_step_percent=.25),trace=events.append)
            coarse=[e["parameters"]["incidence_1"] for e in events if e["phase"]=="coarse" and e["cycle"]==1]
            fine=[e["parameters"]["incidence_1"] for e in events if e["phase"]=="fine" and e["cycle"]==1]
            self.assertEqual(coarse,[0,5,10,15,20])
            self.assertTrue(all(4.5<=x<=5.5 for x in fine))
            self.assertEqual(result["parameters"]["incidence_1"],5.05)
            self.assertEqual(result["resolution"]["incidence_1"]["step"],.05)
            self.assertTrue(result["converged"])
    def test_validation(self):
        self.assertEqual(sweep_resolution({}),(10,.25))
        for c,f in ((0,.25),(10,0),(20,2.5),("2.5",.25),(True,.25),(10,"nan")):
            with self.subTest(c=c,f=f),self.assertRaises(ValueError):
                sweep_resolution(dict(coarse_divisions=c,fine_step_percent=f))
    def test_tabs_are_independent_and_roundtrip(self):
        root=tk.Tk();root.withdraw()
        try:
            desktop=DesktopApp(root)
            a=desktop.panes["placement"];b=desktop.panes["sizing"]
            for pane in (a,b):
                self.assertIn("Search settings",[pane.tabs.tab(tab,"text") for tab in pane.tabs.tabs()])
            a.fidelity.coarse.set("5");a.fidelity.fine.set("0.1")
            a.fidelity.workers.set("3")
            c=a.config()
            self.assertEqual(c["search"]["coarse_divisions"],5)
            self.assertEqual(b.config()["search"]["coarse_divisions"],10)
            self.assertEqual(c["search"]["workers"],3)
            self.assertEqual(b.config()["search"]["workers"],4)
            a.fidelity.set({});a.apply_config(c)
            self.assertEqual(a.fidelity.get(),dict(coarse_divisions=5,fine_step_percent=.1,workers=3))
            self.assertIn("Fine step: 0.1% of the full range",a.fidelity.description.get())
            self.assertIn("Coarse step: 20%",a.fidelity.description.get())
        finally:root.destroy()
