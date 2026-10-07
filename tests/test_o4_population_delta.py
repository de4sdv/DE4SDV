"""Wave A Requirement-population delta measurement (owner decision 6).

Synthetic corpora and a fake traversal; no network. Expectation handling is
tested both ways: a match exits 0, a difference is reported (never adjusted)
and exits non-zero.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from scripts import measure_requirement_population_delta as delta

REVISION = "a" * 40
SEVEN = delta.SEVEN_AEBS_DEFINITIONS


def corpus(*, specialized=True, usages_per_def=(4, 4, 4, 4, 4, 4, 3),
           extra_statements=1):
    """7 defs, N typed usages each, one shadow verify statement per usage."""
    elements = [
        {"@id": "kernel-ec", "@type": "RequirementDefinition", "declaredName": "EvidenceContract"},
        {"@id": "lib-check", "@type": "RequirementDefinition", "declaredName": "RequirementCheck"},
    ]
    statements = 0
    for index, (name, count) in enumerate(zip(SEVEN, usages_per_def)):
        def_id = f"def-{index}"
        elements.append({"@id": def_id, "@type": "RequirementDefinition", "declaredName": name})
        elements.append({"@id": f"sc-{index}", "@type": "Subclassification",
                         "subclassifier": {"@id": def_id},
                         "superclassifier": {"@id": "kernel-ec" if specialized else "lib-check"}})
        for u in range(count):
            usage = f"use-{index}-{u}"
            elements.append({"@id": usage, "@type": "RequirementUsage",
                             "declaredName": f"evidenceContract{index}{u}"})
            elements.append({"@id": f"ft-{index}-{u}", "@type": "FeatureTyping",
                             "typedFeature": {"@id": usage}, "type": {"@id": def_id}})
            repeats = 2 if (extra_statements and index == 0 and u == 0) else 1
            for r in range(repeats):
                shadow = f"shadow-{index}-{u}-{r}"
                elements.append({"@id": shadow, "@type": "RequirementUsage"})
                elements.append({"@id": f"rs-{index}-{u}-{r}", "@type": "ReferenceSubsetting",
                                 "owningRelatedElement": {"@id": shadow},
                                 "referencedFeature": {"@id": usage}})
                elements.append({"@id": f"rvm-{index}-{u}-{r}",
                                 "@type": "RequirementVerificationMembership",
                                 "memberElement": {"@id": shadow}})
                statements += 1
    # An unrelated verify statement that must not be attributed.
    elements.append({"@id": "other-use", "@type": "RequirementUsage"})
    elements.append({"@id": "other-rvm", "@type": "RequirementVerificationMembership",
                     "memberElement": {"@id": "other-use"}})
    return elements, statements


class FakeTraversal:
    """verifiedBy grounds a subject only when ``grounded`` says so."""

    def __init__(self, elements, grounded=True):
        # Resolve the serialized shadow back to its declared usage, the way
        # the real verifiedBy resolver does (queried source = declared usage).
        shadow_to_declared = {e["owningRelatedElement"]["@id"]: e["referencedFeature"]["@id"]
                              for e in elements if e["@type"] == "ReferenceSubsetting"}
        self.by_member = {}
        for element in elements:
            if element["@type"] == "RequirementVerificationMembership":
                member = element["memberElement"]["@id"]
                declared = shadow_to_declared.get(member, member)
                self.by_member.setdefault(declared, []).append(element)
        self.grounded = grounded
        self.calls = []

    def traverse(self, predicate, element, elements):
        self.calls.append((predicate, element["@id"]))
        assert predicate == "verifiedBy"
        if not self.grounded:
            return []
        return [SimpleNamespace(api_object=rvm, target={"@id": f"case-of-{rvm['@id']}"})
                for rvm in self.by_member.get(element["@id"], [])]


def test_structural_population_attributes_usages_and_statements():
    elements, statements = corpus()
    report = delta.structural_population(elements)
    assert report["usage_count"] == 27
    assert report["verify_statement_count"] == statements == 28
    assert report["all_specialize_evidence_contract"] is True
    assert sorted(report["definitions"]) == sorted(SEVEN)
    assert "other-rvm" not in {s for d in report["definitions"].values() for s in d["verify_statements"]}


def test_structural_population_detects_missing_specialization():
    elements, _ = corpus(specialized=False)
    report = delta.structural_population(elements)
    assert report["all_specialize_evidence_contract"] is False


def test_runtime_grounding_counts_usages_and_statements():
    elements, _ = corpus()
    structural = delta.structural_population(elements)
    traversal = FakeTraversal(elements)
    runtime = delta.runtime_grounding(SimpleNamespace(traversal=traversal), elements, structural)
    assert runtime["grounded_usage_count"] == 27
    assert runtime["grounded_verify_statement_count"] == 28
    assert runtime["ungrounded_usages"] == []
    assert {c[0] for c in traversal.calls} == {"verifiedBy"}
    assert "other-use" not in {c[1] for c in traversal.calls}


def test_measure_matches_expectation():
    elements, _ = corpus()
    report = delta.measure(elements, service=SimpleNamespace(traversal=FakeTraversal(elements)),
                           revision=REVISION)
    assert report["classification"] == "MATCHES_EXPECTATION"
    assert report["expected"] == {"usages": 27, "verify_statements": 28,
                                  "definitions": 7}
    assert delta.exit_code(report) == 0


def test_measure_reports_difference_without_adjusting_expectation():
    elements, statements = corpus(extra_statements=0, usages_per_def=(4, 4, 4, 4, 4, 4, 4))
    report = delta.measure(elements, service=SimpleNamespace(traversal=FakeTraversal(elements)),
                           revision=REVISION)
    assert report["measured"]["runtime_grounded_usages"] == 28
    assert report["classification"] == "DIFFERS_FROM_EXPECTATION"
    assert report["expected"]["usages"] == 27  # never rewritten to the measurement
    assert delta.exit_code(report) != 0


def test_ungrounded_runtime_is_a_difference():
    elements, _ = corpus()
    report = delta.measure(elements, service=SimpleNamespace(
        traversal=FakeTraversal(elements, grounded=False)), revision=REVISION)
    assert report["measured"]["runtime_grounded_usages"] == 0
    assert report["classification"] == "DIFFERS_FROM_EXPECTATION"


def test_baseline_cross_check_attributes_delta_to_specialization():
    elements, _ = corpus()
    baseline, _ = corpus(specialized=False)
    report = delta.measure(elements, service=SimpleNamespace(traversal=FakeTraversal(elements)),
                           revision=REVISION, baseline_elements=baseline,
                           baseline_revision="b" * 40)
    cross = report["baseline_cross_check"]
    assert cross["available"] is True
    assert cross["baseline_specialized"] is False
    assert cross["same_structural_population"] is True
    assert cross["delta_attributable_to_specialization"] is True


def test_baseline_already_specialized_is_not_attributable():
    elements, _ = corpus()
    report = delta.measure(elements, service=SimpleNamespace(traversal=FakeTraversal(elements)),
                           revision=REVISION, baseline_elements=corpus()[0],
                           baseline_revision="b" * 40)
    assert report["baseline_cross_check"]["delta_attributable_to_specialization"] is False
    assert report["classification"] == "DIFFERS_FROM_EXPECTATION"


def test_missing_baseline_is_recorded_not_invented():
    elements, _ = corpus()
    report = delta.measure(elements, service=SimpleNamespace(traversal=FakeTraversal(elements)),
                           revision=REVISION)
    assert report["baseline_cross_check"] == {"available": False,
                                              "reason": "no retained pre-Wave-A export supplied"}


def test_real_pre_wave_a_export_shape_if_retained():
    """Real-shape replay of the retained 4d2f3ae export (pre-Wave-A).

    Skipped when the retained artifact is not on this host. Records the
    structural counts that the privileged run's expectation is compared to.
    """
    from pathlib import Path

    path = Path("/home/mrk/.hermes/outputs/ingestion-37144085070/artifact/"
                "de4sdv-full-model-export.json")
    if not path.is_file():
        pytest.skip("retained pre-Wave-A export not available on this host")
    document = json.loads(path.read_text(encoding="utf-8"))
    report = delta.structural_population(document["elements"])
    assert report["all_specialize_evidence_contract"] is False
    assert report["usage_count"] == 27
    # 31 textual verify statements reach the 27 usages: four Regulatory
    # usages are verified by both the pedestrian and the bicycle objective.
    # The owner record says 28; the privileged run reports the difference.
    assert report["verify_statement_count"] == 31


def test_cli_exit_code_and_report(tmp_path, monkeypatch):
    elements, _ = corpus()
    export = tmp_path / "export.json"
    export.write_text(json.dumps({"git_commit": REVISION, "elements": elements}), encoding="utf-8")
    monkeypatch.setattr(delta, "_git_head", lambda: REVISION)
    monkeypatch.setattr(delta, "_build_service",
                        lambda args: (SimpleNamespace(traversal=FakeTraversal(elements),
                                                      binding=SimpleNamespace(git_commit=REVISION)),
                                      SimpleNamespace(provenance=lambda: {"kind": "o3"})))
    monkeypatch.setattr(delta, "_live_elements", lambda service: elements)
    out = tmp_path / "delta.json"
    assert delta.main(["--api-url", "u", "--binding", "b", "--export", str(export),
                       "--git-revision", REVISION, "--output", str(out)]) == 0
    report = json.loads(out.read_text())
    assert report["semantic_authority"] == {"kind": "o3"}
    assert report["export_sha256"].startswith("sha256:")
