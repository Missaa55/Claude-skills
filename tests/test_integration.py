import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "framework"))
sys.path.insert(0, str(ROOT / "scripts"))
from route import route
from validate_registry import check_registry

class IntegrationTests(unittest.TestCase):
    def test_registry_integrity(self):
        self.assertEqual(check_registry(), [])

    def test_all_registered_paths_exist(self):
        registry = json.loads((ROOT / "framework/registry.json").read_text())
        for domain, config in registry["domains"].items():
            for skill in config["skills"]:
                self.assertTrue((ROOT / config["root"] / skill / "SKILL.md").is_file(),
                                (domain, skill))

    def test_routing_matrix(self):
        cases = [
            ("Use app builder to generate an app", "appbuilder",
             "AppBuilder/skills/appbuilder-orchestrator/SKILL.md"),
            ("Build a responsive website with SEO", "webbuilder",
             "WebBuilder/skills/webbuilder-content-seo/SKILL.md"),
            ("Build a responsive website with SEO", "webbuilder",
             "WebBuilder/skills/webbuilder-layout/SKILL.md"),
            ("Build a minecraft fabric mod", "minecraft",
             "Minecraft/skills/minecraft-fabric/SKILL.md"),
            ("Deploy a server", "applications",
             "Applications/skills/deployment-engineer/SKILL.md"),
            ("Review a code change", "universal", "skills/change-reviewer/SKILL.md"),
            ("Investigate a bug", "universal", "skills/bug-investigator/SKILL.md"),
            ("Audit documentation", "universal", "skills/documentation-auditor/SKILL.md"),
            ("Create a website with backend API", "webbuilder",
             "WebBuilder/skills/webbuilder-orchestrator/SKILL.md"),
        ]
        for task, domain, skill in cases:
            with self.subTest(task=task, skill=skill):
                result = route(task)
                self.assertIn(domain, result["domains"])
                self.assertIn(skill, result["skill_paths"])
                for path in result["skill_paths"]:
                    self.assertTrue((ROOT / path).is_file(), path)

    def test_no_false_minecraft_server(self):
        for task in ("Deploy a server", "Fix server deployment", "Review a web server"):
            with self.subTest(task=task):
                self.assertNotIn("minecraft", route(task)["domains"])

    def test_no_duplicate_skills(self):
        for task in ("Build a minecraft server backend API", "Build a responsive website with SEO",
                     "Review a bug in documentation"):
            paths = route(task)["skill_paths"]
            self.assertEqual(len(paths), len(set(paths)))

    def test_broken_registry_path_detected(self):
        registry = json.loads((ROOT / "framework/registry.json").read_text())
        registry["domains"]["appbuilder"]["skills"].append("missing-example")
        self.assertTrue(any("missing-example" in err for err in check_registry(registry=registry)))

    def test_invalid_alias_detected(self):
        registry = json.loads((ROOT / "framework/registry.json").read_text())
        registry["skill_keywords"]["ghost/unknown"] = ["ghost"]
        self.assertTrue(any("ghost/unknown" in err for err in check_registry(registry=registry)))

if __name__ == "__main__":
    unittest.main()
