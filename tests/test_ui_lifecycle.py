import tkinter as tk
import unittest
from app import DesktopApp

class LifecycleTests(unittest.TestCase):
    def test_destroy_cancels_refresh_timers(self):
        root=tk.Tk();root.withdraw()
        app=DesktopApp(root)
        for pane in app.panes.values():
            pane.poll()  # Manual refresh must not create a second timer.
        timers=[token for token in root.tk.call("after","info") if "poll" in str(root.tk.call("after","info",token))]
        self.assertEqual(len(timers),2)
        root.destroy()
        pending=root.tk.call("after","info")
        self.assertTrue(all(token not in pending for token in timers))
