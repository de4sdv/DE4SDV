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

Support promotion: ``support_state`` is ``vocabulary-only`` unless a
structured :class:`ClosureAttestation` — evidence identity, exact Git
revision, SysML project/commit, proof result, covered semantic subjects, and
evidence artifact identity/digest — is supplied and validated against the
bound ``RevisionIdentity``. There is no boolean shortcut, and a supplied
attestation that does not match the bound revision fails closed.

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

#: The verified companion predicate: inverse navigation over the SAME native
#: connection witness. Bounded schema identifier; its oracle row is
#: pair-parity-checked against the canonical row below (Wave 0b, F5).
_INVERSE_PREDICATE = "derivedRequirementsOfNeed"

#: The traversal strategy token the pair must declare (bounded schema
#: identifier for the derivation-connection strategy).
_DERIVATION_STRATEGY = "derivation-connection"

#: The only legal query-direction pairing for one inverse-navigation pair.
_PAIR_DIRECTIONS = {"inverse": "forward", "forward": "inverse"}

#: The semantic subjects a K closure attestation must cover.
_REQUIRED_CLOSURE_SUBJECTS = (_CONNECTION_DEFINITION, _PREDICATE, _INVERSE_PREDICATE)

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ClosureAttestation:
    """Structured, revision-bound witness-closure attestation (the C1 gate).

    A bare caller boolean is never a valid support-promotion mechanism: the
    attestation binds an evidence identity, the exact Git revision and SysML
    project/commit it proves, the proof result, the covered semantic
    subjects, and the evidence artifact identity/digest. Support promotion
    validates this structure against the projection's ``RevisionIdentity``
    and fails closed on any mismatch — a supplied contradictory or stale
    attestation is never quietly downgraded.

    Constructed directly or from a mapping via :meth:`from_mapping`; the
    mapping must use exactly these field names.
    """

    evidence_id: str
    git_commit: str
    sysml_project_id: str
    sysml_commit_id: str
    proof_result: str
    subject_identities: tuple[str, ...]
    artifact_identity: str
    artifact_digest: str | None = None

    @classmethod
    def from_mapping(cls, value: Any) -> "ClosureAttestation":
        if not isinstance(value, dict):
            raise ValueError(
                "closure attestation must be a ClosureAttestation or a mapping"
            )
        required = (
            "evidence_id",
            "git_commit",
            "sysml_project_id",
            "sysml_commit_id",
            "proof_result",
            "subject_identities",
            "artifact_identity",
        )
        missing = [field for field in required if field not in value]
        if missing:
            raise ValueError(
                f"malformed closure attestation: missing fields {missing}"
            )
        subjects = value.get("subject_identities")
        if isinstance(subjects, str) or not isinstance(subjects, (list, tuple)):
            raise ValueError(
                "malformed closure attestation: subject_identities must be a "
                "sequence of identities"
            )
        return cls(
            evidence_id=str(value["evidence_id"]),
            git_commit=str(value["git_commit"]),
            sysml_project_id=str(value["sysml_project_id"]),
            sysml_commit_id=str(value["sysml_commit_id"]),
            proof_result=str(value["proof_result"]),
            subject_identities=tuple(str(item) for item in subjects),
            artifact_identity=str(value["artifact_identity"]),
            artifact_digest=(
                None
                if value.get("artifact_digest") is None
                else str(value["artifact_digest"])
            ),
        )


def _coerce_attestation(value: Any) -> ClosureAttestation:
    if isinstance(value, ClosureAttestation):
        return value
    return ClosureAttestation.from_mapping(value)


def _validate_closure_attestation(
    attestation: ClosureAttestation, revision: RevisionIdentity
) -> None:
    """Fail closed on any malformed, non-pass, or mismatched attestation."""
    if not _FULL_SHA.fullmatch(attestation.git_commit):
        raise ValueError(
            f"malformed closure attestation: git_commit must be a full 40-hex "
            f"SHA, got {attestation.git_commit!r}"
        )
    if not str(attestation.evidence_id).strip():
        raise ValueError(
            "malformed closure attestation: evidence_id must be a non-empty "
            "evidence identity"
        )
    if not str(attestation.artifact_identity).strip():
        raise ValueError(
            "malformed closure attestation: artifact_identity must be a "
            "non-empty evidence artifact identity"
        )
    if attestation.artifact_digest is not None and not _SHA256_DIGEST.fullmatch(
        attestation.artifact_digest
    ):
        raise ValueError(
            "malformed closure attestation: artifact_digest must be a "
            f"sha256:<64-hex> digest, got {attestation.artifact_digest!r}"
        )
    if attestation.proof_result != "pass":
        raise ValueError(
            f"closure attestation proof_result {attestation.proof_result!r} is "
            "not a passing proof; support promotion requires a pass"
        )
    missing = [
        subject
        for subject in _REQUIRED_CLOSURE_SUBJECTS
        if subject not in attestation.subject_identities
    ]
    if missing:
        raise ValueError(
            f"closure attestation does not cover required semantic subjects "
            f"{missing}; the K closure scope is {list(_REQUIRED_CLOSURE_SUBJECTS)}"
        )
    if attestation.git_commit != revision.git_commit:
        raise ValueError(
            f"closure attestation git_commit {attestation.git_commit} does not "
            f"match the bound revision {revision.git_commit}; a stale or "
            "foreign attestation never promotes support"
        )
    if attestation.sysml_project_id != revision.sysml_project_id:
        raise ValueError(
            f"closure attestation sysml_project_id "
            f"{attestation.sysml_project_id!r} does not match the bound "
            f"revision {revision.sysml_project_id!r}"
        )
    if attestation.sysml_commit_id != revision.sysml_commit_id:
        raise ValueError(
            f"closure attestation sysml_commit_id "
            f"{attestation.sysml_commit_id!r} does not match the bound "
            f"revision {revision.sysml_commit_id!r}"
        )


def _support_state(
    revision: RevisionIdentity,
    closure_attestation: Any,
) -> str:
    """Compute the support state from a structured closure attestation.

    ``supported`` requires a valid, exact-revision ``ClosureAttestation``
    (the C1 gate: official export/import/read-back of the witness at this
    revision). Without an attestation the state is ``vocabulary-only`` — a
    generated projection must not promote an unproven representation into
    advertised support (UG-06, plan §8.1). A supplied attestation that does
    not match the ``RevisionIdentity`` exactly (or is malformed) fails
    closed; there is no boolean shortcut.
    """
    if closure_attestation is None:
        return "vocabulary-only"
    _validate_closure_attestation(
        _coerce_attestation(closure_attestation), revision
    )
    return "supported"


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


def _pair_oracle_rows(contract: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """The canonical and companion oracle rows, as checkable field maps."""
    canonical_mapping = contract.relationship_mapping(_PREDICATE)
    companion_mapping = contract.relationship_mapping(_INVERSE_PREDICATE)
    canonical_row = contract.relationships.get(_PREDICATE) or {}
    companion_row = contract.relationships.get(_INVERSE_PREDICATE) or {}

    def fields(mapping: Any, row: dict[str, Any]) -> dict[str, Any]:
        config = mapping.configuration
        return {
            "strategy": mapping.strategy,
            "connection_definition": config.get("connection_definition"),
            "need_role": config.get("need_role"),
            "requirement_role": config.get("requirement_role"),
            "query_direction": config.get("query_direction"),
            "semantic_strength": mapping.semantic_strength,
            "domain": row.get("domain"),
            "range": row.get("range"),
            "source_lineage_of": config.get("source_lineage_of"),
            "target_lineage_of": config.get("target_lineage_of"),
            # The shared kernel end-type declarations (both rows traverse the
            # same two ends); compared against the model-derived declarations.
            "need_end_type_declaration": str(
                contract.classes.get("Need", {}).get("kernel", {}).get("declaration", "")
            ).partition(" def ")[2],
            "requirement_end_type_declaration": str(
                contract.classes.get("Requirement", {})
                .get("kernel", {})
                .get("declaration", "")
            ).partition(" def ")[2],
        }

    return fields(canonical_mapping, canonical_row), fields(
        companion_mapping, companion_row
    )


def _assert_oracle_parity(contract: Any, semantics: dict[str, Any]) -> dict[str, Any]:
    """Pair-parity-check the authored ontology YAML against the model semantics.

    The YAML is the O0/O1 parity oracle: it may contradict nothing and it may
    not redefine anything. The check covers the COMPLETE pair — the canonical
    row (``Requirement -> Need``, inverse navigation) and the companion row
    (``Need -> Requirement``, forward traversal) — and verifies the
    pair-level invariants: one shared discriminator connection definition,
    identical typed roles, swapped domain/range and lineage sides, opposite
    query directions, identical semantic strength, and traversal of the same
    native connection witness (both rows resolve to the single
    ``DerivesFromNeed`` application definition; no second modeled fact).

    A drift in EITHER row fails generation naming the exact field. Returns
    the verified pair identity used to fill the projection row.
    """
    canonical, companion = _pair_oracle_rows(contract)

    canonical_direction = str(canonical.get("query_direction", ""))
    expected_companion_direction = _PAIR_DIRECTIONS.get(canonical_direction)
    if expected_companion_direction is None:
        raise ValueError(
            f"unsupported K query direction {canonical_direction!r} for "
            f"{_PREDICATE}; the pair direction vocabulary is "
            f"{sorted(_PAIR_DIRECTIONS)}"
        )

    # Side values come from the model-resolved end types; the traversal's
    # source/target lineage sides depend on the query direction (the same
    # mapping the traversal implementation consumes): inverse traversal
    # starts at the requirement side; forward traversal starts at the need
    # side.
    requirement_side = str(semantics["requirement_end_type"])
    need_side = str(semantics["need_end_type"])
    inverse_mode = canonical_direction == "inverse"
    source_side = requirement_side if inverse_mode else need_side
    target_side = need_side if inverse_mode else requirement_side

    expected_canonical = {
        "strategy": _DERIVATION_STRATEGY,
        "connection_definition": semantics["connection_definition"],
        "need_role": semantics["need_role"],
        "requirement_role": semantics["requirement_role"],
        "query_direction": semantics["query_direction"],
        "semantic_strength": semantics["semantic_strength"],
        "domain": semantics["domain"],
        "range": semantics["range"],
        "source_lineage_of": source_side,
        "target_lineage_of": target_side,
        "need_end_type_declaration": semantics["need_end_type_declaration"],
        "requirement_end_type_declaration": semantics[
            "requirement_end_type_declaration"
        ],
    }
    # The companion is the same single model fact navigated the other way:
    # swapped domain/range and lineage sides, opposite direction, identical
    # discriminator definition / roles / strength.
    expected_companion = {
        "strategy": expected_canonical["strategy"],
        "connection_definition": expected_canonical["connection_definition"],
        "need_role": expected_canonical["need_role"],
        "requirement_role": expected_canonical["requirement_role"],
        "query_direction": expected_companion_direction,
        "semantic_strength": expected_canonical["semantic_strength"],
        "domain": expected_canonical["range"],
        "range": expected_canonical["domain"],
        "source_lineage_of": expected_canonical["target_lineage_of"],
        "target_lineage_of": expected_canonical["source_lineage_of"],
        "need_end_type_declaration": expected_canonical["need_end_type_declaration"],
        "requirement_end_type_declaration": expected_canonical[
            "requirement_end_type_declaration"
        ],
    }

    drift: list[str] = []
    for predicate, oracle, expected in (
        (_PREDICATE, canonical, expected_canonical),
        (_INVERSE_PREDICATE, companion, expected_companion),
    ):
        for field, expected_value in expected.items():
            if not str(oracle.get(field, "")).strip():
                drift.append(
                    f"{predicate}.{field}: oracle value is missing/empty; the "
                    f"pair requires {expected_value!r}"
                )
            elif str(oracle[field]) != str(expected_value):
                drift.append(
                    f"{predicate}.{field}: oracle {oracle[field]!r} != "
                    f"expected {expected_value!r}"
                )

    # Pair invariants stated over the oracle rows themselves (redundant with
    # the comparisons above by construction, but kept explicit so every
    # pairwise drift names its own invariant).
    if str(canonical.get("connection_definition")) != str(
        companion.get("connection_definition")
    ):
        drift.append(
            "pair.connection_definition: the canonical and companion rows must "
            "resolve to the same discriminator connection witness"
        )
    for role_field in ("need_role", "requirement_role"):
        if str(canonical.get(role_field)) != str(companion.get(role_field)):
            drift.append(
                f"pair.{role_field}: both rows must use the same typed model role"
            )
    if str(canonical.get("semantic_strength")) != str(
        companion.get("semantic_strength")
    ):
        drift.append(
            "pair.semantic_strength: both rows must carry identical strength"
        )
    if (
        str(canonical.get("domain")) != str(companion.get("range"))
        or str(canonical.get("range")) != str(companion.get("domain"))
    ):
        drift.append(
            "pair.domain/range: the companion row must swap the canonical "
            "row's domain and range"
        )
    if (
        str(canonical.get("source_lineage_of")) != str(companion.get("target_lineage_of"))
        or str(canonical.get("target_lineage_of"))
        != str(companion.get("source_lineage_of"))
    ):
        drift.append(
            "pair.lineage: the companion row must swap the canonical row's "
            "source/target lineage sides"
        )
    if _PAIR_DIRECTIONS.get(str(companion.get("query_direction"))) != str(
        canonical.get("query_direction")
    ):
        drift.append(
            "pair.query_direction: the two rows must traverse the same "
            "witness in opposite directions"
        )

    if drift:
        raise ValueError(
            "ontology parity oracle drift for the K predicate pair "
            f"({_PREDICATE} / {_INVERSE_PREDICATE}): " + "; ".join(drift)
        )
    return {
        "predicate": _PREDICATE,
        "inverse_navigation_identity": _INVERSE_PREDICATE,
    }


def build_projection(
    contract: Any,
    kernel_bindings: Any,
    revision: RevisionIdentity,
    by_id: dict[str, dict[str, Any]],
    *,
    repository_root: Path,
    closure_attestation: ClosureAttestation | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate the v0 projection row from the validated model authority.

    Every semantic field published here is COPIED from the model-derived
    authority (``model_authority.model_semantics``); nothing is restated as a
    Python semantic literal. The authored ontology YAML is loaded only as the
    O0/O1 parity oracle: both rows of the K predicate pair are compared
    against the model-derived semantics and any unintended drift fails
    generation (F5).

    Fails closed when any grounding required by the slice is missing from the
    validated binding index, absent from the bound revision, or not stated by
    the model (UG-24). ``closure_attestation`` must be a structured,
    revision-bound ``ClosureAttestation`` (or an equivalent mapping); only a
    valid attestation matching the bound ``RevisionIdentity`` exactly turns
    ``support_state`` from ``vocabulary-only`` into ``supported``. A bare
    boolean is never a valid promotion mechanism.
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
    pair = _assert_oracle_parity(contract, semantics)
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
                    "claim_strength_witness": semantics[
                        "claim_strength_witness"
                    ],
                    "documentation_witness": semantics[
                        "documentation_witness"
                    ],
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
            "inverse_navigation_identity": pair["inverse_navigation_identity"],
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
            "support_state": _support_state(revision, closure_attestation),
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
    # The echoed closure/support state must stay in the honest vocabulary; it
    # is a projection-level decision echoed here, never re-made.
    support_echo = predicate.get("support_state_from_projection")
    if support_echo is not None and support_echo not in (
        "supported",
        "vocabulary-only",
    ):
        raise ValueError(
            f"profile support_state_from_projection {support_echo!r} is outside "
            "the honest support-state vocabulary for " + _PREDICATE
        )


def build_representation_profile(
    contract: Any,
    kernel_bindings: Any,
    revision: RevisionIdentity,
    by_id: dict[str, dict[str, Any]],
    *,
    repository_root: Path,
    closure_attestation: ClosureAttestation | dict[str, Any] | None = None,
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

    The closure/support decision is NOT re-made here: the profile delegates
    to :func:`build_projection` with the same ``closure_attestation``, so
    projection and profile generated from identical inputs cannot disagree
    on closure/support state (a supplied mismatched attestation fails both
    identically).
    """
    projection = build_projection(
        contract,
        kernel_bindings,
        revision,
        by_id,
        repository_root=repository_root,
        closure_attestation=closure_attestation,
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
            "(DerivesFromNeed; typed via authored FeatureTyping)",
            "property_paths": {
                "need_end": need_role,
                "requirement_end": requirement_role,
                "end_membership": (
                    "ownedRelationship[@type=EndFeatureMembership] "
                    "(memberName = end role)"
                ),
                "end_feature": (
                    "memberElement|ownedRelatedElement (synthesized end "
                    "Feature, isEnd=true)"
                ),
                "reference_subsetting": (
                    "ReferenceSubsetting.referencedFeature (authored; never "
                    "implied)"
                ),
                "connected_usage": (
                    "the ReferenceSubsetting target (or the end element itself "
                    "for legacy shapes)"
                ),
                "definition_typing": "FeatureTyping.type|general (authored)",
            },
            "supported_witness_forms": {
                "connection_assertion": [
                    "ConnectionUsage",
                    "authored FeatureTyping -> DerivesFromNeed (an implied "
                    "typing is not an authored derivation assertion)",
                    "EndFeatureMembership (memberName = need|derivedRequirement)",
                    "end Feature (isEnd=true)",
                    "authored ReferenceSubsetting",
                    "connected engineering usage",
                    "connected usage FeatureTyping -> candidate definition",
                    "Subclassification* -> governed Need|Requirement lineage",
                ],
                "definition_semantic_authority": [
                    "ConnectionDefinition DerivesFromNeed",
                    "FeatureMembership (object-shape EndFeatureMembership is a "
                    "compatible variant)",
                    "end Feature (isEnd=true) in authored membership order",
                    "authored FeatureTyping -> StakeholderNeedCandidate | "
                    "RequirementCandidate",
                    "owned Documentation via OwningMembership/memberElement "
                    "(direct documentation reference array is a compatible "
                    "variant)",
                ],
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
                "ConnectionUsage; each end membership owns a synthesized end "
                "Feature whose authored ReferenceSubsetting names the "
                "connected engineering usage; the connection is typed by the "
                "validated DerivesFromNeed application definition via an "
                "authored FeatureTyping"
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
                "ends, each end Feature's authored ReferenceSubsetting, the "
                "connected usage typings, and the definition FeatureTyping "
                "must survive official export, API import, and read-back; "
                "pruning any witness element makes the predicate unsupported "
                "for that revision (UG-06)"
            ),
        },
        "completeness_check": (
            "derivesRequirementFromNeed.derivation-connection-closure (fail "
            "closed: a validated binding for the DerivesFromNeed application "
            "definition is required, and a connection missing an end, with a "
            "missing/ambiguous/implied-only ReferenceSubsetting, with a "
            "connected usage outside the Need/Requirement lineages, or "
            "without the authored definition typing is not a derivation)"
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
            # Closure/support state is decided ONCE, in build_projection;
            # this echo lets a consumer read it without a second decision.
            "support_state_from_projection": predicate["support_state"],
        },
    }
    assert_profile_compatible(profile)
    return profile
