import json
from pathlib import Path
import tempfile
import unittest
from quality.cleaner import scan, proposal


class CleanerV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def kinds(self, builder="app"):
        return {item["kind"] for item in scan(self.root, builder)["findings"]}

    def test_ast_import_and_unreachable_and_safe_proposal(self):
        path = self.put("main.py", "import os\nimport json\nprint(json.dumps({}))\ndef result():\n    return 1\n    print('unreachable')\n")
        before = path.read_bytes()
        self.assertIn("unused_import_candidate", self.kinds())
        self.assertIn("unreachable_code", self.kinds())
        planned = proposal(self.root, "app")
        self.assertFalse(planned["applied"])
        self.assertIn("-import os", planned["changes"][0]["diff"])
        self.assertNotIn("-import json", planned["changes"][0]["diff"])
        self.assertEqual(path.read_bytes(), before)

    def test_exported_import_not_flagged(self):
        self.put("exports.py", 'from pathlib import Path\n__all__ = ["Path"]\n')
        self.assertNotIn("unused_import_candidate", self.kinds())

    def test_duplicate_functions(self):
        body = "    first = value + 10\n    second = first * 500\n    third = second - first\n    return {'first': first, 'second': second, 'third': third}\n"
        self.put("one.py", "def one(value):\n" + body)
        self.put("two.py", "def two(value):\n" + body)
        self.assertIn("duplicate_code_candidate", self.kinds())

    def test_reference_aware_unused_files_and_dependencies(self):
        self.put("index.html", '<script src="./used.js"></script>')
        self.put("used.js", "console.log('used');")
        self.put("unreferenced.js", "console.log('needs review');")
        self.put("package.json", json.dumps({"dependencies": {"unused-library": "1.0.0"}}))
        report = scan(self.root, "web")
        unused = [f["path"] for f in report["findings"] if f["kind"] == "unused_file_candidate"]
        self.assertEqual(unused, ["unreferenced.js"])
        self.assertIn("dependency_candidate", {f["kind"] for f in report["findings"]})

    def test_minecraft_assets_are_inspected_not_deleted(self):
        self.put("src/main/resources/assets/demo/models/block/copper.json", json.dumps({"textures": {"all": "demo:block/missing"}}))
        self.assertIn("missing_asset", self.kinds("minecraft"))
        self.put("src/main/resources/assets/demo/textures/block/missing.png", "synthetic")
        self.assertNotIn("missing_asset", self.kinds("minecraft"))

    def test_web_static_a11y_and_visual_scope(self):
        self.put("index.html", "<html><head></head><body><img src='x.png'></body></html>")
        report = scan(self.root, "web")
        self.assertIn("accessibility", {f["kind"] for f in report["findings"]})
        self.assertTrue(report["visual_review"].startswith("NOT VERIFIED"))

    def test_source_security_findings_do_not_echo_credentials(self):
        token = "sk-" + "synthetic" * 5
        self.put("main.py", f'api_key = "{token}"\neval("2+2")\n')
        report = scan(self.root, "app")
        self.assertIn("security_candidate", {f["kind"] for f in report["findings"]})
        self.assertIn("credential_candidate", {f["kind"] for f in report["findings"]})
        self.assertNotIn(token, json.dumps(report))

    def test_naming_and_missing_tests(self):
        self.put("logic.py", "def snake_case():\n    return 1\ndef camelCase():\n    return 2\n" + "# repeated source detail\n" * 30)
        self.assertIn("naming_candidate", self.kinds())
        self.assertIn("missing_tests_candidate", self.kinds())


if __name__ == "__main__":
    unittest.main()
