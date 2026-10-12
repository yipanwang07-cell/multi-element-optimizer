import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import wing_optimizer as w
from coordinate_search import run_search

def setup(mode="sequential", workers=4, budget=30):
    return dict(elements=[dict(profile="0012",chord_m=1,incidence_deg=dict(min=0,max=10,step=1))],
                reference_chord_m=1,alpha_deg=0,panels_per_element=40,
                simulation=dict(reynolds=300000),search=dict(mode=mode,workers=workers,max_geometries=budget))

class Solver:
    parallel_safe=True
    def __init__(self,stop=None,fail=False):
        self.lock=threading.Lock();self.active=0;self.peak=0;self.stop=stop;self.fail=fail
    def analyze(self,geom,settings,alphas,directory):
        with self.lock:
            self.active+=1;self.peak=max(self.peak,self.active)
        try:
            time.sleep(.015)
            if self.stop:
                self.stop.set()
                raise w.Cancelled()
            if self.fail and directory.name.endswith("3"):raise RuntimeError("fixture failure")
            directory.mkdir(parents=True)
            (directory/"polar.txt").write_text("fixture")
            (directory/"run.jfscript").write_text("fixture")
            return [dict(alpha=0,cl=geom[0][0][1],cd=.01,cm=0)]
        finally:
            with self.lock:self.active-=1

class ParallelTests(unittest.TestCase):
    def test_serial_parallel_same_winner_and_csv(self):
        for mode in ("sequential","free","grid","random"):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d,patch("cpu_workers.physical_core_cpus",return_value=list(range(8))):
                outputs=[]
                for workers in (1,4):
                    c=setup(mode,workers)
                    if mode=="free":
                        c["elements"][0]["chord"]=dict(min=.8,max=1,step=.1)
                        c["height_constraints"]=[dict(elements=[1],max_height=.5)]
                    solver=Solver(fail=True); dest=Path(d)/str(workers)
                    result=w.run(c,dest,solver=solver,progress=lambda _:None)
                    outputs.append((result["best"],(dest/"results.csv").read_text(),result["evaluated_geometries"]))
                    self.assertEqual(solver.active,0)
                    if workers==4:self.assertEqual(solver.peak,4)
                self.assertEqual(outputs[0],outputs[1])
    def test_legacy_budget_does_not_stop_refinement(self):
        with tempfile.TemporaryDirectory() as d,patch("cpu_workers.physical_core_cpus",return_value=list(range(8))):
            result=w.run(setup(budget=6),Path(d)/"run",solver=Solver(),progress=lambda _:None)
            self.assertGreater(result["evaluated_geometries"],6)
            self.assertEqual(result["search"]["termination"],"bounded_coordinate_local_maximum")
    def test_more_than_1000_evaluations_and_minimal_console(self):
        from test_optimizer import WorkflowTests
        c=setup("grid")
        c["search"]["max_geometries"]=1000
        c["elements"][0]["incidence_deg"]=dict(min=0,max=10,step=.01)
        messages=[]
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/"run"
            result=w.run(c,dest,solver=WorkflowTests.FakeSolver(),progress=messages.append)
            self.assertEqual(result["evaluated_geometries"],1001)
            self.assertEqual(len(messages),1001)
            self.assertEqual(messages[1],"Iteration 2: sweep angle 1: 0.01 deg")
            self.assertTrue(messages[-1].startswith("Iteration 1001:"))
            self.assertTrue(all("best" not in line and "/1000" not in line for line in messages))
            self.assertNotIn("max_geometries",json.loads((dest/"config.json").read_text())["search"])
    def test_cancel_drains_workers(self):
        with tempfile.TemporaryDirectory() as d,patch("cpu_workers.physical_core_cpus",return_value=list(range(8))):
            stop=threading.Event();solver=Solver(stop)
            result=w.run(setup("grid"),Path(d)/"run",solver=solver,stop=stop,progress=lambda _:None)
            self.assertTrue(result["cancelled"]);self.assertEqual(solver.active,0)
    def test_batch_search_matches_serial_for_interacting_parameters(self):
        axes=dict(incidence_1=[0,10],incidence_2=[0,10],gap_2=[.1],overlap_2=[0])
        def evaluate(p):return dict(cl=-(p["incidence_1"]-3)**2-(p["incidence_2"]-p["incidence_1"])**2)
        a=run_search(axes,evaluate,{"incidence_1","incidence_2"})
        b=run_search(axes,evaluate,{"incidence_1","incidence_2"},evaluate_many=lambda ps:map(evaluate,ps))
        self.assertEqual(a,b)
