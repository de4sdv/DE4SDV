"""Release evidence over the export: each check passes on agreement and fails alone.

``scripts/check_release_evidence.py`` replaces the per-release acceptance
package and the deployed-API closure. Its checks compare content and
identities, never reviewed counts. These tests drive the pure evaluation over
synthetic collected evidence (the real-data run is privileged-run evidence)
and the export transport that replaces the API.
"""
from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from scripts import check_release_evidence as cre

HEAD = "a" * 40
SAI = {"schema": "de4sdv.semantic-authority/v1", "id": "sai-" + "1" * 32,
       "layers": [{"path": "x.json", "sha256": "sha256:" + "2" * 64}]}
EXPORT_SHA = "3" * 64
CONTENT = "sha256:" + "4" * 64
SERVED = {"schema": "de4sdv.served-model/v1", "source_export_sha256": EXPORT_SHA,
          "element_count": 2, "content_sha256": CONTENT}
KB = [{"ontology_class": "Need", "element_id": "e-need", "source_file": "m.sysml",
       "declaration": "part def Need"}]
DOCUMENTS = "sha256:" + "5" * 64


def _parity():
    """A passing successor parity section of the query-coverage battery (the allocatedTo obligations)."""
    return {"schema": cre.PARITY_SCHEMA, "passed": True,
            "relations": {name: {"passed": True} for name in cre.PARITY_RELATIONS},
            "allocation_end_closure": {"passed": True}}


def _batteries():
    authority = {"semantic_authority": SAI["id"], "served_model": CONTENT}
    revision = {"git_commit": HEAD, "sysml_project_id": "p", "sysml_commit_id": "c"}
    return {
        "query_coverage": {"schema": cre.BATTERY_SCHEMAS["query_coverage"], "git_commit": HEAD,
                           "sysml_project_id": "p", "sysml_commit_id": "c",
                           "semantic_authority": dict(authority), "successor_parity": _parity()},
        "scope_validation": {"schema": cre.BATTERY_SCHEMAS["scope_validation"],
                             "revision": dict(revision), "model_authority": dict(authority),
                             "api_element_count": 2},
        "mcp_validation": {"schema": cre.BATTERY_SCHEMAS["mcp_validation"], "read_only": True,
                           "tool_count": 7, "revision": dict(revision),
                           "semantic_authority": dict(authority)},
    }


def _evidence() -> cre.Evidence:
    return cre.Evidence(
        head=HEAD,
        export={"git_commit": HEAD, "elements": [{"@id": "e-need"}, {"@id": "e2"}]},
        export_sha256=EXPORT_SHA,
        binding_document={"schema": "de4sdv.revision-binding/v2", "scope": "full-model",
                          "semantic_validation": "passed", "git_commit": HEAD,
                          "sysml_project_id": "p", "sysml_commit_id": "c",
                          "semantic_authority": SAI, "kernel_bindings": KB,
                          "served_model": dict(SERVED),
                          "export_documents": {"source_export_sha256": EXPORT_SHA, "content_sha256": DOCUMENTS}},
        semantic_report={"git_commit": HEAD, "source_export_sha256": EXPORT_SHA,
                         "element_count": 2, "semantic_authority": SAI},
        batteries=_batteries(),
        export_content_sha256=CONTENT,
        export_documents_sha256=DOCUMENTS,
        export_kernel_bindings=[("Need", "e-need", "m.sysml", "part def Need")],
        checkout_semantic_authority=SAI,
        runtime={"startup_check": "passed", "served_model_check": "passed",
                 "k_pair": {"classification": "EQUIVALENT", "export_witness_population": ["k1"],
                            "errors": [], "missing": []},
                 "discriminator": {"hop_count": 18, "distinct_sources": 11, "errors": []},
                 "closure_identity": {"result": "EQUAL", "live_only": [], "bound_only": []},
                 "grounding": {"result": "EQUIVALENT", "missing": [], "conflicts": [],
                               "governed_population": {"definitions": 1, "usages": 1}}},
        coverage={"residual": [], "residual_declarations": [], "duplicates": [],
                  "kernel_accounting_errors": []},
    )


def _failed(evidence):
    return [r["check"] for r in cre.evaluate(evidence) if not r["ok"]]


def test_agreeing_evidence_passes_every_check():
    results = cre.evaluate(_evidence())
    assert all(r["ok"] for r in results), [r for r in results if not r["ok"]]
    assert len(results) == 19


def _mutated(mutate):
    evidence = copy.deepcopy(_evidence())
    mutate(evidence)
    return evidence


@pytest.mark.parametrize("mutate,check", [
    (lambda e: e.export.__setitem__("git_commit", "b" * 40), "revision"),
    (lambda e: setattr(e, "export_sha256", "9" * 64), "export file digest"),
    (lambda e: setattr(e, "export_content_sha256", "sha256:" + "9" * 64), "content digest"),
    (lambda e: e.export["elements"].append({"@id": "e3"}), "content digest"),
    (lambda e: e.binding_document.__setitem__("scope", "candidate"), "binding: v2"),
    (lambda e: e.binding_document.pop("export_documents"), "export documents"),
    (lambda e: setattr(e, "export_documents_sha256", "sha256:" + "9" * 64), "export documents"),
    (lambda e: e.binding_document["export_documents"].update(source_export_sha256="9" * 64),
     "export documents"),
    (lambda e: setattr(e, "checkout_semantic_authority", dict(SAI, id="sai-" + "9" * 32)),
     "semantic authority"),
    (lambda e: setattr(e, "export_kernel_bindings", [("Need", "other", "m.sysml", "part def Need")]),
     "kernel bindings"),
    (lambda e: setattr(e, "export_kernel_bindings", None), "kernel bindings"),
    (lambda e: e.runtime.update(startup_check=None, error="StartupCheckError: dirty tree"),
     "runtime over the export"),
    (lambda e: e.runtime.update(served_model_check="failed: drift"), "runtime over the export"),
    (lambda e: e.runtime["k_pair"].update(classification="BLOCKING_MISMATCH"), "K pair"),
    (lambda e: e.runtime["discriminator"].update(errors=["x: boom"]), "discriminator: has"),
    (lambda e: e.runtime["discriminator"].update(hop_count=0), "discriminator: has"),
    (lambda e: e.runtime["closure_identity"].update(result="BLOCKING_MISMATCH"),
     "discriminator: live"),
    (lambda e: e.runtime["grounding"].update(missing=["anchor"]), "VerificationCase"),
    (lambda e: e.coverage.update(residual=["Planted"]), "coverage"),
    (lambda e: e.batteries["query_coverage"].update(git_commit="b" * 40), "battery query_coverage"),
    (lambda e: e.batteries["scope_validation"]["revision"].update(sysml_commit_id="x"),
     "battery scope_validation: schema"),
    (lambda e: e.batteries["mcp_validation"]["semantic_authority"].update(
        semantic_authority="sai-" + "9" * 32), "battery mcp_validation: schema"),
    (lambda e: e.batteries["query_coverage"]["semantic_authority"].update(served_model=None),
     "battery query_coverage"),
    (lambda e: e.batteries["mcp_validation"].update(tool_count=6), "seven exercised tools"),
    (lambda e: e.batteries["query_coverage"].pop("successor_parity"), "successor parity"),
    (lambda e: e.batteries["query_coverage"]["successor_parity"].update(passed=False), "successor parity"),
    (lambda e: e.batteries["query_coverage"]["successor_parity"]["relations"].pop("hasValidationScenario"),
     "successor parity"),
    (lambda e: e.batteries["query_coverage"]["successor_parity"]["relations"]["allocatedTo"].update(
        passed=False), "successor parity"),
    (lambda e: e.batteries["query_coverage"]["successor_parity"]["allocation_end_closure"].update(
        passed=False), "successor parity"),
    (lambda e: e.batteries["query_coverage"]["successor_parity"].update(schema="other"), "successor parity"),
    (lambda e: e.batteries["scope_validation"].update(api_element_count=1),
     "listing holds the served model"),
])
def test_each_disagreement_fails_its_own_check(mutate, check):
    failed = _failed(_mutated(mutate))
    assert failed and all(check in name for name in failed), failed


def test_battery_checks_run_only_for_supplied_reports():
    evidence = replace(_evidence(), batteries={"query_coverage": None, "scope_validation": None,
                                               "mcp_validation": None})
    results = cre.evaluate(evidence)
    assert all(r["ok"] for r in results)
    assert not any(r["check"].startswith("battery") for r in results)


def test_no_check_compares_a_reviewed_count():
    source = (cre.ROOT / "scripts/check_release_evidence.py").read_text(encoding="utf-8")
    for frozen in ("== 27", "== 25", "== 38", "== 88527", "READINESS_BASELINE"):
        assert frozen not in source, frozen


# -- the export replaces the API transport -------------------------------------------


def test_the_export_transport_serves_only_the_bound_revision():
    from de4sdv.sysml_api.revisions import RevisionBinding
    from tests.model_contract_fixtures import binding_dict

    elements = [{"@id": "a", "@type": "Package"}, {"@id": "b", "@type": "PartUsage"}]
    binding = RevisionBinding.from_dict(binding_dict(sysml_project_id="p", sysml_commit_id="c"))
    repository = cre.export_repository(elements, binding)
    assert repository.list_elements("p", "c") == elements
    assert repository.get_element("p", "c", "b") == elements[1]
    with pytest.raises(ValueError, match="bound revision"):
        repository.client.get_all("/projects/p/commits/other/elements")
    with pytest.raises(ValueError, match="element reads"):
        repository.client.request("POST", "/projects/p/commits/c/elements/a")
