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
