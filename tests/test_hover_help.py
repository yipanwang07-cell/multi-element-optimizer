import tkinter as tk
import unittest
from unittest.mock import patch
from hover_help import HELP,help_icon
from app import DesktopApp

class HelpTests(unittest.TestCase):
    def test_popup_lifecycle_and_hidden_controls(self):
        root=tk.Tk();root.withdraw()
        try:
            icon=help_icon(root,"gap");icon.pack();tip=icon.tooltip
            tip.schedule()
            self.assertIsNotNone(tip.timer)
            tip.hide();self.assertIsNone(tip.timer)
            tip.show();self.assertIsNone(tip.window)
            with patch.object(icon,"winfo_ismapped",return_value=True),patch.object(tk.Toplevel,"deiconify"):
                tip.show();self.assertIsNotNone(tip.window)
                popup=tip.window
                tip.hide();self.assertFalse(popup.winfo_exists())
                tip.show();icon.destroy()
                self.assertIsNone(tip.window)
        finally:root.destroy()
    def test_real_forms_have_help_for_their_technical_terms(self):
        root=tk.Tk();root.withdraw()
        try:
            app=DesktopApp(root)
            def keys(widget):
                found={widget.help_key} if hasattr(widget,"help_key") else set()
                for child in widget.winfo_children():found|=keys(child)
                return found
            required={"chord","gap","overlap","angle_mode","incidence_deg","wingspan","airspeed","reynolds","mach","workers","ground_effect","ground_clearance","cl"}
            for pane in app.panes.values():self.assertTrue(required<=keys(pane.tabs.master))
            self.assertTrue({"height_airfoil","geometry_limit"}<=keys(app.frames["sizing"]))
            for key in required:self.assertTrue(HELP[key])
        finally:root.destroy()

if __name__=="__main__":unittest.main()
