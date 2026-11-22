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

    def test_empty_task(self):
        with self.assertRaises(ValueError):
            route("   ")

    def test_no_match_defaults_to_universal(self):
        self.assertEqual(route("Investigate something unusual")["domains"], ["universal"])

if __name__ == "__main__":
    unittest.main()
