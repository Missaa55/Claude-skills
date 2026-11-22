import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_skills import validate


VALID = """---
name: example-skill
description: Example for testing.
---

# Example

## When to use

A safe example.

## Procedure

1. Check.

## Output

A result.
"""


class ValidatorTests(unittest.TestCase):
    def test_valid_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example-skill" / "SKILL.md"
            path.parent.mkdir()
            path.write_text(VALID, encoding="utf-8")
            self.assertEqual(validate(path), [])

    def test_rejects_name_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example-skill" / "SKILL.md"
            path.parent.mkdir()
            path.write_text(VALID.replace("name: example-skill", "name: other"), encoding="utf-8")
            self.assertTrue(any("name must match" in item for item in validate(path)))

    def test_rejects_private_key_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example-skill" / "SKILL.md"
            path.parent.mkdir()
            path.write_text(VALID + "\n-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")
            self.assertTrue(any("credential" in item for item in validate(path)))


if __name__ == "__main__":
    unittest.main()
