import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "framework"))
from route import route

class RouterTests(unittest.TestCase):
    def test_minecraft(self):
        result = route("Build a minecraft fabric mod")
        self.assertEqual(result["domains"], ["minecraft"])
        self.assertIn("Minecraft/skills/minecraft-fabric/SKILL.md", result["skill_paths"])

    def test_application(self):
        result = route("Build a react frontend application")
        self.assertIn("applications", result["domains"])

    def test_mixed_workflow(self):
        result = route("Build a minecraft server backend api")
        self.assertIn("skills/workflow-orchestrator/SKILL.md", result["skill_paths"])

    def test_webbuilder(self):
        result = route("Build a responsive website with SEO")
        self.assertIn("webbuilder", result["domains"])
        self.assertIn("WebBuilder/skills/webbuilder-orchestrator/SKILL.md", result["skill_paths"])

    def test_appbuilder(self):
        result = route("Use app builder to generate an app")
        self.assertIn("appbuilder", result["domains"])
        self.assertIn("AppBuilder/skills/appbuilder-orchestrator/SKILL.md", result["skill_paths"])

    def test_seo_skill(self):
        result = route("Build a responsive website with SEO")
        self.assertIn("WebBuilder/skills/webbuilder-content-seo/SKILL.md", result["skill_paths"])
        self.assertIn("WebBuilder/skills/webbuilder-layout/SKILL.md", result["skill_paths"])

    def test_server_deployment_not_minecraft(self):
        result = route("Deploy a server")
        self.assertNotIn("minecraft", result["domains"])

    def test_shared_skills(self):
        cases = {
            "Review a code change": "change-reviewer",
            "Investigate a bug": "bug-investigator",
            "Audit documentation": "documentation-auditor",
        }
        for task, skill in cases.items():
            with self.subTest(task=task):
                self.assertIn(f"skills/{skill}/SKILL.md", route(task)["skill_paths"])

    def test_all_paths_exist(self):
        for task in ("Build a minecraft fabric mod", "Build a responsive website with SEO",
                     "Deploy a server", "Use app builder to generate an app",
                     "Review a code change"):
            for path in route(task)["skill_paths"]:
                self.assertTrue((Path(__file__).resolve().parents[1] / path).is_file(), path)

    def test_empty_task(self):
        with self.assertRaises(ValueError):
            route("   ")

    def test_no_match_defaults_to_universal(self):
        self.assertEqual(route("Investigate something unusual")["domains"], ["universal"])

if __name__ == "__main__":
    unittest.main()
