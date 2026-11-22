import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from core.pipeline import build_prompt, run_pipeline, verify, select_builder


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name)

    def test_builder_context_isolation(self):
        for builder, own, others in (("web", "webbuilder-orchestrator", ("minecraft-architecture", "appbuilder-orchestrator")),
                                    ("app", "appbuilder-orchestrator", ("minecraft-architecture", "webbuilder-orchestrator")),
                                    ("minecraft", "minecraft-architecture", ("webbuilder-orchestrator", "appbuilder-orchestrator"))):
            prompt = build_prompt(builder, "Build a project")
            self.assertIn(own, prompt)
            for other in others:
                self.assertNotIn("### " + other, prompt)

    def test_routing_czech_and_ambiguity(self):
        self.assertEqual(select_builder("Responzivní webové stránky"), "web")
        self.assertEqual(select_builder("Aplikace pro zakázky"), "app")
        self.assertEqual(select_builder("Fabric Minecraft mod"), "minecraft")
        with self.assertRaises(ValueError):
            select_builder("backend a website")

    def test_approval_and_limits(self):
        with self.assertRaises(PermissionError):
            run_pipeline("web", "Build", self.workspace, "claude")
        with self.assertRaises(ValueError):
            run_pipeline("web", "Build", self.workspace, "claude", approved=True, repair_attempts=10)

    def test_missing_configuration(self):
        for builder in ("web", "app", "minecraft"):
            self.assertEqual(verify(self.workspace, builder)["status"], "not_configured")

    @patch("core.pipeline.run", return_value={"status": "passed", "stdout": "BUILD SUCCESSFUL", "stderr": ""})
    def test_exit_zero_with_corrupt_jar_fails_verification(self, _):
        (self.workspace / "build.gradle").write_text("// simulated build command")
        libs = self.workspace / "build/libs"
        libs.mkdir(parents=True)
        (libs / "broken.jar").write_bytes(b"not a ZIP archive")
        result = verify(self.workspace, "minecraft", approved=True)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["artifacts"], [])

    @patch("core.pipeline.verify", return_value={"status": "passed"})
    @patch("core.pipeline.execute", return_value={"status": "success"})
    def test_exit_zero_without_artifacts_is_unverified(self, *_):
        result = run_pipeline("web", "Build", self.workspace, "claude", approved=True)
        self.assertFalse(result["verified"])
        self.assertEqual(result["evidence_label"], "NOT VERIFIED")

    @patch("core.pipeline.verify", return_value={"status": "failed", "reason": "No artifacts"})
    @patch("core.pipeline.execute", return_value={"status": "success"})
    def test_bounded_repairs_and_saved_state(self, agent, _):
        result = run_pipeline("web", "Build", self.workspace, "claude", approved=True, repair_attempts=2)
        self.assertEqual(agent.call_count, 3)
        self.assertFalse(result["verified"])
        self.assertEqual(len(json.loads(Path(result["log_file"]).read_text())["events"]), 3)

    @patch("core.pipeline.verify", return_value={"status": "not_configured"})
    @patch("core.pipeline.execute", return_value={"status": "success"})
    def test_missing_tools_are_not_repaired(self, agent, _):
        result = run_pipeline("app", "Build", self.workspace, "claude", approved=True, repair_attempts=3)
        self.assertEqual(agent.call_count, 1)

    @patch("core.pipeline.execute", side_effect=FileNotFoundError("Docker unavailable"))
    def test_unavailable_provider_safely_recorded(self, _):
        result = run_pipeline("web", "Build", self.workspace, "claude", approved=True)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["verified"])

    @patch("core.pipeline.execute", return_value={"status": "cancelled"})
    def test_interrupt_during_repair(self, agent):
        result = run_pipeline("web", "Build", self.workspace, "claude", approved=True, repair_attempts=3)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(agent.call_count, 1)


if __name__ == "__main__":
    unittest.main()
