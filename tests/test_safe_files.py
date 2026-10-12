import errno
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import safe_files
import wing_optimizer as w


class SafeSaveTests(unittest.TestCase):
    def test_export_recovers_from_invalid_argument(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            replace = safe_files.os.replace
            failed = []
            def flaky(source, destination):
                if Path(destination).name == "coordinates_at_best_alpha_m.json" and not failed:
                    failed.append(True)
                    raise OSError(errno.EINVAL, "Invalid argument", str(destination))
                return replace(source, destination)
            with patch("safe_files.os.replace", side_effect=flaky), patch("safe_files.time.sleep"):
                w.export_geometry(target, [w.naca4("0012")], 1)
            self.assertTrue(failed)
            self.assertTrue((target / "coordinates_at_best_alpha_m.json").read_text().startswith("["))
            self.assertEqual(list(target.glob(".save-*")), [])

    def test_permanent_failure_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "best.json"
            target.write_text("previous")
            with patch("safe_files.os.replace", side_effect=OSError(errno.EINVAL, "Invalid argument")) as replace, patch("safe_files.time.sleep"):
                with self.assertRaises(OSError):
                    safe_files.atomic_write_text(target, "replacement")
            self.assertEqual(replace.call_count, 5)
            self.assertEqual(target.read_text(), "previous")
            self.assertEqual(list(Path(folder).glob(".save-*")), [])

    def test_disk_full_is_not_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("safe_files.os.replace", side_effect=OSError(errno.ENOSPC, "Disk full")) as replace:
                with self.assertRaises(OSError):
                    safe_files.atomic_write_text(Path(folder) / "best.json", "data")
            self.assertEqual(replace.call_count, 1)

    def test_unicode_path_and_repeated_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "design α 翼.json"
            for text in ("first", "翼 α", ""):
                safe_files.atomic_write_text(target, text)
                self.assertEqual(target.read_text(encoding="utf-8"), text)
            self.assertEqual(list(Path(folder).glob(".save-*")), [])

    def test_sync_failure_preserves_old_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "best.json"
            target.write_text("old")
            with patch("safe_files.os.fsync", side_effect=OSError(errno.ENOSPC, "Disk full")):
                with self.assertRaises(OSError): safe_files.atomic_write_text(target, "new")
            self.assertEqual(target.read_text(), "old")
            self.assertEqual(list(Path(folder).glob(".save-*")), [])

    def test_temporary_creation_failure_recovers(self):
        with tempfile.TemporaryDirectory() as folder:
            original = safe_files.tempfile.NamedTemporaryFile
            calls = []
            def flaky(*args, **kwargs):
                calls.append(True)
                if len(calls) == 1: raise PermissionError(errno.EACCES, "Busy")
                return original(*args, **kwargs)
            with patch("safe_files.tempfile.NamedTemporaryFile", side_effect=flaky), patch("safe_files.time.sleep"):
                safe_files.atomic_write_text(Path(folder) / "best.json", "new")
            self.assertEqual(len(calls), 2)
            self.assertEqual((Path(folder) / "best.json").read_text(), "new")

    def test_whole_run_recovers_at_each_winner_file(self):
        import json
        from test_optimizer import config, WorkflowTests
        names = ["coordinates_at_best_alpha_m.json", "best.json", "best_config.json", "polar.txt", "source_case.jfscript"]
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / "run"
                original = safe_files.os.replace
                failures = []
                def flaky(source, destination):
                    if Path(destination).name == name and not failures:
                        failures.append(True)
                        raise OSError(errno.EINVAL, "Invalid argument")
                    return original(source, destination)
                with patch("safe_files.os.replace", side_effect=flaky), patch("safe_files.time.sleep"):
                    summary = w.run(config(), target, solver=WorkflowTests.FakeSolver(), progress=lambda _: None)
                self.assertTrue(failures)
                self.assertEqual(summary["best"], json.loads((target / "best/best.json").read_text())["result"])
                self.assertEqual(summary["successful_geometries"], 8)
                self.assertEqual(list(target.rglob(".save-*")), [])

    def test_persistent_export_failure_keeps_winning_csv_row(self):
        import csv
        from test_optimizer import config, WorkflowTests
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "run"
            with patch("safe_files.os.replace", side_effect=OSError(errno.EACCES, "Locked")), patch("safe_files.time.sleep"):
                with self.assertRaises(OSError):
                    w.run(config(), target, solver=WorkflowTests.FakeSolver(), progress=lambda _: None)
            with (target / "results.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertTrue((target / "cases" / rows[0]["geometry_id"] / "polar.txt").is_file())
