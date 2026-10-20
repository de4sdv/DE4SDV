"""The privileged run's successor parity over the imported API revision (the allocatedTo obligations).

``scripts/validate_full_model_semantic_queries.py`` (the privileged step
"Exercise production semantic concerns and the successor parity") compares,
for ``allocatedTo`` and ``hasValidationScenario``, the facts the production
runtime serves over the imported API revision with the export snapshot of
the same revision and the method's reader, and closes the typed allocation
ends (``de4sdv.semantic.successor_parity``). These tests run that step's
function through the deployment runtime (startup check on a clean clone,
served-model check) over a synthetic HTTP API serving the genuine export cut.
Not privileged-run evidence: the real run is the exact-SHA ingestion.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

import anyio
import pytest

from de4sdv.semantic.deployment_runtime import build_deployment_runtime
from de4sdv.semantic.export_evaluation import load_export_snapshot
from de4sdv.sysml_api.served_model import ServedModel
from increment_model_fixtures import GENUINE_EXPORT
from scripts import validate_full_model_semantic_queries as queries
from tests.model_contract_fixtures import binding_dict
from test_validator_runtime import COMMIT, PROJECT, checkout, synthetic_api  # noqa: F401 - fixture


def _relabeled_export(tmp_path: Path, head: str) -> tuple[Path, dict]:
    """The genuine cut as the export of ``head`` (identical model content; the revision is relabeled)."""
    export = json.loads(gzip.decompress(GENUINE_EXPORT.read_bytes()))
    export["git_commit"] = head
    path = tmp_path / "export.json"
    path.write_text(json.dumps(export), encoding="utf-8")
    return path, export


def _binding(tmp_path: Path, head: str, export_path: Path, served_elements: list[dict]) -> Path:
    snapshot = load_export_snapshot(export_path)
    served = ServedModel.from_elements(
        served_elements, source_export_sha256=hashlib.sha256(export_path.read_bytes()).hexdigest()).to_dict()
    path = tmp_path / "binding.json"
    path.write_text(json.dumps(binding_dict(
        git_repository="de4sdv/DE4SDV", git_commit=head, sysml_project_id=PROJECT, sysml_commit_id=COMMIT,
        served_model=served, kernel_bindings=[
            dict(ontology_class=b.ontology_class, element_id=b.element_id, source_file=b.source_file,
                 declaration=b.declaration) for b in snapshot.kernel_bindings])), encoding="utf-8")
    return path


def _parity(checkout_root: Path, head: str, binding: Path, export_path: Path, served: list[dict]) -> dict:
    async def run():
        async with synthetic_api(served) as url:
            runtime = build_deployment_runtime(checkout_root, api_url=url, binding_path=binding,
                                               expected_git_revision=head)
            return queries.successor_parity(runtime, export_path, head)

    return anyio.run(run)


@pytest.fixture
def cut(tmp_path, checkout, monkeypatch):  # noqa: F811 - the imported fixture
    root, head = checkout
    monkeypatch.setattr(queries, "ROOT", root)
    export_path, export = _relabeled_export(tmp_path, head)
    return root, head, export_path, export


def test_the_api_revision_serves_the_export_facts_and_closes_the_typed_allocation_ends(cut, tmp_path):
    root, head, export_path, export = cut
    binding = _binding(tmp_path, head, export_path, export["elements"])
    report = _parity(root, head, binding, export_path, export["elements"])
    assert report["passed"], json.dumps(report)[:2000]
    assert {name: len(record["facts"]) for name, record in report["relations"].items()} == {
        "allocatedTo": 27, "hasValidationScenario": 5}
    assert report["allocation_end_closure"]["passed"]


def test_an_api_revision_that_serves_other_allocation_ends_fails_the_parity(cut, tmp_path):
    """The API serves (and the binding records) a corpus that lost one allocation end: the runtime
    accepts it as served, and the parity against the export refuses it."""
    root, head, export_path, export = cut
    elements = export["elements"]
    allocation = next(e for e in elements if e.get("declaredName") == "presentByApplication")
    membership = next(r["@id"] for r in allocation["ownedRelationship"]
                      if next(e for e in elements if e["@id"] == r["@id"])["@type"] == "EndFeatureMembership")
    served = [e for e in elements if e["@id"] != membership]
    binding = _binding(tmp_path, head, export_path, served)
    report = _parity(root, head, binding, export_path, served)
    assert not report["passed"]
    assert not report["relations"]["allocatedTo"]["passed"]
    assert report["allocation_end_closure"]["unreadable"] == [allocation["@id"]]


def test_an_export_of_another_revision_refuses_the_parity(cut, tmp_path):
    root, head, export_path, export = cut
    binding = _binding(tmp_path, head, export_path, export["elements"])
    other = json.loads(export_path.read_text(encoding="utf-8"))
    other["git_commit"] = "b" * 40
    other_path = tmp_path / "other-export.json"
    other_path.write_text(json.dumps(other), encoding="utf-8")
    with pytest.raises(RuntimeError, match="not the checkout"):
        _parity(root, head, binding, other_path, export["elements"])


def test_the_step_fails_closed_when_the_parity_fails_and_keeps_the_report(tmp_path, monkeypatch):
    """A failed parity writes the report, names the failed checks and exits 1, so the privileged run
    fails and no deploy takes its evidence (a failure blocks activation)."""
    report = {"concern_count": 3, "successor_parity": {
        "passed": False,
        "relations": {"allocatedTo": {"passed": False, "checks": {"the API-served traversal returns the "
                                                                  "method's facts": False}},
                      "hasValidationScenario": {"passed": True, "checks": {}}},
        "allocation_end_closure": {"passed": True, "checks": {}}}}
    monkeypatch.setattr(queries, "run_queries", lambda **kwargs: report)
    output = tmp_path / "coverage.json"
    monkeypatch.setattr(sys, "argv", ["validate_full_model_semantic_queries.py", "--api-url", "http://x",
                                      "--binding", "b.json", "--semantic-report", "r.json",
                                      "--export", "e.json", "--output", str(output)])
    assert queries.main() == 1
    assert json.loads(output.read_text())["successor_parity"]["passed"] is False
    report["successor_parity"]["passed"] = True
    report["successor_parity"]["relations"]["allocatedTo"]["passed"] = True
    assert queries.main() == 0
