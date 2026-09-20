"""Vocabulary-relationship definition carriers: governed, fail-closed, prepared.

The machinery defines ONE reusable carrier representation for reviewed
vocabulary-only relationships (``recordsGap``, ``recordsAssumption``,
``addressesConcern``, ``selectedViewpoint``, ``producesView``): a model-resident
carrier declaration whose owned documentation carries the reviewed definition,
typed ends carrying domain/range, a generated Projection representation, an
optional API-representation profile entry, and NO executable traversal claim.

No admission is active in this preparation state: the five candidates await
the method-owner definition acceptance. Until then every admitted entry is
refused for a missing acceptance reference, and the module only proves the
mechanism end-to-end on synthetic fixtures.
"""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _model(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "textual-notation-of-model" / "packages" / "methods" / "de4sdv").mkdir(parents=True)
    (root / "docs" / "method-conformance" / "o4").mkdir(parents=True)
    (root / "textual-notation-of-model" / "packages" / "methods" / "de4sdv" / "de4sdv_method_context.sysml").write_text(
        "package DE4SDV_MethodContext {\n"
        "  part def EngineeringIncrement {\n"
        "    doc /* A bounded DE4SDV work package. */\n"
        "  }\n"
        "  part def IncrementGap {\n"
        "    doc /* A known missing trace link or unproven claim. */\n"
        "  }\n"
        "  connection def RecordsGap {\n"
        "    end gap : IncrementGap;\n"
        "    end recordingIncrement : EngineeringIncrement;\n"
        "    doc /* Engineering increment explicitly records an unresolved engineering/evidence gap. */\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    return root


_DEFINITIONS = {
    "recordsGap": ("Engineering increment explicitly records an unresolved engineering/evidence gap.", "Gap"),
    "recordsAssumption": ("Engineering increment explicitly records an assumption relevant to its bounded work.", "Assumption"),
    "addressesConcern": ("Engineering increment records an explicitly reviewed concern within its scope; no automatic concern satisfaction.", "Concern"),
    "selectedViewpoint": ("Engineering increment records a viewpoint explicitly selected for its review questions.", "Viewpoint"),
    "producesView": ("Engineering increment identifies a view artifact produced as an increment deliverable.", "View"),
    "hasStakeholder": ("Engineering increment records a stakeholder role explicitly engaged by its review scope.", "Stakeholder"),
}


def _document(**overrides) -> dict:
    entry = {
        "identity": "recordsGap",
        "carrier": {
            "file": "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml",
            "declaration": "connection def RecordsGap",
        },
        "ends": {
            "domain": {"feature": "recordingIncrement", "type": "EngineeringIncrement"},
            "range": {"feature": "gap", "type": "IncrementGap"},
        },
        "accepted_ref": "owner-decision packet W4 vocabulary definitions (2026-09-20)",
    }
    document = {
        "schema": "de4sdv.o4-vocabulary-carriers/v1",
        "expected_candidates": sorted(_DEFINITIONS),
        "excluded": [{"identity": "hasStakeholder", "reason": "decision-11 gates its range"}],
        "admitted": [entry],
    }
    for key, value in overrides.items():
        document[key] = value
    return document


def _review() -> dict:
    rows = []
    for identity in sorted(_DEFINITIONS):
        definition, range_name = _DEFINITIONS[identity]
        rows.append({
            "identity": identity,
            "kind": "relationship",
            "target": {
                "disposition": "KEEP_VOCABULARY_ONLY",
                "authority": "DE4SDV model-resident method vocabulary",
                "definition": definition,
                "domain": "EngineeringIncrement",
                "range": range_name,
                "direction": "not-applicable",
                "semantic_strength": "not-declared",
                "projection_required": True,
                "api_profile_required": True,
                "traversal_required": False,
                "runtime_support_target": "vocabulary-only",
            },
        })
    return {"rows": rows}


def _build(root: Path, document: dict, review: dict):
    from de4sdv.semantic.vocabulary_carrier import build_carrier_outputs

    return build_carrier_outputs(root, document, review)


def test_positive_admitted_carrier_emits_separate_outputs(tmp_path):
    root = _model(tmp_path)
    outputs = _build(root, _document(), _review())
    assert [row["identity"] for row in outputs["projection_rows"]] == ["recordsGap"]
    row = outputs["projection_rows"][0]
    assert row["definition"] == "Engineering increment explicitly records an unresolved engineering/evidence gap."
    assert row["domain"] == {"identity": "EngineeringIncrement", "type": "EngineeringIncrement"}
    assert row["range"] == {"identity": "Gap", "type": "IncrementGap"}
    assert row["support"] == "vocabulary-only"
    assert row["traversal"] is False
    entry = outputs["profile_entries"][0]
    assert entry["identity"] == "recordsGap"
    assert "sysml_mapping" not in entry
    assert "sysml_mapping" not in row


def test_missing_acceptance_ref_is_refused(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["accepted_ref"] = ""
    with pytest.raises(CarrierError, match="acceptance"):
        _build(root, document, _review())


def test_definition_must_match_the_reviewed_text_exactly(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    file = root / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
    file.write_text(file.read_text().replace("unresolved engineering/evidence gap", "unresolved engineering gap"))
    with pytest.raises(CarrierError, match="definition"):
        _build(root, _document(), _review())


def test_sysml_mapping_is_rejected(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["sysml_mapping"] = {"strategy": "dependency"}
    with pytest.raises(CarrierError, match="sysml_mapping"):
        _build(root, document, _review())


def test_unknown_identity_is_rejected(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["identity"] = "hasEvidence"
    with pytest.raises(CarrierError, match="candidate family"):
        _build(root, document, _review())


def test_end_type_must_exist_or_be_marked_library(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["ends"]["range"]["type"] = "TotallyUnknownType"
    with pytest.raises(CarrierError, match="declaration"):
        _build(root, document, _review())


def test_review_flag_drift_refuses_generation(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    review = _review()
    for row in review["rows"]:
        if row["identity"] == "recordsGap":
            row["target"]["traversal_required"] = True
    with pytest.raises(CarrierError, match="review"):
        _build(root, _document(), review)


def test_committed_carrier_document_is_pending_and_matches_review():
    from de4sdv.semantic.vocabulary_carrier import (
        CARRIERS_PATH, load_carriers, run_check_errors,
    )

    document = load_carriers(REPO_ROOT / CARRIERS_PATH)
    assert document["admitted"] == []
    assert sorted(document["expected_candidates"]) == [
        "addressesConcern", "hasStakeholder", "producesView", "recordsAssumption",
        "recordsGap", "selectedViewpoint",
    ]
    excluded = {item["identity"]: item["reason"] for item in document["excluded"]}
    assert "decision-11" in excluded["hasStakeholder"]
    assert run_check_errors(REPO_ROOT) == []


def test_excluded_candidate_cannot_be_admitted(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    entry = dict(document["admitted"][0])
    entry["identity"] = "hasStakeholder"
    document["admitted"].append(entry)
    with pytest.raises(CarrierError, match="excluded from admission"):
        _build(root, document, _review())


def test_check_errors_fail_closed_on_mutated_candidate_family(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import (
        CarrierError, load_carriers, validate_candidate_family,
    )

    document = load_carriers(REPO_ROOT / "docs/method-conformance/o4/vocabulary-carriers.yaml")
    import copy

    mutated = copy.deepcopy(document)
    mutated["expected_candidates"].remove("recordsGap")
    with pytest.raises(CarrierError, match="candidate family"):
        validate_candidate_family(mutated, _review())

def test_carrier_module_is_never_imported_by_the_runtime_path():
    forbidden = {
        "query.py", "runtime.py", "traversal.py", "mcp_server.py",
        "validation.py", "impact.py", "api_binding.py", "kernel_binding_index.py",
    }
    semantic = REPO_ROOT / "de4sdv" / "semantic"
    for name in sorted(forbidden):
        path = semantic / name
        if not path.is_file():
            continue
        assert "vocabulary_carrier" not in path.read_text(encoding="utf-8"), name
