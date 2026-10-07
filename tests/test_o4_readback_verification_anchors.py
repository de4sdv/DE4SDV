"""Decision-13 API read-back of the implied VerificationCase anchors.

Synthetic transports only: a fake repository stands in for the queried API; no
network is opened. A pass here is evaluator consistency, never privileged
read-back evidence.
"""
from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

from scripts import readback_verification_anchors as rb

REVISION = "d" * 40
ANCHOR_DEF = "anchor-def"
ANCHOR_USE = "anchor-use"
URI = "pkg:Systems%20Library/VerificationCases.sysml#x"


def corpus(definitions=22, usages=34):
    elements = []
    for i in range(definitions):
        gid, wid = f"vcd-{i}", f"sub-{i}"
        elements.append({"@id": gid, "@type": "VerificationCaseDefinition"})
        elements.append({"@id": wid, "@type": "Subclassification", "isImplied": True,
                         "subclassifier": {"@id": gid},
                         "superclassifier": {"@id": ANCHOR_DEF, "@uri": URI}})
    for i in range(usages):
        gid, wid = f"vcu-{i}", f"subset-{i}"
        elements.append({"@id": gid, "@type": "VerificationCaseUsage"})
        elements.append({"@id": wid, "@type": "Subsetting", "isImplied": True,
                         "subsettingFeature": {"@id": gid},
                         "subsettedFeature": {"@id": ANCHOR_USE, "@uri": URI}})
    elements.append({"@id": "other", "@type": "PartUsage"})
    return elements


def export_document(elements):
    return {
        "git_commit": REVISION,
        "elements": copy.deepcopy(elements),
        "external_references": [],
        "library_anchors": {"VerificationCases::VerificationCase": ANCHOR_DEF,
                            "VerificationCases::verificationCases": ANCHOR_USE},
    }


class FakeRepository:
    """Transport spy: records every read; refuses anything else."""

    def __init__(self, elements, *, overrides=None, missing=()):
        self.elements = elements
        self.by_id = {e["@id"]: e for e in elements}
        self.overrides = overrides or {}
        self.missing = set(missing)
        self.calls = []

    def list_elements(self, project, commit):
        self.calls.append(("list", project, commit))
        return self.elements

    def get_element(self, project, commit, identifier):
        self.calls.append(("get", project, commit, identifier))
        if identifier in self.missing:
            from de4sdv.sysml_api.errors import ApiError

            raise ApiError("GET", identifier, "404")
        return self.overrides.get(identifier, self.by_id[identifier])


def binding(commit=REVISION):
    return SimpleNamespace(git_commit=commit, sysml_project_id="p", sysml_commit_id="c")


def run(repository, export, **kwargs):
    return rb.readback_anchors(repository, binding(kwargs.pop("commit", REVISION)), export,
                               revision=REVISION, **kwargs)


def test_full_population_passes_and_is_activation_eligible():
    elements = corpus()
    repo = FakeRepository(elements)
    report = run(repo, export_document(elements), semantic_report={"element_count": len(elements)})
    assert report["passed"] is True and report["activation_eligible"] is True
    assert report["measured"] == {"definitions": 22, "usages": 34,
                                  "proved_definitions": 22, "proved_usages": 34,
                                  "dereferenced": 56}
    assert report["live_grounding"]["result"] == "EQUIVALENT"
    assert report["failures"] == []
    gets = [call for call in repo.calls if call[0] == "get"]
    assert len(gets) == 2 * 56  # witness + governed element per proved anchor
    assert all(call[1:3] == ("p", "c") for call in repo.calls)


def _failing(report, needle):
    assert report["passed"] is False
    assert report["activation_eligible"] is False
    assert any(needle in failure for failure in report["failures"]), report["failures"]


def test_population_drift_blocks_activation():
    elements = corpus(definitions=21)
    _failing(run(FakeRepository(elements), export_document(elements)), "expected 22")


def test_live_corpus_differing_from_export_blocks():
    elements = corpus()
    live = [e for e in elements if e["@id"] != "other"]
    _failing(run(FakeRepository(live), export_document(elements)), "live corpus")


def test_live_witness_not_implied_blocks():
    elements = corpus()
    live = copy.deepcopy(elements)
    for element in live:
        if element["@id"] == "sub-3":
            element["isImplied"] = False
    report = run(FakeRepository(live), export_document(elements))
    _failing(report, "live grounding")
    assert report["live_grounding"]["result"] == "BLOCKING_MISMATCH"


def test_dereference_shape_mismatch_blocks():
    elements = corpus()
    tampered = dict(next(e for e in elements if e["@id"] == "subset-5"))
    tampered["isImplied"] = False
    _failing(run(FakeRepository(elements, overrides={"subset-5": tampered}),
                 export_document(elements)), "subset-5")


def test_dereference_missing_element_blocks():
    elements = corpus()
    _failing(run(FakeRepository(elements, missing={"vcd-0"}), export_document(elements)),
             "vcd-0")


def test_dereference_wrong_specific_end_blocks():
    elements = corpus()
    tampered = dict(next(e for e in elements if e["@id"] == "sub-1"))
    tampered["subclassifier"] = {"@id": "vcd-2"}
    _failing(run(FakeRepository(elements, overrides={"sub-1": tampered}),
                 export_document(elements)), "sub-1")


def test_export_and_live_witness_sets_must_match():
    elements = corpus()
    export = export_document(elements)
    for element in export["elements"]:
        if element["@id"] == "sub-0":
            element["@id"] = "sub-0-export"
    # the export carries a different witness id for the same governed element
    _failing(run(FakeRepository(elements), export), "witness")


@pytest.mark.parametrize("field", ["binding", "export"])
def test_revision_mismatch_blocks(field):
    elements = corpus()
    export = export_document(elements)
    if field == "export":
        export["git_commit"] = "e" * 40
        report = run(FakeRepository(elements), export)
    else:
        report = run(FakeRepository(elements), export, commit="e" * 40)
    _failing(report, "revision")


def test_semantic_report_element_count_mismatch_blocks():
    elements = corpus()
    _failing(run(FakeRepository(elements), export_document(elements),
                 semantic_report={"element_count": 7}), "element_count")


def test_claim_boundary_is_explicit():
    elements = corpus()
    report = run(FakeRepository(elements), export_document(elements))
    assert "not" in report["claim_boundary"]
    assert report["schema"] == rb.READBACK_SCHEMA
    assert report["decision"] == "decision-13"


def test_cli_writes_report_and_exit_code_tracks_pass(tmp_path, monkeypatch):
    elements = corpus()
    export = tmp_path / "export.json"
    export.write_text(json.dumps(export_document(elements)), encoding="utf-8")
    binding_path = tmp_path / "binding.json"
    binding_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(rb, "_git_head", lambda: REVISION)
    monkeypatch.setattr(rb, "_load_binding", lambda path: binding())
    for live, expected in ((elements, 0), (corpus(usages=33), 2)):
        monkeypatch.setattr(rb, "_repository", lambda url, live=live: FakeRepository(live))
        out = tmp_path / f"out-{expected}.json"
        code = rb.main(["--api-url", "http://127.0.0.1:9", "--binding", str(binding_path),
                        "--export", str(export), "--git-revision", REVISION,
                        "--api-source", "restored-same-run-snapshot", "--output", str(out)])
        assert code == expected
        report = json.loads(out.read_text())
        assert report["activation_eligible"] is (expected == 0)


def test_cli_refuses_moving_revision(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "_git_head", lambda: "f" * 40)
    with pytest.raises(SystemExit):
        rb.main(["--api-url", "u", "--binding", "b", "--export", "e", "--api-source",
                 "deployed-api", "--git-revision", REVISION, "--output", str(tmp_path / "o.json")])


@pytest.mark.parametrize("source, needle", [
    ("restored-same-run-snapshot", "pg_restore"),
    ("deployed-api", "deployed SysML v2 API"),
])
def test_claim_boundary_names_the_queried_api_instance(source, needle):
    """R7: the CI read-back queries a restored same-run snapshot, never 'the live production API'."""
    elements = corpus()
    report = run(FakeRepository(elements), export_document(elements), api_source=source)
    assert report["api_source"] == source
    assert needle in report["claim_boundary"]
    assert "identity-checked against the export" in report["claim_boundary"]
    if source == "restored-same-run-snapshot":
        assert "not the live production API" in report["claim_boundary"]


def test_cli_requires_the_api_source():
    with pytest.raises(SystemExit):
        rb.main(["--api-url", "u", "--binding", "b", "--export", "e", "--git-revision",
                 REVISION, "--output", "o"])


def test_workflow_declares_the_restored_snapshot_source():
    from pathlib import Path

    text = (Path(rb.ROOT) / ".github/workflows/privileged-full-model-api-ingestion.yml").read_text()
    call = text[text.index("python scripts/readback_verification_anchors.py"):]
    assert "--api-source restored-same-run-snapshot" in call[:600]
