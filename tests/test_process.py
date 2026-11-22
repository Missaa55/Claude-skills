import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from core.process import Policy, isolated_command, run, redact


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def call(self, code, **kwargs):
        return run([sys.executable, "-c", code], self.root, approved=True,
                   policy=Policy("trusted-local"), **kwargs)

    def test_real_success_and_failure(self):
        self.assertEqual(self.call("print('real process')")["status"], "passed")
        self.assertEqual(self.call("raise SystemExit(2)")["exit_code"], 2)

    def test_no_shell_interpolation(self):
        text = "$(whoami); & echo secret"
        result = run([sys.executable, "-c", "import sys; print(sys.argv[1])", text], self.root,
                     approved=True, policy=Policy("trusted-local"))
        self.assertEqual(result["stdout"].strip(), text)

    def test_secrets_removed_from_environment(self):
        with patch.dict(os.environ, {"SYNTHETIC_API_KEY": "fake-sensitive-value-123"}):
            result = self.call("import os; print(os.environ.get('SYNTHETIC_API_KEY', 'ABSENT'))")
            self.assertEqual(result["stdout"].strip(), "ABSENT")
            self.assertNotIn("fake-sensitive-value-123", redact("token=fake-sensitive-value-123"))

    def test_bounded_output(self):
        result = self.call("print('a' * 1000000)", max_output=4096)
        self.assertEqual(result["status"], "output_limit")
        self.assertLessEqual(len(result["stdout"]), 4096)

    def test_real_timeout_kills_descendants(self):
        # A descendant would write a marker after its parent has timed out.
        child = "import time,pathlib; time.sleep(1); pathlib.Path('escaped').write_text('FAIL')"
        code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(30)"
        self.assertEqual(self.call(code, timeout=0.25)["status"], "timeout")
        threading.Event().wait(1.2)
        self.assertFalse((self.root / "escaped").exists())

    def test_cancellation(self):
        event = threading.Event()
        timer = threading.Timer(0.2, event.set)
        timer.start()
        try:
            self.assertEqual(self.call("import time; time.sleep(30)", cancel=event)["status"], "cancelled")
        finally:
            timer.cancel()

    @patch("core.process.shutil.which", return_value=None)
    def test_untrusted_has_no_host_fallback(self, _):
        with self.assertRaises(FileNotFoundError):
            run([sys.executable, "-c", "print('must not run')"], self.root, approved=True)

    @patch("core.process.shutil.which", return_value="docker")
    def test_container_policy(self, _):
        command = isolated_command(["python", "build.py"], self.root, Policy(image="sha256:" + "a"*64))
        self.assertIn("--network=none", command)
        self.assertIn("--cap-drop=ALL", command)
        self.assertFalse(any("docker.sock" in item for item in command))
        with self.assertRaises(PermissionError):
            isolated_command(["python"], self.root, Policy(image="sha256:" + "a"*64, network=True))


if __name__ == "__main__":
    unittest.main()
