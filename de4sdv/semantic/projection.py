"""DE4SDV Semantic Projection v0 and API Representation Profile v0 (K slice).

The projection is a consumer-facing, revision-bound artifact generated from
validated model semantics plus the reviewed model-resident contract. It is
not an independent semantic authority and may not define serializer property
paths, runtime dispatch, importer quirks, or transport behavior — those live
in the representation profile.

v0 covers exactly one predicate (``derivesRequirementFromNeed``); this module
deliberately does not generalize the schema (plan §8.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PROJECTION_SCHEMA = "de4sdv.semantic-projection.v0"
PROFILE_SCHEMA = "de4sdv.api-representation-profile.v0"
PROFILE_IDENTITY = "de4sdv.api-representation-profile.v0#derivesRequirementFromNeed"

_PREDICATE = "derivesRequirementFromNeed"
_MARKER_CLASS = "RequirementDerivation"


@dataclass(frozen=True)
class RevisionIdentity:
    """Revision identity bound into every generated artifact."""

    git_commit: str
    sysml_project_id: str
    sysml_commit_id: str


@dataclass(frozen=True)
class ModelGrounding:
    """Ingestion-validated model identities the projection cites."""

    requirement_definition_id: str
    need_definition_id: str
    marker_definition_id: str


def build_projection(
    contract: Any,
    kernel_bindings: Any,
    revision: RevisionIdentity,
    by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Generate the v0 projection row from contract + validated bindings.

    Fails closed when any grounding required by the slice is missing from the
    validated binding index or absent from the bound revision: a projection
    generated without validated model identity would advertise semantics the
    runtime cannot ground (UG-24).
    """
    mapping = contract.relationship_mapping(_PREDICATE)
    config = mapping.configuration
    marker_name = str(config.get("metadata_definition", ""))
    marker_id = kernel_bindings.element_id_for(marker_name, by_id)
    requirement_id = kernel_bindings.element_id_for(
        str(mapping.configuration.get("source_lineage_of", "")), by_id
    )
    need_id = kernel_bindings.element_id_for(
        str(mapping.configuration.get("target_lineage_of", "")), by_id
    )
    grounding = ModelGrounding(
        requirement_definition_id=requirement_id,
        need_definition_id=need_id,
        marker_definition_id=marker_id,
    )
    return {
        "schema": PROJECTION_SCHEMA,
        "revision_binding": {
            "git_commit": revision.git_commit,
            "sysml_project": revision.sysml_project_id,
            "sysml_commit": revision.sysml_commit_id,
            "generated_from": {
                "model_definitions": [
                    grounding.requirement_definition_id,
                    grounding.need_definition_id,
                    grounding.marker_definition_id,
                ],
                "model_resident_contract": (
                    "approach/framework/ontology/de4sdv-basic-ontology.yaml"
                ),
            },
        },
        "predicate": {
            "identity": _PREDICATE,
            "definition": (
                "Requirement R is derived from stakeholder need N. "
                "Design-input derivation; no satisfaction, allocation, "
                "verification, evidence, or acceptance claim."
            ),
            "domain": str(config.get("source_lineage_of", "")) or "Requirement",
            "range": str(config.get("target_lineage_of", "")) or "Need",
            "canonical_direction": "Requirement -> Need",
            "inverse_navigation_identity": "derivedRequirementsOfNeed",
            "semantic_strength": mapping.semantic_strength,
            "semantic_exclusions": [],
            "applicability_scope": "de4sdv method increments (System 2)",
            "native_grounding": {
                "metaclass": "MetadataUsage",
                "metadata_definition": marker_name,
                "witness_uuids_required": ["relationship", "source", "target"],
            },
            "model_external_boundary": "none",
            "support_state": "supported",
        },
    }


def build_representation_profile(
    contract: Any,
    kernel_bindings: Any,
    revision: RevisionIdentity,
    by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Generate the v0 API Representation Profile entry.

    Representation mechanics only: witness shape, property paths, direction
    extraction, and the fail-closed completeness check. The profile may never
    redefine domain, range, direction, or semantic strength (UG-25): those
    fields are copied from the projection row built from the same inputs, so
    a profile generated against a different model revision cannot silently
    reinterpret meaning.
    """
    projection = build_projection(contract, kernel_bindings, revision, by_id)
    predicate = projection["predicate"]
    return {
        "schema": PROFILE_SCHEMA,
        "profile_identity": PROFILE_IDENTITY,
        "for_predicate": predicate["identity"],
        "model_revision_binding": projection["revision_binding"],
        "witness": {
            "api_metaclass": "Dependency",
            "relationship_kind": "Annotation-owned metadata application",
            "property_paths": {
                "source": "source",
                "target": "target",
                "annotation": "ownedRelationship[@type=Annotation]",
                "annotated_element": "annotatedElement",
                "metadata_usage": "ownedRelatedElement",
                "metadata_typing": "FeatureTyping.type",
            },
            "direction_extraction": (
                "Dependency client is the requirement (source); supplier is "
                "the need (target); canonical direction Requirement -> Need"
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
    }
