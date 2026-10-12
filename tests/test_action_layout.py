import tkinter as tk
import unittest
from app import DesktopApp

class ActionLayoutTests(unittest.TestCase):
    def test_actions_stay_visible_on_every_tab_at_supported_sizes(self):
        root=tk.Tk();root.attributes("-alpha",0)
        try:
            desktop=DesktopApp(root)
            for width,height in ((1060,700),(1280,940)):
                root.geometry(f"{width}x{height}");root.update()
                for name,pane in desktop.panes.items():
                    desktop.tabs.select(desktop.frames[name])
                    for tab in pane.tabs.tabs():
                        pane.tabs.select(tab);root.update()
                        for button in (pane.preview_button,pane.start_button,pane.stop_button,pane.save_design_button):
                            self.assertTrue(button.winfo_ismapped())
                            y=button.winfo_rooty()-root.winfo_rooty()
                            self.assertGreaterEqual(y,0)
                            self.assertLessEqual(y+button.winfo_height(),root.winfo_height())
                        self.assertGreater(pane.tabs.winfo_height(),100)
            self.assertTrue(desktop.panes["sizing"].fidelity.scrollbar.winfo_manager())
        finally:root.destroy()
