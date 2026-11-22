"""Fault injection is SIMULATED; filesystem/junction/lifecycle checks are real."""
import base64
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from distribution import installer as mod


class InstallerSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.target = self.base / "skills"

    def snapshot(self):
        return {p.relative_to(self.target).as_posix(): p.read_bytes()
                for p in self.target.rglob("*") if p.is_file()}

    def test_portable_traversals(self):
        for path in ("../x", "/x", "C:/x", "a/../../x", "webbuilder-a/../x", "a\\b", "//host/file",
                     "webbuilder-a/NUL", "webbuilder-a/x.", "webbuilder-a//x", "./webbuilder-a/x"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                mod._destination(self.target, path, "web")

    def test_corrupt_states_fail_before_mutation(self):
        self.target.mkdir()
        sentinel = self.target / "personal.txt"
        sentinel.write_text("KEEP")
        cases = [[], {}, {"schema_version": 1, "modules": {"web": []}},
                 {"schema_version": 1, "modules": {"web": {"files": []}}},
                 {"schema_version": 1, "modules": {"web": {"files": {"webbuilder-a/x": "invalid"}}}},
                 {"schema_version": 1, "modules": {"web": {"files": {"appbuilder-design/SKILL.md": "0"*64}}}}]
        for state in cases:
            (self.target / mod.STATE).write_text(json.dumps(state))
            before = self.snapshot()
            with self.subTest(state=state), self.assertRaises(ValueError):
                mod.install("web", self.target)
            self.assertEqual(self.snapshot(), before)

    def test_duplicate_json_keys_rejected(self):
        self.target.mkdir()
        (self.target / mod.STATE).write_text('{"schema_version":1,"modules":{},"modules":{}}')
        with self.assertRaises(ValueError):
            mod.status(self.target)

    def test_identical_unmanaged_file_is_not_adopted(self):
        rel, data = next(iter(mod._source_files("app", mod.ROOT).items()))
        dest = self.target / rel
        dest.parent.mkdir(parents=True)
        dest.write_bytes(data)
        with self.assertRaises(FileExistsError):
            mod.install("app", self.target)
        self.assertFalse((self.target / mod.STATE).exists())

    def test_disk_full_rolls_back_new_install(self):
        original = mod._write_atomic
        count = 0
        def faulty(path, data):
            nonlocal count
            count += 1
            if count == 4:
                raise OSError(errno.ENOSPC, "injected disk full")
            original(path, data)
        with patch.object(mod, "_write_atomic", side_effect=faulty), self.assertRaises(OSError):
            mod.install("web", self.target)
        self.assertEqual(list(self.target.iterdir()), [])
        mod.install("web", self.target)
        self.assertEqual(mod.status(self.target)["installed"], ["web"])

    def test_update_failure_preserves_previous_install(self):
        mod.install("app", self.target)
        before = self.snapshot()
        sources = mod._source_files("app", mod.ROOT)
        rel = next(iter(sources))
        sources[rel] += b"\nupdated\n"
        original = mod._write_atomic
        count = 0
        def faulty(path, data):
            nonlocal count
            count += 1
            if count == 4:
                raise PermissionError("injected permission denial")
            original(path, data)
        with patch.object(mod, "_source_files", return_value=sources), patch.object(mod, "_write_atomic", side_effect=faulty):
            with self.assertRaises(PermissionError):
                mod.install("app", self.target)
        self.assertEqual(self.snapshot(), before)

    def test_update_removes_only_obsolete_owned_files(self):
        mod.install("app", self.target)
        user = self.target / "notes.txt"
        user.write_text("KEEP")
        files = mod._source_files("app", mod.ROOT)
        obsolete = next(iter(files))
        del files[obsolete]
        with patch.object(mod, "_source_files", return_value=files):
            mod.install("app", self.target)
        self.assertFalse((self.target / obsolete).exists())
        mod.uninstall("app", self.target)
        self.assertEqual(user.read_text(), "KEEP")
        self.assertEqual([p.name for p in self.target.iterdir()], ["notes.txt"])

    def test_recovery_after_interrupted_write(self):
        self.target.mkdir()
        rel = "webbuilder-layout/SKILL.md"
        path = self.target / rel
        path.parent.mkdir()
        path.write_bytes(b"new")
        encoded = lambda value: base64.b64encode(value).decode()
        journal = {"version": 1, "module": "web", "entries": {rel: {"before": encoded(b"old"), "after": encoded(b"new")}}}
        (self.target / mod.JOURNAL).write_text(json.dumps(journal))
        self.assertTrue(mod.recover(self.target)["recovered"])
        self.assertEqual(path.read_bytes(), b"old")

    def test_recovery_refuses_subsequent_user_edit(self):
        self.target.mkdir()
        rel = "webbuilder-layout/SKILL.md"
        path = self.target / rel
        path.parent.mkdir()
        path.write_bytes(b"user edit")
        journal = {"version": 1, "module": "web", "entries": {rel: {"before": None, "after": base64.b64encode(b"new").decode()}}}
        (self.target / mod.JOURNAL).write_text(json.dumps(journal))
        with self.assertRaises(FileExistsError):
            mod.recover(self.target)
        self.assertEqual(path.read_bytes(), b"user edit")

    def test_concurrent_operation_fails_safely(self):
        with mod._lock(self.target):
            result = subprocess.run([os.sys.executable, "-m", "distribution.cli", "install", "app", "--target", str(self.target)],
                                    cwd=mod.ROOT, capture_output=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((self.target / mod.STATE).exists())
        mod.install("app", self.target)

    @unittest.skipUnless(os.name == "nt", "Windows junction-specific check")
    def test_windows_junction_target_and_child_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        junction = self.base / "junction"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.addCleanup(lambda: junction.rmdir() if junction.exists() else None)
        with self.assertRaises(ValueError):
            mod.install("app", junction)
        self.target.mkdir()
        child = self.target / "appbuilder-design"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(child), str(outside)], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.addCleanup(lambda: child.rmdir() if child.exists() else None)
        with self.assertRaises(ValueError):
            mod.install("app", self.target)
        self.assertEqual(list(outside.iterdir()), [])

    def test_integrity_detects_edit(self):
        mod.install("app", self.target)
        path = self.target / "appbuilder-design/SKILL.md"
        path.write_text("user modification")
        self.assertIn("appbuilder-design/SKILL.md", mod.status(self.target)["integrity"]["app"]["modified_or_missing"])


if __name__ == "__main__":
    unittest.main()
