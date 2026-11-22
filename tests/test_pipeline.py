import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.pipeline import build_prompt, run_pipeline, verify

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)

    def test_separate_builder_context(self):
        for builder, own, others in (
            ("web", "webbuilder-orchestrator", ("minecraft-architecture", "appbuilder-orchestrator")),
            ("app", "appbuilder-orchestrator", ("minecraft-architecture", "webbuilder-orchestrator")),
            ("minecraft", "minecraft-architecture", ("webbuilder-orchestrator", "appbuilder-orchestrator")),
        ):
            with self.subTest(builder=builder):
                prompt = build_prompt(builder, "Build a project")
                self.assertIn(own, prompt)
                for other in others:
                    self.assertNotIn("### " + other, prompt)

    def test_requires_approval(self):
        with self.assertRaises(PermissionError):
            run_pipeline("web", "Build a page", self.workspace, "claude")

    def test_no_web_build_without_manifest(self):
        self.assertEqual(verify(self.workspace, "web")["status"], "not_configured")

    def test_no_app_tests_without_config(self):
        self.assertEqual(verify(self.workspace, "app")["status"], "not_configured")

    def test_no_minecraft_build_without_wrapper(self):
        self.assertEqual(verify(self.workspace, "minecraft")["status"], "not_configured")

    @patch("core.pipeline.verify", return_value={"status": "passed", "exit_code": 0})
    @patch("core.pipeline.execute", return_value={"status": "success"})
    def test_verified_only_on_passed_check(self, *_):
        result = run_pipeline("web", "Build", self.workspace, "claude", approved=True)
        self.assertTrue(result["verified"])
        self.assertEqual(len(result["events"]), 1)

    @patch("core.pipeline.verify", return_value={"status": "failed", "exit_code": 1})
    @patch("core.pipeline.execute", return_value={"status": "success"})
    def test_bounded_repairs(self, agent, _):
        result = run_pipeline("web", "Build", self.workspace, "claude",
                              approved=True, repair_attempts=2)
        self.assertFalse(result["verified"])
        self.assertEqual(agent.call_count, 3)

    @patch("core.pipeline.verify", return_value={"status": "not_configured"})
    @patch("core.pipeline.execute", return_value={"status": "success"})
    def test_no_repair_without_config(self, agent, _):
        result = run_pipeline("web", "Build", self.workspace, "claude",
                              approved=True, repair_attempts=3)
        self.assertFalse(result["verified"])
        self.assertEqual(agent.call_count, 1)

    @patch("core.pipeline.execute", return_value={"status": "failed"})
    def test_agent_failure_is_not_verified(self, _):
        result = run_pipeline("web", "Build", self.workspace, "claude", approved=True)
        self.assertFalse(result["verified"])

    @patch("core.pipeline.subprocess.run")
    @patch("core.pipeline.shutil.which", return_value="/usr/bin/gradle")
    def test_minecraft_gradle_fallback(self, _, runner):
        from subprocess import CompletedProcess
        (self.workspace / "build.gradle").write_text("plugins {}")
        runner.return_value = CompletedProcess(["gradle", "build"], 0, "", "")
        result = verify(self.workspace, "minecraft")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(runner.call_args.args[0], ["gradle", "build"])

    def test_invalid_repair_limit(self):
        with self.assertRaises(ValueError):
            run_pipeline("web", "Build", self.workspace, "claude",
                         approved=True, repair_attempts=10)

if __name__ == "__main__":
    unittest.main()
