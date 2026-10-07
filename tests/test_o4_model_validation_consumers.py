"""Wave B validation consumers under ``model`` authority (synthetic inputs)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import import_sysml_api_baseline as importer
from scripts import validate_full_model_semantic_queries as queries
from scripts import validate_product_line_scope_api as scope
from scripts import validate_semantic_mcp as mcp

ROOT = Path(__file__).resolve().parents[1]
MAB_ID = "mab-" + "b" * 32


# -- import: authored vs model-provider cross-check ------------------------------


class _Contract:
    def __init__(self, mappings):
        self._mappings = mappings

    def mapping(self, name):
        from de4sdv.semantic.kernel_contract import KernelFileMapping, KernelNativeMapping

        if name not in self._mappings:
            raise KeyError(name)
        value = self._mappings[name]
        if value == "native":
            return KernelNativeMapping("SysML::X")
        return KernelFileMapping(*value)


def _projection(root, relative, rows):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": "x", "rows": rows}), encoding="utf-8")


def _row(identity, source_file, declaration):
    return {"identity": identity,
            "grounding": {"kernel_binding_contract": {"source_file": source_file,
                                                      "declaration": declaration}}}


def test_cross_check_matches_on_real_repository():
    from de4sdv.semantic.kernel_contract import KernelContract

    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml")
    report = importer.cross_check_model_provider(contract, [], root=ROOT)
    assert report["classification"] == "EQUIVALENT"
    assert report["projected_identity_count"] >= 29
    assert report["mismatches"] == [] and report["duplicate_providers"] == []
    assert "docs/method-conformance/o4/definition-projection.json" in report["provider_sources"]


def test_cross_check_refuses_declaration_mismatch(tmp_path):
    _projection(tmp_path, "docs/method-conformance/o4/definition-projection.json",
                [_row("Need", "m.sysml", "part def Need"),
                 _row("Gap", "m.sysml", "part def RenamedGap")])
    contract = _Contract({"Need": ("m.sysml", "part def Need"), "Gap": ("m.sysml", "part def Gap")})
    report = importer.cross_check_model_provider(contract, [], root=tmp_path)
    assert report["classification"] == "BLOCKING_MISMATCH"
    assert [m["identity"] for m in report["mismatches"]] == ["Gap"]
    assert report["matched"] == 1


def test_cross_check_refuses_projected_identity_without_file_mapping(tmp_path):
    _projection(tmp_path, "docs/method-conformance/o2/semantic-projection-v1.json",
                [_row("Orphan", "m.sysml", "part def Orphan"),
                 _row("Native", "m.sysml", "part def Native")])
    report = importer.cross_check_model_provider(_Contract({"Native": "native"}), [],
                                                 root=tmp_path)
    assert report["classification"] == "BLOCKING_MISMATCH"
    assert {m["reason"] for m in report["mismatches"]} == {
        "projected identity has no authored kernel mapping",
        "projected identity is not file-mapped in the authored contract",
    }


def test_cross_check_refuses_conflicting_duplicate_providers(tmp_path):
    _projection(tmp_path, "docs/method-conformance/o4/a-projection.json",
                [_row("Need", "m.sysml", "part def Need")])
    _projection(tmp_path, "docs/method-conformance/o4/b-projection.json",
                [_row("Need", "other.sysml", "part def Need")])
    report = importer.cross_check_model_provider(
        _Contract({"Need": ("m.sysml", "part def Need")}), [], root=tmp_path)
    assert report["classification"] == "BLOCKING_MISMATCH"
    assert report["duplicate_providers"][0]["identity"] == "Need"


def test_cross_check_records_ingestion_resolution(tmp_path):
    _projection(tmp_path, "docs/method-conformance/o4/definition-projection.json",
                [_row("Need", "m.sysml", "part def Need")])
    bindings = [{"ontology_class": "Need", "element_id": "uuid-1",
                 "source_file": "m.sysml", "declaration": "part def Need"}]
    report = importer.cross_check_model_provider(
        _Contract({"Need": ("m.sysml", "part def Need")}), bindings, root=tmp_path)
    assert report["rows"] == [{"identity": "Need", "source_file": "m.sysml",
                               "declaration": "part def Need",
                               "provider": "docs/method-conformance/o4/definition-projection.json",
                               "ingested_element_id": "uuid-1"}]


def test_cross_check_with_no_projection_is_not_comparable(tmp_path):
    report = importer.cross_check_model_provider(_Contract({}), [], root=tmp_path)
    assert report["classification"] == "NOT_YET_COMPARABLE"


def test_import_binding_schema_is_unchanged_by_cross_check():
    # The cross-check is additive to the REPORT; the revision-binding writer
    # is not touched (no new binding field).
    source = (ROOT / "scripts/import_sysml_api_baseline.py").read_text(encoding="utf-8")
    binding_block = source.split("binding = RevisionBinding(", 1)[1].split(")\n", 1)[0]
    assert "model_provider" not in binding_block


# -- full-model semantic queries -------------------------------------------------


def _braking(edges, gaps=("evidence",)):
    return {"edges": edges, "gaps": [{"category": c} for c in gaps]}


def test_queries_legacy_and_o3_still_refuse_evidence_edges():
    braking = _braking([{"predicate": "hasRelevantEvidenceContract"}])
    for authority in ("legacy", "o3", None):
        with pytest.raises(RuntimeError, match="blocked"):
            queries.evidence_contract_state(braking, authority)
    assert queries.evidence_contract_state(_braking([]), "o3") == "blocked"


def test_queries_model_requires_resolved_evidence_edges():
    assert queries.evidence_contract_state(
        _braking([{"predicate": "hasRelevantEvidenceContract", "semantic_strength": "relevance"}],
                 gaps=()), "model") == "resolved"
    with pytest.raises(RuntimeError, match="no hasRelevantEvidenceContract"):
        queries.evidence_contract_state(_braking([]), "model")


def test_queries_model_bundle_id_must_be_literal(tmp_path):
    with pytest.raises(ValueError, match="mab-"):
        queries.run_queries(api_url="u", binding_path=tmp_path / "b", semantic_report_path=tmp_path,
                            authority="model", model_bundle_id="mab-nothex")


# -- MCP Proof A under model ------------------------------------------------------


def _neighbors(edges, unsupported=()):
    return {"root": {"element_id": "r"}, "edges": edges, "semantic_status": "complete",
            "unsupported_predicates": list(unsupported)}


def _coverage(contracts):
    return {"requirement": {"element_id": "r"}, "evidence_contracts": contracts,
            "unsupported_predicates": [], "gaps": [], "status": "covered",
            "semantic_status": "complete"}


EDGE = {"predicate": "hasRelevantEvidenceContract", "target": "ec-1"}


def test_mcp_model_proof_a_accepts_resolved_range():
    mcp.require_resolved_evidence_state(_neighbors([EDGE]), _coverage([{"element_id": "ec-1"}]))


@pytest.mark.parametrize("neighbors,coverage,match", [
    (_neighbors([]), _coverage([{"element_id": "ec-1"}]), "no hasRelevantEvidenceContract edge"),
    (_neighbors([EDGE], unsupported=[{"predicate": "hasRelevantEvidenceContract",
                                      "authority_state": "blocked"}]),
     _coverage([{"element_id": "ec-1"}]), "still reports"),
    (_neighbors([EDGE]), _coverage([]), "evidence_contracts"),
    (_neighbors([EDGE]), {**_coverage([{"element_id": "ec-1"}]),
                          "requirement": {"element_id": "other"}}, "subject-coherent"),
])
def test_mcp_model_proof_a_refuses(neighbors, coverage, match):
    with pytest.raises(RuntimeError, match=match):
        mcp.require_resolved_evidence_state(neighbors, coverage)


def test_mcp_proof_a_dispatch_by_authority(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp, "_require_blocked_evidence_state", lambda n, c: calls.append("blocked"))
    monkeypatch.setattr(mcp, "require_resolved_evidence_state", lambda n, c: calls.append("resolved"))
    mcp.require_proof_a({}, {}, "legacy")
    mcp.require_proof_a({}, {}, "o3")
    mcp.require_proof_a({}, {}, "model")
    assert calls == ["blocked", "blocked", "resolved"]


def test_mcp_server_arguments_carry_model_bundle(tmp_path):
    args = mcp.server_authority_arguments(authority="model", bundle_path=None, bundle_id=None,
                                          composition=None,
                                          model_bundle_path=tmp_path / "mab.json",
                                          model_bundle_id=MAB_ID)
    assert args == ["--semantic-authority", "model",
                    "--model-authority-bundle", str(tmp_path / "mab.json"),
                    "--model-authority-bundle-id", MAB_ID]


# -- product-line scope: contract from the selected runtime -----------------------


def test_scope_contract_identity_from_selected_runtime(monkeypatch, tmp_path):
    seen = {}
    identity = SimpleNamespace(name="model-identity")

    def build(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(contract=SimpleNamespace(identity=identity)), None

    from de4sdv.semantic import entry_authority

    monkeypatch.setattr(entry_authority, "build_entry_semantic_runtime", build)
    got = scope.selected_contract_identity(
        api_url="u", binding_path=tmp_path / "b.json", git_commit="c" * 40,
        authority="model", model_bundle_path="/m.json", model_bundle_id=MAB_ID)
    assert got is identity
    assert seen["authority"] == "model" and seen["model_bundle_id"] == MAB_ID
    assert seen["environ"] == {}


def test_scope_legacy_default_keeps_authored_contract(monkeypatch, tmp_path):
    from de4sdv.semantic import entry_authority

    monkeypatch.setattr(entry_authority, "build_entry_semantic_runtime",
                        lambda **kwargs: pytest.fail("legacy must not build a runtime"))
    got = scope.selected_contract_identity(api_url="u", binding_path=tmp_path / "b",
                                           git_commit="c" * 40)
    from de4sdv.semantic.kernel_contract import KernelContract

    assert got == KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml").identity
