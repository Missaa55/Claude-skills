import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from core.process import Policy
from core.runtime import RunRequest, execute, prepare, doctor, _usage, valid_response


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.request = RunRequest("web", "Build a page", self.path, "claude", 5, Policy("trusted-local"))

    def test_approval_required(self):
        with self.assertRaises(PermissionError):
            execute(self.request)

    @patch("core.runtime.shutil.which", return_value="/usr/bin/claude")
    def test_prompt_not_in_arguments(self, _):
        plan = prepare(RunRequest("web", "hello; $(secret)", self.path, "claude", policy=Policy("trusted-local")))
        self.assertFalse(any("secret" in p for p in plan["command"]))

    def test_codex_limits(self):
        plan = prepare(RunRequest("app", "hello", self.path, "codex"))
        self.assertIn("--ignore-user-config", plan["command"])
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", plan["command"])

    def test_invalid_requests(self):
        for builder, prompt, provider, timeout in (("invalid", "x", "claude", 5), ("web", " ", "claude", 5), ("web", "x", "bad", 5), ("web", "x", "claude", 0)):
            with self.subTest(builder=builder, provider=provider), self.assertRaises(ValueError):
                prepare(RunRequest(builder, prompt, self.path, provider, timeout))
        with self.assertRaises(FileNotFoundError):
            prepare(RunRequest("web", "x", self.path / "absent", "claude"))

    @patch("core.runtime.run", return_value={"status": "passed", "exit_code": 0, "stdout": '{"type":"result","subtype":"success","result":"Synthetic response"}', "stderr": "", "elapsed_seconds": 0.1})
    @patch("core.runtime.shutil.which", return_value="/usr/bin/claude")
    def test_success_logs_and_stdin(self, _, runner):
        result = execute(self.request, approved=True)
        self.assertEqual(result["status"], "success")
        record = json.loads(Path(result["log_file"]).read_text())
        self.assertIn("Synthetic response", record["stdout"])
        self.assertEqual(record["verification"], "NOT VERIFIED")
        self.assertEqual(runner.call_args.kwargs["stdin"], self.request.prompt)

    @patch("core.runtime.shutil.which", return_value="/usr/bin/claude")
    def test_external_logs_rejected(self, _):
        with tempfile.TemporaryDirectory() as other, self.assertRaises(ValueError):
            execute(self.request, approved=True, log_dir=Path(other))

    @patch("core.runtime.shutil.which", return_value=None)
    def test_missing_cli_and_doctor(self, _):
        with self.assertRaises(FileNotFoundError):
            prepare(self.request)
        self.assertFalse(doctor("claude")["available_on_host"])
        self.assertEqual(doctor("claude")["authenticated"], "NOT VERIFIED")

    def test_usage_no_invented_costs(self):
        result = _usage('{"type":"turn.completed","usage":{"input_tokens":123,"output_tokens":20}}')
        self.assertEqual(result["tokens"]["input_tokens"], 123)
        self.assertIsNone(result["estimated_cost_usd"])
        self.assertIsNone(_usage("invalid provider response")["tokens"])

    def test_invalid_ai_response_and_partial_codex_turn(self):
        self.assertFalse(valid_response("claude", "exit zero, but invalid provider output"))
        self.assertFalse(valid_response("codex", '{"type":"turn.completed"}'))
        self.assertTrue(valid_response("codex", '{"type":"item.completed","item":{"type":"agent_message","text":"Synthetic finished response"}}\n{"type":"turn.completed"}'))

    @patch("core.runtime.run", return_value={"status": "passed", "exit_code": 0, "stdout": "invalid", "stderr": "", "elapsed_seconds": 0.1})
    @patch("core.runtime.shutil.which", return_value="/usr/bin/claude")
    def test_invalid_response_exit_zero_never_succeeds(self, *_):
        self.assertEqual(execute(self.request, approved=True)["status"], "invalid_response")


if __name__ == "__main__":
    unittest.main()
