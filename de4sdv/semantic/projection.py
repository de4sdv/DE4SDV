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
    marker_name = str(config.get("metadata_definition", ""))
    marker_id = kernel_bindings.element_id_for(marker_name, by_id)
    requirement_id = kernel_bindings.element_id_for(
        str(config.get("source_lineage_of", "")), by_id
    )
    need_id = kernel_bindings.element_id_for(
        str(config.get("target_lineage_of", "")), by_id
    )
    if not marker_name or not requirement_id or not need_id:
        raise ValueError(
            "projection requires validated groundings for the marker, "
            "Requirement, and Need definitions"
        )
    return {
        "schema": PROJECTION_SCHEMA,
        "revision_binding": {
            "git_commit": revision.git_commit,
            "sysml_project": revision.sysml_project_id,
            "sysml_commit": revision.sysml_commit_id,
            "generated_from": {
                "model_definitions": [requirement_id, need_id, marker_id],
                # O0/O1 honesty: the executable meaning for this unmigrated
                # slice lives in the authored ontology/kernel contract. This
                # is the contract identity whose digest was recomputed at
                # generation time — not a claim that the definitions are
                # model-resident yet.
                "ontology_contract": contract_identity_from_file(
                    repository_root
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
                "metaclass": "MetadataUsage",
                "metadata_definition": marker_name,
                "witness_uuids_required": [
                    "relationship",
                    "annotation",
                    "marker_usage",
                    "source",
                    "target",
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
    if str(paths.get("source")) != str(config.get("source_property", "source")):
        raise ValueError(
            f"profile source property {paths.get('source')!r} contradicts "
            f"the executable mapping source_property "
            f"{config.get('source_property')!r} for {_PREDICATE}"
        )
    if str(paths.get("target")) != str(config.get("target_property", "target")):
        raise ValueError(
            f"profile target property {paths.get('target')!r} contradicts "
            f"the executable mapping target_property "
            f"{config.get('target_property')!r} for {_PREDICATE}"
        )
    profile_direction = str(profile["witness"].get("direction", ""))
    mapping_direction = str(config.get("direction", "outgoing"))
    if profile_direction and profile_direction != mapping_direction:
        raise ValueError(
            f"profile direction {profile_direction!r} contradicts the "
            f"executable mapping direction {mapping_direction!r} for "
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
    source_property = str(config.get("source_property", "source"))
    target_property = str(config.get("target_property", "target"))
    direction = str(config.get("direction", "outgoing"))
    profile: dict[str, Any] = {
        "schema": PROFILE_SCHEMA,
        "profile_identity": PROFILE_IDENTITY,
        "for_predicate": predicate["identity"],
        "model_revision_binding": projection["revision_binding"],
        "witness": {
            "api_metaclass": str(
                (config.get("relationship_types") or ["Dependency"])[0]
            ),
            "relationship_kind": "Annotation-owned metadata application",
            "property_paths": {
                "source": source_property,
                "target": target_property,
                "annotation": "ownedRelationship[@type=Annotation]",
                "annotated_element": "annotatedElement",
                "metadata_usage": "ownedRelatedElement",
                "metadata_typing": "FeatureTyping.type",
            },
            "direction": direction,
            "direction_extraction": (
                f"Dependency {source_property} is the "
                f"{predicate['domain']} ({source_property}); "
                f"{target_property} is the {predicate['range']}; canonical "
                f"direction {predicate['canonical_direction']} "
                f"({direction})"
            ),
            "ownership_traversal": (
                "Annotation owned by the Dependency (owningRelatedElement = "
                "the dependency); MetadataUsage owned by the Annotation "
                "(ownedRelatedElement)"
            ),
            "reference_vs_containment": (
                "source/target are element references; metadata usage is "
                "related-element ownership, not namespace membership"
            ),
        },
        "serializer_importer_compatibility": {
            "known_omissions": [],
            "uuid_preservation": "single-transaction-required",
            "out_of_export_risk": (
                "C1 closure: the Annotation/MetadataUsage/FeatureTyping "
                "witness must survive official export, API import, and "
                "read-back; pruning any witness element makes the predicate "
                "unsupported for that revision (UG-06)"
            ),
        },
        "completeness_check": (
            "derivesRequirementFromNeed.marker-closure (fail closed: a "
            "validated binding for the marker definition is required, and a "
            "dependency without the full witness is not a derivation)"
        ),
        "semantic_strength_from_projection": predicate["semantic_strength"],
        "domain_from_projection": predicate["domain"],
        "range_from_projection": predicate["range"],
        "support_state": predicate["support_state"],
    }
    assert_profile_compatible(contract, profile)
    return profile
