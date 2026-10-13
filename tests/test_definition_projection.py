"""First definition admission: scope, model-owned docs and mechanics.

This cleanup retires live revision containment and copied-definition parity. Independent
literal artifact oracles and strict synthetic current-source gate tests live in
``test_commit_independent_definition_artifacts.py``. Scope, grounding,
non-claims, runtime independence and repository wiring remain covered here.
Frozen source bindings and historical reviews are not changed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = "de4sdv/semantic/contract-data/class-definition-admission.yaml"
MODULE_PATH = "de4sdv/semantic/definition_projection.py"
GENERATOR_PATH = "scripts/generate_definition_projection.py"
#: The two shared modules the generation path EXECUTES (proved by the
#: executed-path audit) and therefore must bind as generation software.
AUTHORITY_INVENTORY_PATH = "de4sdv/semantic/authority_inventory.py"
PROJECTION_O2P_PATH = "de4sdv/semantic/projection_o2p.py"
BOUND_PROGRAM_INPUTS = (
    MODULE_PATH,
    GENERATOR_PATH,
    AUTHORITY_INVENTORY_PATH,
    PROJECTION_O2P_PATH,
)
_MODEL_FILE = (
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
)
#: The governed model files carrying the admitted declarations of the real
#: manifest (all four participate in the real bound-input set).
_MODEL_FILES = (
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml",
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml",
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_operational_context.sysml",
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml",
)

ADMITTED_ROWS = (
    "Assumption",
    "BlockedRealizationBranchRecord",
    "DeferredProductLineScope",
    "EngineeringIncrement",
    "FeatureIncrement",
    "Gap",
    "IncrementEngineeringQuestion",
    "IncrementLifecycleDecision",
    "LogicalToSoftwareSignalMappingRecord",
    "MemberProduct",
    "MissingRealizationRecord",
    "Need",
    "NeedsRequirementsIncrement",
    "ProblemStatement",
    "ProductLine",
    "ProductLineCharacteristic",
    "RegulatoryConstraint",
    "Requirement",
    "Scenario",
    "SignalMappingDisposition",
    "SystemLayer",
    "SystemToSoftwareSignalMappingCandidate",
)

#: Layer-B reviewed-decision field names that must never leak into generated
#: semantic rows (identical to the O1 governance guard used by the other
#: projection suites).
O1_GOVERNANCE_FIELDS = (
    "authority_current",
    "authority_target",
    "evidence_state",
    "adoption_status",
    "transition_gate",
    "conditional_target",
    "disposition",
    "confidence",
    "stage",
    "unknowns",
    "required_evidence",
    "exact_fit_decision",
)

_FIXTURE_MANIFEST = {
    "schema": "de4sdv.o4-definition-admission/v1",
    "status": "admitted",
    "warning": "fixture",
    "admitted": [
        {
            "identity": "FixtureAlpha",
            "semantic_kind": "class",
            "wave": "W2",
            "stage": "fixture",
            "declaration": {"file": _MODEL_FILE, "declaration": "part def FixtureAlpha"},
            "evidence_state": "repository-evidenced",
            "authority_current": "legacy-yaml",
            "required_runtime_support_target": (
                "runtime-queryable (post-migration, exact-revision evidence required)"
            ),
        },
        {
            "identity": "FixtureBeta",
            "semantic_kind": "class",
            "wave": "W2",
            "stage": "fixture",
            "declaration": {"file": _MODEL_FILE, "declaration": "part def FixtureBeta"},
            "evidence_state": "repository-evidenced",
            "authority_current": "legacy-yaml",
            "required_runtime_support_target": (
                "runtime-queryable (post-migration, exact-revision evidence required)"
            ),
        },
    ],
}

_FIXTURE_SYSML = """package FixtureDefinitions {
  part def FixtureAlpha {
    doc /* An exact fixture definition for alpha. */
  }
  part def FixtureBeta {
    doc /* A differing fixture definition for beta that carries extra words. */
  }
}
"""


# ---------------------------------------------------------------------------
# 1. The real committed admission
# ---------------------------------------------------------------------------


def test_manifest_scope_is_exactly_the_admitted_family():
    from de4sdv.semantic.definition_projection import load_document

    document = load_document(REPO_ROOT)
    admitted = [row["identity"] for row in document["admitted"]]
    assert sorted(admitted) == list(ADMITTED_ROWS)
    assert len(admitted) == 22


def test_family_invariant_from_canonical_governance():
    """The admitted rows are disjoint from every other projected layer and
    from the frozen identities."""
    from de4sdv.semantic.definition_projection import load_document
    from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES as MIGRATED_IDENTITIES

    other = set()
    v1 = json.loads(
        (REPO_ROOT / "de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.json").read_text()
    )
    other |= {row["identity"] for row in v1["concepts"]}
    v11 = json.loads(
        (REPO_ROOT / "de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.1.json").read_text()
    )
    other |= {row["identity"] for row in v11["concepts"] + v11["predicates"]}
    v12 = json.loads(
        (REPO_ROOT / "de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.2.json").read_text()
    )
    other |= {row["identity"] for row in v12["predicates"]}
    o2p = json.loads(
        (
            REPO_ROOT / "de4sdv/semantic/contract-data/native-grounding-projection.json"
        ).read_text()
    )
    other |= {row["identity"] for row in o2p["rows"]}
    carriers = json.loads(
        (
            REPO_ROOT / "de4sdv/semantic/contract-data/increment-relationship-projection.json"
        ).read_text()
    )
    other |= {row["identity"] for row in carriers["rows"]}

    admitted = {row["identity"] for row in load_document(REPO_ROOT)["admitted"]}
    assert admitted == set(ADMITTED_ROWS)
    assert not (admitted & other)
    # The frozen O3 thirteen are structurally excluded from this layer.
    assert not (set(ADMITTED_ROWS) & set(MIGRATED_IDENTITIES))


def test_every_admitted_row_resolves_to_authoritative_model_documentation():
    from de4sdv.semantic.definition_projection import build_outputs, load_document

    document = load_document(REPO_ROOT)
    outputs = build_outputs(REPO_ROOT, document)
    assert len(outputs["projection_rows"]) == 22
    assert {row["identity"] for row in outputs["projection_rows"]} == set(ADMITTED_ROWS)
    for row in outputs["projection_rows"]:
        definition = row["definition"]
        witness = definition["documentation_witness"]
        file_text = (REPO_ROOT / witness["source_file"]).read_text(encoding="utf-8")
        assert witness["declaration"] in file_text, row["identity"]
        assert witness["doc_count"] >= 1, row["identity"]
        assert definition["documentation"].strip(), row["identity"]
        assert definition["documentation_observation"] == "model-owned-documentation"
        assert "semantic_text_equivalence" not in definition
    for admitted in document["admitted"]:
        assert not {"reviewed_definition", "expected_documentation_observation", "semantic_text_equivalence"} & set(admitted)

def test_generated_rows_stay_vocabulary_only_and_free_of_governance_fields():
    from de4sdv.semantic.definition_projection import (
        API_METACLASSES,
        PROFILE_SCHEMA,
        build_outputs,
        load_document,
    )

    outputs = build_outputs(REPO_ROOT, load_document(REPO_ROOT))
    assert len(outputs["projection_rows"]) == 22
    assert len(outputs["profile_entries"]) == 22
    for row in outputs["projection_rows"]:
        assert row["support"] == "vocabulary-only"
        assert row["traversal"] is False
        assert row["api_identity"] == "unclaimed"
        serialized = json.dumps(row)
        for field in O1_GOVERNANCE_FIELDS:
            assert f'"{field}"' not in serialized, (row["identity"], field)
    for entry in outputs["profile_entries"]:
        assert entry["profile_identity"] == f"{PROFILE_SCHEMA}#{entry['for_concept']}"
        assert entry["binding_contract_echo"]["api_metaclass"] in set(API_METACLASSES.values())
        serialized = json.dumps(entry)
        for field in O1_GOVERNANCE_FIELDS:
            assert f'"{field}"' not in serialized, (entry["for_concept"], field)
    assert [row["identity"] for row in outputs["projection_rows"]] == sorted(
        entry["for_concept"] for entry in outputs["profile_entries"]
    )


def test_excluded_section_records_the_non_admitted_rows():
    manifest = yaml.safe_load((REPO_ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    excluded = {entry["identity"]: entry["reason"] for entry in manifest["excluded"]}
    # Scenario joined the admitted set (batch-1 amendment) and is no longer an
    # exclusion; the remaining considered-not-admitted rows keep their reasons.
    assert "Scenario" not in excluded
    for identity in ("ArchitectureDecisionRecord", "Baseline", "IncrementSize"):
        assert identity in excluded, identity
        assert excluded[identity].strip(), identity


# ---------------------------------------------------------------------------
# 2. Manifest fail-closed negatives
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "definition-admission.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


def _mutated(**changes) -> dict:
    document = json.loads(json.dumps(_FIXTURE_MANIFEST))
    document["admitted"][0].update(changes)
    return document


def test_unknown_row_key_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = _mutated(syaml_mapping={"file": "x"})
    with pytest.raises(DefinitionAdmissionError, match="unknown keys"):
        load_admission(_write_manifest(tmp_path, document))


def test_retired_reviewed_definition_oracle_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = _mutated(reviewed_definition="A second text authority.")
    with pytest.raises(DefinitionAdmissionError, match="unknown keys"):
        load_admission(_write_manifest(tmp_path, document))

@pytest.mark.parametrize("key", ["expected_documentation_observation", "semantic_text_equivalence"])
def test_retired_live_parity_metadata_is_refused(tmp_path, key):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = _mutated(**{key: "reviewed-equivalent"})
    with pytest.raises(DefinitionAdmissionError, match="unknown keys"):
        load_admission(_write_manifest(tmp_path, document))

def test_duplicate_identity_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = json.loads(json.dumps(_FIXTURE_MANIFEST))
    document["admitted"].append(dict(document["admitted"][0]))
    with pytest.raises(DefinitionAdmissionError, match="duplicate"):
        load_admission(_write_manifest(tmp_path, document))


def test_empty_admitted_list_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = json.loads(json.dumps(_FIXTURE_MANIFEST))
    document["admitted"] = []
    with pytest.raises(DefinitionAdmissionError, match="non-empty"):
        load_admission(_write_manifest(tmp_path, document))


def test_missing_required_key_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = json.loads(json.dumps(_FIXTURE_MANIFEST))
    del document["admitted"][0]["required_runtime_support_target"]
    with pytest.raises(DefinitionAdmissionError, match="missing keys"):
        load_admission(_write_manifest(tmp_path, document))


# ---------------------------------------------------------------------------
# 3. Current-source fixture generation and refusal behaviour
# ---------------------------------------------------------------------------


def _fixture_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for relative, text in ((_MODEL_FILE, _FIXTURE_SYSML), (MANIFEST_PATH, yaml.safe_dump(_FIXTURE_MANIFEST))):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root

def test_generation_from_synthetic_sources_preserves_projection_profile_separation(tmp_path):
    from de4sdv.semantic.definition_projection import build_artifact_pair

    pair = build_artifact_pair(_fixture_repo(tmp_path))
    assert "binding" not in pair["projection"] and "binding" not in pair["profile"]
    rows = pair["projection"]["rows"]
    assert [row["identity"] for row in rows] == ["FixtureAlpha", "FixtureBeta"]
    assert [row["definition"]["documentation"] for row in rows] == [
        " An exact fixture definition for alpha. ",
        " A differing fixture definition for beta that carries extra words. ",
    ]
    assert [entry["for_concept"] for entry in pair["profile"]["entries"]] == ["FixtureAlpha", "FixtureBeta"]

def test_generation_accepts_source_changes_without_git_metadata(tmp_path):
    from de4sdv.semantic.definition_projection import build_artifact_pair

    root = _fixture_repo(tmp_path)
    model = root / _MODEL_FILE
    model.write_text(model.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    pair = build_artifact_pair(root)
    assert len(pair["projection"]["rows"]) == 2
    assert "binding" not in pair["projection"]

def test_module_declares_the_executed_shared_modules_as_bound_inputs():
    """The real bound-input set is the four executed program inputs + models."""
    from de4sdv.semantic import definition_projection

    assert definition_projection.AUTHORITY_INVENTORY_PATH == AUTHORITY_INVENTORY_PATH
    assert definition_projection.PROJECTION_O2P_PATH == PROJECTION_O2P_PATH
    outputs = definition_projection.build_outputs(
        REPO_ROOT, definition_projection.load_document(REPO_ROOT)
    )
    bound = definition_projection.collect_bound_inputs(REPO_ROOT, outputs)
    assert set(bound) == {
        MANIFEST_PATH,
        MODULE_PATH,
        GENERATOR_PATH,
        AUTHORITY_INVENTORY_PATH,
        PROJECTION_O2P_PATH,
        *_MODEL_FILES,
    }
    for relative in (AUTHORITY_INVENTORY_PATH, PROJECTION_O2P_PATH):
        assert (REPO_ROOT / relative).is_file(), relative
        assert bound[relative].startswith("sha256:")


# This cleanup retires the live shared-module Git-containment test. Independent literal
# gate tests live in test_commit_independent_definition_artifacts.py; frozen
# binding tests in other suites are unchanged.

def test_model_documentation_change_is_projected_without_manifest_text_edit(tmp_path):
    from de4sdv.semantic.definition_projection import build_artifact_pair

    root = _fixture_repo(tmp_path)
    model = root / _MODEL_FILE
    model.write_text(model.read_text(encoding="utf-8").replace(
        "An exact fixture definition for alpha.", "A substantially reworded fixture definition for alpha."), encoding="utf-8")
    pair = build_artifact_pair(root)
    assert pair["projection"]["rows"][0]["definition"]["documentation"] == " A substantially reworded fixture definition for alpha. "
    assert pair["projection"]["rows"][0]["definition"]["documentation_observation"] == "model-owned-documentation"

def test_missing_declaration_file_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import (
        DefinitionAdmissionError,
        build_artifact_pair,
    )

    root = _fixture_repo(tmp_path)
    (root / _MODEL_FILE).unlink()
    with pytest.raises(DefinitionAdmissionError):
        build_artifact_pair(root)


def test_declaration_without_documentation_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import (
        DefinitionAdmissionError,
        build_outputs,
        load_document,
    )

    root = _fixture_repo(tmp_path)
    model = root / _MODEL_FILE
    model.write_text(
        "package FixtureDefinitions {\n"
        "  part def FixtureAlpha;\n"
        "  part def FixtureBeta {\n"
        "    doc /* A differing fixture definition for beta that carries extra words. */\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    with pytest.raises(DefinitionAdmissionError):
        build_outputs(root, load_document(root))


def test_decoy_o1_artifacts_cannot_change_the_output(tmp_path):
    from de4sdv.semantic.definition_projection import build_outputs, load_document
    from de4sdv.semantic.projection_o2p import canonical_json

    root = _fixture_repo(tmp_path)
    baseline = canonical_json(build_outputs(root, load_document(root)))
    decoy = root / "docs/method-conformance/o1/semantic-authority-inventory.json"
    decoy.parent.mkdir(parents=True, exist_ok=True)
    decoy.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "identity": "FixtureGamma",
                        "observed": {},
                        "reviewed": {"stage": "o2+ safe-set 1 (grounding + projection)"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert canonical_json(build_outputs(root, load_document(root))) == baseline


# ---------------------------------------------------------------------------
# 4. Strict live gate: committed artifact bytes equal current-source regeneration
# ---------------------------------------------------------------------------


def test_committed_artifacts_match_regeneration():
    from de4sdv.semantic.definition_projection import PROFILE_PATH, PROJECTION_PATH, run_check_errors

    assert (REPO_ROOT / PROJECTION_PATH).is_file()
    assert (REPO_ROOT / PROFILE_PATH).is_file()
    assert run_check_errors(REPO_ROOT) == []

# ---------------------------------------------------------------------------
# 5. Runtime independence and repository wiring
# ---------------------------------------------------------------------------


def test_definition_projection_is_never_imported_by_the_runtime_path():
    runtime_modules = (
        "de4sdv/semantic/query.py",
        "de4sdv/semantic/traversal.py",
        "de4sdv/semantic/impact.py",
        "de4sdv/semantic/mcp_server.py",
        "de4sdv/semantic/api_binding.py",
        "de4sdv/semantic/kernel_binding_index.py",
    )
    for relative in runtime_modules:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "definition_projection" not in text, relative
        assert "definition-projection" not in text, relative
        assert "definition-admission" not in text, relative
    # The model-authority runtime reads the generated pair as a data layer
    # (O4 Wave C2: runtime.py was deleted); it never imports the generator.
    for relative in ("de4sdv/semantic/model_authority_runtime.py",
                     "de4sdv/semantic/model_contract.py"):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "definition_projection" not in text, relative
        assert "definition-admission" not in text, relative


def _passing_gate_mocks():
    """All other aggregate gates mocked passing through shared controls."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_retired_semantic_authority import _passing_gate_mocks as shared

    return shared()


def test_check_repo_actually_invokes_the_definition_admission_gate():
    from unittest import mock

    from de4sdv.semantic import definition_projection
    from scripts import check_repo

    calls: list[int] = []

    def spy(root):
        calls.append(1)
        return []

    mocks = _passing_gate_mocks()
    for m in mocks:
        m.start()
    try:
        with mock.patch.object(definition_projection, "run_check_errors", side_effect=spy):
            result = check_repo.main()
    finally:
        for m in mocks:
            m.stop()
    assert calls, "check_repo did not invoke the definition-admission gate"
    assert result == 0


def test_check_repo_fails_when_the_definition_admission_gate_fails():
    from unittest import mock

    from de4sdv.semantic import definition_projection
    from scripts import check_repo

    mocks = _passing_gate_mocks()
    for m in mocks:
        m.start()
    try:
        with mock.patch.object(
            definition_projection,
            "run_check_errors",
            return_value=["sentinel definition-admission error"],
        ):
            assert check_repo.main() == 1
    finally:
        for m in mocks:
            m.stop()