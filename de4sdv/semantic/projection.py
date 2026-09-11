"""DE4SDV Semantic Projection v0 and API Representation Profile v0 (K slice).

The projection is a consumer-facing, revision-bound artifact generated for
the one-predicate K slice. Its semantic fields are derived from the
VALIDATED MODEL representation (plan v1.1 §16 final decision): the
application connection definition ``DerivesFromNeed`` is an ontology-mapped
kernel declaration whose typed ends (``need : StakeholderNeedCandidate``,
``derivedRequirement : RequirementCandidate``) carry the predicate's
domain, range, and direction in the model itself; the kernel role-binding
contract (connection definition + end types + role-binding doc) carries the
meaning and claim boundary. The authored ontology YAML is loaded ONLY as
the O0/O1 parity oracle: it is compared against the model-derived fields
and any unintended drift fails generation — it never supplies a semantic
field. The projection may not define serializer property paths, runtime
dispatch, importer quirks, or transport behavior — those live in the
representation profile.

Every generated artifact binds:

- the validated revision identity (Git SHA + SysML project/commit), which
  must be provided by the caller from a validated revision binding — the
  builders never invent or accept unverified revision labels; and
- the ontology contract identity (path + SHA-256) whose digest is recomputed
  from the actual contract file at generation time, recording exactly which
  oracle text the parity check compared against.

v0 covers exactly one predicate (``derivesRequirementFromNeed``); this module
deliberately does not generalize the schema (plan §8.1).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model_authority import model_semantics

PROJECTION_SCHEMA = "de4sdv.semantic-projection.v0"
PROFILE_SCHEMA = "de4sdv.api-representation-profile.v0"
PROFILE_IDENTITY = "de4sdv.api-representation-profile.v0#derivesRequirementFromNeed"

CONTRACT_REPOSITORY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"

# Bounded schema identifiers/selectors for this one K slice (plan v1.1 §16).
# They LOCATE the model authority; they do not define domain, range,
# direction, claim strength, or claim boundary — every one of those values is
# read from the validated model below and generation fails when the model does
# not carry them.
#   * ``_CONNECTION_DEFINITION`` — the ontology class key of the single K
#     application definition, used to resolve its validated element id;
#   * ``_NEED_ROLE`` / ``_REQUIREMENT_ROLE`` — the declared end names that
#     identify the definition's two ends;
#   * ``_PREDICATE`` — the identity of the predicate being generated; the
#     authority module separates its subject/object vocabulary names so the
#     projection matches them against the model's end classes instead of
#     restating domain/range as literals.
_CONNECTION_DEFINITION = "DerivesFromNeed"
_NEED_ROLE = "need"
_REQUIREMENT_ROLE = "derivedRequirement"

#: The predicate identity being generated. Bounded schema identifier: it does
#: not define domain/range/direction/strength — those are matched against and
#: copied from the validated model (see ``model_authority``).
_PREDICATE = "derivesRequirementFromNeed"


@dataclass(frozen=True)
class RevisionIdentity:
    """Validated revision identity bound into every generated artifact.

    Constructed only from a validated revision binding's identity fields —
    the builders verify the full 40-hex SHA shape and never generate a
    projection for an unverified revision label.
    """

    git_commit: str
    sysml_project_id: str
    sysml_commit_id: str

    def __post_init__(self) -> None:
        import re

        if not re.fullmatch(r"[0-9a-f]{40}", self.git_commit):
            raise ValueError(
                f"git_commit must be a full 40-hex SHA from a validated "
                f"revision binding, got {self.git_commit!r}"
            )
        if not self.sysml_project_id or not self.sysml_commit_id:
            raise ValueError(
                "sysml project/commit ids are required from the validated "
                "revision binding"
            )

    @classmethod
    def from_binding(cls, binding: Any) -> "RevisionIdentity":
        """Build from a validated RevisionBinding (the only trusted source)."""
        return cls(
            git_commit=str(binding.git_commit),
            sysml_project_id=str(binding.sysml_project_id),
            sysml_commit_id=str(binding.sysml_commit_id),
        )


def contract_identity_from_file(repository_root: Path) -> dict[str, str]:
    """Recompute the ontology contract identity from the actual file."""
    contract_path = repository_root / CONTRACT_REPOSITORY_PATH
    return {
        "path": CONTRACT_REPOSITORY_PATH,
        "sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
    }


def _support_state(
    by_id: dict[str, dict[str, Any]],
    witness_closure_verified: bool,
) -> str:
    """Compute the support state from the representation closure evidence.

    ``supported`` requires the exact-candidate closure evidence (the C1
    gate: official export/import/read-back of the witness at this revision)
    to have been verified by the caller. Without that evidence the state is
    ``vocabulary-only`` — a generated projection must not promote an
    unproven representation into advertised support (UG-06, plan §8.1).
    """
    if witness_closure_verified:
        return "supported"
    return "vocabulary-only"


def _assert_oracle_parity(contract: Any, semantics: dict[str, Any]) -> None:
    """Compare the authored ontology YAML against the model-derived semantics.

    The YAML is the O0/O1 parity oracle: it may contradict nothing and it may
    not redefine anything. Unintended drift fails generation naming the exact
    field. This is the only role the authored contract has for the K slice.
    """
    mapping = contract.relationship_mapping(_PREDICATE)
    config = mapping.configuration
    relationship = contract.relationships.get(_PREDICATE) or {}
    oracle_by_field = {
        "connection_definition": config.get("connection_definition"),
        "need_role": config.get("need_role"),
        "requirement_role": config.get("requirement_role"),
        "query_direction": config.get("query_direction"),
        "semantic_strength": mapping.semantic_strength,
        "domain": relationship.get("domain"),
        "range": relationship.get("range"),
        "need_end_type_declaration": str(
            contract.classes.get("Need", {}).get("kernel", {}).get("declaration", "")
        ).partition(" def ")[2],
        "requirement_end_type_declaration": str(
            contract.classes.get("Requirement", {})
            .get("kernel", {})
            .get("declaration", "")
        ).partition(" def ")[2],
    }
    inverse = str(config.get("query_direction", "inverse")) == "inverse"
    oracle_by_field["need_end_type"] = config.get(
        "target_lineage_of" if inverse else "source_lineage_of"
    )
    oracle_by_field["requirement_end_type"] = config.get(
        "source_lineage_of" if inverse else "target_lineage_of"
    )
    drift = [
        f"{field}: oracle {oracle_value!r} != model {semantics[field]!r}"
        for field, oracle_value in oracle_by_field.items()
        if oracle_value and str(oracle_value) != str(semantics[field])
    ]
    if drift:
        raise ValueError(
            "ontology parity oracle drift for " + _PREDICATE + ": " + "; ".join(drift)
        )


def build_projection(
    contract: Any,
    kernel_bindings: Any,
    revision: RevisionIdentity,
    by_id: dict[str, dict[str, Any]],
    *,
    repository_root: Path,
    witness_closure_verified: bool = False,
) -> dict[str, Any]:
    """Generate the v0 projection row from the validated model authority.

    Every semantic field published here is COPIED from the model-derived
    authority (``model_authority.model_semantics``); nothing is restated as a
    Python semantic literal. The authored ontology YAML is loaded only to
    compare against those values and fails generation on unintended drift.

    Fails closed when any grounding required by the slice is missing from the
    validated binding index, absent from the bound revision, or not stated by
    the model (UG-24). ``witness_closure_verified`` must only be passed as
    True after the exact-candidate export/import/read-back proof; it is what
    turns ``support_state`` from ``vocabulary-only`` into ``supported``.
    """
    definition_id = kernel_bindings.element_id_for(_CONNECTION_DEFINITION, by_id)
    semantics = model_semantics(
        definition_id,
        by_id,
        kernel_bindings,
        _PREDICATE,
        _NEED_ROLE,
        _REQUIREMENT_ROLE,
    )
    _assert_oracle_parity(contract, semantics)
    requirement_id = kernel_bindings.element_id_for("Requirement", by_id)
    need_id = kernel_bindings.element_id_for("Need", by_id)
    if not definition_id or not requirement_id or not need_id:
        raise ValueError(
            "projection requires validated groundings for the application "
            "connection definition, Requirement, and Need definitions"
        )
    return {
        "schema": PROJECTION_SCHEMA,
        "revision_binding": {
            "git_commit": revision.git_commit,
            "sysml_project": revision.sysml_project_id,
            "sysml_commit": revision.sysml_commit_id,
            "generated_from": {
                "model_definitions": [
                    requirement_id,
                    need_id,
                    definition_id,
                ],
                # K authority (plan v1.1 §16): identity, meaning,
                # domain/range, native and canonical direction, claim
                # strength, and claim boundary are all grounded in the
                # validated model. The ontology contract identity is carried
                # as the O0/O1 parity oracle, not as a semantic authority.
                "model_semantic_authority": {
                    "connection_definition": semantics["connection_definition"],
                    "element_id": definition_id,
                    "ends": semantics["ends"],
                    "need_role": semantics["need_role"],
                    "requirement_role": semantics["requirement_role"],
                    "need_end_type": semantics["need_end_type"],
                    "requirement_end_type": semantics["requirement_end_type"],
                    "need_end_type_declaration": semantics[
                        "need_end_type_declaration"
                    ],
                    "requirement_end_type_declaration": semantics[
                        "requirement_end_type_declaration"
                    ],
                    "end_type_provenance": semantics["end_type_provenance"],
                    "end_order_source": semantics["end_order_source"],
                    "native_direction": semantics["native_direction"],
                    "canonical_direction": semantics["canonical_direction"],
                    "query_direction": semantics["query_direction"],
                    "domain": semantics["domain"],
                    "range": semantics["range"],
                    "semantic_strength": semantics["semantic_strength"],
                    "claim_boundary": semantics["claim_boundary"],
                    "authority_provenance": semantics["authority_provenance"],
                },
                "ontology_contract_parity_oracle": (
                    contract_identity_from_file(repository_root)
                ),
            },
        },
        "predicate": {
            "identity": _PREDICATE,
            "definition": semantics["meaning"],
            "domain": semantics["domain"],
            "range": semantics["range"],
            "native_direction": semantics["native_direction"],
            "canonical_direction": semantics["canonical_direction"],
            "query_direction": semantics["query_direction"],
            "inverse_navigation_identity": "derivedRequirementsOfNeed",
            "semantic_strength": semantics["semantic_strength"],
            "claim_boundary": semantics["claim_boundary"],
            "applicability_scope": "de4sdv method increments (System 2)",
            "native_grounding": {
                "api_metaclass": "ConnectionUsage",
                "connection_definition": _CONNECTION_DEFINITION,
                "need_role": semantics["need_role"],
                "requirement_role": semantics["requirement_role"],
                "witness_uuids_required": [
                    "connection",
                    "need_end",
                    "derived_requirement_end",
                    "definition_typing",
                ],
            },
            "model_external_boundary": "none",
            "support_state": _support_state(by_id, witness_closure_verified),
        },
    }


def assert_profile_compatible(profile: dict[str, Any]) -> None:
    """Semantic compatibility gate (UG-25): mechanics vs model authority.

    The profile carries the projection's model-derived authority. Its
    representation mechanics (end property paths, query direction) and its
    echoed semantic fields are compared against THAT authority — never against
    Python constants and never against the authored oracle. A profile that
    contradicts the model-derived projection raises ``ValueError``:
    representation mechanics cannot silently redefine meaning.
    """
    authority = profile["model_revision_binding"]["generated_from"][
        "model_semantic_authority"
    ]
    predicate = profile.get("predicate_echo") or profile
    paths = profile["witness"]["property_paths"]
    for field, authority_key in (
        ("need_end", "need_role"),
        ("requirement_end", "requirement_role"),
    ):
        expected = str(authority[authority_key])
        if str(paths.get(field)) != expected:
            raise ValueError(
                f"profile {field} {paths.get(field)!r} contradicts the "
                f"model-derived authority {authority_key} {expected!r} for "
                f"{_PREDICATE}"
            )
    profile_direction = str(profile["witness"].get("query_direction", ""))
    expected_direction = str(authority["query_direction"])
    if profile_direction and profile_direction != expected_direction:
        raise ValueError(
            f"profile query direction {profile_direction!r} contradicts the "
            f"model-derived authority query_direction {expected_direction!r} "
            f"for {_PREDICATE}"
        )
    # Echoed semantic fields must be the model-derived ones, not independent
    # values: a hand-edited profile cannot restate domain/range/strength.
    for field, authority_key in (
        ("domain_from_projection", "domain"),
        ("range_from_projection", "range"),
        ("semantic_strength_from_projection", "semantic_strength"),
        ("claim_boundary_from_projection", "claim_boundary"),
    ):
        if field not in predicate:
            continue
        expected = str(authority[authority_key])
        if str(predicate[field]) != expected:
            raise ValueError(
                f"profile {field} {predicate[field]!r} contradicts the "
                f"model-derived authority {authority_key} {expected!r} for "
                f"{_PREDICATE}"
            )


def build_representation_profile(
    contract: Any,
    kernel_bindings: Any,
    revision: RevisionIdentity,
    by_id: dict[str, dict[str, Any]],
    *,
    repository_root: Path,
    witness_closure_verified: bool = False,
) -> dict[str, Any]:
    """Generate the v0 API Representation Profile entry.

    Representation mechanics only: witness shape, property paths, direction
    extraction, and the fail-closed completeness check. The mechanics are
    DERIVED from the model-resident authority (not hard-coded beside it),
    and the generated profile is validated with
    :func:`assert_profile_compatible` before it is returned, so a future
    authority change that the derived description no longer matches fails
    generation instead of shipping a contradiction (UG-25). Domain, range,
    direction, and semantic strength are echoes of the projection row built
    from the same inputs.
    """
    projection = build_projection(
        contract,
        kernel_bindings,
        revision,
        by_id,
        repository_root=repository_root,
        witness_closure_verified=witness_closure_verified,
    )
    predicate = projection["predicate"]
    authority = projection["revision_binding"]["generated_from"][
        "model_semantic_authority"
    ]
    need_role = str(authority["need_role"])
    requirement_role = str(authority["requirement_role"])
    query_direction = str(authority["query_direction"])
    native_direction = str(authority["native_direction"])
    canonical_direction = str(authority["canonical_direction"])
    profile: dict[str, Any] = {
        "schema": PROFILE_SCHEMA,
        "profile_identity": PROFILE_IDENTITY,
        "for_predicate": predicate["identity"],
        "model_revision_binding": projection["revision_binding"],
        "witness": {
            "api_metaclass": "ConnectionUsage",
            "relationship_kind": "Typed DE4SDV application connection "
            "(DerivesFromNeed; typed via FeatureTyping)",
            "property_paths": {
                "need_end": need_role,
                "requirement_end": requirement_role,
                "ends": "ownedRelationship[@type=EndFeatureMembership]",
                "definition_typing": "FeatureTyping.type",
            },
            "query_direction": query_direction,
            "direction_extraction": (
                f"The end grounding in the {predicate['domain']} lineage is "
                f"the {requirement_role} (the derived requirement); the end "
                f"grounding in the {predicate['range']} lineage is the "
                f"{need_role} (the need). Model-native direction "
                f"{native_direction}; canonical consumer direction "
                f"{canonical_direction}; DE4SDV query direction: "
                f"{query_direction} over the native witness"
            ),
            "ownership_traversal": (
                "Ends are EndFeatureMembership ownedRelationships of the "
                "ConnectionUsage; the connection is typed by the validated "
                "DerivesFromNeed application definition via FeatureTyping"
            ),
            "reference_vs_containment": (
                "Ends are referential usages (validateUsageIsReferential); "
                "the connection itself is owned by its enclosing namespace"
            ),
        },
        "serializer_importer_compatibility": {
            "known_omissions": [],
            "uuid_preservation": "single-transaction-required",
            "out_of_export_risk": (
                "C1 closure: the ConnectionUsage, its EndFeatureMembership "
                "ends, and the definition FeatureTyping must survive "
                "official export, API import, and read-back; pruning any "
                "witness element makes the predicate unsupported for that "
                "revision (UG-06)"
            ),
        },
        "completeness_check": (
            "derivesRequirementFromNeed.derivation-connection-closure (fail "
            "closed: a validated binding for the DerivesFromNeed "
            "application definition is required, and a connection missing "
            "an end, with an out-of-lineage end, or without the definition "
            "typing is not a derivation)"
        ),
                # Echo of the model-derived projection row (not an independent
        # semantic definition): the gate below compares these back against
        # the embedded authority.
        "predicate_echo": {
            "identity": predicate["identity"],
            "domain_from_projection": predicate["domain"],
            "range_from_projection": predicate["range"],
            "semantic_strength_from_projection": predicate["semantic_strength"],
            "claim_boundary_from_projection": predicate["claim_boundary"],
        },
    }
    assert_profile_compatible(profile)
    return profile
