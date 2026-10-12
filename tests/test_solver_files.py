import errno
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import wing_optimizer as w
import safe_files

class SolverFileTests(unittest.TestCase):
    def solver(self):
        solver=object.__new__(w.JavaFoil)
        return solver

    def test_isolated_files_archived_with_retry_and_replay_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/"synced run";seen=[]
            def solve(g,s,a,d,*args):
                seen.append(d)
                self.assertNotEqual(d.parent,dest.parent)
                (d/"polar.txt").write_text("polar")
                (d/"run.jfscript").write_text('Open("'+d.as_posix()+'/geometry.txt");')
                return [dict(cl=1)]
            original=safe_files.os.replace;failed=[]
            def replace(a,b):
                if not failed:failed.append(True);raise OSError(errno.EINVAL,"Temporary sync error")
                return original(a,b)
            with patch.object(w.JavaFoil,"_analyze_local",side_effect=solve),patch("safe_files.os.replace",side_effect=replace),patch("safe_files.time.sleep"):
                rows=self.solver().analyze([],{},[0],dest)
            self.assertEqual(rows,[dict(cl=1)])
            self.assertEqual((dest/"polar.txt").read_text(),"polar")
            self.assertIn(dest.as_posix(),(dest/"run.jfscript").read_text())
            self.assertFalse(seen[0].exists())

    def test_failure_preserves_diagnostics_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            seen=[]
            def fail(g,s,a,d,*args):
                seen.append(d);(d/"javafoil.log").write_text("export failed")
                raise RuntimeError("solver failed")
            with patch.object(w.JavaFoil,"_analyze_local",side_effect=fail),self.assertRaisesRegex(RuntimeError,"solver failed"):
                self.solver().analyze([],{},[0],Path(folder))
            self.assertEqual((Path(folder)/"javafoil.log").read_text(),"export failed")
            self.assertFalse(seen[0].exists())

    def test_parallel_calls_have_distinct_workspaces(self):
        from concurrent.futures import ThreadPoolExecutor
        barrier=threading.Barrier(2);seen=[]
        def solve(g,s,a,d,*args):
            seen.append(d);barrier.wait(timeout=5)
            (d/"polar.txt").write_text(str(d))
            return []
        with tempfile.TemporaryDirectory() as folder,patch.object(w.JavaFoil,"_analyze_local",side_effect=solve):
            with ThreadPoolExecutor(2) as pool:
                futures=[pool.submit(self.solver().analyze,[],{},[0],Path(folder)/str(i)) for i in range(2)]
                for f in futures:f.result()
            self.assertEqual(len(set(seen)),2)
            self.assertTrue(all(not p.exists() for p in seen))
