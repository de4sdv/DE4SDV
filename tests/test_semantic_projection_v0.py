"""Tests for the DE4SDV Semantic Projection v0 / API Representation Profile v0
(K slice: derivesRequirementFromNeed).

Covers the R3 review requirements: validated-revision binding, contract
identity recomputation, honest O0/O1 support state, semantic compatibility
gate, and determinism.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.revisions import KernelElementBinding
from de4sdv.semantic.projection import (
    PROFILE_SCHEMA,
    PROJECTION_SCHEMA,
    RevisionIdentity,
    assert_profile_compatible,
    build_projection,
    build_representation_profile,
    contract_identity_from_file,
)
from de4sdv.semantic.kernel_binding_index import KernelBindingIndex

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_derivation_connection_traversal import (  # noqa: E402
    DEF_DERIV_ID,
    NEED_DEF_ID,
    REQ_DEF_ID,
    _binding_index,
    _contract,
    _default_binding_entries,
    _elements,
)

ROOT = Path(__file__).resolve().parents[1]
REVISION = RevisionIdentity(
    git_commit="0" * 40,
    sysml_project_id="proj-0001",
    sysml_commit_id="commit-0001",
)


def definition_claim() -> str:
    """The claim boundary exactly as carried in the fixture definition doc."""
    return (
        "Design-input provenance: the derivedRequirement originates from the "
        "stakeholder need. Provenance/traceability semantics only: neither "
        "satisfaction nor logical implication between the connected usages "
        "is claimed; verification, evidence, and acceptance claims are out "
        "of scope."
    )


def _projection_binding_index() -> KernelBindingIndex:
    # _default_binding_entries already carries Requirement/Need (R1 lineages)
    # and the library Derivation definition grounding used by this module.
    return _binding_index(list(_default_binding_entries()))


def _by_id() -> dict[str, dict]:
    return {item["@id"]: item for item in _elements()}


def _build(**kwargs) -> dict:
    return build_projection(
        _contract(),
        _projection_binding_index(),
        REVISION,
        _by_id(),
        repository_root=ROOT,
        **kwargs,
    )


def _build_profile(**kwargs) -> dict:
    return build_representation_profile(
        _contract(),
        _projection_binding_index(),
        REVISION,
        _by_id(),
        repository_root=ROOT,
        **kwargs,
    )


def test_projection_row_binds_revision_and_validated_groundings() -> None:
    projection = _build()
    assert projection["schema"] == PROJECTION_SCHEMA
    assert projection["revision_binding"]["git_commit"] == REVISION.git_commit
    predicate = projection["predicate"]
    assert predicate["identity"] == "derivesRequirementFromNeed"
    assert predicate["domain"] == "Requirement"
    assert predicate["range"] == "Need"
    assert predicate["semantic_strength"] == "derivation"
    generated_from = projection["revision_binding"]["generated_from"]
    assert set(generated_from["model_definitions"]) == {
        REQ_DEF_ID,
        NEED_DEF_ID,
        DEF_DERIV_ID,
    }
    grounding = generated_from["model_semantic_authority"]
    assert grounding["connection_definition"] == "DerivesFromNeed"
    assert grounding["element_id"] == DEF_DERIV_ID
    assert grounding["need_role"] == "need"
    assert grounding["requirement_role"] == "derivedRequirement"
    assert grounding["need_end_type"] == "StakeholderNeedCandidate"
    assert grounding["requirement_end_type"] == "RequirementCandidate"
    assert "ingestion-validated" in grounding["authority_provenance"]


def test_projection_binds_recomputed_contract_identity() -> None:
    """The contract identity is recomputed from the actual file, not trusted."""
    projection = _build()
    identity = projection["revision_binding"]["generated_from"][
        "ontology_contract_parity_oracle"
    ]
    expected = contract_identity_from_file(ROOT)
    assert identity == expected
    assert identity["sha256"] == expected["sha256"]


def test_projection_support_state_is_honest_without_closure_evidence() -> None:
    """O0/O1 honesty: without exact-candidate closure evidence the generated
    projection reports vocabulary-only, never supported (UG-06/UG-24)."""
    assert _build()["predicate"]["support_state"] == "vocabulary-only"
    assert (
        _build(witness_closure_verified=True)["predicate"]["support_state"]
        == "supported"
    )


def test_projection_definition_comes_from_model_doc_not_yaml() -> None:
    """Plan v1.1 §16 Q2: the projection's semantic fields originate from the
    validated model (the definition's ingested doc), never from the YAML
    oracle. Editing the YAML definition must NOT change the projection, and
    a model doc missing the claim boundary must fail generation."""
    import copy

    import de4sdv.semantic.projection as projection_module

    definition = _build()["predicate"]["definition"]
    assert definition.startswith("Design-input provenance")
    assert "neither satisfaction nor logical implication" in definition

    # YAML drift in definition text does NOT leak into the projection.
    contract = _contract()
    contract.relationships["derivesRequirementFromNeed"]["definition"] = (
        "TAMPERED definition text that must never reach the projection."
    )
    tampered = build_projection(
        contract,
        _projection_binding_index(),
        REVISION,
        _by_id(),
        repository_root=ROOT,
    )
    assert tampered["predicate"]["definition"] == definition

    # A definition element without the claim-boundary doc fails closed.
    by_id = _by_id()
    del by_id["def-doc"]
    with pytest.raises(ValueError, match="claim boundary"):
        build_projection(
            _contract(),
            _projection_binding_index(),
            REVISION,
            by_id,
            repository_root=ROOT,
        )


def test_projection_forbids_representation_mechanics() -> None:
    projection = _build()
    text = json.dumps(projection)
    for forbidden in ("property_path", "serializer", "dispatch", "transport"):
        assert forbidden not in text.lower()


def test_projection_deterministic_for_identical_inputs() -> None:
    """UG-23: same semantic inputs produce the same canonical payload."""
    first = _build()
    second = _build()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_projection_rejects_unverified_revision_labels() -> None:
    """R3: arbitrary caller-supplied revision labels are rejected."""
    with pytest.raises(ValueError, match="40-hex"):
        build_projection(
            _contract(),
            _projection_binding_index(),
            RevisionIdentity("unrelated", "other-project", "other-commit"),
            _by_id(),
            repository_root=ROOT,
        )


def test_projection_fails_closed_without_marker_binding() -> None:
    """UG-24: missing validated grounding blocks generation."""
    with pytest.raises(IdentityNotFoundError):
        build_projection(
            _contract(),
            _binding_index([]),
            REVISION,
            _by_id(),
            repository_root=ROOT,
        )


def test_profile_carries_mechanics_and_echoes_projection_meaning() -> None:
    profile = _build_profile()
    assert profile["schema"] == PROFILE_SCHEMA
    assert profile["for_predicate"] == "derivesRequirementFromNeed"
    witness = profile["witness"]
    assert witness["api_metaclass"] == "ConnectionUsage"
    # Mechanics are derived from the model authority.
    assert witness["property_paths"]["need_end"] == "need"
    assert witness["property_paths"]["requirement_end"] == "derivedRequirement"
    assert witness["query_direction"] == "inverse"
    # Meaning fields are echoes of the projection row, not independent values.
    assert profile["domain_from_projection"] == "Requirement"
    assert profile["range_from_projection"] == "Need"
    assert profile["semantic_strength_from_projection"] == "derivation"
    assert profile["claim_boundary_from_projection"] == definition_claim()
    assert (
        profile["model_revision_binding"]["generated_from"]
        is not None
    )
    # Support state stays on the projection predicate (the profile echoes
    # mechanics; support is a projection-level honesty field).
    projection_predicate_support = _build()["predicate"]["support_state"]
    assert projection_predicate_support == "vocabulary-only"


def test_profile_compatibility_gate_rejects_mapping_contradiction() -> None:
    """UG-25: a profile must not contradict the executable mapping."""
    contract = _contract()
    profile = _build_profile()
    assert_profile_compatible(contract, profile)  # passes unmodified
    mutated = json.loads(json.dumps(profile))
    mutated["witness"]["property_paths"]["need_end"] = "someOtherRole"
    with pytest.raises(ValueError, match="contradicts"):
        assert_profile_compatible(contract, mutated)
    mutated2 = json.loads(json.dumps(profile))
    mutated2["witness"]["query_direction"] = "forward"
    with pytest.raises(ValueError, match="contradicts"):
        assert_profile_compatible(contract, mutated2)


def test_profile_mechanics_follow_model_authority_and_oracle_drift_fails() -> None:
    """R3 (v1.1 §16): profile mechanics derive from the MODEL authority. The
    YAML oracle may not redefine them: a tampered oracle mapping now FAILS
    the parity gate at generation instead of being echoed into the profile."""
    contract = _contract()
    contract.relationships["derivesRequirementFromNeed"]["sysml_mapping"][
        "need_role"
    ] = "someOtherRole"
    with pytest.raises(ValueError, match="parity oracle drift"):
        build_representation_profile(
            contract,
            _projection_binding_index(),
            REVISION,
            _by_id(),
            repository_root=ROOT,
        )


def test_profile_without_projection_inputs_fails_closed() -> None:
    with pytest.raises(IdentityNotFoundError):
        build_representation_profile(
            _contract(),
            _binding_index([]),
            REVISION,
            _by_id(),
            repository_root=ROOT,
        )
