import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from workflow import new_plan, record, report, validate_plan


class WorkflowTests(unittest.TestCase):
    def test_plan_has_six_pending_stages(self):
        plan = new_plan("Fix a bug")
        self.assertEqual(len(plan["stages"]), 6)
        validate_plan(plan)

    def test_complete_requires_evidence(self):
        with self.assertRaisesRegex(ValueError, "requires evidence"):
            record(new_plan("Fix a bug"), "test", "complete", None)

    def test_record_and_report(self):
        plan = record(new_plan("Fix a bug"), "investigate", "complete", "Synthetic reproduction")
        self.assertIn("Synthetic reproduction", report(plan))

    def test_invalid_schema(self):
        with self.assertRaises(ValueError):
            validate_plan({"schema_version": 999})

    def test_blank_task(self):
        with self.assertRaises(ValueError):
            new_plan(" ")


if __name__ == "__main__":
    unittest.main()
