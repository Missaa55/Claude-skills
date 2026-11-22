import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from distribution.bundle import build, verify_archive, verify_directory
from distribution.installer import install, uninstall, status, MODULES


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_standalone_bundles_work_outside_repository(self):
        for module in MODULES:
            with self.subTest(module=module):
                package = build(module, self.root / "archives")
                archive = Path(package["archive"])
                entries = verify_archive(archive.read_bytes())
                checkout = self.root / module
                for name, data in entries.items():
                    path = checkout / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                self.assertEqual(verify_directory(checkout)["builder"], module)
                project = self.root / (module + "-generated")
                result = subprocess.run([sys.executable, "builder.py", "create", "--spec", f"examples/briefs/{module}.json", "--workspace", str(project)], cwd=checkout, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((project / "builder-manifest.json").is_file())
                other = "web" if module != "web" else "app"
                denied = subprocess.run([sys.executable, "builder.py", "clean", other, "--workspace", str(project)], cwd=checkout, capture_output=True, timeout=30)
                self.assertNotEqual(denied.returncode, 0)
                target = self.root / (module + "-skills")
                for action in ("install", "update", "uninstall"):
                    cmd = subprocess.run([sys.executable, "-m", "distribution.cli", action, module, "--target", str(target)], cwd=checkout, capture_output=True, timeout=30)
                    self.assertEqual(cmd.returncode, 0, cmd.stderr)
                self.assertEqual(list(target.iterdir()), [])

    def test_corruption_and_interrupted_download(self):
        package = build("web", self.root)
        data = Path(package["archive"]).read_bytes()
        with self.assertRaises(ValueError):
            verify_archive(data[:len(data)//2])
        entries = verify_archive(data)
        entries["builder.py"] += b"\n# tampered\n"
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, content in entries.items():
                archive.writestr(name, content)
        with self.assertRaises(ValueError):
            verify_archive(buffer.getvalue())

    def test_all_seven_module_combinations(self):
        modules = list(MODULES)
        for mask in range(1, 8):
            target = self.root / str(mask)
            selected = [module for i, module in enumerate(modules) if mask & (1 << i)]
            for module in selected:
                install(module, target)
                install(module, target)
            self.assertEqual(status(target)["installed"], sorted(selected))
            sentinel = target / "user-note.txt"
            sentinel.write_text("KEEP")
            for module in reversed(selected):
                uninstall(module, target)
            self.assertEqual([p.name for p in target.iterdir()], ["user-note.txt"])

    def test_installed_runtime_creates_project_without_repository(self):
        target = self.root / "installed"
        install("web", target)
        runtime = target / "webbuilder-orchestrator/runtime"
        project = self.root / "fresh-website"
        result = subprocess.run([sys.executable, str(runtime / "builder.py"), "create", "--spec", str(runtime / "examples/briefs/web.json"), "--workspace", str(project)], cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((project / "index.html").is_file())
        uninstall("web", target)
        self.assertEqual(list(target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
