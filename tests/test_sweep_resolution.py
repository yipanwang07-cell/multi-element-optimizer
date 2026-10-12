import unittest
from coordinate_search import run_search
from geometric_constraints import free_order

class SweepResolutionTests(unittest.TestCase):
    def test_positions_refine_near_coarse_winner(self):
        events=[]; calls=[]
        def evaluate(p):
            calls.append(p["incidence_1"]); return dict(cl=-(p["incidence_1"]-3.03)**2)
        result=run_search({"incidence_1":[0,10]},evaluate,{"incidence_1"},
            settings=dict(max_refinements=99,angle_tolerance_deg=.0000001,cl_tolerance=1e-9),trace=events.append)
        self.assertEqual(result["initial_divisions"],10)
        self.assertTrue(result["fine_stage"])
        self.assertAlmostEqual(result["parameters"]["incidence_1"],3.025)
        self.assertEqual(result["refinement_half_width_percent"],2.5)
        self.assertTrue(any(e["phase"]=="fine" for e in events))
        self.assertLessEqual(len(calls),32)
        fine=[e["parameters"]["incidence_1"] for e in events if e["phase"]=="fine" and e["cycle"]==1]
        self.assertTrue(all(2.75-1e-10<=x<=3.25+1e-10 for x in fine))
    def test_sizing_finishes_coarse_before_single_fine_stage(self):
        axes={"chord_1":[1,2],"incidence_1":[0,10]}
        events=[]; calls=[]
        def evaluate(p):
            calls.append(dict(p))
            return dict(cl=10-(p["chord_1"]-1.6125)**2-(p["incidence_1"]-3.03)**2)
        result=run_search(axes,evaluate,set(axes),settings=dict(mode="free",parameter_order=free_order(1),max_passes=1,cl_tolerance=1e-9),trace=events.append)
        coarse=[i for i,e in enumerate(events) if e["phase"]=="coarse"]
        fine=[i for i,e in enumerate(events) if e["phase"]=="fine"]
        self.assertLess(max(coarse),min(fine))
        self.assertAlmostEqual(result["parameters"]["chord_1"],1.6125)
        self.assertAlmostEqual(result["parameters"]["incidence_1"],3.025)
        self.assertAlmostEqual(result["resolution"]["incidence_1"]["step"],.025)
        self.assertAlmostEqual(result["refinement_windows"]["incidence_1"]["center"],3)
        self.assertAlmostEqual(result["refinement_windows"]["chord_1"]["step"],.0025)
        self.assertTrue(all(e.get("level",0)<=1 for e in events))
        self.assertTrue(result["converged"])

if __name__=="__main__": unittest.main()
