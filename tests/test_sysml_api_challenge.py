import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sysml_api_challenge as challenge


class SysmlApiChallengeTests(unittest.TestCase):
    def test_context_challenge_uses_stable_ids_and_relationship_payloads(self):
        model = challenge.context_challenge_model()

        self.assertIn("de4sdv-context-lifecycle-engineering-system", model.elements)
        self.assertIn("de4sdv-relationship-engineers-assures", model.elements)

        relationship = model.elements["de4sdv-relationship-engineers-assures"]
        self.assertEqual(relationship["@type"], "Dependency")
        self.assertEqual(
            relationship["source"],
            [{"@id": "de4sdv-context-lifecycle-engineering-system"}],
        )
        self.assertEqual(
            relationship["target"],
            [{"@id": "de4sdv-context-configurable-sdv-product-line"}],
        )

    def test_challenge_report_marks_missing_expected_element_as_failure(self):
        model = challenge.context_challenge_model()
        observed = {
            element_id: payload
            for element_id, payload in model.elements.items()
            if element_id != "de4sdv-relationship-engineers-assures"
        }

        report = challenge.build_challenge_report(model, observed, source="unit-test")

        self.assertEqual(report["summary"]["status"], "failed")
        self.assertIn(
            {
                "id": "de4sdv-relationship-engineers-assures",
                "type": "Dependency",
                "name": "engineers / assures",
                "reason": "expected element missing from observed API graph",
            },
            report["failed"],
        )

    def test_dry_run_report_is_json_serializable_and_records_api_gap_questions(self):
        model = challenge.context_challenge_model()
        report = challenge.build_challenge_report(model, model.elements, source="dry-run")

        encoded = json.dumps(report, indent=2)

        self.assertIn("diagram layout/view representation", encoded)
        self.assertEqual(report["summary"]["status"], "passed")
        self.assertGreaterEqual(report["summary"]["tested_elements"], 10)


if __name__ == "__main__":
    unittest.main()
