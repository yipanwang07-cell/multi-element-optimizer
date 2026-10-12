import csv
import json
from pathlib import Path
import tempfile
import unittest
from cfd_solver import configuration,read_result,surface_diagnostics,write_report

class CFDTests(unittest.TestCase):
    def test_configuration_is_viscous_infinite_span_and_explicit_ground(self):
        text=configuration(dict(reynolds=1000000,ground_effect=True),dict(transition=True))
        self.assertIn("SOLVER= INC_RANS",text)
        self.assertIn("WRT_RESTART_COMPACT= NO",text)
        self.assertIn("KIND_TURB_MODEL= SST",text)
        self.assertIn("KIND_TRANS_MODEL= LM",text)
        self.assertIn("MARKER_SYM= (ground)",text)
        self.assertIn("MU_CONSTANT= 1e-06",text)
        self.assertNotIn("ASPECT_RATIO",text)
        self.assertNotIn("MARKER_SYM",configuration(dict(reynolds=1e6),{}))
        with self.assertRaises(ValueError):configuration(dict(reynolds=-1),{})

    def history(self,path,unstable=False,nonfinite=False):
        with path.open("w",newline="") as stream:
            writer=csv.writer(stream);writer.writerow(["CL","CD","CMz","rms[P]","rms[U]","rms[V]","rms[w]"])
            for i in range(100):
                residual=-1 if i<20 else -9
                writer.writerow([float("nan") if nonfinite else 1+(i%2 if unstable else 0),.02,0,residual,residual,residual,residual])

    def test_convergence_rejects_unstable_and_nonfinite_values(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"history.csv"
            self.history(p);self.assertTrue(read_result(p)["converged"])
            self.history(p,unstable=True);self.assertFalse(read_result(p)["converged"])
            self.history(p,nonfinite=True)
            with self.assertRaises(ValueError):read_result(p)

    def test_wall_shear_diagnostics_and_report(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"surface.csv"
            p.write_text("x,y,Y_Plus,Skin_Friction_Coefficient_x,Skin_Friction_Coefficient_y,Pressure_Coefficient\n0.5,0.1,0.8,-0.01,0,0\n0.5,-0.1,0.9,0.01,0,0\n")
            g=[[(1,0),(.5,.1),(0,0),(.5,-.1),(1,0)]]
            result=surface_diagnostics(p,g)
            self.assertEqual(result["airfoils"][1]["reversed_shear_samples"],1)
            self.assertEqual(result["max_y_plus"],.9)
            write_report(Path(folder),dict(status="not converged",surface_diagnostics=result))
            self.assertIn("not converged",(Path(folder)/"report.html").read_text())

    def test_cancel_and_timeout_terminate_solver(self):
        import sys,threading
        import wing_optimizer as w
        from cfd_solver import run_process
        with tempfile.TemporaryDirectory() as folder:
            stop=threading.Event();stop.set()
            with self.assertRaises(w.Cancelled):
                run_process([sys.executable,"-c","import time; time.sleep(20)"],Path(folder),stop,10,"cancel")
            stop.clear()
            with self.assertRaisesRegex(RuntimeError,"timed out"):
                run_process([sys.executable,"-c","import time; time.sleep(20)"],Path(folder),stop,.01,"timeout")
