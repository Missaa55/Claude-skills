import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "framework"))
from plan import build_manifest, validate_manifest

class PlanningTests(unittest.TestCase):
    def test_cross_domain_plan(self):
        plan = build_manifest("Build a minecraft server backend API")
        self.assertIn("minecraft", plan["domains"])
        self.assertIn("applications", plan["domains"])
        self.assertIn("skills/workflow-orchestrator/SKILL.md", plan["skill_paths"])
        self.assertEqual(validate_manifest(plan), [])
        self.assertEqual(plan["execution"], "not_started")
        self.assertFalse(plan["approved_for_release"])

    def test_stage_dependencies(self):
        plan = build_manifest("Build a responsive website with SEO")
        stages = {s["id"]: s for s in plan["stages"]}
        self.assertEqual(stages["implementation"]["depends_on"], ["architecture"])
        self.assertEqual(stages["delivery"]["depends_on"], ["review"])
        self.assertIn("WebBuilder/skills/webbuilder-content-seo/SKILL.md", plan["skill_paths"])

    def test_unverified_completion_is_rejected(self):
        plan = build_manifest("Build an app")
        plan["stages"][0]["status"] = "complete"
        self.assertTrue(any("no evidence" in x for x in validate_manifest(plan)))

    def test_release_requires_completed_stages(self):
        plan = build_manifest("Build an app")
        plan["approved_for_release"] = True
        self.assertTrue(any("all stages" in x for x in validate_manifest(plan)))

if __name__ == "__main__":
    unittest.main()
