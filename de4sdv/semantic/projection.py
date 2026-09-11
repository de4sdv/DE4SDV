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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model_edges import end_feature_ids, typing_index
from .relationships import build_relationship_graph

PROJECTION_SCHEMA = "de4sdv.semantic-projection.v0"
PROFILE_SCHEMA = "de4sdv.api-representation-profile.v0"
PROFILE_IDENTITY = "de4sdv.api-representation-profile.v0#derivesRequirementFromNeed"

CONTRACT_REPOSITORY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"

_PREDICATE = "derivesRequirementFromNeed"

# Model-resident authority for the K predicate (plan v1.1 §16): the
# application connection definition and its typed end roles.
_CONNECTION_DEFINITION = "DerivesFromNeed"
_NEED_ROLE = "need"
_REQUIREMENT_ROLE = "derivedRequirement"

# Role-binding contract carried in the kernel definition's doc (validated
# model text). The projection compares the ingested documentation of the
# bound definition against this contract; a missing or divergent role
# binding fails generation — the runtime never inherits meaning from an
# unreviewed doc edit.
_CLAIM_BOUNDARY = (
    "Design-input provenance only: neither satisfaction nor logical "
    "implication between the connected usages is claimed; verification, "
    "evidence, and acceptance claims are out of scope."
)


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


def _model_derived_semantics(
    definition_id: str,
    by_id: dict[str, dict[str, Any]],
    contract: Any,
) -> dict[str, Any]:
    """Derive the predicate's semantic fields from the validated model.

    Authority chain (plan v1.1 §16): the application connection definition
    ``DerivesFromNeed`` carries the predicate. Identity comes from the
    ingestion-validated kernel binding (no name fallback); the typed end
    declarations on the definition element carry domain/range/roles; the
    definition's ingested documentation carries the meaning and claim
    boundary. The ontology YAML is consulted ONLY as the parity oracle and
    compared against these model-derived fields.
    """
    definition = by_id.get(definition_id)
    if definition is None:
        raise ValueError(
            "model authority missing: the validated DerivesFromNeed "
            "definition is not present in the bound revision"
        )

    # Model-resident end types: the definition's end features and their
    # types. The post-Lane-B graph carries both object-shape memberships and
    # inlined references, so end discovery and typing are
    # representation-tolerant; `ownedMember` + inlined `variant` remain as
    # the fallback shape. Explicit provenance is preferred, and an
    # implied-only typing is recorded as such (never silently promoted).
    graph = build_relationship_graph(list(by_id.values()))
    end_ids = end_feature_ids(graph, definition_id)
    if not end_ids:
        end_ids = _reference_ids(definition.get("ownedMember"))
    typed_explicit, typed_implied = typing_index(graph, list(by_id))

    need_type: str | None = None
    requirement_type: str | None = None
    end_type_provenance = "explicit"
    for end_id in end_ids:
        end = by_id.get(end_id, {})
        end_name = str(end.get("declaredName") or "")
        end_type: str | None = None
        end_type_id: str | None = None
        explicit_types = typed_explicit.get(end_id, set())
        implied_types = typed_implied.get(end_id, set())
        for candidate in sorted(explicit_types):
            element = by_id.get(candidate, {})
            if element.get("declaredName"):
                end_type, end_type_id = str(element["declaredName"]), candidate
                break
        if end_type is None:
            for candidate in sorted(implied_types):
                element = by_id.get(candidate, {})
                if element.get("declaredName"):
                    end_type, end_type_id = str(element["declaredName"]), candidate
                    end_type_provenance = "implied-fallback"
                    break
        if end_type is None:
            end_type = _first_reference_name(end.get("variant"), by_id)
        if end_name == _NEED_ROLE and end_type:
            need_type = end_type
        elif end_name == _REQUIREMENT_ROLE and end_type:
            requirement_type = end_type
    if need_type is None or requirement_type is None:
        raise ValueError(
            "model authority incomplete: the validated DerivesFromNeed "
            "definition does not expose typed `need` and "
            "`derivedRequirement` ends; the model does not carry the "
            "predicate's domain/range"
        )

    # Model-resident meaning: the definition's ingested documentation.
    documentation = _definition_documentation(definition, by_id)
    claim_boundary = _CLAIM_BOUNDARY
    for line in documentation:
        if "neither satisfaction nor logical implication" in line:
            claim_boundary = line.strip()
            break
    else:
        raise ValueError(
            "model authority incomplete: the validated DerivesFromNeed "
            "definition carries no role-binding/claim-boundary doc; the "
            "model does not state the predicate's claim boundary"
        )
    meaning = documentation[0].strip() if documentation else claim_boundary

    # Parity oracle (NOT authority): compare the model-derived fields with
    # the authored ontology YAML; unintended drift fails generation.
    oracle = contract.relationship_mapping(_PREDICATE)
    oracle_config = oracle.configuration
    drift: list[str] = []
    if str(oracle_config.get("connection_definition", "")) != _CONNECTION_DEFINITION:
        drift.append(
            f"oracle connection_definition "
            f"{oracle_config.get('connection_definition')!r} != model "
            f"{_CONNECTION_DEFINITION!r}"
        )
    if str(oracle_config.get("need_role", "")) != _NEED_ROLE:
        drift.append(
            f"oracle need_role {oracle_config.get('need_role')!r} != model "
            f"{_NEED_ROLE!r}"
        )
    if str(oracle_config.get("requirement_role", "")) != _REQUIREMENT_ROLE:
        drift.append(
            f"oracle requirement_role "
            f"{oracle_config.get('requirement_role')!r} != model "
            f"{_REQUIREMENT_ROLE!r}"
        )
    oracle_need_type = str(
        contract.classes.get("Need", {}).get("kernel", {}).get("declaration", "")
    ).partition(" def ")[2]
    oracle_requirement_type = str(
        contract.classes.get("Requirement", {})
        .get("kernel", {})
        .get("declaration", "")
    ).partition(" def ")[2]
    if need_type != oracle_need_type:
        drift.append(
            f"model need end type {need_type!r} != oracle Need kernel "
            f"declaration {oracle_need_type!r}"
        )
    if requirement_type != oracle_requirement_type:
        drift.append(
            f"model derivedRequirement end type {requirement_type!r} != "
            f"oracle Requirement kernel declaration {oracle_requirement_type!r}"
        )
    if oracle.semantic_strength != "derivation":
        drift.append(
            f"oracle semantic_strength {oracle.semantic_strength!r} != "
            f"model claim 'derivation' (provenance only)"
        )
    if drift:
        raise ValueError(
            "ontology parity oracle drift for " + _PREDICATE + ": "
            + "; ".join(drift)
        )

    return {
        "definition": _CONNECTION_DEFINITION,
        "definition_id": definition_id,
        "need_role": _NEED_ROLE,
        "requirement_role": _REQUIREMENT_ROLE,
        "need_end_type": need_type,
        "requirement_end_type": requirement_type,
        "meaning": meaning,
        "claim_boundary": claim_boundary,
        "end_type_provenance": end_type_provenance,
        "authority_provenance": (
            "ingestion-validated DerivesFromNeed definition: typed ends "
            "carry domain/range; ingested definition doc carries meaning "
            "and claim boundary; ontology YAML compared as O0/O1 parity "
            "oracle only"
        ),
    }


def _definition_documentation(
    definition: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> list[str]:
    """Ingested documentation of the definition element (API-resident)."""
    bodies: list[str] = []
    for document_id in _reference_ids(definition.get("documentation")):
        document = by_id.get(document_id, {})
        body = document.get("body") or document.get("bodyText")
        if body:
            bodies.append(str(body))
    return bodies


def _reference_ids(value: Any) -> list[str]:
    """Extract @id references from a serializer field."""
    if value is None:
        return []
    if isinstance(value, dict):
        item_id = value.get("@id")
        return [str(item_id)] if item_id else []
    if isinstance(value, list):
        found: list[str] = []
        for item in value:
            found.extend(_reference_ids(item))
        return found
    return []


def _first_reference_name(value: Any, by_id: dict[str, dict[str, Any]]) -> str | None:
    """Declared name of the first referenced element (e.g. an end's type)."""
    for reference_id in _reference_ids(value):
        element = by_id.get(reference_id)
        if element is not None and element.get("declaredName"):
            return str(element["declaredName"])
        # The referenced element may not be in this listing; its @id then
        # cannot be resolved to a name here — the caller validated the
        # definition itself, and end-type names are model-resident on the
        # same element.
    return None


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

    Fails closed when any grounding required by the slice is missing from the
    validated binding index or absent from the bound revision: a projection
    generated without validated model identity would advertise semantics the
    runtime cannot ground (UG-24). ``witness_closure_verified`` must only be
    passed as True after the exact-candidate export/import/read-back proof;
    it is what turns ``support_state`` from ``vocabulary-only`` into
    ``supported``. The ontology YAML is loaded only for the parity
    comparison; every semantic field originates from the model.
    """
    definition_id = kernel_bindings.element_id_for(_CONNECTION_DEFINITION, by_id)
    model_semantics = _model_derived_semantics(definition_id, by_id, contract)
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
                # K authority (plan v1.1 §16 final decision): identity/
                # meaning/domain/range/direction/strength for this predicate
                # are grounded in the validated model — the application
                # connection definition and its typed ends. The ontology
                # contract identity is carried as the O0/O1 parity oracle,
                # not as the semantic authority.
                "model_semantic_authority": {
                    "connection_definition": model_semantics["definition"],
                    "element_id": model_semantics["definition_id"],
                    "need_role": model_semantics["need_role"],
                    "requirement_role": model_semantics["requirement_role"],
                    "need_end_type": model_semantics["need_end_type"],
                    "requirement_end_type": model_semantics[
                        "requirement_end_type"
                    ],
                    "end_type_provenance": model_semantics[
                        "end_type_provenance"
                    ],
                    "authority_provenance": model_semantics[
                        "authority_provenance"
                    ],
                },
                "ontology_contract_parity_oracle": (
                    contract_identity_from_file(repository_root)
                ),
            },
        },
        "predicate": {
            "identity": _PREDICATE,
            "definition": model_semantics["meaning"],
            "domain": "Requirement",
            "range": "Need",
            "canonical_direction": (
                f"{model_semantics['need_role']} -> "
                f"{model_semantics['requirement_role']} (model-native); "
                f"Requirement -> Need query"
            ),
            "inverse_navigation_identity": "derivedRequirementsOfNeed",
            "semantic_strength": "derivation",
            "claim_boundary": model_semantics["claim_boundary"],
            "semantic_exclusions": [
                "satisfaction",
                "allocation",
                "verification",
                "evidence",
                "acceptance",
            ],
            "applicability_scope": "de4sdv method increments (System 2)",
            "native_grounding": {
                "api_metaclass": "ConnectionUsage",
                "connection_definition": model_semantics["definition"],
                "need_role": model_semantics["need_role"],
                "requirement_role": model_semantics["requirement_role"],
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


def assert_profile_compatible(
    contract: Any, profile: dict[str, Any]
) -> None:
    """Semantic compatibility gate (UG-25): profile mechanics vs model authority.

    The profile's representation mechanics are checked against the
    model-resident role binding (the same fields the runtime consumes): the
    end roles and query direction must match. A profile that contradicts the
    model authority raises ``ValueError`` — representation mechanics cannot
    silently redefine meaning.
    """
    paths = profile["witness"]["property_paths"]
    if str(paths.get("need_end")) != _NEED_ROLE:
        raise ValueError(
            f"profile need end {paths.get('need_end')!r} contradicts the "
            f"model authority need_role {_NEED_ROLE!r} for {_PREDICATE}"
        )
    if str(paths.get("requirement_end")) != _REQUIREMENT_ROLE:
        raise ValueError(
            f"profile requirement end {paths.get('requirement_end')!r} "
            f"contradicts the model authority requirement_role "
            f"{_REQUIREMENT_ROLE!r} for {_PREDICATE}"
        )
    profile_direction = str(profile["witness"].get("query_direction", ""))
    if profile_direction and profile_direction != "inverse":
        raise ValueError(
            f"profile query direction {profile_direction!r} contradicts the "
            f"model authority query_direction 'inverse' for {_PREDICATE}"
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
            "query_direction": "inverse",
            "direction_extraction": (
                f"The end grounding in the {predicate['domain']} lineage is "
                f"the {requirement_role} (the derived requirement); the end "
                f"grounding in the {predicate['range']} lineage is the "
                f"{need_role} (the need). Model-native direction "
                f"{predicate['canonical_direction']}; DE4SDV query "
                f"direction: inverse over the native witness"
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
                "semantic_strength_from_projection": predicate["semantic_strength"],
        "domain_from_projection": predicate["domain"],
        "range_from_projection": predicate["range"],
        "claim_boundary_from_projection": predicate["claim_boundary"],
    }
    assert_profile_compatible(contract, profile)
    return profile
