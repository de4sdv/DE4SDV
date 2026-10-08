"""Answer-report pair manifests carry each report's real label (O4 Wave C2, G3).

The O3 runner hard-coded ``legacy-authored``/``o3-authority`` for every pair,
mislabelling the model pairs (owner amendment 2026-10-08). The comparison now
takes each manifest's ``authority_path`` from its own report's ``label``;
equal or empty labels are refused, any basis difference blocks, and
``allow_revision_change`` relaxes only the Git revision. Synthetic answer
reports; no runtime, no API.
"""
from __future__ import annotations

import copy
import json

import pytest

from de4sdv.semantic import runtime_answers as ra

OLD_LABEL = "c1:mab:mab-" + "1" * 32
NEW_LABEL = "c2:mab:mab-" + "2" * 32


def _record(subject, revision="a" * 40, targets=("t-1",)):
    return {"predicate": "p", "subject_id": subject, "source_revision": revision,
            "sysml_project_id": "pid", "sysml_commit_id": "cid", "direction": "forward",
            "semantic_strength": "native-reference", "claim_boundary": "b",
            "support_state": "supported", "completeness": "complete", "unsupported": False,
            "targets": list(targets), "witnesses": [], "nodes": [], "diagnostics": [],
            "unsupported_predicates": [], "path": []}


def report(label, *, revision="a" * 40, project="pid", commit="cid", scope="full-model",
           element_count=10, subjects=("s-1", "s-2")):
    predicates = {}
    for predicate in ra.RELATIONSHIP_PREDICATES:
        records = {s: dict(_record(s, revision), predicate=predicate) for s in subjects}
        for record in records.values():
            record.update(sysml_project_id=project, sysml_commit_id=commit)
        predicates[predicate] = {"subjects": list(subjects), "records": records}
    classes = {name: {"element_id": f"root-{name}"} for name in ra.FILE_MAPPED_CLASSES}
    classes[ra.NATIVE_CLASS_IDENTITY] = {"grounding_result": "EQUIVALENT"}
    return {"schema": ra.ANSWER_REPORT_SCHEMA, "label": label,
            "authority_id": label.split(":", 1)[1], "git_revision": revision,
            "sysml_project_id": project, "sysml_commit_id": commit,
            "evaluation_scope": scope, "element_count": element_count,
            "predicates": predicates, "classes": classes,
            "k_pair": {"classification": "EQUIVALENT", "forward_witness_population": ["w-1"]}}


def test_manifests_carry_each_reports_own_label():
    result = ra.compare_answer_reports(report(OLD_LABEL), report(NEW_LABEL))
    assert result["overall"] == "EQUIVALENT", result["manifest_validation"]
    assert result["labels"] == {"old": OLD_LABEL, "new": NEW_LABEL}
    assert result["manifests"]["old"]["authority_path"] == OLD_LABEL
    assert result["manifests"]["new"]["authority_path"] == NEW_LABEL
    assert result["manifests"]["old"]["authority_id"] == "mab:mab-" + "1" * 32


def test_hard_coded_o3_labels_never_appear():
    text = json.dumps(ra.compare_answer_reports(report(OLD_LABEL), report(NEW_LABEL)))
    assert "legacy-authored" not in text and "o3-authority" not in text


def test_equal_labels_are_refused():
    result = ra.compare_answer_reports(report(OLD_LABEL), report(OLD_LABEL))
    assert "authority-path-not-distinct" in result["manifest_validation"]["errors"]
    assert result["overall"] == "BLOCKING_MISMATCH"


def test_empty_label_is_refused():
    result = ra.compare_answer_reports(dict(report(OLD_LABEL), label=""), report(NEW_LABEL))
    assert "authority-path-missing" in result["manifest_validation"]["errors"]
    assert result["overall"] == "BLOCKING_MISMATCH"


def test_collect_answers_requires_a_label():
    with pytest.raises(ValueError, match="authority label"):
        ra.collect_answers(None, [], label="  ")


@pytest.mark.parametrize("change,field", [
    ({"revision": "b" * 40}, "git_revision"),
    ({"project": "other"}, "sysml_project_id"),
    ({"commit": "other"}, "sysml_commit_id"),
    ({"scope": "fixture"}, "evaluation_scope"),
    ({"element_count": 11}, "element_count"),
    ({"subjects": ("s-1",)}, "subject_ids"),
])
def test_basis_mismatch_blocks(change, field):
    result = ra.compare_answer_reports(report(OLD_LABEL), report(NEW_LABEL, **change))
    assert f"basis-mismatch:{field}" in result["manifest_validation"]["errors"]
    assert result["overall"] == "BLOCKING_MISMATCH"


def test_allow_revision_change_relaxes_only_the_git_revision():
    moved = report(NEW_LABEL, revision="b" * 40)
    result = ra.compare_answer_reports(report(OLD_LABEL), moved, allow_revision_change=True)
    assert result["manifest_validation"]["errors"] == []
    assert result["overall"] == "EQUIVALENT"
    for change, field in (({"project": "other"}, "sysml_project_id"),
                          ({"commit": "other"}, "sysml_commit_id"),
                          ({"scope": "fixture"}, "evaluation_scope"),
                          ({"element_count": 11}, "element_count")):
        result = ra.compare_answer_reports(report(OLD_LABEL),
                                           report(NEW_LABEL, revision="b" * 40, **change),
                                           allow_revision_change=True)
        assert f"basis-mismatch:{field}" in result["manifest_validation"]["errors"]
        assert result["overall"] == "BLOCKING_MISMATCH"


def test_a_changed_answer_blocks_even_with_distinct_labels():
    new = report(NEW_LABEL)
    changed = copy.deepcopy(new)
    changed["predicates"]["hasSubject"]["records"]["s-1"]["targets"] = ["t-other"]
    result = ra.compare_answer_reports(report(OLD_LABEL), changed)
    assert result["manifest_validation"]["errors"] == []
    assert result["per_identity"]["hasSubject"]["classification"] == "BLOCKING_MISMATCH"
    assert result["overall"] == "BLOCKING_MISMATCH"


def test_non_answer_reports_are_refused():
    with pytest.raises(ValueError, match="not an answer report"):
        ra.compare_answer_reports(dict(report(OLD_LABEL), schema="other"), report(NEW_LABEL))
