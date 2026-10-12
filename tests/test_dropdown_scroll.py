import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
from ui_theme import apply_theme, attach_scroll


class DropdownScrollTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        apply_theme(self.root)
        self.root.geometry("500x300+50+50")
        self.canvas = tk.Canvas(self.root)
        self.canvas.pack(fill="both", expand=True)
        self.content = ttk.Frame(self.canvas)
        self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, 450, 2000))
        attach_scroll(self.canvas, self.content)

    def tearDown(self):
        self.root.destroy()

    def combo(self, state):
        box = ttk.Combobox(self.content, state=state, height=6,
                           values=[f"Airfoil {i}" for i in range(100)])
        box.pack()
        box.current(2)
        self.root.update()
        return box

    def test_closed_fields_preserve_selection_and_scroll_panel(self):
        for state in ("normal", "readonly"):
            with self.subTest(state=state):
                self.canvas.yview_moveto(0)
                box = self.combo(state)
                changes = []
                box.bind("<<ComboboxSelected>>", lambda event: changes.append(box.get()))
                before = self.canvas.yview()
                # Synthetic input targets this field even if another desktop window covers it.
                with patch.object(self.root, "winfo_containing", return_value=box):
                    box.event_generate("<MouseWheel>", delta=-120, x=10, y=10)
                    self.root.update()
                self.assertEqual(box.current(), 2)
                self.assertEqual(changes, [])
                self.assertGreater(self.canvas.yview()[0], before[0])
                box.destroy()

    def test_open_long_list_scrolls_and_explicit_selection_works(self):
        box = self.combo("readonly")
        self.root.tk.call("ttk::combobox::Post", str(box))
        self.root.update()
        popup = self.root.tk.call("ttk::combobox::PopdownWindow", str(box))
        listing = str(popup) + ".f.l"
        before = self.root.tk.call(listing, "yview")
        self.root.tk.call("event", "generate", listing, "<MouseWheel>", "-delta", -120)
        self.root.update()
        after = self.root.tk.call(listing, "yview")
        self.assertGreater(float(after[0]), float(before[0]))
        self.assertEqual(box.current(), 2)
        self.root.tk.call(listing, "selection", "clear", 0, "end")
        self.root.tk.call(listing, "selection", "set", 20)
        self.root.tk.call("event", "generate", listing, "<Return>")
        self.root.update()
        self.assertEqual(box.current(), 20)
