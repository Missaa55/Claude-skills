"""Generate new projects from briefs, then run real builds and HTTP/database suites."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from builders.scaffold import create, validate, minecraft_files, ROOT
from core.artifacts import inspect
from core.pipeline import verify
from core.process import Policy


class ReferenceProjects(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_actual_web_and_app_builds_and_http_suites(self):
        for builder in ("web", "app"):
            with self.subTest(builder=builder):
                spec = json.loads((ROOT / "examples/briefs" / f"{builder}.json").read_text(encoding="utf-8"))
                project = self.root / builder
                result = create(spec, project)
                self.assertFalse(result["ai_generated"])
                checked = verify(project, builder, approved=True, policy=Policy("trusted-local"), timeout=120)
                self.assertEqual(checked["status"], "passed", str(checked)[-5000:])
                self.assertTrue(checked["artifacts"])
                self.assertIn("Ran ", checked["checks"][1]["stderr"])

    def test_new_minecraft_brief_changes_content(self):
        spec = json.loads((ROOT / "examples/briefs/minecraft.json").read_text(encoding="utf-8"))
        spec.update(mod_id="test_wiring", block_id="wire_tile", item_id="test_probe")
        project = self.root / "fresh-mod"
        create(spec, project)
        java = (project / "src/main/java/dev/builders/WorkshopMod.java").read_text()
        self.assertIn('"test_wiring"', java)
        self.assertIn('"wire_tile"', java)
        self.assertIn('"test_probe"', java)
        self.assertNotIn("claudeskills_block", java)
        self.assertTrue((project / "src/main/resources/assets/test_wiring/textures/item/test_probe.png").read_bytes().startswith(b"\x89PNG"))
        self.assertFalse(json.loads((project / "builder-manifest.json").read_text())["ai_generated"])

    def test_all_minecraft_target_structures(self):
        for target, marker in (("fabric", "src/main/resources/fabric.mod.json"), ("paper", "src/main/resources/plugin.yml"), ("neoforge", "src/main/resources/META-INF/neoforge.mods.toml"), ("datapack", "pack.mcmeta")):
            result = minecraft_files(validate({"builder": "minecraft", "task": "Synthetic test", "kind": target}))
            self.assertIn(marker, result)

    def test_no_overwrite_or_invalid_brief(self):
        existing = self.root / "existing"
        existing.mkdir()
        with self.assertRaises(FileExistsError):
            create({"builder": "web", "task": "Test"}, existing)
        for data in ({}, {"builder": "web", "task": ""}, {"builder": "minecraft", "task": "x", "mod_id": "../../escape"}, {"builder": "web", "task": "x", "shell": "bad"}):
            with self.assertRaises(ValueError):
                validate(data)

    def test_artifact_inspection_rejects_empty_outputs(self):
        (self.root / "dist").mkdir()
        (self.root / "dist/index.html").write_text("")
        with self.assertRaises(ValueError):
            inspect(self.root, "web")
        with self.assertRaises(ValueError):
            inspect(self.root, "minecraft")


if __name__ == "__main__":
    unittest.main()
