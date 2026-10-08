"""O4 definition-candidate loader — fail-closed offline pair consumption.

Tests written first (TDD). Synthetic fixtures cover every rejection rule
(missing artifact, malformed JSON, schema drift, identity-set mismatch,
duplicates, binding-pair mismatch, echo mismatch, digest shape, frozen O3
identity overlap); the real repository pair loads through the existing
binding + regeneration validators, and a tamper probe on the committed
projection artifact is refused and restored.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from de4sdv.semantic.definition_candidate import (
    DefinitionCandidate,
    DefinitionCandidateError,
    load_definition_candidate,
)
from de4sdv.semantic.definition_projection import PROFILE_SCHEMA, PROJECTION_SCHEMA

O4_DIR = "docs/method-conformance/o4"
PROJECTION_NAME = "definition-projection.json"
PROFILE_NAME = "definition-profile.json"


# ---------------------------------------------------------------------------
# Fixture builders (synthetic pair, never the real repository artifacts)
# ---------------------------------------------------------------------------


def _binding(source_revision: str = "a" * 40, bound_inputs: dict | None = None) -> dict:
    return {
        "source_revision": source_revision,
        "bound_inputs": bound_inputs
        if bound_inputs is not None
        else {"model/x.sysml": "sha256:" + "b" * 64},
    }


def _row(identity: str, *, declaration: str | None = None, file: str = "model/x.sysml") -> dict:
    declaration = declaration or f"part def {identity}"
    return {
        "identity": identity,
        "semantic_kind": "class",
        "wave": "W2",
        "definition": {
            "documentation": f" {identity} definition text. ",
            "documentation_witness": {
                "source_file": file,
                "declaration": declaration,
                "doc_count": 1,
            },
            "documentation_observation": "normalized-exact",
            "semantic_text_equivalence": None,
        },
        "grounding": {
            "kernel_binding_contract": {"source_file": file, "declaration": declaration}
        },
        "support": "vocabulary-only",
        "traversal": False,
        "api_identity": "unclaimed",
    }


def _entry(identity: str, *, declaration: str | None = None, file: str = "model/x.sysml") -> dict:
    declaration = declaration or f"part def {identity}"
    return {
        "profile_identity": f"{PROFILE_SCHEMA}#{identity}",
        "for_concept": identity,
        "representation_class": "part-definition",
        "binding_contract_echo": {
            "source_file": file,
            "declaration": declaration,
            "api_metaclass": "PartDefinition",
        },
        "witness_forms": [
            "ownedRelationship -> OwningMembership -> Documentation "
            "(definition documentation, authored source order)"
        ],
    }


def _projection(identities, binding: dict | None = None, rows=None) -> dict:
    return {
        "schema": PROJECTION_SCHEMA,
        "status": "admitted",
        "warning": "vocabulary-only, no traversal, no runtime read, no authority retirement",
        "binding": binding if binding is not None else _binding(),
        "scope": {
            "admission": "fixture",
            "admitted": sorted(identities),
            "note": "fixture",
        },
        "rows": rows if rows is not None else [_row(identity) for identity in identities],
    }


def _profile(identities, binding: dict | None = None, entries=None) -> dict:
    return {
        "schema": PROFILE_SCHEMA,
        "status": "admitted",
        "warning": "vocabulary-only, no traversal, no runtime read, no authority retirement",
        "binding": binding if binding is not None else _binding(),
        "entries": entries if entries is not None else [_entry(identity) for identity in identities],
    }


def _write_pair(tmp_path: Path, projection: dict, profile: dict) -> Path:
    target = tmp_path / O4_DIR
    target.mkdir(parents=True, exist_ok=True)
    (target / PROJECTION_NAME).write_text(json.dumps(projection), encoding="utf-8")
    (target / PROFILE_NAME).write_text(json.dumps(profile), encoding="utf-8")
    return tmp_path


def _load(tmp_path: Path) -> DefinitionCandidate:
    from unittest.mock import patch

    with patch("de4sdv.semantic.authority_inventory.validate_source_binding", return_value=[]), patch(
        "de4sdv.semantic.definition_projection.run_check_errors", return_value=[]
    ):
        return load_definition_candidate(tmp_path)


def test_candidate_nested_state_cannot_be_mutated(tmp_path):
    _write_pair(tmp_path, _projection(["Assumption"]), _profile(["Assumption"]))
    candidate = _load(tmp_path)
    with pytest.raises(TypeError):
        candidate.row_for("Assumption")["definition"]["documentation"] = "forged"
    with pytest.raises(TypeError):
        candidate.entries[0]["binding_contract_echo"]["declaration"] = "forged"
    with pytest.raises(TypeError):
        candidate.bound_inputs["model/x.sysml"] = "forged"


def test_public_loader_has_no_verification_bypass(tmp_path):
    with pytest.raises(TypeError, match="verify_repository"):
        load_definition_candidate(tmp_path, verify_repository=False)


def test_loaded_snapshot_must_match_validated_documents():
    from unittest.mock import patch
    from de4sdv.semantic import definition_candidate as dc

    original = dc._load_document
    reads = 0

    def altered_initial_read(*args):
        nonlocal reads
        document = original(*args)
        reads += 1
        if reads == 1:
            document["rows"][0]["definition"]["documentation"] = "unvalidated snapshot"
        return document

    with patch.object(dc, "_load_document", side_effect=altered_initial_read):
        with pytest.raises(DefinitionCandidateError, match="changed during validation"):
            load_definition_candidate(REPO_ROOT)


def test_candidate_has_no_mutable_instance_dictionary(tmp_path):
    _write_pair(tmp_path, _projection(["Assumption"]), _profile(["Assumption"]))
    assert not hasattr(_load(tmp_path), "__dict__")


# ---------------------------------------------------------------------------
# 1. Shape and presence
# ---------------------------------------------------------------------------


def test_missing_projection_artifact_fails_closed(tmp_path):
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    assert PROJECTION_NAME in str(excinfo.value)


def test_missing_profile_artifact_fails_closed(tmp_path):
    _write_pair(tmp_path, _projection(["Assumption"]), _profile(["Assumption"]))
    (tmp_path / O4_DIR / PROFILE_NAME).unlink()
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    assert PROFILE_NAME in str(excinfo.value)


def test_malformed_json_fails_closed(tmp_path):
    target = tmp_path / O4_DIR
    target.mkdir(parents=True)
    (target / PROJECTION_NAME).write_text("{not json", encoding="utf-8")
    (target / PROFILE_NAME).write_text(json.dumps(_profile(["Assumption"])), encoding="utf-8")
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    assert "malformed" in str(excinfo.value)


def test_schema_drift_fails_closed(tmp_path):
    projection = _projection(["Assumption"])
    projection["schema"] = PROJECTION_SCHEMA + "-next"
    _write_pair(tmp_path, projection, _profile(["Assumption"]))
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    assert "schema" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 2. Valid pair loads (offline)
# ---------------------------------------------------------------------------


def test_valid_synthetic_pair_loads(tmp_path):
    identities = ["DeferredProductLineScope", "Assumption"]
    _write_pair(tmp_path, _projection(identities), _profile(identities))
    candidate = _load(tmp_path)
    assert candidate.identities == ("Assumption", "DeferredProductLineScope")
    assert candidate.source_revision == "a" * 40
    row = candidate.row_for("Assumption")
    assert row["support"] == "vocabulary-only"
    assert row["grounding"]["kernel_binding_contract"]["declaration"] == "part def Assumption"
    entry = candidate.entry_for("Assumption")
    assert entry["binding_contract_echo"]["api_metaclass"] == "PartDefinition"
    assert entry["representation_class"] == "part-definition"
    with pytest.raises(DefinitionCandidateError):
        candidate.row_for("NotAdmitted")


# ---------------------------------------------------------------------------
# 3. Pair consistency: missing, duplicate, mismatched entries
# ---------------------------------------------------------------------------


def test_missing_entry_fails_closed(tmp_path):
    projection = _projection(["Assumption", "DeferredProductLineScope"])
    profile = _profile(["Assumption", "DeferredProductLineScope"])
    profile["entries"] = profile["entries"][:1]
    _write_pair(tmp_path, projection, profile)
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    message = str(excinfo.value)
    assert "DeferredProductLineScope" in message
    assert "entry" in message


def test_duplicate_row_identity_fails_closed(tmp_path):
    rows = [_row("Assumption"), _row("Assumption")]
    projection = _projection(["Assumption"], rows=rows)
    _write_pair(tmp_path, projection, _profile(["Assumption"]))
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    assert "duplicate" in str(excinfo.value)


def test_duplicate_entry_identity_fails_closed(tmp_path):
    entries = [_entry("Assumption"), _entry("Assumption")]
    projection = _projection(["Assumption"])
    profile = _profile(["Assumption"], entries=entries)
    _write_pair(tmp_path, projection, profile)
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    assert "duplicate" in str(excinfo.value)


def test_scope_admitted_drift_fails_closed(tmp_path):
    projection = _projection(["Assumption"])
    projection["scope"]["admitted"] = ["Assumption", "Ghost"]
    _write_pair(tmp_path, projection, _profile(["Assumption"]))
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    assert "Ghost" in str(excinfo.value)


def test_binding_pair_mismatch_fails_closed(tmp_path):
    projection = _projection(["Assumption"], binding=_binding(source_revision="a" * 40))
    profile = _profile(["Assumption"], binding=_binding(source_revision="c" * 40))
    _write_pair(tmp_path, projection, profile)
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    assert "binding" in str(excinfo.value)


def test_bound_input_digest_shape_fails_closed(tmp_path):
    binding = _binding(bound_inputs={"model/x.sysml": "not-a-digest"})
    _write_pair(tmp_path, _projection(["Assumption"], binding=binding),
                _profile(["Assumption"], binding=binding))
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    assert "digest" in str(excinfo.value)


@pytest.mark.parametrize("field", ["wave", "documentation_observation"])
@pytest.mark.parametrize("value", [[], {}])
def test_unhashable_row_labels_use_candidate_error(tmp_path, field, value):
    projection = _projection(["Assumption"])
    row = projection["rows"][0]
    target = row["definition"] if field == "documentation_observation" else row
    target[field] = value
    _write_pair(tmp_path, projection, _profile(["Assumption"]))
    with pytest.raises(DefinitionCandidateError, match=field):
        _load(tmp_path)


@pytest.mark.parametrize("grounding", [None, [], 42, False, "invalid"])
def test_malformed_grounding_uses_candidate_error(tmp_path, grounding):
    projection = _projection(["Assumption"])
    projection["rows"][0]["grounding"] = grounding
    _write_pair(tmp_path, projection, _profile(["Assumption"]))
    with pytest.raises(DefinitionCandidateError, match="grounding must be a mapping"):
        _load(tmp_path)


def test_kernel_binding_echo_mismatch_fails_closed(tmp_path):
    projection = _projection(["Assumption"])
    profile = _profile(["Assumption"], entries=[_entry("Assumption", declaration="part def Other")])
    _write_pair(tmp_path, projection, profile)
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    assert "Assumption" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 4. Frozen O3 identity overlap
# ---------------------------------------------------------------------------


def test_frozen_o2_chain_identity_overlap_fails_closed(tmp_path):
    identities = ["Assumption", "VerificationCase"]
    _write_pair(tmp_path, _projection(identities), _profile(identities))
    with pytest.raises(DefinitionCandidateError) as excinfo:
        _load(tmp_path)
    message = str(excinfo.value)
    assert "VerificationCase" in message
    assert "frozen O2-chain" in message


# ---------------------------------------------------------------------------
# 5. Real repository artifact load (existing validators executed)
# ---------------------------------------------------------------------------


def test_real_repository_pair_loads_through_existing_validators():
    from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES as MIGRATED_IDENTITIES

    committed = json.loads(
        (REPO_ROOT / O4_DIR / PROJECTION_NAME).read_text(encoding="utf-8")
    )
    candidate = load_definition_candidate(REPO_ROOT)
    assert len(candidate.identities) == 22
    assert candidate.identities == tuple(committed["scope"]["admitted"])
    assert len(candidate.rows) == len(candidate.entries) == 22
    assert candidate.source_revision == committed["binding"]["source_revision"]
    assert candidate.bound_inputs == committed["binding"]["bound_inputs"]
    assert not set(candidate.identities) & set(MIGRATED_IDENTITIES)
    for identity in candidate.identities:
        row = candidate.row_for(identity)
        entry = candidate.entry_for(identity)
        assert row["grounding"]["kernel_binding_contract"] == {
            "source_file": entry["binding_contract_echo"]["source_file"],
            "declaration": entry["binding_contract_echo"]["declaration"],
        }
        assert row["definition"]["documentation"].strip()


def test_tampered_committed_projection_is_refused_and_restored():
    path = REPO_ROOT / O4_DIR / PROJECTION_NAME
    original = path.read_text(encoding="utf-8")
    needle = '" A stated condition treated as true'
    assert original.count(needle) == 1
    try:
        path.write_text(
            original.replace(needle, '" A stated condition treated as true (tampered)', 1),
            encoding="utf-8",
        )
        with pytest.raises(DefinitionCandidateError) as excinfo:
            load_definition_candidate(REPO_ROOT)
        assert PROJECTION_NAME in str(excinfo.value)
    finally:
        path.write_text(original, encoding="utf-8")
    assert path.read_text(encoding="utf-8") == original
    load_definition_candidate(REPO_ROOT)


# ---------------------------------------------------------------------------
# 6. Runtime independence
# ---------------------------------------------------------------------------


def test_candidate_loader_is_never_referenced_by_runtime_modules():
    """The runtime never imports or loads the candidate loader/provider.

    Only the model-authority construction path (definition_migration) loads
    the verified pair; the query surfaces never import, load or name the
    candidate modules themselves.
    """
    runtime_modules = (
        "de4sdv/semantic/query.py",
        "de4sdv/semantic/traversal.py",
        "de4sdv/semantic/impact.py",
        "de4sdv/semantic/mcp_server.py",
        "de4sdv/semantic/api_binding.py",
        "de4sdv/semantic/kernel_binding_index.py",
    )
    forbidden = (
        "from .definition_candidate import",
        "from de4sdv.semantic.definition_candidate import",
        "import definition_candidate",
        "definition_candidate import",
        "definition_candidate_provider",
        "definition_candidate.py",
    )
    for relative in runtime_modules:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, (relative, needle)
