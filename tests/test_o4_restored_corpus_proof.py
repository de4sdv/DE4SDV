"""Fail-fast proof that a restored API database serves the export corpus.

Synthetic transports only: a fake repository stands in for the restored API;
no network is opened. A pass here is evaluator consistency, never privileged
restore evidence.

Regression anchor: the first real model-authority-evidence run
(37677500924) restored the same-run pg_dump and then started the stock API
build, whose ``hibernate.hbm2ddl.auto=create-drop`` recreated the schema and
served 0 of 84429 elements. Every evidence step refused, but only after the
fact and with secondary messages; this proof names the cause first.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from scripts import verify_restored_api_corpus as proof

PROJECT, COMMIT = "project-1", "commit-1"


def binding():
    return SimpleNamespace(git_commit="d" * 40, sysml_project_id=PROJECT, sysml_commit_id=COMMIT)


def export_document(count=5):
    return {"git_commit": "d" * 40,
            "elements": [{"@id": f"e-{i}", "@type": "PartUsage"} for i in range(count)]}


class FakeRepository:
    """Transport spy: records every read."""

    def __init__(self, elements, *, projects=(PROJECT,), commits=(COMMIT,)):
        self.elements = elements
        self.projects = set(projects)
        self.commits = set(commits)
        self.calls = []

    def get_project(self, project_id):
        self.calls.append(("project", project_id))
        if project_id not in self.projects:
            raise RuntimeError("404 project not found")
        return {"@id": project_id}

    def get_commit(self, project_id, commit_id):
        self.calls.append(("commit", project_id, commit_id))
        if commit_id not in self.commits:
            raise RuntimeError("404 commit not found")
        return {"@id": commit_id}

    def list_elements(self, project_id, commit_id):
        self.calls.append(("elements", project_id, commit_id))
        return list(self.elements)


def test_restored_corpus_equal_to_the_export_passes():
    export = export_document()
    repo = FakeRepository(export["elements"])
    report = proof.prove_restored_corpus(repo, binding(), export, {"element_count": 5})
    assert report["passed"] is True, report["failures"]
    assert report["export_element_count"] == report["live_element_count"] == 5
    assert report["semantic_report_element_count"] == 5
    # Reads only through the binding's project/commit (the existing read path).
    assert ("project", PROJECT) in repo.calls
    assert ("commit", PROJECT, COMMIT) in repo.calls
    assert ("elements", PROJECT, COMMIT) in repo.calls


def test_empty_restored_api_names_the_schema_wipe_cause():
    """The run-37677500924 symptom: project reachable, 0 elements served."""
    report = proof.prove_restored_corpus(FakeRepository([]), binding(), export_document(),
                                         {"element_count": 5})
    assert report["passed"] is False
    assert report["live_element_count"] == 0
    joined = " ".join(report["failures"])
    assert "0 of 5" in joined and "create-drop" in joined


def test_missing_binding_project_is_refused_before_listing():
    repo = FakeRepository([], projects=())
    report = proof.prove_restored_corpus(repo, binding(), export_document(), None)
    assert report["passed"] is False
    assert any("project" in f and PROJECT in f for f in report["failures"])
    assert not any(c[0] == "elements" for c in repo.calls)


def test_missing_binding_commit_is_refused_before_listing():
    repo = FakeRepository([], commits=())
    report = proof.prove_restored_corpus(repo, binding(), export_document(), None)
    assert report["passed"] is False
    assert any("commit" in f and COMMIT in f for f in report["failures"])
    assert not any(c[0] == "elements" for c in repo.calls)


def test_partial_restore_is_refused():
    export = export_document()
    report = proof.prove_restored_corpus(FakeRepository(export["elements"][:3]), binding(),
                                         export, None)
    assert report["passed"] is False
    assert any("3" in f and "5" in f for f in report["failures"])


def test_same_count_different_ids_is_refused():
    export = export_document()
    other = [{"@id": f"x-{i}"} for i in range(5)]
    report = proof.prove_restored_corpus(FakeRepository(other), binding(), export, None)
    assert report["passed"] is False
    assert any("element id set" in f for f in report["failures"])


def test_export_and_semantic_report_disagreement_is_refused():
    export = export_document()
    report = proof.prove_restored_corpus(FakeRepository(export["elements"]), binding(), export,
                                         {"element_count": 6})
    assert report["passed"] is False
    assert any("semantic report" in f for f in report["failures"])


def test_cli_emits_error_annotations_and_exit_2(tmp_path, monkeypatch, capsys):
    export = export_document()
    (tmp_path / "export.json").write_text(json.dumps(export), encoding="utf-8")
    (tmp_path / "report.json").write_text(json.dumps({"element_count": 5}), encoding="utf-8")
    monkeypatch.setattr(proof, "_load_binding", lambda path: binding())
    monkeypatch.setattr(proof, "_repository", lambda url: FakeRepository([]))
    rc = proof.main(["--api-url", "http://127.0.0.1:9000", "--binding", str(tmp_path / "b.json"),
                     "--export", str(tmp_path / "export.json"),
                     "--semantic-report", str(tmp_path / "report.json"),
                     "--output", str(tmp_path / "out" / "proof.json")])
    assert rc == 2
    out = capsys.readouterr().out
    assert "::error::" in out and "create-drop" in out
    written = json.loads((tmp_path / "out" / "proof.json").read_text(encoding="utf-8"))
    assert written["passed"] is False and written["export_sha256"].startswith("sha256:")


def test_cli_passes_with_exit_0(tmp_path, monkeypatch, capsys):
    export = export_document()
    (tmp_path / "export.json").write_text(json.dumps(export), encoding="utf-8")
    monkeypatch.setattr(proof, "_load_binding", lambda path: binding())
    monkeypatch.setattr(proof, "_repository", lambda url: FakeRepository(export["elements"]))
    rc = proof.main(["--api-url", "http://x", "--binding", str(tmp_path / "b.json"),
                     "--export", str(tmp_path / "export.json"),
                     "--output", str(tmp_path / "proof.json")])
    assert rc == 0
    assert "::error::" not in capsys.readouterr().out


@pytest.mark.parametrize("failure", [RuntimeError("connection refused")])
def test_listing_failure_is_a_refusal_not_a_crash(failure):
    class Broken(FakeRepository):
        def list_elements(self, project_id, commit_id):
            raise failure

    report = proof.prove_restored_corpus(Broken([]), binding(), export_document(), None)
    assert report["passed"] is False
    assert any("connection refused" in f for f in report["failures"])
