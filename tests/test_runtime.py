import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch
from core.runtime import RunRequest, prepare, execute

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.request = RunRequest("web", "Build a page", self.path, "claude", 5)

    def test_approval_required(self):
        with self.assertRaises(PermissionError):
            execute(self.request)

    @patch("core.runtime.shutil.which", return_value="/usr/bin/claude")
    def test_no_shell_interpolation(self, _):
        plan = prepare(RunRequest("web", "hello; rm -rf /", self.path, "claude"))
        self.assertEqual(plan["command"], ["/usr/bin/claude", "-p", "hello; rm -rf /"])

    @patch("core.runtime.shutil.which", return_value="/usr/bin/codex")
    def test_codex(self, _):
        self.assertEqual(prepare(RunRequest("app", "hello", self.path, "codex"))["command"][1], "exec")

    def test_invalid_builder(self):
        with self.assertRaises(ValueError):
            prepare(RunRequest("invalid", "x", self.path, "claude"))

    def test_invalid_provider(self):
        with self.assertRaises(ValueError):
            prepare(RunRequest("web", "x", self.path, "invalid"))

    def test_empty_prompt(self):
        with self.assertRaises(ValueError):
            prepare(RunRequest("web", " ", self.path, "claude"))

    def test_timeout_validation(self):
        with self.assertRaises(ValueError):
            prepare(RunRequest("web", "x", self.path, "claude", 0))

    def test_missing_workspace(self):
        with self.assertRaises(FileNotFoundError):
            prepare(RunRequest("web", "x", self.path / "missing", "claude"))

    @patch("core.runtime.subprocess.run", return_value=CompletedProcess([], 0, "ok", ""))
    @patch("core.runtime.shutil.which", return_value="/usr/bin/claude")
    def test_success_log(self, _, run):
        result = execute(self.request, approved=True)
        self.assertEqual(result["status"], "success")
        self.assertEqual(json.loads(Path(result["log_file"]).read_text())["stdout"], "ok")
        self.assertFalse(run.call_args.kwargs.get("shell", False))

    @patch("core.runtime.subprocess.run", return_value=CompletedProcess([], 1, "", "error"))
    @patch("core.runtime.shutil.which", return_value="/usr/bin/claude")
    def test_failure(self, *_):
        self.assertEqual(execute(self.request, approved=True)["status"], "failed")

    @patch("core.runtime.subprocess.run", side_effect=TimeoutExpired("cmd", 5))
    @patch("core.runtime.shutil.which", return_value="/usr/bin/claude")
    def test_timeout(self, *_):
        self.assertEqual(execute(self.request, approved=True)["status"], "timeout")

    @patch("core.runtime.shutil.which", return_value=None)
    def test_missing_cli(self, _):
        with self.assertRaises(FileNotFoundError):
            prepare(self.request)

    @patch("core.runtime.shutil.which", return_value="/usr/bin/claude")
    def test_external_logs_rejected(self, _):
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaises(ValueError):
                execute(self.request, approved=True, log_dir=Path(other))

if __name__ == "__main__":
    unittest.main()
