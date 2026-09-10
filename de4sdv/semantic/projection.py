"""DE4SDV Semantic Projection v0 and API Representation Profile v0 (K slice).

The projection is a consumer-facing, revision-bound artifact generated for
the one-predicate K slice. During the O0/O1 migration stages the executable
meaning of the predicate lives in the reviewed ontology/kernel contract
(``de4sdv-basic-ontology.yaml``); the projection is generated FROM that
contract identity plus the ingestion-validated model groundings and is
therefore a projection, not an independent semantic authority. It may not
define serializer property paths, runtime dispatch, importer quirks, or
transport behavior — those live in the representation profile.

Every generated artifact binds:

- the validated revision identity (Git SHA + SysML project/commit), which
  must be provided by the caller from a validated revision binding — the
  builders never invent or accept unverified revision labels; and
- the ontology contract identity (path + SHA-256) whose digest is recomputed
  from the actual contract file at generation time, so a projection cannot
  be produced against contract content other than what was validated.

v0 covers exactly one predicate (``derivesRequirementFromNeed``); this module
deliberately does not generalize the schema (plan §8.1).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECTION_SCHEMA = "de4sdv.semantic-projection.v0"
PROFILE_SCHEMA = "de4sdv.api-representation-profile.v0"
PROFILE_IDENTITY = "de4sdv.api-representation-profile.v0#derivesRequirementFromNeed"

CONTRACT_REPOSITORY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"

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


def build_projection(
    contract: Any,
    kernel_bindings: Any,
    revision: RevisionIdentity,
    by_id: dict[str, dict[str, Any]],
    *,
    repository_root: Path,
    witness_closure_verified: bool = False,
) -> dict[str, Any]:
    """Generate the v0 projection row from contract + validated bindings.

    Fails closed when any grounding required by the slice is missing from the
    validated binding index or absent from the bound revision: a projection
    generated without validated model identity would advertise semantics the
    runtime cannot ground (UG-24). ``witness_closure_verified`` must only be
    passed as True after the exact-candidate export/import/read-back proof;
    it is what turns ``support_state`` from ``vocabulary-only`` into
    ``supported``.
    """
    mapping = contract.relationship_mapping(_PREDICATE)
    config = mapping.configuration
    library_definition = str(config.get("native_library_definition", ""))
    library_id = kernel_bindings.element_id_for(library_definition, by_id)
    requirement_id = kernel_bindings.element_id_for(
        str(config.get("source_lineage_of", "")), by_id
    )
    need_id = kernel_bindings.element_id_for(
        str(config.get("target_lineage_of", "")), by_id
    )
    if not library_definition or not requirement_id or not need_id:
        raise ValueError(
            "projection requires validated groundings for the native "
            "library definition, Requirement, and Need definitions"
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
                    library_id,
                ],
                # K authority (plan v1.1 §16 K row): identity/meaning/
                # domain/range/direction/strength for this predicate are
                # grounded in the validated model + standard library
                # definition. The ontology contract identity is carried as
                # the O0/O1 parity oracle, not as the semantic authority.
                "native_library_grounding": {
                    "library": (
                        "SysML Requirement Derivation Domain Library 2.0.0"
                    ),
                    "definition": library_definition,
                    "element_id": library_id,
                    "need_role": str(config.get("need_role", "")),
                    "requirement_role": str(config.get("requirement_role", "")),
                    "grounding_provenance": (
                        "explicit connection typing; library constraints "
                        "(originalImpliesDerived, originalNotDerived) are "
                        "standard semantics"
                    ),
                },
                "ontology_contract_parity_oracle": (
                    contract_identity_from_file(repository_root)
                ),
            },
        },
        "predicate": {
            "identity": _PREDICATE,
            "definition": str(
                contract.relationships[_PREDICATE].get("definition")
                or (
                    "Requirement R is derived from stakeholder need N. "
                    "Design-input derivation; no satisfaction, allocation, "
                    "verification, evidence, or acceptance claim."
                )
            ).strip(),
            "domain": str(config.get("source_lineage_of", "")),
            "range": str(config.get("target_lineage_of", "")),
            "canonical_direction": (
                f"{config.get('source_lineage_of')} -> "
                f"{config.get('target_lineage_of')}"
            ),
            "inverse_navigation_identity": "derivedRequirementsOfNeed",
            "semantic_strength": mapping.semantic_strength,
            "semantic_exclusions": [],
            "applicability_scope": "de4sdv method increments (System 2)",
            "native_grounding": {
                "api_metaclass": "ConnectionUsage",
                "library_definition": library_definition,
                "need_role": str(config.get("need_role", "")),
                "requirement_role": str(config.get("requirement_role", "")),
                "witness_uuids_required": [
                    "connection",
                    "original_requirement_end",
                    "derived_requirement_end",
                    "library_typing",
                ],
            },
            "model_external_boundary": "none",
            "support_state": _support_state(by_id, witness_closure_verified),
        },
    }


def assert_profile_compatible(
    contract: Any, profile: dict[str, Any]
) -> None:
    """Semantic compatibility gate (UG-25): profile mechanics vs runtime mapping.

    The profile's representation mechanics are checked against the executable
    ontology mapping: the property paths and direction must match the
    mapping's configured source/target properties and direction. A profile
    that contradicts the executable mapping raises ``ValueError`` —
    representation mechanics cannot silently redefine meaning.
    """
    mapping = contract.relationship_mapping(_PREDICATE)
    config = mapping.configuration
    paths = profile["witness"]["property_paths"]
    if str(paths.get("need_end")) != str(
        config.get("need_role", "originalRequirements")
    ):
        raise ValueError(
            f"profile need end {paths.get('need_end')!r} contradicts the "
            f"executable mapping need_role "
            f"{config.get('need_role')!r} for {_PREDICATE}"
        )
    if str(paths.get("requirement_end")) != str(
        config.get("requirement_role", "derivedRequirements")
    ):
        raise ValueError(
            f"profile requirement end {paths.get('requirement_end')!r} "
            f"contradicts the executable mapping requirement_role "
            f"{config.get('requirement_role')!r} for {_PREDICATE}"
        )
    profile_direction = str(profile["witness"].get("query_direction", ""))
    mapping_direction = str(config.get("query_direction", ""))
    if profile_direction and profile_direction != mapping_direction:
        raise ValueError(
            f"profile query direction {profile_direction!r} contradicts the "
            f"executable mapping query_direction {mapping_direction!r} for "
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
    DERIVED from the executable ontology mapping (not hard-coded beside it),
    and the generated profile is validated with
    :func:`assert_profile_compatible` before it is returned, so a future
    mapping change that the derived description no longer matches fails
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
    config = contract.relationship_mapping(_PREDICATE).configuration
    need_role = str(config.get("need_role", "originalRequirements"))
    requirement_role = str(config.get("requirement_role", "derivedRequirements"))
    query_direction = str(config.get("query_direction", "inverse"))
    profile: dict[str, Any] = {
        "schema": PROFILE_SCHEMA,
        "profile_identity": PROFILE_IDENTITY,
        "for_predicate": predicate["identity"],
        "model_revision_binding": projection["revision_binding"],
        "witness": {
            "api_metaclass": "ConnectionUsage",
            "relationship_kind": "Typed derivation connection (standard "
            "library definition; typed via FeatureTyping)",
            "property_paths": {
                "need_end": need_role,
                "requirement_end": requirement_role,
                "ends": "ownedRelationship[@type=EndFeatureMembership]",
                "library_typing": "FeatureTyping.type",
            },
            "query_direction": query_direction,
            "direction_extraction": (
                f"The end grounding in {predicate['range']} lineage is the "
                f"{need_role} (originalRequirement; the Need); the end "
                f"grounding in {predicate['domain']} lineage is the "
                f"{requirement_role} (the derived requirement). Canonical "
                f"direction {predicate['canonical_direction']}; DE4SDV "
                f"query direction: {query_direction} over the native "
                f"witness"
            ),
            "ownership_traversal": (
                "Ends are EndFeatureMembership ownedRelationships of the "
                "ConnectionUsage; the connection is typed by the validated "
                "library Derivation definition via FeatureTyping"
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
                "ends, and the library FeatureTyping must survive official "
                "export, API import, and read-back; pruning any witness "
                "element makes the predicate unsupported for that revision "
                "(UG-06)"
            ),
        },
        "completeness_check": (
            "derivesRequirementFromNeed.derivation-connection-closure (fail "
            "closed: a validated binding for the library Derivation "
            "definition is required, and a connection missing an end, with "
            "an out-of-lineage end, or without the library typing is not a "
            "derivation)"
        ),
        "semantic_strength_from_projection": predicate["semantic_strength"],
        "domain_from_projection": predicate["domain"],
        "range_from_projection": predicate["range"],
        "support_state": predicate["support_state"],
    }
    assert_profile_compatible(contract, profile)
    return profile
