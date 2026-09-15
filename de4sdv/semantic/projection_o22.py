"""O2.2 additive extension: Semantic Projection v1.1 / API Representation Profile v1.1.

Second bounded generation stage of the semantic-authority migration. This
module is **additive**: it generates the machine-readable semantic
representation for exactly the three settled c2/c3 identities —

- ``VerificationCase`` (native verification-case construct),
- ``hasSubject`` (``Requirement -> MemberProduct`` subject relation),
- ``verifiedBy`` (``Requirement -> VerificationCase`` native
  verification-objective relation),

— as an **extension of the immutable O2.1 baseline**, never as a mutation of
it. The O2.1 artifacts (``semantic-projection-v1.json`` /
``api-representation-profile-v1.json`` bound to the permanent Stage A
revision produced by the #250 squash-merge) remain the canonical
representation of their seven identities; this module neither re-emits nor
re-binds them. The extension document binds the O2.1 baseline by path, schema,
source revision, and artifact digest (``extends`` block).

O2.2 identity scope and admission locks are imported from the frozen O2.1
module (``O2_SEQUENCING``); the extension must emit exactly
``o2.2 = (VerificationCase, hasSubject, verifiedBy)``, must not re-emit the
O2.1 seven, and must not emit any O2.3 identity or any guarded
retired/blocked/rename-required identity. The cumulative semantic surface
(O2.1 seven + O2.2 three) is exactly ten; the manifest and the frozen lock
must agree exactly (both directions).

Source-of-truth rule (O2.2, corrected after independent review):

- **model/contract-derived semantic core** — per identity, the projection
  derives ``identity``, ``semantic_kind``, domain, range (with the governed
  lineage anchor declarations), canonical engineering direction, semantic
  strength, the load-bearing scope restrictions, the native grounding
  identity at the semantic level, and model witness anchors from the
  validated authoritative representation: the reviewed representation
  contract (the governed ontology/kernel contract's declared entries,
  consumed read-only as the current permitted-interpretation authority for
  this unmigrated scope, locked against the reviewed O2.2 locks — drift
  fails closed) and the governed model declarations (located structurally,
  fail closed);
- **projection-schema / reviewed claim-boundary metadata** — the explicit
  negative laws and claim boundaries live in the projection-level
  ``projection_contract.identity_claim_boundaries`` block as SCHEMA-LEVEL
  reviewed contract metadata, never as per-row engineering-semantic fields.
  They are transcribed from the merged reviewed decisions and governing
  plans and machine-locked by tests; the generator reads no review artifact.

Separation discipline: the Semantic Projection carries WHAT the engineering
fact means; the SysML API Representation Profile carries HOW it appears in
the representation (witness strategies, membership types, property paths,
owner chains, direction extraction, reference bridging, resolution rules,
library grounding mechanics, API metaclasses, evidence). The compatibility
gate holds the profile to the projection through a per-identity
``semantic_contract_echo`` — representation mechanics never redefine domain,
range, canonical direction, semantic strength, scope restrictions, or claim
boundaries (UG-25 analogue).

Support state (established DE4SDV rule): without structured exact-revision
closure evidence, ``support_state`` is ``vocabulary-only``. Generation of a
row is NOT support promotion; an existing runtime mapping is NOT support
promotion; retained historical API evidence is NOT current exact-revision
closure. The extension therefore emits ``vocabulary-only`` for all rows, and
the existing runtime-mapping fact, where useful, is recorded only as
non-support profile metadata (``runtime_mapping_state =
existing-not-authority``).

Baseline anchoring (squash-safe, additive): the projection extension
independently extends the immutable O2.1 **projection** baseline; the
profile extension independently extends the immutable O2.1 **profile**
baseline. Each pin records and verifies path, schema, source revision, and
artifact digest; both baselines are bound inputs; a missing, wrong-schema,
revision-less, digest-changed, or non-ancestor baseline fails closed.

``api_binding`` stays explicitly ``unclaimed``: no current exact-revision API
closure exists (privileged/CI-owned); retained privileged runs remain
representation-shape evidence only, and standard-library anchors are
run-pinned evidence, never universal constants. Generation performs no
authority activation (O3 owns authority transition; O4 owns authored-ontology
retirement). The runtime does not read these artifacts.

Squash-safe delivery: Stage A (this module, its generator, the O2.2 admission
manifest, the design record, and the tests) is delivered first and
squash-merged; Stage B generates and commits the v1.1 artifacts bound to that
permanent revision and activates the repository gate. In a squash-only
repository a feature-branch commit never survives in ``main`` ancestry, so no
canonical artifact may bind to one.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .authority_inventory import (
    _DuplicateKeyLoader,
    canonical_json,
    file_digest,
    resolve_source_revision,
    validate_source_binding,
    verify_source_revision_contains_inputs,
    _git,
)
from .kernel_contract import KernelContract, KernelFileMapping
from .projection_v1 import (
    O21_ADMITTED_IDENTITIES,
    O21_EXCLUDED_IDENTITIES,
    O2_SEQUENCING,
    PROFILE_V1_SCHEMA,
    PROJECTION_V1_SCHEMA,
)

# ---------------------------------------------------------------------------
# Schema and artifact paths
# ---------------------------------------------------------------------------

PROJECTION_V11_SCHEMA = "de4sdv.semantic-projection.v1.1"
PROFILE_V11_SCHEMA = "de4sdv.api-representation-profile.v1.1"
ADMISSION_O22_SCHEMA_ID = "de4sdv.o2-2-admission/v1"

O2_DIRECTORY = "docs/method-conformance/o2"
ADMISSION_O22_PATH = f"{O2_DIRECTORY}/o22-admission.yaml"
PROJECTION_V11_JSON_PATH = f"{O2_DIRECTORY}/semantic-projection-v1.1.json"
PROFILE_V11_JSON_PATH = f"{O2_DIRECTORY}/api-representation-profile-v1.1.json"
BASELINE_PROJECTION_V1_PATH = f"{O2_DIRECTORY}/semantic-projection-v1.json"
BASELINE_PROFILE_V1_PATH = f"{O2_DIRECTORY}/api-representation-profile-v1.json"

ONTOLOGY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"

#: Program sources whose behavior produces the O2.2 artifacts. Every one is a
#: bound input; the O2.1 module is included because the extension imports its
#: frozen locks (any change requires rebinding both artifact families).
BOUND_INPUT_PROGRAM_PATHS_O22: tuple[str, ...] = (
    "de4sdv/semantic/projection_o22.py",
    "de4sdv/semantic/projection_v1.py",
    "de4sdv/semantic/authority_inventory.py",
    "de4sdv/semantic/kernel_contract.py",
    "scripts/generate_semantic_projection_o22.py",
)


class ProjectionO22Error(Exception):
    """Generation/validation failure for the O2.2 projection extension."""


# ---------------------------------------------------------------------------
# Machine-locked O2.2 admission boundary
# ---------------------------------------------------------------------------

#: The reviewed O2.2 admission boundary, read from the frozen O2 sequencing.
#: The manifest must agree with this lock exactly (order and set); the
#: emission path iterates this tuple only — new ontology/model entries cannot
#: expand the output.
O22_ADMITTED_IDENTITIES: tuple[str, ...] = O2_SEQUENCING["o2.2"]

_O22_ADMITTED_SET = frozenset(O22_ADMITTED_IDENTITIES)

#: Identities that must never appear in O2.2 output: the O2.1 seven (already
#: published in the immutable baseline; never re-emitted or re-bound), every
#: identity guarded by the O2.1 exclusion lock, and the O2.3 set — minus the
#: three admitted O2.2 identities. Machine-derived from the frozen locks so a
#: drifted guard set cannot be introduced silently.
O22_GUARDED_IDENTITIES: tuple[str, ...] = tuple(
    sorted(
        (set(O21_EXCLUDED_IDENTITIES) | set(O21_ADMITTED_IDENTITIES) | set(O2_SEQUENCING["o2.3"]))
        - _O22_ADMITTED_SET
    )
)

#: The cumulative reviewed O2 semantic surface after O2.2: the O2.1 seven plus
#: the O2.2 three = exactly ten identities, with no overlap.
O22_CUMULATIVE_SURFACE: tuple[str, ...] = tuple(O21_ADMITTED_IDENTITIES) + tuple(
    O22_ADMITTED_IDENTITIES
)

#: Reviewed predicate contract locks. The governed contract's declared values
#: for these fields were settled by the merged O1 c2/c3 decisions; a drift
#: means the reviewed boundary changed and requires explicit review — never a
#: silent regeneration.
_O22_PREDICATE_LOCKS: dict[str, dict[str, Any]] = {
    "hasSubject": {
        "domain": "Requirement",
        "range": "MemberProduct",
        "strategy": "subject-membership",
        "semantic_strength": "native-reference",
        "membership_types": ("SubjectMembership",),
    },
    "verifiedBy": {
        "domain": "Requirement",
        "range": "VerificationCase",
        "strategy": "verification-membership",
        "semantic_strength": "native-verification",
        "membership_types": ("RequirementVerificationMembership",),
    },
}

#: Reviewed class contract lock for the native verification-case construct:
#: the governed ontology entry must stay native (not file-mapped) and the
#: construct stays grounded in the pinned ``VerificationCases`` library
#: roles.
_O22_CLASS_LOCKS: dict[str, dict[str, Any]] = {
    "VerificationCase": {
        "grounding": "native",
        "definition_role": "VerificationCases::VerificationCase",
        "usage_role": "VerificationCases::verificationCases",
    },
}

#: Governed verification witness anchors (reviewed O2.2-owned locator data;
#: representation anchors only, never identity basis). The definition and its
#: usages are located structurally by declaration shape in the model file.
VERIFICATION_MODEL_FILE = (
    "textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml"
)
VERIFICATION_DEFINITION_NAME = "ConsciousOverrideVerification"

#: The established DE4SDV support-state rule: without structured
#: exact-revision closure evidence, ``support_state`` is ``vocabulary-only``.
#: Generation of a row is NOT support promotion; an existing runtime mapping
#: is NOT support promotion; retained historical API evidence is NOT current
#: exact-revision closure. No other support vocabulary exists in this module
#: and there is no promotion input anywhere.
SUPPORT_STATE_VOCABULARY_ONLY = "vocabulary-only"

#: Non-support implementation metadata recorded in the representation profile
#: (never in ``support_state``): the reviewed runtime mapping exists, but it
#: is not authority for these artifacts.
RUNTIME_MAPPING_STATE_EXISTING_NOT_AUTHORITY = "existing-not-authority"

#: Identity-resolution contract recorded for model witnesses and lineage
#: anchors (ADR 0011). Provenance/resolution metadata, never a semantic field.
_O22_IDENTITY_RESOLUTION = (
    "ingestion-validated kernel binding: exactly one API element whose "
    "declaredName and @type match the governed declaration and whose "
    "serializer-recorded source document equals the bound source file; "
    "multiple candidates are ambiguous and zero candidates is unresolved "
    "(both fail closed); the runtime consumes the resulting "
    "KernelElementBinding through KernelBindingIndex, never a name-based "
    "fallback"
)

_O22_LINEAGE_RESOLUTION = (
    "validated lineage proof over the representation-tolerant relationship "
    "graph: the element's authored typing/classification chain plus the "
    "tool-derived implied subsumption edges resolve to the governed lineage "
    "root through the ingestion-validated kernel binding "
    "(KernelBindingIndex.element_id_for); explicit and implied grounding "
    "provenance stay separate; a missing validated binding fails closed and "
    "no name/path/string fallback exists"
)

#: Reviewed negative-witness registry: the machine-locked negative laws of
#: the merged O1 c2/c3 reviews and the governing plans. This registry is the
#: reviewed source of the projection-contract claim boundaries
#: (:data:`PROJECTION_CONTRACT_O22` ``identity_claim_boundaries``): the
#: generated artifact serializes the laws as SCHEMA-LEVEL reviewed contract
#: metadata (never as per-row engineering-semantic fields), and tests
#: machine-lock the registry against the serialized boundaries. The O1 review
#: artifacts themselves are governance records and are never read at
#: generation.
_O22_NEGATIVE_WITNESSES: dict[str, tuple[str, ...]] = {
    "hasSubject": (
        "RequirementVerificationMembership",
        "generic untyped PartUsage",
        "a part merely named `memberProduct`",
        "a part typed by an unrelated same-named definition",
        "PLE selection or configuration membership",
        "allocation",
        "realization",
        "instantiation",
        "satisfaction",
        "verification success",
    ),
    "verifiedBy": (
        "generic Dependency",
        "SubjectMembership",
        "VerificationMethod metadata",
        "retained execution records",
        "evaluation records",
        "name-only correspondence",
        "verification-looking names",
    ),
}

#: Reviewed stronger-relation exclusions (claim boundary, expressed as the
#: closed set of relations this predicate is NOT).
_O22_STRONGER_RELATIONS: dict[str, tuple[str, ...]] = {
    "hasSubject": (
        "appliesToMemberProduct",
        "PLE selection",
        "configuration membership",
        "allocation",
        "realization",
        "instantiation",
        "satisfaction",
    ),
    "verifiedBy": (
        "execution occurrence",
        "evaluation result",
        "success or failure",
        "requirement satisfaction",
        "approval",
        "acceptance",
        "certification",
        "evidence validity or freshness",
    ),
}

#: Projection-schema contract (Unified Plan section 8.1): what extension rows
#: may claim and what they do not. Schema/projection metadata — model-derived
#: meaning lives only in each row's derived fields. The claim boundaries are
#: REVIEWED CONTRACT METADATA carried by this module (transcribed from the
#: merged reviewed decisions and the governing plans); they are explicitly a
#: schema-level block, never serialized as per-row engineering-semantic
#: fields, and the generator reads no review artifact at generation time.
PROJECTION_CONTRACT_O22: dict[str, Any] = {
    "semantic_scope": (
        "verification/subject identity definitions only: each row projects "
        "the reviewed declared contract of a class or predicate identity at "
        "the bound source revision; domain, range, canonical direction, "
        "semantic strength, native grounding identity, and the load-bearing "
        "scope restrictions are the identity's declared meaning"
    ),
    "does_not_assert": [
        "obligation satisfaction",
        "method-phase completion",
        "acceptance or approval decision",
        "evidence validity or freshness",
        "tested-scope equality",
        "evaluation success",
        "verification execution or results",
        "satisfaction of any verified requirement",
    ],
    "derivation_rule": (
        "fields in the projected semantic core are derived from the governed "
        "authoritative representation at the bound source revision; "
        "projection-schema claim boundaries, admission governance, "
        "representation-profile mechanics, and provenance metadata are "
        "explicitly separated and identified as such"
    ),
    "identity_claim_boundaries": {
        "hasSubject": {
            "claims": (
                "the queried requirement declares the returned member-product "
                "element as its subject through native subject-membership "
                "semantics, restricted to the governed Requirement -> "
                "MemberProduct lineages"
            ),
            "restrictions_are_meaning": (
                "the source and target restrictions are load-bearing semantic "
                "restrictions, not query conveniences; native SubjectMembership "
                "alone is not this predicate"
            ),
            "does_not_assert": [
                "that a native subject membership sourced outside the governed "
                "Requirement lineage establishes this relation (sibling "
                "lineages serialized as RequirementUsage do not)",
                "that a subject member outside the governed MemberProduct "
                "lineage establishes this relation (benches, increments, claim "
                "subjects, generic untyped part usages, parts merely named "
                "`memberProduct`, and parts typed by unrelated same-named "
                "definitions do not)",
                "that RequirementVerificationMembership is a witness of this "
                "relation",
                "selection, configuration membership, allocation, "
                "realization, instantiation, satisfaction, or verification "
                "success",
            ],
        },
        "verifiedBy": {
            "claims": (
                "the requirement is declared as a verification objective of "
                "the returned verification case through native verification "
                "semantics (declared verification-objective / coverage "
                "relation only)"
            ),
            "does_not_assert": [
                "that a generic Dependency establishes this relation",
                "that a SubjectMembership establishes this relation",
                "that VerificationMethod metadata establishes this relation",
                "that retained execution records or evaluation records "
                "establish this relation",
                "that name-only correspondence or verification-looking names "
                "establish this relation",
                "that a native membership whose anchored source cannot be "
                "machine-proven in the governed Requirement domain "
                "establishes this relation (unresolved anchors fail closed)",
                "execution occurrence or results, success or failure, "
                "requirement satisfaction, approval, acceptance, "
                "certification, or evidence validity or freshness",
            ],
        },
    },
    "external_artifact_treatment": (
        "external identities referenced by projected constructs (retained "
        "records, policies, registries) remain external; generation neither "
        "absorbs nor evaluates them"
    ),
    "runtime_boundary": (
        "generation is not authority activation; the runtime does not read "
        "this artifact; no support promotion occurs here and none exists as "
        "an input; authority transition is a separate reviewed stage (O3)"
    ),
}

# ---------------------------------------------------------------------------
# O2.2 admission manifest (governance boundary)
# ---------------------------------------------------------------------------


def load_admission_manifest_o22(path: Path) -> dict[str, Any]:
    """Load and shape-check the machine-locked O2.2 admission manifest."""
    if not path.is_file():
        raise ProjectionO22Error(f"O2.2 admission manifest not found: {path}")
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=_DuplicateKeyLoader)
    except ProjectionO22Error:
        raise
    except yaml.YAMLError as exc:
        raise ProjectionO22Error(
            f"O2.2 admission manifest is not valid YAML: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise ProjectionO22Error("O2.2 admission manifest must be a YAML mapping")
    if value.get("schema") != ADMISSION_O22_SCHEMA_ID:
        raise ProjectionO22Error(
            f"admission schema must be {ADMISSION_O22_SCHEMA_ID!r}, "
            f"got {value.get('schema')!r}"
        )
    return value


def validate_admission_o22(manifest: dict[str, Any]) -> None:
    """Machine-lock the O2.2 admission boundary; fail closed on any drift.

    Locks (each direction): admitted set equals the frozen o2.2 sequencing
    (order and set); the manifest's sequencing echo equals the frozen O2
    sequencing; the cumulative surface (o2.1 + o2.2) is exactly ten distinct
    identities; no identity is both admitted and guarded; every guarded entry
    carries a non-empty reason and a kind in {class, relationship}.
    """
    admitted = manifest.get("admitted")
    if not isinstance(admitted, list) or not all(
        isinstance(item, str) and item for item in admitted
    ):
        raise ProjectionO22Error(
            "admission manifest `admitted` must be a list of identities"
        )
    if tuple(admitted) != O22_ADMITTED_IDENTITIES:
        raise ProjectionO22Error(
            "admission manifest `admitted` does not equal the frozen O2.2 "
            f"lock: manifest={tuple(admitted)!r} "
            f"lock={O22_ADMITTED_IDENTITIES!r}"
        )

    sequencing = manifest.get("sequencing")
    if not isinstance(sequencing, dict) or set(sequencing) != set(O2_SEQUENCING):
        raise ProjectionO22Error(
            "admission manifest `sequencing` must echo exactly "
            f"{sorted(O2_SEQUENCING)}"
        )
    for phase, identities in O2_SEQUENCING.items():
        if tuple(sequencing.get(phase, ())) != identities:
            raise ProjectionO22Error(
                f"admission sequencing {phase!r} must equal {identities!r}"
            )
    union = tuple(
        identity
        for phase in ("o2.1", "o2.2", "o2.3")
        for identity in O2_SEQUENCING[phase]
    )
    if len(union) != 13 or len(set(union)) != 13:
        raise ProjectionO22Error(
            "the overall O2 admission must remain exactly 13 distinct identities"
        )
    if len(O22_CUMULATIVE_SURFACE) != 10 or len(set(O22_CUMULATIVE_SURFACE)) != 10:
        raise ProjectionO22Error(
            "the cumulative O2.1+O2.2 surface must be exactly ten distinct identities"
        )

    guarded = manifest.get("guarded")
    if not isinstance(guarded, list) or not guarded:
        raise ProjectionO22Error("admission manifest `guarded` must be a non-empty list")
    seen: set[str] = set()
    for entry in guarded:
        if not isinstance(entry, dict):
            raise ProjectionO22Error("guarded entries must be mappings")
        identity = str(entry.get("identity") or "")
        if not identity:
            raise ProjectionO22Error("guarded entry without an identity")
        if identity in seen:
            raise ProjectionO22Error(f"duplicate guarded identity {identity!r}")
        seen.add(identity)
        if entry.get("kind") not in {"class", "relationship"}:
            raise ProjectionO22Error(
                f"guarded identity {identity!r} must declare kind class|relationship"
            )
        if not str(entry.get("reason") or "").strip():
            raise ProjectionO22Error(f"guarded identity {identity!r} has no reason")
    if set(seen) != set(O22_GUARDED_IDENTITIES):
        raise ProjectionO22Error(
            "the manifest `guarded` set must equal the frozen O2.2 guard set: "
            f"manifest-only={sorted(set(seen) - set(O22_GUARDED_IDENTITIES))} "
            f"lock-only={sorted(set(O22_GUARDED_IDENTITIES) - set(seen))}"
        )
    both = set(admitted) & seen
    if both:
        raise ProjectionO22Error(
            f"identities both admitted and guarded: {sorted(both)}"
        )

# ---------------------------------------------------------------------------
# Model-side derivation (governed model + reviewed contract only)
# ---------------------------------------------------------------------------


def _matching_brace(text: str, open_index: int) -> int:
    """Index of the brace closing the one opened at ``open_index``."""
    from .projection_v1 import _matching_brace as _impl

    return _impl(text, open_index)


_SHORT_NAMED = re.compile(
    r"(?m)^[ \t]*verification(?P<def>\s+def\s+)?\s*<'(?P<short>[^']+)'>[ \t]*"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?P<specializes>[ \t]*:[ \t]*[A-Za-z_][A-Za-z0-9_]*)?[ \t]*"
)
_VERIFY_STATEMENT = re.compile(r"verify\s+([A-Za-z_][A-Za-z0-9_]*)\s*;")

#: The only text allowed between a governed anchor declaration and its body:
#: an optional typed specialization clause (``:> A, B`` / ``: A``).
_SPECIALIZATION_BETWEEN = re.compile(
    r"\s*(?::>|:)\s*[A-Za-z_][A-Za-z0-9_:]*(\s*,\s*[A-Za-z_][A-Za-z0-9_:]*)*\s*\Z"
)


def _locate_verification_constructs(text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Locate the reviewed verification definition and its usages structurally.

    A construct matches only as a braced ``verification [def] <'short'>
    name [: Specialization] {`` declaration with an ADJACENT body. The
    definition is the one without a specialization; usages must specialize
    the definition's declared name. Missing, duplicated, or malformed
    constructs fail closed.
    """
    definition: dict[str, Any] | None = None
    usages: list[dict[str, Any]] = []
    for match in _SHORT_NAMED.finditer(text):
        brace = text.find("{", match.end())
        if brace == -1 or text[match.end():brace].strip():
            raise ProjectionO22Error(
                "verification construct declaration without an adjacent body: "
                f"{match.group(0).strip()!r}"
            )
        close = _matching_brace(text, brace)
        block = text[brace:close + 1]
        record = {
            "declared_short_name": match.group("short"),
            "declaration": (
                ("verification def " if match.group("def") else "verification ")
                + match.group("name")
            ),
            "declared_name": match.group("name"),
            "specializes": (match.group("specializes") or "").lstrip(" \t:").strip() or None,
            "block": block,
        }
        if match.group("def"):
            if definition is not None:
                raise ProjectionO22Error(
                    "ambiguous verification definition grounding: multiple "
                    "verification def constructs found"
                )
            definition = record
        else:
            usages.append(record)
    if definition is None:
        raise ProjectionO22Error(
            "governed verification definition is not locatable in "
            f"{VERIFICATION_MODEL_FILE}; the model does not carry the "
            "reviewed verification construct"
        )
    if definition["declared_name"] != VERIFICATION_DEFINITION_NAME:
        raise ProjectionO22Error(
            "governed verification definition name drift: expected "
            f"{VERIFICATION_DEFINITION_NAME!r}, found "
            f"{definition['declared_name']!r}"
        )
    if definition["specializes"] is not None:
        raise ProjectionO22Error(
            "the governed verification definition must not carry a "
            "specialization; found "
            f"{definition['specializes']!r} — wrong structural identity"
        )
    qualified = [
        usage for usage in usages if usage["specializes"] == definition["declared_name"]
    ]
    foreign = [
        usage for usage in usages if usage["specializes"] != definition["declared_name"]
    ]
    if not qualified:
        raise ProjectionO22Error(
            "no verification usage specializes the governed verification "
            "definition; the reviewed witness population is unavailable"
        )
    if foreign:
        raise ProjectionO22Error(
            "verification usages outside the governed definition lineage: "
            f"{[usage['declared_short_name'] for usage in foreign]}"
        )
    return definition, qualified


def _locate_required_declaration(root: Path, file: str, declaration: str) -> str:
    """Locate one braced governed anchor declaration exactly once; fail closed.

    The anchor locator is O2.2-owned and bounded: the declaration line is
    matched by keyword + declared name at line start (same shape as the
    kernel contract's declarations), and the text between the name and the
    opening brace may contain ONLY an optional typed specialization clause
    (``:> A, B`` / ``: A``) — anything else is a malformed or interrupted
    declaration and fails closed. The declaration must occur exactly once;
    zero occurrences (missing/bodyless) and multiple occurrences (ambiguous
    grounding) both fail closed.
    """
    path = root / file
    if not path.is_file():
        raise ProjectionO22Error(f"model file not found: {file}")
    text = path.read_text(encoding="utf-8")
    kind, _, name = declaration.partition(" def ")
    pattern = re.compile(
        r"(?m)^[ \t]*(?:(?:public|private|protected)\s+)?(?:abstract\s+)?"
        + re.escape(kind.strip()).replace(r"\ ", r"\s+")
        + r"\s+def\s+"
        + re.escape(name.strip())
        + r"\b"
    )
    matches = list(pattern.finditer(text))
    if not matches:
        raise ProjectionO22Error(
            f"declaration {declaration!r} is not locatable as a braced "
            f"declaration in {file} (missing or bodyless); the model does not "
            "carry the lineage anchor"
        )
    if len(matches) > 1:
        raise ProjectionO22Error(
            f"declaration {declaration!r} occurs {len(matches)} times in "
            f"{file}; ambiguous grounding"
        )
    match = matches[0]
    brace = text.find("{", match.end())
    if brace == -1:
        raise ProjectionO22Error(
            f"declaration {declaration!r} in {file} has no braced body"
        )
    between = text[match.end():brace]
    if between.strip() and not _SPECIALIZATION_BETWEEN.fullmatch(between):
        raise ProjectionO22Error(
            f"declaration {declaration!r} in {file} is interrupted or "
            f"malformed between the declaration and its body: {between!r}"
        )
    close = _matching_brace(text, brace)
    return text[brace:close + 1]


def _contract_class_anchor(
    contract: KernelContract, root: Path, ontology_class: str, identity: str
) -> dict[str, str]:
    """Resolve one governed lineage anchor through the contract locators.

    The anchor declaration must be locatable in the governed model file
    exactly once (braced, adjacent body); a missing, bodyless, ambiguous, or
    malformed declaration fails closed — the lineage cannot be proven and no
    name/path fallback exists.
    """
    mapping = contract.mapping(ontology_class)
    if not isinstance(mapping, KernelFileMapping):
        raise ProjectionO22Error(
            f"{identity}: {ontology_class} is not file-mapped in the governed "
            "contract; the lineage anchor cannot be proven and generation "
            "fails closed (no name/path fallback exists)"
        )
    _locate_required_declaration(root, mapping.file, mapping.declaration)
    return {"file": mapping.file, "declaration": mapping.declaration}


def derive_verification_case_row(contract: KernelContract, root: Path) -> dict[str, Any]:
    """Derive the ``VerificationCase`` row from the reviewed native construct."""
    mapping = contract.mapping("VerificationCase")
    if isinstance(mapping, KernelFileMapping) or getattr(mapping, "native", None) is None:
        raise ProjectionO22Error(
            "VerificationCase: the governed contract entry is no longer the "
            "reviewed native grounding; contract drift requires explicit review"
        )
    model_path = root / VERIFICATION_MODEL_FILE
    if not model_path.is_file():
        raise ProjectionO22Error(
            f"verification witness file not found: {VERIFICATION_MODEL_FILE}"
        )
    definition, usages = _locate_verification_constructs(
        model_path.read_text(encoding="utf-8")
    )
    targets = _VERIFY_STATEMENT.findall(definition["block"])
    if not targets:
        raise ProjectionO22Error(
            "the governed verification definition carries no objective verify "
            "witness; the reviewed construct structure is unavailable"
        )
    return {
        "identity": "VerificationCase",
        "semantic_kind": "verification-case",
        "construct": {
            "kind": "native",
            "native_grounding": {
                "identity": (
                    "native verification-case construct (VerificationCase), "
                    "pinned standard library"
                ),
                "recorded_at": (
                    "semantic level only: representation mechanics, "
                    "representation identifiers, and grounding evidence for "
                    "this construct are recorded in the API Representation "
                    "Profile"
                ),
            },
        },
        "model_evidence": {
            "definition": {
                "source_file": VERIFICATION_MODEL_FILE,
                "declared_short_name": definition["declared_short_name"],
                "declaration": definition["declaration"],
                "objective_verify_targets": list(targets),
                "objective_note": (
                    "the definition's objective carries the requirement "
                    "verification witnesses; usages inherit the objective"
                ),
            },
            "usages": [
                {
                    "source_file": VERIFICATION_MODEL_FILE,
                    "declared_short_name": usage["declared_short_name"],
                    "declaration": usage["declaration"],
                    "specializes": usage["specializes"],
                }
                for usage in usages
            ],
        },
        "support_state": SUPPORT_STATE_VOCABULARY_ONLY,
    }


def derive_relationship_row(
    identity: str, contract: KernelContract, root: Path, vc_row: dict[str, Any]
) -> dict[str, Any]:
    """Derive one predicate row from the reviewed relationship contract."""
    lock = _O22_PREDICATE_LOCKS[identity]
    mapping = contract.relationship_mapping(identity)
    if (
        mapping.domain != lock["domain"]
        or mapping.range != lock["range"]
        or mapping.strategy != lock["strategy"]
        or mapping.semantic_strength != lock["semantic_strength"]
    ):
        raise ProjectionO22Error(
            f"{identity}: the governed contract's declared domain/range/"
            "strategy/strength no longer matches the reviewed O2.2 lock "
            f"(contract: domain={mapping.domain!r} range={mapping.range!r} "
            f"strategy={mapping.strategy!r} strength={mapping.semantic_strength!r}); "
            "contract drift requires explicit review, never silent regeneration"
        )
    membership_types = mapping.configuration.get("membership_types")
    if (
        not isinstance(membership_types, list)
        or tuple(membership_types) != lock["membership_types"]
    ):
        raise ProjectionO22Error(
            f"{identity}: declared membership witnesses {membership_types!r} do "
            f"not match the reviewed witness lock {lock['membership_types']!r}"
        )
    if identity == "hasSubject":
        domain_anchor = _contract_class_anchor(contract, root, "Requirement", identity)
        range_anchor = _contract_class_anchor(contract, root, "MemberProduct", identity)
        range_side: dict[str, Any] = {
            "ontology_class": "MemberProduct",
            "lineage": dict(range_anchor),
        }
        native_grounding = {
            "native_construct": "SubjectMembership",
            "note": (
                "native subject semantics are the grounding identity, "
                "narrowed by the declared scope restrictions; the "
                "representation mechanics for this witness are recorded in "
                "the API Representation Profile"
            ),
        }
        scope_restrictions = [
            {
                "axis": "source",
                "restriction": (
                    "the source must machine-resolve into the governed "
                    "Requirement lineage"
                ),
                "meaning": (
                    "part of the predicate's meaning, not a query convenience: "
                    "sibling lineages serialized as RequirementUsage are not "
                    "this predicate's sources"
                ),
            },
            {
                "axis": "target",
                "restriction": (
                    "the subject member must machine-resolve into the governed "
                    "MemberProduct lineage"
                ),
                "meaning": (
                    "part of the predicate's meaning: native subjects outside "
                    "the member-product lineage are not this predicate's targets"
                ),
            },
        ]
    else:
        if vc_row.get("identity") != "VerificationCase":
            raise ProjectionO22Error(
                "verifiedBy: the range row reference is not the VerificationCase "
                "concept row; range grounding fails closed"
            )
        domain_anchor = _contract_class_anchor(contract, root, "Requirement", identity)
        range_side = {
            "ontology_class": "VerificationCase",
            "native": True,
            "row_ref": "VerificationCase",
        }
        native_grounding = {
            "native_construct": "RequirementVerificationMembership",
            "note": (
                "declared verification-objective semantics are the grounding "
                "identity (coverage relation only); the representation "
                "mechanics for this witness are recorded in the API "
                "Representation Profile"
            ),
        }
        scope_restrictions = [
            {
                "axis": "source",
                "restriction": (
                    "the anchored source must be machine-proven in the "
                    "governed Requirement domain"
                ),
                "meaning": (
                    "the declared predicate domain is enforced: a native "
                    "membership whose source cannot be proven in the "
                    "Requirement domain is not this predicate's fact; "
                    "unresolved anchors fail closed"
                ),
            }
        ]

    return {
        "identity": identity,
        "semantic_kind": "relationship",
        "relation": {
            "domain": {
                "ontology_class": "Requirement",
                "lineage": dict(domain_anchor),
            },
            "range": range_side,
            "canonical_direction": f"{lock['domain']} -> {lock['range']}",
            "inverse_navigation": (
                "inverse queries reverse traversal direction only; the "
                "modeled fact is the declared canonical direction"
            ),
            "semantic_strength": lock["semantic_strength"],
            "native_grounding": native_grounding,
            "scope_restrictions": scope_restrictions,
        },
        "support_state": SUPPORT_STATE_VOCABULARY_ONLY,
    }

# ---------------------------------------------------------------------------
# Binding collection and the extends (baseline) block
# ---------------------------------------------------------------------------


def collect_bound_inputs_o22(root: Path, contract: KernelContract) -> dict[str, str]:
    """Every source consumed to produce the extension artifacts.

    Program inputs are declared in :data:`BOUND_INPUT_PROGRAM_PATHS_O22`; data
    inputs are the O2.2 admission manifest, the ontology/kernel contract
    (locators only), the baseline O2.1 projection (the extension's
    ``extends`` target), the governed lineage-anchor model files, and the
    governed verification witness file. Derived mechanically so a changed
    membership cannot silently drop an input.
    """
    paths: set[str] = set(BOUND_INPUT_PROGRAM_PATHS_O22)
    paths.add(ADMISSION_O22_PATH)
    paths.add(ONTOLOGY_PATH)
    paths.add(BASELINE_PROJECTION_V1_PATH)
    paths.add(BASELINE_PROFILE_V1_PATH)
    paths.add(VERIFICATION_MODEL_FILE)
    for ontology_class in ("Requirement", "MemberProduct"):
        mapping = contract.mapping(ontology_class)
        if isinstance(mapping, KernelFileMapping):
            paths.add(mapping.file)
    inputs: dict[str, str] = {}
    for path in sorted(paths):
        file = root / path
        if not file.is_file():
            raise ProjectionO22Error(f"bound input missing: {path}")
        inputs[path] = file_digest(root, path)
    return inputs


def read_baseline_pins(root: Path) -> dict[str, dict[str, Any]]:
    """Build the two independent ``extends`` pins from the v1 baselines.

    The Semantic Projection extension extends the Semantic Projection
    baseline; the API Representation Profile extension independently extends
    the API Representation Profile baseline. Each pin records and verifies
    the baseline's artifact path, schema, source revision, and artifact
    digest — fail closed on a missing, unreadable, wrong-schema, or
    revision-less baseline. The two baselines happen to share one source
    revision today, but each pin records its own; nothing assumes equality.
    """
    pins: dict[str, dict[str, Any]] = {}
    for key, artifact_path, expected_schema in (
        ("projection", BASELINE_PROJECTION_V1_PATH, PROJECTION_V1_SCHEMA),
        ("profile", BASELINE_PROFILE_V1_PATH, PROFILE_V1_SCHEMA),
    ):
        pins[key] = _read_baseline_pin(root, artifact_path, expected_schema)
    return pins


def _read_baseline_pin(
    root: Path, artifact_path: str, expected_schema: str
) -> dict[str, Any]:
    import json

    path = root / artifact_path
    if not path.is_file():
        raise ProjectionO22Error(
            f"O2.1 baseline not found: {artifact_path}; the extension cannot "
            "anchor to an unpublished baseline"
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ProjectionO22Error(
            f"O2.1 baseline {artifact_path} is not readable JSON: {exc}"
        ) from exc
    if document.get("schema") != expected_schema:
        raise ProjectionO22Error(
            f"O2.1 baseline {artifact_path} schema mismatch: expected "
            f"{expected_schema!r}, found {document.get('schema')!r}"
        )
    baseline_revision = (document.get("binding") or {}).get("source_revision")
    if not isinstance(baseline_revision, str) or len(baseline_revision) != 40:
        raise ProjectionO22Error(
            f"O2.1 baseline {artifact_path} does not record a full-commit "
            "binding.source_revision"
        )
    return {
        "artifact": artifact_path,
        "schema": expected_schema,
        "source_revision": baseline_revision,
        "artifact_digest": file_digest(root, artifact_path),
        "note": (
            "Additive extension of this immutable O2.1 baseline: the baseline "
            "remains canonical for its own content and is neither re-emitted "
            "nor re-bound here. The recorded digest pins the baseline bytes "
            "this extension was generated against; the baseline's own "
            "repository gate validates its revision binding, and the "
            "extension gate additionally requires the baseline source "
            "revision to remain an ancestor of the extension source revision."
        ),
    }


# ---------------------------------------------------------------------------
# Artifact assembly
# ---------------------------------------------------------------------------


def _binding_block_o22(
    root: Path,
    source_revision: str,
    bound_inputs: dict[str, str],
) -> dict[str, Any]:
    """Revision binding shared by the extension projection and profile."""
    program_inputs = sorted(BOUND_INPUT_PROGRAM_PATHS_O22)
    return {
        "source_revision": source_revision,
        "source_revision_note": (
            "Git commit that contains every bound input byte-for-byte. The "
            "gate validates commit existence, ancestry of the checked-out "
            "revision, per-input content equality, and the recorded content "
            "digests - a stale revision cannot pass by string reuse."
        ),
        "artifact_commit": None,
        "artifact_commit_note": (
            "The commit that introduces these artifacts cannot be known when "
            "they are generated; left explicitly unclaimed."
        ),
        "generation_software": {
            "program_inputs": program_inputs,
            "note": (
                "Generation-software revision: the commit containing these "
                "program inputs byte-for-byte (including the frozen O2.1 "
                "module whose locks this extension imports). Distinguished "
                "from the semantic-model revision so generator changes are "
                "never confused with model or contract changes."
            ),
        },
        "semantic_model_revision": {
            "model_inputs": sorted(
                {
                    path
                    for path in bound_inputs
                    if path
                    not in set(BOUND_INPUT_PROGRAM_PATHS_O22)
                    | {
                        ADMISSION_O22_PATH,
                        ONTOLOGY_PATH,
                        BASELINE_PROJECTION_V1_PATH,
                        BASELINE_PROFILE_V1_PATH,
                    }
                }
            ),
            "note": (
                "Semantic-model revision: the governed model declarations "
                "and the reviewed contract files these artifacts were "
                "generated from, contained byte-for-byte in source_revision. "
                "The ontology/kernel contract supplies the reviewed declared "
                "predicate contract and declaration locators; the model files "
                "carry the lineage anchors and the governed verification "
                "constructs."
            ),
        },
        "api_binding": {
            "status": "unclaimed",
            "note": (
                "O2.2 produces no validated SysML API project/commit closure "
                "and claims no current API element UUID. Element identity is "
                "resolved at a bound API revision through ingestion-validated "
                "kernel bindings (KernelBindingIndex, fail closed); the "
                "exact-revision API closure belongs to the privileged "
                "ingestion path and a later reviewed step. Retained "
                "privileged-run evidence is representation-shape evidence "
                "only, and the pinned standard-library anchor evidence is "
                "run-pinned, never a universal constant."
            ),
        },
        "admission_manifest": {
            "path": ADMISSION_O22_PATH,
            "digest": bound_inputs[ADMISSION_O22_PATH],
        },
        "ontology_contract_locator": {
            "path": ONTOLOGY_PATH,
            "digest": bound_inputs[ONTOLOGY_PATH],
        },
        "baseline_projection": {
            "path": BASELINE_PROJECTION_V1_PATH,
            "digest": bound_inputs[BASELINE_PROJECTION_V1_PATH],
        },
        "baseline_profile": {
            "path": BASELINE_PROFILE_V1_PATH,
            "digest": bound_inputs[BASELINE_PROFILE_V1_PATH],
        },
        "bound_inputs": bound_inputs,
    }


def _scope_block_o22(manifest: dict[str, Any]) -> dict[str, Any]:
    """The machine-locked O2.2 admission boundary, echoed for reviewability."""
    return {
        "admission": (
            "O2.2 additive generation stage (settled c2/c3 verification and "
            "subject identities)"
        ),
        "admitted": list(O22_ADMITTED_IDENTITIES),
        "sequencing": {
            phase: list(identities) for phase, identities in O2_SEQUENCING.items()
        },
        "cumulative_surface": {
            "o2_1": list(O21_ADMITTED_IDENTITIES),
            "o2_2": list(O22_ADMITTED_IDENTITIES),
            "total": len(O22_CUMULATIVE_SURFACE),
            "note": (
                "Cumulative reviewed O2 semantic surface: the O2.1 seven (in "
                "the immutable v1 baseline) plus the O2.2 three (in this "
                "extension) = exactly ten distinct identities; the O2.3 set "
                "remains absent."
            ),
        },
        "guarded": [
            {
                "identity": str(entry["identity"]),
                "kind": str(entry["kind"]),
                "reason": " ".join(str(entry["reason"]).split()),
            }
            for entry in manifest["guarded"]
        ],
        "admission_note": (
            "Machine-locked reviewed migration boundary: the emission path "
            "iterates the admitted set only (no heuristic query); an extra "
            "identity, a missing admitted identity, an O2.3 identity, or a "
            "re-emission of the O2.1 baseline set is a generation failure."
        ),
    }


def _profile_entry_o22(row: dict[str, Any], contract: KernelContract) -> dict[str, Any]:
    """Per-identity representation profile (mechanics, keyed to semantics).

    All serializer/API mechanics live here: witness strategies, membership
    types, property paths, owner chains, direction extraction, reference
    bridging, resolution rules, library grounding mechanics, metaclasses, and
    evidence. The entry echoes the projection's semantic contract as
    ``semantic_contract_echo``; the compatibility gate fails closed if the
    echo contradicts the projection — mechanics can never redefine meaning.
    """
    identity = row["identity"]
    if identity == "VerificationCase":
        lock = _O22_CLASS_LOCKS["VerificationCase"]
        return {
            "profile_identity": f"{PROFILE_V11_SCHEMA}#{identity}",
            "for_identity": identity,
            "representation_class": "native-verification-construct",
            "semantic_contract_echo": {
                "native_grounding": row["construct"]["native_grounding"]["identity"],
            },
            "library_grounding_mechanics": {
                "definition_role": {
                    "library_identity": lock["definition_role"],
                    "mechanism": "implied Subclassification",
                    "provenance": "implied",
                    "applies_to": "VerificationCaseDefinition",
                },
                "usage_role": {
                    "library_identity": lock["usage_role"],
                    "mechanism": "implied Subsetting",
                    "provenance": "implied",
                    "applies_to": "VerificationCaseUsage",
                },
                "library_proof_step": (
                    "controlled standard-library proof: the licensed exporter "
                    "resolves the pinned library anchors by their qualified "
                    "names from the pinned Systems Library/VerificationCases.sysml "
                    "document and records the resolved anchor identities in the "
                    "export artifact; the read-back proves each implied edge "
                    "targets exactly the recorded anchor with a uri into that "
                    "document. The qualified names are used only by this "
                    "controlled proof step — never as a general identity "
                    "fallback."
                ),
                "anchor_policy": (
                    "run-pinned anchor evidence, not universal constants: no "
                    "library UUID is recorded as a stable identity across "
                    "revisions"
                ),
                "evidence": {
                    "kind": "retained privileged full-model API ingestion run",
                    "run": "34576049742",
                    "candidate_revision": "0a23902370de9fc74d6118afe480382e0b0d8aa0",
                    "artifact": (
                        "full-model-api-ingestion-"
                        "0a23902370de9fc74d6118afe480382e0b0d8aa0"
                    ),
                    "scope": (
                        "standard-library grounding shape evidence only "
                        "(implied edge shapes and metaclass separation); not "
                        "a current exact-revision API closure"
                    ),
                },
            },
            "api_metaclasses": [
                "VerificationCaseDefinition",
                "VerificationCaseUsage",
            ],
            "api_metaclass_note": (
                "recorded separately from the standard-library grounding; the "
                "metaclass alone is not the semantic proof (UG-28)"
            ),
            "resolution": {"identity": _O22_IDENTITY_RESOLUTION},
            "witness_forms": [
                "definition: toolchain-materialized implied Subclassification "
                "to the library definition anchor (general|superclassifier "
                "external reference; provenance implied)",
                "usage: implied Subsetting to the library base-feature anchor "
                "(provenance implied)",
                "objective: the definition's objective owns the verify "
                "targets through requirement-verification memberships "
                "inherited by the usages",
            ],
        }
    mapping = contract.relationship_mapping(identity)
    strategy = mapping.strategy
    locked_witnesses = list(_O22_PREDICATE_LOCKS[identity]["membership_types"])
    if identity == "hasSubject":
        witness_forms = [
            "SubjectMembership serializes with memberElement (the subject) "
            "and owningRelatedElement (the owner); memberName and "
            "ownedRelatedElement are compatible shapes",
            "the subject member may serialize as ReferenceUsage or PartUsage; "
            "the member's authored FeatureTyping carries the product-line "
            "typing",
            "lineage enforcement runs through the validated kernel binding "
            "index and the representation-tolerant relationship graph; "
            "explicit versus implied grounding provenance is preserved",
            "a corrupted configuration (missing declared lineage) refuses to "
            "run instead of degrading silently",
        ]
        serializer_mechanics = {
            "strategy": strategy,
            "membership_types": locked_witnesses,
            "member_property": mapping.configuration.get("member_property"),
            "owner_types": list(mapping.configuration.get("owner_types") or ()),
        }
    else:
        witness_forms = [
            "RequirementVerificationMembership anchors the verified "
            "requirement through verifiedRequirement (derived; redefines "
            "referencedConstraint), with the ReferenceSubsetting "
            "shadow-reference bridge where the serializer references a "
            "shadow usage",
            "the case is resolved from the membership's ownership chain "
            "(owner membership types FeatureMembership, OwningMembership, "
            "ObjectiveMembership, RequirementVerificationMembership), "
            "stopping only at a VerificationCaseUsage or "
            "VerificationCaseDefinition",
            "direction extraction is reverse: the canonical Requirement -> "
            "VerificationCase navigation reads the single native witness "
            "backwards; the modeled fact never reverses",
            "source-domain identity rule: candidate-first; direct "
            "Requirement-lineage grounding or the reviewed shadow bridge "
            "followed by the lineage proof; unresolved anchors fail closed; "
            "never name-based",
        ]
        serializer_mechanics = {
            "strategy": strategy,
            "membership_types": locked_witnesses,
            "reference_property": mapping.configuration.get("reference_property"),
            "direction": mapping.configuration.get("direction"),
            "element_types": list(mapping.configuration.get("element_types") or ()),
            "owner_membership_types": list(
                mapping.configuration.get("owner_membership_types") or ()
            ),
        }
    return {
        "profile_identity": f"{PROFILE_V11_SCHEMA}#{identity}",
        "for_identity": identity,
        "representation_class": f"{strategy}-relationship",
        "semantic_contract_echo": {
            "domain": row["relation"]["domain"]["ontology_class"],
            "range": row["relation"]["range"]["ontology_class"],
            "canonical_direction": row["relation"]["canonical_direction"],
            "semantic_strength": row["relation"]["semantic_strength"],
            "scope_restrictions": [
                entry["restriction"] for entry in row["relation"]["scope_restrictions"]
            ],
        },
        "serializer_mechanics": serializer_mechanics,
        "resolution": {
            "identity": _O22_IDENTITY_RESOLUTION,
            "lineage": _O22_LINEAGE_RESOLUTION,
        },
        "witness_forms": witness_forms,
        "mechanics_refs": {
            "runtime_strategy": strategy,
            "lineage_resolver": (
                "validated lineage proof through the kernel binding index and "
                "the representation-tolerant relationship graph (fail closed)"
            ),
        },
        "runtime_mapping_state": RUNTIME_MAPPING_STATE_EXISTING_NOT_AUTHORITY,
    }


def _representation_contract_o22() -> dict[str, Any]:
    """The O2.2 representation mechanics, witnessed by the evidence basis."""
    return {
        "identity_resolution": {
            "rule": _O22_IDENTITY_RESOLUTION,
            "prohibited_fallbacks": [
                "declaredName alone",
                "qualifiedName alone",
                "package path",
                "source filename",
                "doc text",
                "string matching",
            ],
        },
        "lineage_resolution": _O22_LINEAGE_RESOLUTION,
        "verification_case_mechanics": (
            "definition/usage resolution through the verification-membership "
            "strategy: the membership anchors on the verified requirement and "
            "the case is resolved from the ownership chain, stopping only at "
            "a VerificationCaseUsage or VerificationCaseDefinition; the "
            "standard-library roles stay visible as implied grounding edges"
        ),
        "subject_membership_mechanics": (
            "the subject witness is the configured SubjectMembership member "
            "(memberElement) of the owning requirement usage; both the owner "
            "and the member are resolved through the validated lineages "
            "before a hop is emitted"
        ),
        "library_anchor_mechanics": (
            "the pinned standard-library anchors are resolved only by the "
            "controlled library-proof step (licensed exporter reading the "
            "pinned library documents) and are run-pinned evidence; the "
            "qualified names used there never become a general identity "
            "fallback and no library UUID is recorded as a universal constant"
        ),
        "serializer_importer_compatibility": {
            "uuid_preservation": "single-transaction-required",
            "known_omissions": [],
            "out_of_export_risk": (
                "the verification constructs, their memberships and member "
                "elements, the lineage anchors, and the implied library edges "
                "must survive official export, API import, and read-back; "
                "pruning any required witness makes the identity unsupported "
                "for that revision"
            ),
        },
        "completeness_check": (
            "fail closed: a missing or drifted contract entry, a missing or "
            "ambiguous model witness, a missing lineage anchor declaration, "
            "no objective verify witness, or a foreign verification usage "
            "blocks generation for that identity"
        ),
    }


def assert_profile_compatible_o22(
    projection: dict[str, Any], profile: dict[str, Any]
) -> None:
    """Compatibility gate: mechanics must not contradict the projection.

    Strengthened (O2.2 review corrections): the profile's per-identity
    ``semantic_contract_echo`` must equal the projection's semantic contract
    (domain, range, canonical direction, semantic strength, scope
    restrictions; the native grounding identity for the construct), so
    representation mechanics can never redefine meaning; and every row must
    carry the established ``vocabulary-only`` support state — there is no
    promotion path and no other support vocabulary.
    """
    projection_rows = list(projection["concepts"]) + list(projection["predicates"])
    projection_by_identity = {row["identity"]: row for row in projection_rows}
    profile_by_identity = {entry["for_identity"]: entry for entry in profile["profiles"]}
    if set(projection_by_identity) != set(profile_by_identity):
        raise ProjectionO22Error(
            "profile identities do not match the projection identities: "
            f"projection-only={sorted(set(projection_by_identity) - set(profile_by_identity))} "
            f"profile-only={sorted(set(profile_by_identity) - set(projection_by_identity))}"
        )
    for identity, row in projection_by_identity.items():
        if row["support_state"] != SUPPORT_STATE_VOCABULARY_ONLY:
            raise ProjectionO22Error(
                f"{identity}: support state {row['support_state']!r} violates "
                "the established rule (without structured exact-revision "
                "closure evidence, support_state is vocabulary-only)"
            )
        entry = profile_by_identity[identity]
        echo = entry["semantic_contract_echo"]
        if identity == "VerificationCase":
            expected = row["construct"]["native_grounding"]["identity"]
            if echo["native_grounding"] != expected:
                raise ProjectionO22Error(
                    "VerificationCase: the profile's echoed semantic contract "
                    "contradicts the projection's native grounding identity"
                )
        else:
            relation = row["relation"]
            expected = {
                "domain": relation["domain"]["ontology_class"],
                "range": relation["range"]["ontology_class"],
                "canonical_direction": relation["canonical_direction"],
                "semantic_strength": relation["semantic_strength"],
                "scope_restrictions": [
                    item["restriction"] for item in relation["scope_restrictions"]
                ],
            }
            if echo != expected:
                raise ProjectionO22Error(
                    f"{identity}: the representation profile's echoed semantic "
                    "contract contradicts the projection — mechanics cannot "
                    "redefine domain, range, canonical direction, semantic "
                    "strength, scope restrictions, or claim boundaries"
                )


def _build_pair_o22(
    root: Path,
    *,
    source_revision: str | None = None,
    manifest: dict[str, Any] | None = None,
    contract: KernelContract | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build both extension artifacts over identical inputs."""
    if manifest is None:
        manifest = load_admission_manifest_o22(root / ADMISSION_O22_PATH)
    validate_admission_o22(manifest)
    if contract is None:
        contract = KernelContract.load(root / ONTOLOGY_PATH)
    if source_revision is None:
        source_revision = resolve_source_revision(root)
    bound_inputs = collect_bound_inputs_o22(root, contract)
    verify_source_revision_contains_inputs(root, source_revision, bound_inputs)
    baseline_pins = read_baseline_pins(root)

    vc_row = derive_verification_case_row(contract, root)
    predicate_rows = [
        derive_relationship_row(identity, contract, root, vc_row)
        for identity in ("hasSubject", "verifiedBy")
    ]

    emitted = (vc_row["identity"],) + tuple(row["identity"] for row in predicate_rows)
    if emitted != O22_ADMITTED_IDENTITIES:
        raise ProjectionO22Error(
            f"emitted identities {emitted!r} do not equal the frozen O2.2 "
            f"admission {O22_ADMITTED_IDENTITIES!r}"
        )
    leaked = sorted(set(emitted) & set(O22_GUARDED_IDENTITIES))
    if leaked:
        raise ProjectionO22Error(
            f"guarded identities leaked into O2.2 output: {leaked}"
        )

    binding = _binding_block_o22(root, source_revision, bound_inputs)
    projection = {
        "schema": PROJECTION_V11_SCHEMA,
        "status": (
            "generated O2.2 additive semantic projection extension "
            "(three settled c2/c3 identities)"
        ),
        "warning": (
            "Generated artifact. Additive extension of the immutable O2.1 "
            "semantic-projection baseline (see `extends`). Generation is NOT "
            "authority activation: this projection does not switch runtime "
            "dispatch, does not retire authored contract authority, and "
            "promotes no support state. The O1 migration inventory is "
            "governance, never semantic authority, and is not read by this "
            "generator. The runtime does not read this artifact. Fields in "
            "the projected semantic core are derived from the governed "
            "authoritative representation; projection-schema claim "
            "boundaries, admission governance, representation-profile "
            "mechanics, and provenance metadata are explicitly separated and "
            "identified as such. Generated by "
            "scripts/generate_semantic_projection_o22.py."
        ),
        "extends": baseline_pins["projection"],
        "binding": binding,
        "scope": _scope_block_o22(manifest),
        "projection_contract": dict(PROJECTION_CONTRACT_O22),
        "concepts": [vc_row],
        "predicates": predicate_rows,
    }
    profile = {
        "schema": PROFILE_V11_SCHEMA,
        "profile_version": "v1.1",
        "status": (
            "generated O2.2 SysML API Representation Profile extension "
            "(representation mechanics for the three settled c2/c3 identities)"
        ),
        "warning": (
            "Generated artifact. Representation mechanics only: this profile "
            "cannot redefine domain, range, canonical direction, semantic "
            "strength, scope restrictions, exclusions, or claim boundaries - "
            "those live in the Semantic Projection (the per-identity "
            "`semantic_contract_echo` is held to them by the compatibility "
            "gate). No current SysML API project/commit closure was produced "
            "and no current API element UUID is claimed; retained privileged "
            "runs are representation-shape evidence only and the "
            "standard-library anchors are run-pinned, never universal "
            "constants. The runtime does not read this artifact."
        ),
        "extends": baseline_pins["profile"],
        "binding": binding,
        "evidence_basis": {
            "kind": "retained privileged full-model API ingestion run",
            "run": "34576049742",
            "artifact": "10195168006",
            "candidate_revision": "0a23902370de9fc74d6118afe480382e0b0d8aa0",
            "scope": (
                "Serializer representation shapes only (membership kinds, "
                "property paths, implied library edges, shadow-reference "
                "bridges). Not a current exact-revision API closure and not a "
                "semantic source for generation."
            ),
        },
        "representation_contract": _representation_contract_o22(),
        "profiles": [
            _profile_entry_o22(row, contract) for row in [vc_row, *predicate_rows]
        ],
    }
    assert_profile_compatible_o22(projection, profile)
    return projection, profile


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def build_pair_o22(
    root: Path,
    *,
    source_revision: str | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build both extension artifacts from the given checkout."""
    projection, profile = _build_pair_o22(
        root, source_revision=source_revision, manifest=manifest
    )
    return {"projection": projection, "profile": profile}


# ---------------------------------------------------------------------------
# Committed-artifact consistency gate (--check)
# ---------------------------------------------------------------------------


def run_check_errors_o22(root: Path) -> list[str]:
    """Check that the extension artifacts equal regeneration from inputs.

    Validates the recorded source-revision binding (commit existence,
    ancestry, per-input content equality, recorded digests), the two
    INDEPENDENT baseline anchors (each extension must extend its own v1
    baseline: path/schema/source revision/digest — digest equality against
    the committed baseline bytes and baseline-source-revision ancestry), then
    regenerates with the recorded source revision and compares bytes for both
    artifacts. Absent artifacts are reported as errors — nothing is silently
    passed. Stage A does not register this gate in ``check_repo``; Stage B
    registers it together with the artifacts.
    """
    import json

    errors: list[str] = []
    projection_path = root / PROJECTION_V11_JSON_PATH
    profile_path = root / PROFILE_V11_JSON_PATH
    if not projection_path.is_file():
        errors.append(f"semantic projection v1.1 missing: {PROJECTION_V11_JSON_PATH}")
    if not profile_path.is_file():
        errors.append(
            f"api representation profile v1.1 missing: {PROFILE_V11_JSON_PATH}"
        )
    if errors:
        return errors
    try:
        committed = json.loads(projection_path.read_text(encoding="utf-8"))
        committed_profile = json.loads(profile_path.read_text(encoding="utf-8"))
        binding = committed["binding"]
    except (KeyError, ValueError) as exc:
        return [
            f"{PROJECTION_V11_JSON_PATH}: cannot read binding for validation: {exc}"
        ]
    binding_errors = validate_source_binding(root, binding)
    if binding_errors:
        return [
            f"{PROJECTION_V11_JSON_PATH}: source-revision binding invalid: {error}"
            for error in binding_errors
        ]
    source_revision = binding["source_revision"]
    for label, document, artifact_path, expected_schema in (
        (
            "projection",
            committed,
            BASELINE_PROJECTION_V1_PATH,
            PROJECTION_V1_SCHEMA,
        ),
        ("profile", committed_profile, BASELINE_PROFILE_V1_PATH, PROFILE_V1_SCHEMA),
    ):
        pin = document.get("extends")
        if not isinstance(pin, dict):
            errors.append(
                f"{PROJECTION_V11_JSON_PATH}: {label} extension pin missing"
            )
            continue
        if pin.get("artifact") != artifact_path or pin.get("schema") != expected_schema:
            errors.append(
                f"{label} extension must extend {artifact_path} "
                f"({expected_schema}); recorded pin: "
                f"artifact={pin.get('artifact')!r} schema={pin.get('schema')!r}"
            )
        baseline_file = root / artifact_path
        if not baseline_file.is_file():
            errors.append(f"O2.1 baseline missing: {artifact_path}")
            continue
        if pin.get("artifact_digest") != file_digest(root, artifact_path):
            errors.append(
                f"{label} baseline digest does not match `extends.artifact_digest` "
                "(the baseline was modified or the extension is stale)"
            )
        baseline_revision = pin.get("source_revision")
        if isinstance(baseline_revision, str) and baseline_revision:
            result = _git(
                root, "merge-base", "--is-ancestor", baseline_revision, source_revision
            )
            if result.returncode != 0:
                errors.append(
                    f"{label} baseline source revision {baseline_revision} is "
                    f"not an ancestor of the extension source revision "
                    f"{source_revision}"
                )
    if errors:
        return errors
    try:
        artifacts = build_pair_o22(root, source_revision=source_revision)
    except ProjectionO22Error as exc:
        return [f"semantic projection v1.1 generation failed: {exc}"]
    if canonical_json(artifacts["projection"]) != projection_path.read_text(
        encoding="utf-8"
    ):
        errors.append(
            f"{PROJECTION_V11_JSON_PATH}: committed projection differs from "
            "regeneration from current inputs (regenerate and commit)"
        )
    if canonical_json(artifacts["profile"]) != profile_path.read_text(
        encoding="utf-8"
    ):
        errors.append(
            f"{PROFILE_V11_JSON_PATH}: committed profile differs from "
            "regeneration from current inputs (regenerate and commit)"
        )
    return errors