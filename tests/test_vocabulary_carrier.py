"""Vocabulary-relationship definition carriers: governed, fail-closed, admitted.

The machinery defines ONE reusable carrier representation for reviewed
vocabulary-only relationships (``recordsGap``, ``recordsAssumption``,
``addressesConcern``, ``selectedViewpoint``, ``producesView``): a model-resident
carrier declaration whose owned documentation carries the reviewed definition,
typed ends carrying domain/range, a generated Projection representation, an
API-representation profile entry, and NO executable traversal claim.

The five admissions close as engineering review evidence (the bounded
acceptance review document carries the machine-checked marker); a free-text
acceptance reference or a personal owner-approval claim is refused.
``hasStakeholder`` stays excluded by decision-11.
"""
import json
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

_ACCEPTANCE_DOC = "docs/semantic-relationships/increment-relationship-acceptance-review.md"
_CARRIER_FILE = (
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_vocabulary_carriers.sysml"
)


_DEFINITIONS = {
    "recordsGap": ("Engineering increment explicitly records an unresolved engineering/evidence gap.", "Gap"),
    "recordsAssumption": ("Engineering increment explicitly records an assumption relevant to its bounded work.", "Assumption"),
    "addressesConcern": ("Engineering increment records an explicitly reviewed concern within its scope; no automatic concern satisfaction.", "Concern"),
    "selectedViewpoint": ("Engineering increment records a viewpoint explicitly selected for its review questions.", "Viewpoint"),
    "producesView": ("Engineering increment identifies a view artifact produced as an increment deliverable.", "View"),
    "hasStakeholder": ("Engineering increment records a stakeholder role explicitly engaged by its review scope.", "Stakeholder"),
}

_SYSML = """package DE4SDV_MethodVocabularyCarriers {
  private import DE4SDV_MethodContext::*;
  private import Views::*;
  part def EngineeringIncrement;
  part def IncrementGap;
  abstract concern def IncrementConcern;
  abstract viewpoint def IncrementViewpoint;
  connection def RecordsGap {
    end gap : IncrementGap;
    end recordingIncrement : EngineeringIncrement;
    doc /* Engineering increment explicitly records an unresolved engineering/evidence gap. */
    doc /* Claim boundary: explicit recording only. */
  }
}
"""


_SYNTHETIC_INDEX = "synthetic-kernel-index.json"


@pytest.fixture(autouse=True)
def _synthetic_kernel_index(monkeypatch):
    """Synthetic repositories carry their kernel index as a test file; the
    real checkout uses the model-built contract (``_ontology_kernel_index``)."""
    from de4sdv.semantic import vocabulary_carrier

    real = vocabulary_carrier._ontology_kernel_index

    def index(root):
        path = Path(root) / _SYNTHETIC_INDEX
        if path.is_file():
            return {name: (tuple(pin) if pin else None)
                    for name, pin in json.loads(path.read_text(encoding="utf-8")).items()}
        return real(root)

    monkeypatch.setattr(vocabulary_carrier, "_ontology_kernel_index", index)


def _model(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    carrier = root / _CARRIER_FILE
    carrier.parent.mkdir(parents=True)
    carrier.write_text(_SYSML, encoding="utf-8")
    docs = root / "docs" / "semantic-relationships"
    docs.mkdir(parents=True)
    acceptance = root / _ACCEPTANCE_DOC
    acceptance.write_text(
        "# acceptance\n\nStatus: accepted-as-engineering-review-evidence\n\n"
        + "| identity | reviewed definition | domain | range |\n"
        + "| --- | --- | --- | --- |\n"
        + "\n".join(
            f"| {identity} | definition | EngineeringIncrement | {range_name} |"
            for identity, (_, range_name) in sorted(_DEFINITIONS.items())
        )
        + "\n",
        encoding="utf-8",
    )
    # Synthetic kernel index (identity -> [file, declaration] or null for
    # native/external semantics): stands in for the model-built contract's
    # class mappings of this synthetic repository (O4 Wave C2; no ontology file).
    (root / _SYNTHETIC_INDEX).write_text(json.dumps({
        "EngineeringIncrement": [_CARRIER_FILE, "part def EngineeringIncrement"],
        "Gap": [_CARRIER_FILE, "part def IncrementGap"],
        "Assumption": [_CARRIER_FILE, "part def IncrementAssumption"],
        "Concern": None,
        "Viewpoint": None,
        "View": None,
    }), encoding="utf-8")
    return root


def _document(**overrides) -> dict:
    entry = {
        "identity": "recordsGap",
        "carrier": {"file": _CARRIER_FILE, "declaration": "connection def RecordsGap"},
        "ends": {
            "domain": {"feature": "recordingIncrement", "type": "EngineeringIncrement"},
            "range": {"feature": "gap", "type": "IncrementGap"},
        },
        "accepted_ref": f"{_ACCEPTANCE_DOC}#recordsGap",
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


# ---------------------------------------------------------------------------
# Positive: the real committed admissions
# ---------------------------------------------------------------------------


def test_real_repo_admits_the_five_reviewed_carriers_and_excludes_hasstakeholder():
    from de4sdv.semantic.vocabulary_carrier import (
        CARRIERS_PATH, build_carrier_outputs, load_carriers, load_review,
    )

    document = load_carriers(REPO_ROOT / CARRIERS_PATH)
    assert sorted(document["expected_candidates"]) == [
        "addressesConcern", "hasStakeholder", "producesView", "recordsAssumption",
        "recordsGap", "selectedViewpoint",
    ]
    excluded = {item["identity"]: item["reason"] for item in document["excluded"]}
    assert "decision-11" in excluded["hasStakeholder"]
    outputs = build_carrier_outputs(REPO_ROOT, document, load_review(REPO_ROOT))
    assert outputs["admitted"] == [
        "addressesConcern", "producesView", "recordsAssumption",
        "recordsGap", "selectedViewpoint",
    ]
    assert [row["identity"] for row in outputs["projection_rows"]] == outputs["admitted"]
    assert [entry["identity"] for entry in outputs["profile_entries"]] == outputs["admitted"]
    for row in outputs["projection_rows"]:
        assert row["support"] == "vocabulary-only"
        assert row["traversal"] is False
        assert row["domain"]["identity"] == "EngineeringIncrement"
        assert "sysml_mapping" not in row
        assert row["accepted_ref"].startswith(_ACCEPTANCE_DOC)
    produces_view = next(
        row for row in outputs["projection_rows"] if row["identity"] == "producesView"
    )
    assert produces_view["range"] == {"identity": "View", "type": "View"}


def test_committed_check_reports_pending_generation_or_passes():
    from de4sdv.semantic.vocabulary_carrier import run_check_errors

    errors = run_check_errors(REPO_ROOT)
    assert all("carrier artifacts not generated yet" in error for error in errors)


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


# ---------------------------------------------------------------------------
# This cleanup replaces retired live Git-binding tests with current-input generation.
# Semantic/refusal tests below remain unchanged; fixtures are synthetic only.
# ---------------------------------------------------------------------------


def _input_repo(tmp_path: Path) -> Path:
    root = _model(tmp_path)
    review_path = root / "de4sdv/semantic/contract-data/ontology-review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(_review()), encoding="utf-8")
    (root / "de4sdv/semantic/contract-data/increment-relationship-admission.yaml").write_text(
        yaml.safe_dump(_document()), encoding="utf-8"
    )
    return root


def _refuse_git(*args, **kwargs):
    pytest.fail("live construction/check must not invoke Git")


def test_carrier_cli_constructs_and_checks_without_git(tmp_path, monkeypatch):
    from de4sdv.semantic.vocabulary_carrier import (
        PROFILE_CARRIER_PATH, PROJECTION_CARRIER_PATH,
        build_artifact_pair,
    )
    from scripts import generate_vocabulary_carriers as cli

    root = _input_repo(tmp_path)
    monkeypatch.setattr(cli, "ROOT", root)
    monkeypatch.setattr(subprocess, "run", _refuse_git)
    assert cli.main([]) == 0
    paths = (PROJECTION_CARRIER_PATH, PROFILE_CARRIER_PATH)
    emitted = [(root / path).read_bytes() for path in paths]
    artifacts = build_artifact_pair(root)
    assert all("binding" not in document for document in artifacts.values())
    assert artifacts["projection"]["rows"][0]["traversal"] is False
    assert artifacts["profile"]["entries"][0]["identity"] == "recordsGap"
    assert cli.main(["--check"]) == 0
    with pytest.raises(SystemExit) as rejected:
        cli.main(["--source-revision", "0" * 40])
    assert rejected.value.code == 2
    assert emitted == [(root / path).read_bytes() for path in paths]
    assert artifacts == build_artifact_pair(root, source_revision="1" * 40)


def test_generation_accepts_uncommitted_governance_inputs(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import build_artifact_pair

    root = _input_repo(tmp_path)
    first = build_artifact_pair(root)
    (root / _ACCEPTANCE_DOC).write_text(
        (root / _ACCEPTANCE_DOC).read_text(encoding="utf-8") + "later edit\n",
        encoding="utf-8",
    )
    # A non-semantic acceptance-document edit requires no input commit and
    # changes no payload. Marker and identity checks still run at build time.
    assert build_artifact_pair(root) == first


def test_stale_artifacts_are_refused(tmp_path):
    from de4sdv.semantic.native_grounding_projection import canonical_json
    from de4sdv.semantic.vocabulary_carrier import (
        PROFILE_CARRIER_PATH, PROJECTION_CARRIER_PATH,
        build_artifact_pair, run_check_errors,
    )

    root = _input_repo(tmp_path)
    artifacts = build_artifact_pair(root)
    (root / PROJECTION_CARRIER_PATH).write_text(
        canonical_json(artifacts["projection"]), encoding="utf-8"
    )
    (root / PROFILE_CARRIER_PATH).write_text(
        canonical_json(artifacts["profile"]), encoding="utf-8"
    )
    committed = json.loads((root / PROJECTION_CARRIER_PATH).read_text(encoding="utf-8"))
    committed["rows"][0]["traversal"] = True
    (root / PROJECTION_CARRIER_PATH).write_text(
        canonical_json(committed), encoding="utf-8"
    )
    errors = run_check_errors(root)
    assert errors and any(PROJECTION_CARRIER_PATH in error for error in errors)


# ---------------------------------------------------------------------------
# Negative: acceptance, definitions, flags, exclusions, traversal overloading
# ---------------------------------------------------------------------------


def test_missing_acceptance_ref_is_refused(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["accepted_ref"] = ""
    with pytest.raises(CarrierError, match="acceptance"):
        _build(root, document, _review())


def test_free_text_acceptance_reference_is_refused(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["accepted_ref"] = "owner-decision packet W4 (2026-09-20)"
    with pytest.raises(CarrierError, match="governance document"):
        _build(root, document, _review())


def test_acceptance_reference_must_resolve_to_a_real_document(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["accepted_ref"] = "docs/semantic-relationships/does-not-exist.md"
    with pytest.raises(CarrierError, match="does not resolve"):
        _build(root, document, _review())


def test_acceptance_reference_parent_traversal_is_refused(tmp_path):
    # Reviewer-demonstrated fail-open: `docs/../X` escaped the acceptance root
    # while still satisfying the naive prefix check. The refusal is structural:
    # the planted file EXISTS, so only the traversal rule can reject it.
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    planted = root / "tests" / "planted.md"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "Status: accepted-as-engineering-review-evidence\n| recordsGap | x |\n",
        encoding="utf-8",
    )
    document = _document()
    document["admitted"][0]["accepted_ref"] = "docs/../tests/planted.md#recordsGap"
    with pytest.raises(CarrierError, match="parent traversal"):
        _build(root, document, _review())
    document = _document()
    document["admitted"][0]["accepted_ref"] = (
        "docs/semantic-relationships/../../tests/planted.md#recordsGap"
    )
    with pytest.raises(CarrierError, match="parent traversal"):
        _build(root, document, _review())


def test_acceptance_document_without_marker_is_refused(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    (root / _ACCEPTANCE_DOC).write_text("recordsGap: accepted, trust me\n", encoding="utf-8")
    with pytest.raises(CarrierError, match="marker"):
        _build(root, _document(), _review())


def test_acceptance_document_must_record_the_identity(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    (root / _ACCEPTANCE_DOC).write_text(
        "Status: accepted-as-engineering-review-evidence\nrecordsAssumption only\n",
        encoding="utf-8",
    )
    with pytest.raises(CarrierError, match="does not record this identity"):
        _build(root, _document(), _review())


def test_definition_must_match_the_reviewed_text_exactly(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    file = root / _CARRIER_FILE
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


def test_library_type_end_is_accepted_when_declared(tmp_path):
    # A native reviewed range identity with no repo-resident declaration may be
    # carried by a listed accepted-library type: producesView (range `View`)
    # with `View` listed in library_types.
    root = _model(tmp_path)
    carrier = root / _CARRIER_FILE
    carrier.write_text(
        carrier.read_text().replace(
            "connection def RecordsGap {",
            "connection def ProducesView {\n"
            "    end view : View;\n"
            "    end producingIncrement : EngineeringIncrement;\n"
            "    doc /* Engineering increment identifies a view artifact produced as an increment deliverable. */\n"
            "  }\n"
            "  connection def RecordsGap {",
        ),
        encoding="utf-8",
    )
    document = _document()
    document["admitted"][0]["identity"] = "producesView"
    document["admitted"][0]["carrier"]["declaration"] = "connection def ProducesView"
    document["admitted"][0]["ends"] = {
        "domain": {"feature": "producingIncrement", "type": "EngineeringIncrement"},
        "range": {"feature": "view", "type": "View"},
    }
    document["admitted"][0]["library_types"] = ["Views::View"]
    document["admitted"][0]["accepted_ref"] = (
        f"{_ACCEPTANCE_DOC}#producesView"
    )
    outputs = _build(root, document, _review())
    assert outputs["projection_rows"][0]["range"] == {"identity": "View", "type": "View"}


def test_review_flag_drift_refuses_generation(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    review = _review()
    for row in review["rows"]:
        if row["identity"] == "recordsGap":
            row["target"]["traversal_required"] = True
    with pytest.raises(CarrierError, match="review"):
        _build(root, _document(), review)


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

    document = load_carriers(REPO_ROOT / "de4sdv/semantic/contract-data/increment-relationship-admission.yaml")
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


# ---------------------------------------------------------------------------
# Identity binding: the reviewed identity is bound to the model declaration
# ---------------------------------------------------------------------------


def test_repo_resident_identity_rejects_a_foreign_end_type(tmp_path):
    # recordsGap's reviewed range identity `Gap` is ontology-mapped to
    # `part def IncrementGap`; pointing the end at another existing model
    # declaration must refuse, not silently re-type the range.
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["ends"]["range"]["type"] = "EngineeringIncrement"
    carrier = root / _CARRIER_FILE
    carrier.write_text(
        carrier.read_text().replace(
            "end gap : IncrementGap;", "end gap : EngineeringIncrement;"
        ),
        encoding="utf-8",
    )
    with pytest.raises(CarrierError, match="ontology-mapped declaration"):
        _build(root, document, _review())


def test_native_identity_needs_library_type_or_declaration_pin(tmp_path):
    # addressesConcern's reviewed range identity `Concern` is native: a bare
    # repo-resident declaration without an explicit pin must refuse.
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    carrier = root / _CARRIER_FILE
    carrier.write_text(
        carrier.read_text().replace(
            "connection def RecordsGap {",
            "connection def AddressesConcern {\n"
            "    end concern : IncrementConcern;\n"
            "    end reviewingIncrement : EngineeringIncrement;\n"
            "    doc /* Engineering increment records an explicitly reviewed concern within its scope; no automatic concern satisfaction. */\n"
            "  }\n"
            "  connection def RecordsGap {",
        ),
        encoding="utf-8",
    )
    document = _document()
    document["admitted"][0]["identity"] = "addressesConcern"
    document["admitted"][0]["carrier"]["declaration"] = "connection def AddressesConcern"
    document["admitted"][0]["ends"] = {
        "domain": {"feature": "reviewingIncrement", "type": "EngineeringIncrement"},
        "range": {"feature": "concern", "type": "IncrementConcern"},
    }
    document["admitted"][0]["accepted_ref"] = (
        f"{_ACCEPTANCE_DOC}#addressesConcern"
    )
    with pytest.raises(CarrierError, match="declaration pin"):
        _build(root, document, _review())


def test_declaration_pin_must_resolve_to_the_end_type(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    carrier = root / _CARRIER_FILE
    carrier.write_text(
        carrier.read_text().replace(
            "connection def RecordsGap {",
            "connection def AddressesConcern {\n"
            "    end concern : IncrementConcern;\n"
            "    end reviewingIncrement : EngineeringIncrement;\n"
            "    doc /* Engineering increment records an explicitly reviewed concern within its scope; no automatic concern satisfaction. */\n"
            "  }\n"
            "  connection def RecordsGap {",
        ),
        encoding="utf-8",
    )
    document = _document()
    document["admitted"][0]["identity"] = "addressesConcern"
    document["admitted"][0]["carrier"]["declaration"] = "connection def AddressesConcern"
    document["admitted"][0]["ends"] = {
        "domain": {"feature": "reviewingIncrement", "type": "EngineeringIncrement"},
        "range": {
            "feature": "concern",
            "type": "IncrementConcern",
            "declaration": {
                "file": "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml",
                "declaration": "concern def IncrementConcern",
            },
        },
    }
    document["admitted"][0]["accepted_ref"] = (
        f"{_ACCEPTANCE_DOC}#addressesConcern"
    )
    with pytest.raises(CarrierError, match="does not resolve to the end type"):
        _build(root, document, _review())


def test_declaration_pin_must_agree_with_the_ontology_mapping(tmp_path):
    # A pin that contradicts the ontology kernel mapping of a repo-resident
    # identity is refused even when it resolves.
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["ends"]["range"]["declaration"] = {
        "file": _CARRIER_FILE,
        "declaration": "part def IncrementGap",
    }
    with pytest.raises(CarrierError, match="ontology kernel mapping"):
        # Re-point the kernel mapping: the pin no longer agrees.
        index_path = root / _SYNTHETIC_INDEX
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["Gap"] = [_CARRIER_FILE, "part def EngineeringIncrement"]
        index_path.write_text(json.dumps(index), encoding="utf-8")
        _build(root, document, _review())


def test_type_cannot_be_both_model_declaration_and_library_type(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["library_types"] = ["Views::IncrementGap"]
    with pytest.raises(CarrierError, match="both a model declaration and a listed"):
        _build(root, document, _review())


def test_unqualified_library_type_is_refused(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["library_types"] = ["View"]
    with pytest.raises(CarrierError, match="package-qualified"):
        _build(root, document, _review())


def test_library_type_must_be_imported_by_the_carrier_file(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    carrier = root / _CARRIER_FILE
    carrier.write_text(
        carrier.read_text().replace("private import Views::*;\n", ""),
        encoding="utf-8",
    )
    # recordsGap's reviewed range identity is Gap (ontology-mapped), so build
    # the producesView row (native range `View`, imported simple end type) for
    # a clean import-check exercise.
    carrier.write_text(
        carrier.read_text().replace(
            "connection def RecordsGap {",
            "connection def ProducesView {\n"
            "    end view : View;\n"
            "    end producingIncrement : EngineeringIncrement;\n"
            "    doc /* Engineering increment identifies a view artifact produced as an increment deliverable. */\n"
            "  }\n"
            "  connection def RecordsGap {",
        ),
        encoding="utf-8",
    )
    document = _document()
    document["admitted"][0]["identity"] = "producesView"
    document["admitted"][0]["carrier"]["declaration"] = "connection def ProducesView"
    document["admitted"][0]["ends"] = {
        "domain": {"feature": "producingIncrement", "type": "EngineeringIncrement"},
        "range": {"feature": "view", "type": "View"},
    }
    document["admitted"][0]["library_types"] = ["Views::View"]
    document["admitted"][0]["accepted_ref"] = f"{_ACCEPTANCE_DOC}#producesView"
    with pytest.raises(CarrierError, match="not imported by the carrier file"):
        _build(root, document, _review())


def test_acceptance_fragment_must_equal_the_identity(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    document = _document()
    document["admitted"][0]["accepted_ref"] = f"{_ACCEPTANCE_DOC}#somethingElse"
    with pytest.raises(CarrierError, match="fragment must equal the identity"):
        _build(root, document, _review())


def test_acceptance_document_must_record_the_identity_as_a_table_row(tmp_path):
    from de4sdv.semantic.vocabulary_carrier import CarrierError

    root = _model(tmp_path)
    acceptance = root / _ACCEPTANCE_DOC
    acceptance.write_text(
        "# acceptance\n\nStatus: accepted-as-engineering-review-evidence\n"
        "\nrecordsGap is mentioned in prose only.\n",
        encoding="utf-8",
    )
    with pytest.raises(CarrierError, match="does not record this identity as a table row"):
        _build(root, document := _document(), _review())


@pytest.mark.parametrize("kind", ["projection", "profile"])
@pytest.mark.parametrize("mutation", ["payload", "malformed", "retired-binding", "crlf"])
def test_carrier_check_refuses_noncanonical_bytes(tmp_path, monkeypatch, kind, mutation):
    from de4sdv.semantic.native_grounding_projection import canonical_json
    from de4sdv.semantic.vocabulary_carrier import (
        PROFILE_CARRIER_PATH, PROJECTION_CARRIER_PATH, run_check_errors,
    )
    from scripts import generate_vocabulary_carriers as cli

    root = _input_repo(tmp_path)
    monkeypatch.setattr(cli, "ROOT", root)
    monkeypatch.setattr(subprocess, "run", _refuse_git)
    assert cli.main([]) == 0
    relative = PROJECTION_CARRIER_PATH if kind == "projection" else PROFILE_CARRIER_PATH
    path = root / relative
    payload = path.read_bytes()
    document = json.loads(payload)
    if mutation == "payload":
        if kind == "projection":
            document["rows"][0]["traversal"] = True
        else:
            document["entries"][0]["mechanics"] = "unreviewed mechanics"
        changed = canonical_json(document).encode("utf-8")
    elif mutation == "malformed":
        changed = b"\xff not JSON"
    elif mutation == "retired-binding":
        document["binding"] = {"source_revision": "0" * 40}
        changed = canonical_json(document).encode("utf-8")
    else:
        changed = payload.replace(b"\n", b"\r\n")
    path.write_bytes(changed)
    before = [(root / name).read_bytes() for name in (
        PROJECTION_CARRIER_PATH, PROFILE_CARRIER_PATH,
    )]
    errors = run_check_errors(root)
    assert len(errors) == 1 and relative in errors[0]
    assert "differs from" in errors[0]
    assert cli.main(["--check"]) == 1
    assert before == [(root / name).read_bytes() for name in (
        PROJECTION_CARRIER_PATH, PROFILE_CARRIER_PATH,
    )]


@pytest.mark.parametrize("kind", ["projection", "profile"])
def test_carrier_missing_artifact_fails_closed_without_commit_advice(tmp_path, kind):
    from de4sdv.semantic.native_grounding_projection import canonical_json
    from de4sdv.semantic.vocabulary_carrier import (
        PROFILE_CARRIER_PATH, PROJECTION_CARRIER_PATH, run_check_errors,
    )
    from scripts import generate_vocabulary_carriers as cli

    root = _input_repo(tmp_path)
    artifacts = cli.generate(root)
    paths = {"projection": PROJECTION_CARRIER_PATH, "profile": PROFILE_CARRIER_PATH}
    for name, relative in paths.items():
        (root / relative).write_text(canonical_json(artifacts[name]), encoding="utf-8")
    (root / paths[kind]).unlink()
    errors = run_check_errors(root)
    assert len(errors) == 1 and paths[kind] in errors[0]
    assert "artifacts not generated yet" in errors[0]
    assert "no input commit required" in errors[0]
    assert "commit the admission" not in errors[0]
    assert not (root / paths[kind]).exists()


def test_carrier_current_definition_edit_requires_regeneration_not_a_commit(tmp_path, monkeypatch):
    from de4sdv.semantic.vocabulary_carrier import REVIEW_PATH, build_artifact_pair
    from scripts import generate_vocabulary_carriers as cli

    root = _input_repo(tmp_path)
    monkeypatch.setattr(cli, "ROOT", root)
    monkeypatch.setattr(subprocess, "run", _refuse_git)
    assert cli.main([]) == 0
    review_path = root / REVIEW_PATH
    review = json.loads(review_path.read_text(encoding="utf-8"))
    reviewed = next(row for row in review["rows"] if row["identity"] == "recordsGap")
    original = reviewed["target"]["definition"]
    changed = "Synthetic increment explicitly records a reviewed gap, without traversal."
    reviewed["target"]["definition"] = changed
    review_path.write_text(json.dumps(review), encoding="utf-8")
    carrier_path = root / _CARRIER_FILE
    carrier_path.write_text(
        carrier_path.read_text(encoding="utf-8").replace(original, changed),
        encoding="utf-8",
    )
    assert cli.main(["--check"]) == 1
    with pytest.raises(SystemExit) as rejected:
        cli.main(["--source-revision", "0" * 40])
    assert rejected.value.code == 2
    assert cli.main([]) == 0
    assert cli.main(["--check"]) == 0
    assert build_artifact_pair(root)["projection"]["rows"][0]["definition"] == changed


def test_carrier_generation_never_reads_its_own_outputs(monkeypatch):
    """Real class providers must not turn output recovery into a cycle."""
    from de4sdv.semantic.vocabulary_carrier import (
        PROFILE_CARRIER_PATH, PROJECTION_CARRIER_PATH, build_artifact_pair,
    )

    paths = {
        "projection": REPO_ROOT / PROJECTION_CARRIER_PATH,
        "profile": REPO_ROOT / PROFILE_CARRIER_PATH,
    }
    expected = {name: json.loads(path.read_bytes()) for name, path in paths.items()}
    assert expected["projection"]["rows"] and expected["profile"]["entries"]
    blocked = {path.resolve() for path in paths.values()}
    original_bytes, original_text = Path.read_bytes, Path.read_text

    def read_bytes(path):
        assert path.resolve() not in blocked, "construction read its own generated output"
        return original_bytes(path)

    def read_text(path, *args, **kwargs):
        assert path.resolve() not in blocked, "construction read its own generated output"
        return original_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setattr(Path, "read_text", read_text)
    assert build_artifact_pair(REPO_ROOT) == expected


def test_carrier_class_sources_preserve_complete_runtime_class_mappings():
    from de4sdv.semantic.kernel_contract import KernelContract, KernelFileMapping
    from de4sdv.semantic.vocabulary_carrier import _ontology_kernel_index

    contract = KernelContract.from_layers(REPO_ROOT)
    assert contract.classes
    expected = {}
    for identity in contract.classes:
        mapping = contract.mapping(identity)
        expected[identity] = ((mapping.file, mapping.declaration)
                              if isinstance(mapping, KernelFileMapping) else None)
    assert _ontology_kernel_index(REPO_ROOT) == expected


@pytest.mark.parametrize("kind", ["projection", "profile"])
@pytest.mark.parametrize("mode", ["absent", "malformed", "empty-population"])
def test_real_carrier_cli_repairs_its_own_outputs_without_index_stubs(monkeypatch, kind, mode):
    """Overlay output faults only; all class providers and model reads are real."""
    from de4sdv.semantic.vocabulary_carrier import PROFILE_CARRIER_PATH, PROJECTION_CARRIER_PATH
    from scripts import generate_vocabulary_carriers as cli

    paths = {"projection": REPO_ROOT / PROJECTION_CARRIER_PATH,
             "profile": REPO_ROOT / PROFILE_CARRIER_PATH}
    before = {path: path.read_bytes() for path in paths.values()}
    assert all(json.loads(raw)["rows" if path == paths["projection"] else "entries"]
               for path, raw in before.items())
    target = paths[kind]
    original_read, original_file = Path.read_bytes, Path.is_file
    writes = {}

    def read_bytes(path):
        if path != target:
            return original_read(path)
        if mode == "absent":
            raise FileNotFoundError(str(path))
        if mode == "malformed":
            return b"not a JSON artifact"
        document = json.loads(before[path])
        document["rows" if kind == "projection" else "entries"] = []
        return json.dumps(document).encode()

    def is_file(path):
        return False if path == target and mode == "absent" else original_file(path)

    def write_text(path, text, *args, **kwargs):
        assert path in before, "unexpected CLI write"
        writes[path] = text.encode("utf-8")
        return len(text)

    with monkeypatch.context() as scoped:
        scoped.setattr(cli, "ROOT", REPO_ROOT)
        scoped.setattr(Path, "read_bytes", read_bytes)
        scoped.setattr(Path, "is_file", is_file)
        scoped.setattr(Path, "write_text", write_text)
        assert cli.main(["--check"]) == 1
        assert not writes
        assert cli.main([]) == 0
        assert writes == before
    assert {path: path.read_bytes() for path in before} == before
