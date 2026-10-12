import threading
import tkinter as tk
import unittest
from grouped_search import run_grouped_search,parameter_blocks
from app import DesktopApp

class GroupedSearchTests(unittest.TestCase):
    def test_joint_change_escapes_single_parameter_trap(self):
        axes=dict(chord_1=[0,1],chord_2=[0,1],incidence_1=[0],incidence_2=[0],gap_2=[0],overlap_2=[0])
        def evaluate(p):
            a,b=p["chord_1"],p["chord_2"]
            return dict(cl=5 if a==b==1 else 0 if a==b==0 else -1)
        events=[]
        result=run_grouped_search(axes,evaluate,set(),settings=dict(height_constraints=[dict(elements=[1,2])],
            initial_parameters={n:0 for n in axes},workers=2),trace=events.append)
        self.assertEqual(result["cl"],5)
        self.assertEqual(result["parameters"]["chord_1"],1)
        self.assertEqual(result["parameters"]["chord_2"],1)
        self.assertEqual(result["parameter_blocks"][:2],[["chord_1","chord_2"],["incidence_1","incidence_2"]])
    def test_rejected_combination_cannot_win(self):
        axes=dict(chord_1=[0,1],chord_2=[0,1])
        def evaluate(p):
            if sum(p.values())>1:return None
            return dict(cl=sum(p.values()))
        result=run_grouped_search(axes,evaluate,set(),settings=dict(height_constraints=[dict(elements=[1,2])],initial_parameters=dict(chord_1=0,chord_2=0)))
        self.assertLessEqual(sum(result["parameters"].values()),1)
        self.assertEqual(result["cl"],1)
    def test_grouped_sweep_exceeds_2000_without_cap(self):
        axes=dict(chord_1=list(range(45)),chord_2=list(range(45)))
        result=run_grouped_search(axes,lambda p:dict(cl=sum(p.values())),set(),
            settings=dict(height_constraints=[dict(elements=[1,2])],workers=4,max_geometries=2000))
        self.assertEqual(result["unique_evaluations"],2025)
        self.assertEqual(result["cl"],88)
    def test_group_order_and_all_parameters(self):
        axes={f"{k}_{i}":[0,1] for k in ("chord","incidence","gap","overlap") for i in range(1,5) if i>1 or k in ("chord","incidence")}
        blocks=parameter_blocks(axes,[dict(elements=[1,2]),dict(elements=[3,4])])
        self.assertEqual(blocks[:4],[["chord_1","chord_2"],["incidence_1","incidence_2"],["gap_2"],["overlap_2"]])
        self.assertEqual(blocks[4],["chord_3","chord_4"])
        self.assertEqual({n for b in blocks for n in b},set(axes))
    def test_joint_fine_refinement_and_cancel(self):
        axes=dict(chord_1=[0,10],chord_2=[0,10])
        settings=dict(height_constraints=[dict(elements=[1,2])],coarse_divisions=2,fine_step_percent=.25,workers=3)
        result=run_grouped_search(axes,lambda p:dict(cl=-(p["chord_1"]-5.025)**2-(p["chord_2"]-4.975)**2),set(axes),settings=settings)
        self.assertEqual(result["parameters"],dict(chord_1=5.025,chord_2=4.975))
        stop=threading.Event();stop.set()
        result=run_grouped_search(axes,lambda p:None,set(axes),settings=settings,stop=stop)
        self.assertEqual(result["termination"],"cancelled")
    def test_selector_matches_airfoil_count_and_console_scrolls(self):
        root=tk.Tk();root.withdraw()
        try:
            pane=DesktopApp(root).panes["sizing"]
            self.assertEqual(len(pane.rows),4)
            self.assertTrue(all(len(r["selected"])==4 for r in pane.constraints.rows))
            pane.remove()
            self.assertTrue(all(len(r["selected"])==3 for r in pane.constraints.rows))
            self.assertEqual(pane.constraints.get()[1]["elements"],[3])
            pane.add()
            self.assertTrue(all(len(r["selected"])==4 for r in pane.constraints.rows))
            self.assertEqual(pane.constraints.get()[1]["elements"],[3])
            self.assertEqual(str(pane.console_scrollbar.cget("orient")),"vertical")
            self.assertTrue(pane.log.cget("yscrollcommand"))
        finally:root.destroy()

    def test_invalid_start_is_rejected_before_evaluation(self):
        for initial in (-1, 2, float("nan"), .5):
            with self.subTest(initial=initial):
                calls=[]
                with self.assertRaises(ValueError):
                    run_grouped_search({"chord_1":[0,1]}, lambda p:calls.append(p) or dict(cl=1), set(), settings=dict(initial_parameters={"chord_1":initial}))
                self.assertEqual(calls, [])
