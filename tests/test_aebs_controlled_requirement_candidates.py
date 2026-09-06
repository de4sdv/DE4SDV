"""AEBS needs/requirements controlled-artifact alignment tests.

Since the pilot-YAML deduplication refactor, the YAML is the framing/index
control artifact (need/requirement/gap ID indexes, V&V planning, quality
findings) while the SysML slice is the statement source of truth and the
Markdown renders the reviewer baseline. These tests assert the alignment
across all three artifacts, including the requirement re-parenting and
controlled-terminology decisions recorded as quality findings.
"""

import re
import unittest

import yaml

ROOT = Path = __import__("pathlib").Path(__file__).parents[1]
YAML_PATH = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml"
MARKDOWN_PATH = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.md"
MODEL_PATH = ROOT / "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml"

EXPECTED_SYSTEM1_MEMBER_NEEDS = {"N-AEBS-008", "N-AEBS-014"}
EXPECTED_SYSTEM1_REQUIREMENTS = {
    "REQ-AEBS-001",
    "REQ-AEBS-002",
    "REQ-AEBS-003",
    "REQ-AEBS-004",
    "REQ-AEBS-005",
    "REQ-AEBS-008",
    "REQ-AEBS-009",
    "REQ-AEBS-010",
    "REQ-AEBS-011",
    "REQ-AEBS-012",
    "REQ-AEBS-013",
    "REQ-AEBS-014",
    "REQ-AEBS-015",
}

_FORBIDDEN_CLAIM = re.compile(
    r"\b(?:compliant|certified|homologated|type[- ]approved)\b", re.IGNORECASE
)
_DEP_RE = re.compile(
    r"dependency\s+(?P<dep>\S+)\s+from\s+(?P<from>\S+)\s+to\s+(?P<to>\S+);"
)


def _load_yaml():
    return yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))


def _load_model():
    return MODEL_PATH.read_text(encoding="utf-8")


def _model_dependencies(model):
    return {
        m.group("dep"): (m.group("from"), m.group("to"))
        for m in _DEP_RE.finditer(model)
    }


class TestControlArtifactsAlign(unittest.TestCase):
    def test_yaml_indexes_list_every_controlled_id(self):
        data = _load_yaml()
        model = _load_model()
        for need_id in data["need_ids"]:
            self.assertIn(need_id, model)
        for req_id in data["requirement_ids"]:
            self.assertIn(req_id, model)
        for gap_id in data["gap_ids"]:
            self.assertIn(gap_id, model)

    def test_markdown_renders_every_controlled_id(self):
        data = _load_yaml()
        markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
        for record_id in data["need_ids"] + data["requirement_ids"]:
            self.assertIn(f"`{record_id}`", markdown)

    def test_markdown_member_set_row_lists_new_need(self):
        data = _load_yaml()
        markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
        self.assertIn("N-AEBS-014", data["need_ids"])
        member_row = re.search(r"`SET-AEBS-S1-MEMBER-NEEDS`.*?\n", markdown)
        assert member_row is not None
        self.assertIn("N-AEBS-014", member_row.group(0))

    def test_model_keeps_system_partition_packages(self):
        model = _load_model()
        self.assertIn("package System1Product", model)
        self.assertIn("package System2EngineeringAssurance", model)

    def test_new_member_need_is_registered_as_member_set_member(self):
        data = _load_yaml()
        self.assertIn("N-AEBS-014", data["need_ids"])


class TestRequirementParentage(unittest.TestCase):
    def test_false_reaction_candidates_reparented_to_trustworthy_need(self):
        deps = _model_dependencies(_load_model())
        self.assertIn("reqResistFalseReactionDerivedFromTrustworthyInterventionDecisions", deps)
        self.assertIn("reqResistFalseBrakingCommandDerivedFromTrustworthyInterventionDecisions", deps)
        self.assertNotIn("req008DerivedFromNeed001", deps)
        self.assertNotIn("req012DerivedFromNeed001", deps)
        self.assertEqual(
            deps["reqResistFalseReactionDerivedFromTrustworthyInterventionDecisions"][1],
            "needTrustworthyInterventionDecisions",
        )
        self.assertEqual(
            deps["reqResistFalseBrakingCommandDerivedFromTrustworthyInterventionDecisions"][1],
            "needTrustworthyInterventionDecisions",
        )

    def test_markdown_trace_matrix_matches_reparenting(self):
        markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
        row_001 = re.search(r"^\| `N-AEBS-001` \| System 1 \|.*$", markdown, re.M)
        assert row_001 is not None
        row_001 = row_001.group(0)
        self.assertNotIn("REQ-AEBS-008", row_001)
        self.assertNotIn("REQ-AEBS-012", row_001)
        row_014 = re.search(r"^\| `N-AEBS-014` \| System 1 \|.*$", markdown, re.M)
        assert row_014 is not None
        row_014 = row_014.group(0)
        self.assertIn("REQ-AEBS-008", row_014)
        self.assertIn("REQ-AEBS-012", row_014)

    def test_degraded_candidates_keep_member_need_parent(self):
        deps = _model_dependencies(_load_model())
        self.assertEqual(deps["reqDerivedFromNeedBoundedDegradation"][1],
                         "needBoundedDegradationAndAvailability")
        self.assertEqual(deps["reqIndicateDegradedUnavailableStatusDerivedFromBoundedDegradationAndAvailability"][1],
                         "needBoundedDegradationAndAvailability")


class TestStatementQualityGate(unittest.TestCase):
    STATEMENTS = {
        "REQ-AEBS-001": "shall realize the common AEBS capability by detecting imminent forward collision risk",
        "REQ-AEBS-002": "shall realize the common AEBS capability by providing a collision warning",
        "REQ-AEBS-003": "shall realize the common AEBS capability by commanding emergency braking",
        "REQ-AEBS-008": "shall not issue an AEBS collision warning",
        "REQ-AEBS-012": "shall not command AEBS emergency braking",
        "REQ-AEBS-010": "pedestrian target",
        "REQ-AEBS-011": "bicycle target",
    }

    def test_controlled_statements_present_in_model(self):
        model = _load_model()
        for record_id, fragment in self.STATEMENTS.items():
            block = re.search(
                re.escape(record_id) + r".*?constraint[^{]*\{.*?\*/", model, re.S
            )
            assert block is not None, record_id
            self.assertIn(fragment, block.group(0), record_id)

    def test_no_compliance_claim_in_any_normative_statement(self):
        model = _load_model()
        for m in re.finditer(
            r"require constraint[^{]*\{\s*doc\s*/\*(.*?)\*/", model, re.S
        ):
            self.assertIsNone(
                _FORBIDDEN_CLAIM.search(m.group(1)),
                f"compliance wording in: {m.group(1)[:80]}",
            )

    def test_operating_condition_terminology_is_controlled(self):
        model = _load_model()
        self.assertNotIn("selected operating conditions", model)
        self.assertNotIn("controlled applicable operating conditions", model)

    def test_every_requirement_records_its_need_parent(self):
        deps = _model_dependencies(_load_model())
        for dep, (_, target) in deps.items():
            if dep.startswith("req") and "DerivedFromNeed" in dep:
                self.assertTrue(
                    target.startswith("need"),
                    f"{dep} points at non-need target {target}",
                )


if __name__ == "__main__":
    unittest.main()
