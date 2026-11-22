import tempfile
import unittest
from pathlib import Path
from quality.cleaner import scan

class CleanerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_web_placeholder(self):
        (self.root / "index.html").write_text("Unleash the power")
        report = scan(self.root, "web")
        self.assertIn("slop_candidate", {f["kind"] for f in report["findings"]})
        self.assertEqual(report["deleted_files"], 0)

    def test_minecraft_placeholder(self):
        (self.root / "Example.java").write_text("package examplemod;")
        report = scan(self.root, "minecraft")
        self.assertEqual(len(report["findings"]), 1)

    def test_app_placeholder(self):
        (self.root / "main.py").write_text("# TODO: implement")
        self.assertEqual(len(scan(self.root, "app")["findings"]), 1)

    def test_backup_is_candidate_not_deleted(self):
        path = self.root / "old.bak"
        path.write_text("valuable backup")
        report = scan(self.root, "web")
        self.assertEqual(report["findings"][0]["kind"], "cleanup_candidate")
        self.assertEqual(path.read_text(), "valuable backup")

    def test_protected_resources(self):
        directory = self.root / "resources"
        directory.mkdir()
        (directory / "old.bak").write_text("important")
        self.assertEqual(scan(self.root, "minecraft")["findings"], [])

    def test_protected_migrations(self):
        directory = self.root / "migrations"
        directory.mkdir()
        (directory / "001.bak").write_text("important")
        self.assertEqual(scan(self.root, "app")["findings"], [])

    def test_ignores_symlinks(self):
        target = self.root / "actual.txt"
        target.write_text("data")
        try:
            (self.root / "temp.bak").symlink_to(target)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                self.skipTest("Windows account cannot create symlinks; junctions tested separately")
            raise
        self.assertEqual(scan(self.root, "web")["findings"], [])

    def test_unknown_builder(self):
        with self.assertRaises(ValueError):
            scan(self.root, "other")

    def test_no_changes(self):
        path = self.root / "index.html"
        path.write_text("Lorem ipsum")
        before = path.read_bytes()
        scan(self.root, "web")
        self.assertEqual(path.read_bytes(), before)

    def test_clean_project(self):
        (self.root / "index.html").write_text('<!doctype html><html lang="en"><head><title>Hello</title><meta name="viewport" content="width=device-width"></head><body><h1>Hello</h1></body></html>')
        self.assertEqual(scan(self.root, "web")["findings"], [])

if __name__ == "__main__":
    unittest.main()
