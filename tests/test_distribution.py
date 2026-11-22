import json
import tempfile
import unittest
from pathlib import Path
from distribution.installer import install, uninstall, status, MODULES

ROOT = Path(__file__).resolve().parents[1]

class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name) / "skills"

    def test_isolated_modules(self):
        for module in MODULES:
            with self.subTest(module=module):
                with tempfile.TemporaryDirectory() as tmp:
                    target = Path(tmp) / "skills"
                    result = install(module, target)
                    self.assertGreater(result["files"], 0)
                    installed = {p.parent.name for p in target.glob("*/SKILL.md")}
                    expected = {p.parent.name for p in (ROOT / MODULES[module]).glob("*/SKILL.md")}
                    self.assertEqual(installed, expected)
                    self.assertEqual(status(target)["installed"], [module])

    def test_multiple_modules_independent_uninstall(self):
        install("minecraft", self.target)
        install("web", self.target)
        self.assertEqual(status(self.target)["installed"], ["minecraft", "web"])
        uninstall("minecraft", self.target)
        self.assertEqual(status(self.target)["installed"], ["web"])
        self.assertTrue((self.target / "webbuilder-orchestrator/SKILL.md").exists())

    def test_idempotent(self):
        first = install("app", self.target)
        second = install("app", self.target)
        self.assertEqual(first["files"], second["files"])

    def test_unmanaged_collision(self):
        self.target.mkdir(parents=True)
        dest = self.target / "webbuilder-orchestrator/SKILL.md"
        dest.parent.mkdir()
        dest.write_text("personal content")
        with self.assertRaises(FileExistsError):
            install("web", self.target)
        self.assertEqual(dest.read_text(), "personal content")

    def test_modified_file_blocks_uninstall(self):
        install("app", self.target)
        dest = self.target / "appbuilder-design/SKILL.md"
        dest.write_text("modified")
        with self.assertRaises(FileExistsError):
            uninstall("app", self.target)
        self.assertEqual(dest.read_text(), "modified")

    def test_unknown_module(self):
        with self.assertRaises(ValueError):
            install("all", self.target)

    def test_uninstall_missing(self):
        self.assertEqual(uninstall("web", self.target)["removed"], 0)

    def test_state_is_local(self):
        install("web", self.target)
        state = json.loads((self.target / ".claude-skills-install.json").read_text())
        self.assertEqual(set(state["modules"]), {"web"})

if __name__ == "__main__":
    unittest.main()
