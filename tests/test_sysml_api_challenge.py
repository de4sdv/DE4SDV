import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sysml_api_challenge as challenge
import syson_exchange


class SysmlApiChallengeTests(unittest.TestCase):
    def test_context_challenge_uses_stable_ids_and_relationship_payloads(self):
        model = challenge.context_challenge_model()

        lifecycle_id = challenge.stable_id("partdef.DE4SDV.Context.LifecycleEngineeringSystem")
        product_line_id = challenge.stable_id("partdef.DE4SDV.Context.ConfigurableSDVProductLine")
        relationship_id = challenge.stable_id("dependency.DE4SDV.RelationshipIntents.engineers-assures")

        self.assertIn(lifecycle_id, model.elements)
        self.assertIn(relationship_id, model.elements)

        relationship = model.elements[relationship_id]
        self.assertEqual(relationship["@type"], "Dependency")
        self.assertEqual(
            relationship["source"],
            [{"@id": lifecycle_id}],
        )
        self.assertEqual(
            relationship["target"],
            [{"@id": product_line_id}],
        )

    def test_challenge_report_marks_missing_expected_element_as_failure(self):
        model = challenge.context_challenge_model()
        missing_id = challenge.stable_id("dependency.DE4SDV.RelationshipIntents.engineers-assures")
        observed = {
            element_id: payload
            for element_id, payload in model.elements.items()
            if element_id != missing_id
        }

        report = challenge.build_challenge_report(model, observed, source="unit-test")

        self.assertEqual(report["summary"]["status"], "failed")
        self.assertIn(
            {
                "id": missing_id,
                "type": "Dependency",
                "name": "engineers / assures",
                "reason": "expected element missing from observed API graph",
            },
            report["failed"],
        )

    def test_challenge_report_matches_semantic_element_when_api_reassigns_id(self):
        model = challenge.context_challenge_model()
        expected_id = challenge.stable_id("partdef.DE4SDV.Context.LifecycleEngineeringSystem")
        observed = {
            "api-generated-id": {
                **model.elements[expected_id],
                "@id": "api-generated-id",
                "elementId": "api-generated-id",
            }
        }

        report = challenge.build_challenge_report(
            challenge.ChallengeModel(
                name="single",
                description="single",
                elements={expected_id: model.elements[expected_id]},
                capabilities=[],
                gap_questions=[],
            ),
            observed,
            source="unit-test",
        )

        self.assertEqual(report["summary"]["status"], "passed-with-warnings")
        self.assertEqual(report["summary"]["warnings"], 1)
        self.assertIn("API reassigned @id", report["warnings"][0]["reason"])

    def test_textual_snapshot_export_renders_dependency_relationships(self):
        model = challenge.context_challenge_model()
        text = challenge.render_textual_snapshot(model.elements)

        self.assertIn("package DE4SDV", text)
        self.assertIn("dependency 'engineers / assures'", text)
        self.assertIn("from Context::LifecycleEngineeringSystem", text)
        self.assertIn("to Context::ConfigurableSDVProductLine", text)

    def test_dry_run_report_is_json_serializable_and_records_api_gap_questions(self):
        model = challenge.context_challenge_model()
        report = challenge.build_challenge_report(model, model.elements, source="dry-run")

        encoded = json.dumps(report, indent=2)

        self.assertIn("diagram layout/view representation", encoded)
        self.assertEqual(report["summary"]["status"], "passed")
        self.assertGreaterEqual(report["summary"]["tested_elements"], 10)
    def test_supported_graph_reports_missing_expected_elements(self):
        model = challenge.context_challenge_model()
        graph = {
            "schema": "de4sdv.syson-supported-graph.v1",
            "elements": [
                {"type": payload["@type"], "name": payload["name"]}
                for payload in model.elements.values()
                if payload["name"] != "engineers / assures"
            ],
        }

        missing = challenge.supported_graph_missing_expected(graph, model)

        self.assertIn(
            {
                "type": "Dependency",
                "name": "engineers / assures",
                "reason": "expected semantic element missing from supported graph",
            },
            missing,
        )

    def test_seed_supported_graph_rejects_incomplete_graph_before_api_call(self):
        graph = {"schema": "de4sdv.syson-supported-graph.v1", "elements": []}

        with self.assertRaisesRegex(RuntimeError, "supported graph is incomplete"):
            challenge.seed_supported_graph(None, graph, "unused")  # type: ignore[arg-type]

    def test_syson_view_svg_renders_nodes_and_edges(self):
        view = {
            "id": "view-1",
            "label": "DE4SDV Context View",
            "nodes": [
                {
                    "id": "n1",
                    "type": "node:package",
                    "targetObjectId": "semantic-1",
                    "insideLabel": {"text": "LifecycleEngineeringSystem"},
                    "outsideLabels": [],
                    "childNodes": [],
                    "borderNodes": [],
                    "defaultWidth": 180,
                    "defaultHeight": 70,
                },
                {
                    "id": "n2",
                    "type": "node:package",
                    "targetObjectId": "semantic-2",
                    "insideLabel": {"text": "ValidationPipeline"},
                    "outsideLabels": [],
                    "childNodes": [],
                    "borderNodes": [],
                    "defaultWidth": 180,
                    "defaultHeight": 70,
                },
            ],
            "edges": [{"id": "e1", "sourceId": "n1", "targetId": "n2", "centerLabel": {"text": "executes validation"}}],
            "layoutData": {
                "nodeLayoutData": {
                    "n1": {"id": "n1", "position": {"x": 40, "y": 90}, "size": {"width": 180, "height": 70}},
                    "n2": {"id": "n2", "position": {"x": 300, "y": 90}, "size": {"width": 180, "height": 70}},
                }
            },
        }

        svg = syson_exchange.render_view_svg(view)

        self.assertIn("LifecycleEngineeringSystem", svg)
        self.assertIn("ValidationPipeline", svg)
        self.assertIn("executes validation", svg)
        self.assertIn("<svg", svg)

    def test_syson_view_svg_marks_empty_views(self):
        svg = syson_exchange.render_view_svg({"id": "empty", "label": "Empty", "nodes": [], "edges": []})

        self.assertIn("No diagram nodes are currently visible", svg)


if __name__ == "__main__":
    unittest.main()
