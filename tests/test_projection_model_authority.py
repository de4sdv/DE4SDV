"""Regression tests: model-resident semantic authority for the K projection.

Requirement (plan v1.1 §16): the projection's semantic fields must originate
from validated model-resident evidence — never from Python literals, never
from the authored YAML oracle. These tests prove the authority direction:

* tampering the model changes the projection (no silent Python fallback);
* YAML drift fails parity but cannot redefine the projection;
* representation-profile mechanics cannot redefine model semantics;
* the superseded standard-Derivation representation text is gone from the
  kernel source.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.projection import (
    RevisionIdentity,
    assert_profile_compatible,
    build_projection,
    build_representation_profile,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_derivation_implied_graph import (  # noqa: E402
    DEF_END_NEED,
    DEF_ID,
    _base_elements,
    _binding_index,
    _contract,
)

ROOT = Path(__file__).resolve().parents[1]
KERNEL_FILE = (
    ROOT
    / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
)
REVISION = RevisionIdentity("0" * 40, "proj-0001", "commit-0001")


def _by_id(elements: list[dict]) -> dict[str, dict]:
    return {element["@id"]: element for element in elements}


def _build(elements: list[dict], contract: KernelContract | None = None) -> dict:
    return build_projection(
        contract or _contract(),
        _binding_index(),
        REVISION,
        _by_id(elements),
        repository_root=ROOT,
    )


def _doc_id(elements: list[dict]) -> str:
    for element in elements:
        if element["@id"] == "def-doc-graph":
            return "def-doc-graph"
    raise AssertionError("fixture has no definition doc")


def _retitle_doc(elements: list[dict], new_doc: str) -> list[dict]:
    """Replace the definition's ingested documentation (model text)."""
    mutated = copy.deepcopy(elements)
    for element in mutated:
        if element["@id"] == _doc_id(mutated):
            element["body"] = new_doc
    return mutated


NEW_DOC = (
    "Design-input provenance: the derivedRequirement originates from the "
    "stakeholder need. Native direction: need -> derivedRequirement. "
    "Claim strength: provenance-only (traceability only: no satisfaction, "
    "implication, verification, evidence, or acceptance claim)."
)


# ---------------------------------------------------------------------------
# 1. Model tampering cannot leave the projection at old Python values
# ---------------------------------------------------------------------------


def test_tampered_model_claim_strength_changes_the_projection() -> None:
    """With the oracle pair brought along, a model-only change propagates:
    the strength token and claim boundary are copied from the model text."""
    baseline = _build(_base_elements())
    assert baseline["predicate"]["semantic_strength"] == "derivation"

    elements = _retitle_doc(_base_elements(), NEW_DOC)
    contract = _contract()
    contract.relationships["derivesRequirementFromNeed"]["sysml_mapping"][
        "semantic_strength"
    ] = "provenance-only"
    # The pair invariant requires both rows to carry the same strength.
    contract.relationships["derivedRequirementsOfNeed"]["sysml_mapping"][
        "semantic_strength"
    ] = "provenance-only"
    projection = _build(elements, contract)

    assert projection["predicate"]["semantic_strength"] == "provenance-only"
    assert projection["predicate"]["semantic_strength"] != "derivation"
    assert projection["predicate"]["claim_boundary"].startswith("traceability only")


def test_model_tampering_alone_fails_parity_and_is_never_ignored() -> None:
    """A model-only contradiction cannot be silently absorbed: parity fails."""
    with pytest.raises(ValueError, match="parity oracle drift"):
        _build(_retitle_doc(_base_elements(), NEW_DOC))


def _reversed_end_order() -> list[dict]:
    elements = _base_elements()
    by_id = _by_id(elements)
    definition = by_id[DEF_ID]
    definition["ownedRelationship"] = list(
        reversed(definition["ownedRelationship"])
    )
    return elements


def test_model_only_end_order_change_cannot_pass_parity_silently() -> None:
    """The authored end order drives the native direction, so a model-only
    reorder contradicts the oracle's declared query direction and fails."""
    with pytest.raises(ValueError, match="query_direction"):
        _build(_reversed_end_order())


def test_tampered_end_order_flips_the_model_native_direction() -> None:
    """With the oracle PAIR brought along, the direction follows the MODEL."""
    contract = _contract()
    mapping = contract.relationships["derivesRequirementFromNeed"]["sysml_mapping"]
    mapping["query_direction"] = "forward"
    mapping["source_lineage_of"] = "Need"
    mapping["target_lineage_of"] = "Requirement"
    # Pair consistency: the companion traverses the same witness the other way.
    companion = contract.relationships["derivedRequirementsOfNeed"]["sysml_mapping"]
    companion["query_direction"] = "inverse"
    companion["source_lineage_of"] = "Requirement"
    companion["target_lineage_of"] = "Need"
    projection = _build(_reversed_end_order(), contract)
    authority = projection["revision_binding"]["generated_from"][
        "model_semantic_authority"
    ]
    assert authority["native_direction"] == "Requirement -> Need"
    # Canonical consumer direction is the predicate's own: Requirement -> Need,
    # which now equals the authored order, so traversal is forward.
    assert authority["canonical_direction"] == "Requirement -> Need"
    assert authority["query_direction"] == "forward"
    assert projection["predicate"]["query_direction"] == "forward"


def test_swapped_end_types_cannot_ground_domain_range() -> None:
    """Model ends typed against the wrong classes contradict the predicate
    identity's vocabulary names: generation fails instead of inventing
    domain/range."""
    from de4sdv.sysml_api.errors import IdentityNotFoundError

    elements = _base_elements()
    by_id = _by_id(elements)
    # Point the need end at the Requirement class and vice versa.
    by_id["def-end-need-typing"]["type"] = {"@id": "rd-graph-0002"}
    by_id["def-end-req-typing"]["type"] = {"@id": "nd-graph-0001"}
    with pytest.raises((IdentityNotFoundError, ValueError)):
        _build(elements)


def test_missing_model_claim_strength_fails_generation() -> None:
    """No Claim strength statement in the model: no projection."""
    doc = (
        "Design-input provenance: the derivedRequirement originates from the "
        "stakeholder need. Native direction: need -> derivedRequirement."
    )
    with pytest.raises(ValueError, match="claim strength"):
        _build(_retitle_doc(_base_elements(), doc))


def test_missing_end_definition_documentation_fails_generation() -> None:
    elements = _base_elements()
    elements = [e for e in elements if e["@id"] != "def-doc-graph"]
    with pytest.raises(ValueError, match="documentation"):
        _build(elements)


# ---------------------------------------------------------------------------
# 2. YAML drift fails parity but cannot redefine the projection
# ---------------------------------------------------------------------------


def test_yaml_domain_drift_fails_parity() -> None:
    contract = _contract()
    contract.relationships["derivesRequirementFromNeed"]["domain"] = "Need"
    with pytest.raises(ValueError, match="domain"):
        _build(_base_elements(), contract)


def test_yaml_cannot_redefine_projection_values() -> None:
    """Whatever the YAML says, matching model authority is what is published."""
    baseline = _build(_base_elements())["predicate"]
    contract = _contract()
    contract.relationships["derivesRequirementFromNeed"]["definition"] = (
        "TAMPERED oracle definition text that must never be published."
    )
    projection = _build(_base_elements(), contract)["predicate"]
    for field in ("definition", "domain", "range", "semantic_strength"):
        assert projection[field] == baseline[field]
    assert projection["claim_boundary"] == baseline["claim_boundary"]


def test_yaml_strength_drift_fails_parity() -> None:
    contract = _contract()
    contract.relationships["derivesRequirementFromNeed"]["sysml_mapping"][
        "semantic_strength"
    ] = "satisfaction"
    with pytest.raises(ValueError, match="semantic_strength"):
        _build(_base_elements(), contract)


# ---------------------------------------------------------------------------
# 3. Profile mechanics cannot redefine model semantics
# ---------------------------------------------------------------------------


def _profile() -> dict:
    return build_representation_profile(
        _contract(), _binding_index(), REVISION, _by_id(_base_elements()),
        repository_root=ROOT,
    )


def test_profile_gate_reads_model_authority_not_contract() -> None:
    profile = _profile()
    assert_profile_compatible(profile)  # passes unmodified
    # The gate must not consult an independently supplied oracle at all.
    contract = _contract()
    contract.relationships["derivesRequirementFromNeed"]["sysml_mapping"][
        "need_role"
    ] = "someOtherRole"
    assert_profile_compatible(profile)  # still fine: contract is not authority


def test_profile_mechanics_cannot_redefine_roles_or_direction() -> None:
    profile = _profile()
    mutated = json.loads(json.dumps(profile))
    mutated["witness"]["property_paths"]["need_end"] = "someOtherRole"
    with pytest.raises(ValueError, match="contradicts"):
        assert_profile_compatible(mutated)

    mutated = json.loads(json.dumps(profile))
    mutated["witness"]["query_direction"] = "forward"
    with pytest.raises(ValueError, match="contradicts"):
        assert_profile_compatible(mutated)


def test_profile_cannot_restate_domain_range_or_strength() -> None:
    profile = _profile()
    for field, tampered in (
        ("domain_from_projection", "Need"),
        ("range_from_projection", "Requirement"),
        ("semantic_strength_from_projection", "satisfaction"),
        ("claim_boundary_from_projection", "claims everything"),
    ):
        mutated = json.loads(json.dumps(profile))
        mutated["predicate_echo"][field] = tampered
        with pytest.raises(ValueError, match="contradicts"):
            assert_profile_compatible(mutated)


def test_profile_direction_echo_follows_model_order() -> None:
    """A model whose authored order flips makes the profile echo forward
    (with the oracle pair brought along consistently)."""
    contract = _contract()
    mapping = contract.relationships["derivesRequirementFromNeed"]["sysml_mapping"]
    mapping["query_direction"] = "forward"
    mapping["source_lineage_of"] = "Need"
    mapping["target_lineage_of"] = "Requirement"
    companion = contract.relationships["derivedRequirementsOfNeed"]["sysml_mapping"]
    companion["query_direction"] = "inverse"
    companion["source_lineage_of"] = "Requirement"
    companion["target_lineage_of"] = "Need"
    profile = build_representation_profile(
        contract, _binding_index(), REVISION, _by_id(_reversed_end_order()),
        repository_root=ROOT,
    )
    assert profile["witness"]["query_direction"] == "forward"
    assert_profile_compatible(profile)


# ---------------------------------------------------------------------------
# 4. Superseded standard-Derivation representation text is gone
# ---------------------------------------------------------------------------


def test_kernel_source_no_longer_describes_the_standard_library_relation() -> None:
    text = KERNEL_FILE.read_text(encoding="utf-8")
    for stale in (
        "DerivationConnections",
        "originalImpliesDerived",
        "standard library semantics",
        "Derivation Domain Library",
    ):
        assert stale not in text, f"stale standard-Derivation text remains: {stale}"
    assert "connection def DerivesFromNeed" in text
    assert "Claim strength: derivation" in text
    # The library mention survives only where it records NON-adoption.
    ontology = (
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    ).read_text(encoding="utf-8")
    assert "remains pinned but unadopted" in ontology.lower() or (
        "unadopted" in ontology.lower()
    )
