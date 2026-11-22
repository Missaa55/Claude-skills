import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from distribution.bundle import build_image_skill
from distribution.installer import ROOT

SCRIPT = ROOT / "WebBuilder/skills/claude-image-studio/scripts/asset_studio.py"
spec = importlib.util.spec_from_file_location("image_helper", SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ImageSkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_setup_is_portable_secret_free_and_no_overwrite(self):
        result = helper.setup(self.root / "setup")
        config = json.loads(Path(result["configuration"]).read_text())
        self.assertEqual(config["mcpServers"]["hf-images"]["url"], "https://huggingface.co/mcp?login")
        self.assertNotIn("env", config["mcpServers"]["hf-images"])
        self.assertEqual(result["authenticated"], "NOT VERIFIED")
        with self.assertRaises(FileExistsError):
            helper.setup(self.root / "setup")

    def test_provenance_checks_actual_file_not_realism(self):
        image = self.root / "synthetic.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0"*8 + struct.pack(">II", 64, 32) + b"synthetic-header-fixture")
        output = self.root / "metadata.json"
        record = helper.record(image, output, "generated", provider="SIMULATED header fixture")
        self.assertEqual(record["dimensions"], [64, 32])
        self.assertEqual(record["evidence_label"], "STATIC CHECK")
        self.assertEqual(record["visual_review"], "NOT VERIFIED")
        self.assertEqual(len(record["sha256"]), 64)

    def test_cc0_needs_provenance_and_no_credential_urls(self):
        image = self.root / "not-image.png"
        image.write_text("<html>not a photograph</html>")
        with self.assertRaises(ValueError):
            helper.record(image, self.root / "bad.json", "cc0")

    def test_standalone_skill_archive_runs_without_builder(self):
        result = build_image_skill(self.root)
        with zipfile.ZipFile(result["archive"]) as archive:
            # Only our verified, newly generated package, into a disposable directory.
            for name in archive.namelist():
                self.assertNotIn("..", Path(name).parts)
                path = self.root / "extracted" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(name))
        script = self.root / "extracted/claude-image-studio/scripts/asset_studio.py"
        proc = subprocess.run([sys.executable, str(script), "doctor"], cwd=self.root,
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(json.loads(proc.stdout)["requires_local_gpu"])


if __name__ == "__main__":
    unittest.main()
