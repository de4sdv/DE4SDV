"""DE4SDV Semantic Projection v1 and SysML API Representation Profile v1 (O2.1).

Bounded generation stage of the semantic-authority migration: this module
generates the machine-readable semantic representation for exactly the seven
settled c1 method-conformance identities whose representation/equivalence
review completed in O1 (merged baseline
``9dc0779ba20745d3d0a7eca15e76891b64911ddc``):

- ``MethodPhase``
- ``MethodContractObligation``
- ``EvaluationScopeMembership``
- ``EvaluationSourceKind``
- ``TestedScopeDeclaration``
- ``RetainedExecutionRecordReference``
- ``AcceptanceAttestationReference``

Architecture (Unified Semantic Engineering Plan v1.2, section 8.1):

- the **Semantic Projection v1** records engineering semantics derived from
  the governed model representation: concept identity, semantic kind, the
  model's owned documentation (definition text), typed member structure, the
  claim boundary, and the kernel-binding contract that locates the identity
  in a validated API revision;
- the **SysML API Representation Profile v1** records representation
  mechanics only: membership shapes, property paths, typing/external
  reference mechanics, direction-free traversal facts, serializer/importer
  compatibility, and the fail-closed completeness check. Representation
  mechanics never redefine engineering meaning.

Source-of-truth rule (O2.1): every generated semantic field is derived from
the governed model declarations at the bound source revision — located via
the ontology/kernel contract's file+declaration mapping (locators only) and
read with the reviewed documentation-ownership machinery (SysML v2
documentation ownership: a ``doc`` comment is owned by the element whose body
it lexically sits in). This module does NOT read the O1 migration artifacts
(``semantic-authority-inventory.json``, ``authority-review-decisions.yaml``,
``phase1-inventory-review.md``): the O1 inventory is migration governance,
never runtime semantic authority, and it supplies no semantic field here. The
O2.1 admission boundary is an explicit machine-locked manifest
(``docs/method-conformance/o2/o21-admission.yaml``) plus the frozen
:data:`O21_ADMITTED_IDENTITIES` lock; both must agree exactly.

Identity discipline (ADR 0011): generation never derives identity from
element names, qualified names, package paths, source filenames, or doc text.
The kernel-binding contract recorded per row is exactly the ingestion
validation rule (declaredName + ``@type`` + serializer-recorded source-file
provenance resolving to exactly one element id) whose result the runtime
consumes through ``KernelBindingIndex``; ambiguous or unresolved bindings
fail closed, and no name-based fallback exists anywhere on this path.

Boundaries (O2.1, enforced by tests):

- **generation is not authority activation**: these rows do not switch
  traversal/query authority, do not retire authored YAML authority, do not
  alter ``phase_contract``/``increment_status``/``method_gaps``/
  ``next_obligation`` behavior, and are not read by the semantic runtime
  (O3 owns authority transition; O4 owns authored-ontology retirement);
- **no support promotion by generation**: every row is ``vocabulary-only``;
  there is no promotion input in this module (no boolean shortcut, no
  attestation parameter) — support promotion is a later, explicitly reviewed
  evidence-bearing step;
- **revision binding**: artifacts bind a ``source_revision`` — a Git commit
  containing every bound input byte-for-byte — plus per-input content
  digests; the generation-software inputs and the semantic-model inputs are
  listed separately so the two revisions are never conflated; no validated
  SysML API project/commit closure is claimed (``api_binding`` stays
  explicitly unclaimed — exact-revision API closure is privileged/CI-owned);
- **determinism**: identical inputs produce byte-identical output
  (``canonical_json``); no timestamps, no environment-dependent values.

Projection v0 (``de4sdv/semantic/projection.py``, the K slice) is preserved
unchanged: this module is additive and does not import, alter, or generalize
v0, and v1 does not yet emit K predicates.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

from .authority_inventory import (
    _DuplicateKeyLoader,
    _owned_doc_bodies,
    _skip_string_literal,
    canonical_json,
    file_digest,
    resolve_source_revision,
    validate_source_binding,
    verify_source_revision_contains_inputs,
)
from .kernel_contract import KernelContract, KernelFileMapping, declaration_identity

# ---------------------------------------------------------------------------
# Schema and artifact paths
# ---------------------------------------------------------------------------

PROJECTION_V1_SCHEMA = "de4sdv.semantic-projection.v1"
PROFILE_V1_SCHEMA = "de4sdv.api-representation-profile.v1"
ADMISSION_SCHEMA_ID = "de4sdv.o2-1-admission/v1"

O2_DIRECTORY = "docs/method-conformance/o2"
ADMISSION_PATH = f"{O2_DIRECTORY}/o21-admission.yaml"
PROJECTION_V1_JSON_PATH = f"{O2_DIRECTORY}/semantic-projection-v1.json"
PROFILE_V1_JSON_PATH = f"{O2_DIRECTORY}/api-representation-profile-v1.json"

ONTOLOGY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"

#: Program sources whose behavior produces the artifacts. Every one is a
#: bound input: changing any of them requires rebinding (regenerate against a
#: commit that contains the change). Model/data inputs are collected
#: mechanically from the admission boundary and the contract locators.
BOUND_INPUT_PROGRAM_PATHS: tuple[str, ...] = (
    "de4sdv/semantic/projection_v1.py",
    "de4sdv/semantic/authority_inventory.py",
    "de4sdv/semantic/kernel_contract.py",
    "scripts/generate_semantic_projection_v1.py",
)


class ProjectionV1Error(Exception):
    """Generation/validation failure for the O2.1 projection/profile."""


# ---------------------------------------------------------------------------
# Machine-locked O2.1 admission boundary
# ---------------------------------------------------------------------------

#: The reviewed O2.1 admission boundary (O2.1 is exactly these seven settled
#: c1 identities). The admission manifest must agree with this lock exactly
#: (order and set); a disposition that changes requires an explicit reviewed
#: change to BOTH the lock and the manifest. The emission path iterates this
#: tuple only — new ontology/model entries cannot expand the output.
O21_ADMITTED_IDENTITIES: tuple[str, ...] = (
    "MethodPhase",
    "MethodContractObligation",
    "EvaluationScopeMembership",
    "EvaluationSourceKind",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
)

#: The complete reviewed O2 admission (13 identities) with its sequencing.
#: O2.1 emits only the o2.1 subset; the remaining identities are deferred to
#: later reviewed phases and are machine-checked as absent from O2.1 output.
O2_SEQUENCING: dict[str, tuple[str, ...]] = {
    "o2.1": O21_ADMITTED_IDENTITIES,
    "o2.2": ("VerificationCase", "hasSubject", "verifiedBy"),
    "o2.3": (
        "derivesRequirementFromNeed",
        "derivedRequirementsOfNeed",
        "hasRelevantArchitecture",
    ),
}

#: Identities that must never appear in O2.1 output. The manifest carries the
#: reviewed reason per identity; this lock keeps the guard set machine-visible
#: even if the manifest is malformed.
O21_EXCLUDED_IDENTITIES: tuple[str, ...] = (
    "MethodEvaluationScope",
    "DerivesFromNeed",
    "VerificationCase",
    "hasSubject",
    "verifiedBy",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
    "hasRelevantArchitecture",
    "derivesNeedFromConcern",
    "realizedBy",
    "specifiesFunction",
    "hasRelevantEvidenceContract",
    "EvidenceContract",
    "ArchitectureElement",
    "Function",
    "LogicalElement",
    "PhysicalElement",
    "Interface",
    "allocatedTo",
    "deployedTo",
)

#: Declaration kinds this bounded stage can represent. The kind token comes
#: from the governed declaration (the same locator the kernel contract and
#: the ingestion binding validation use); a declaration outside this set is a
#: generation failure, never a silent skip.
_KIND_TO_SEMANTIC: dict[str, str] = {
    "enum": "enumeration",
    "item": "item",
}

#: Kernel/SysML library scalar types used by the admitted declarations. These
#: are out-of-export library targets in the validated API representation
#: (recorded there through the export's external-reference mechanics); a
#: member type outside this closed set and outside the governed classes is a
#: generation failure.
EXTERNAL_LIBRARY_TYPES: dict[str, str] = {
    "String": "Kernel Data Type Library (ScalarValues.kerml)",
    "Natural": "Kernel Data Type Library (ScalarValues.kerml)",
    "Boolean": "Kernel Data Type Library (ScalarValues.kerml)",
}

#: Applicable standard-library base identity per semantic kind, materialized
#: by the pinned toolchain as an implied Subclassification (provenance
#: ``implied``). Witnessed by the retained privileged full-model API
#: ingestion run recorded in the representation profile's evidence basis.
STANDARD_LIBRARY_BASE: dict[str, dict[str, str]] = {
    "enumeration": {
        "library": "Kernel Semantic Library (Base.kerml)",
        "provenance": "implied",
    },
    "item": {
        "library": "Systems Model Library (Items.sysml)",
        "provenance": "implied",
    },
}

#: Uniform claim boundary recorded on every O2.1 concept row. These are
#: vocabulary/schema definitions; the generated row carries no instance-level
#: fact of any kind. Enforced as a single constant so no row can drift.
CLAIM_BOUNDARY = (
    "Schema/vocabulary semantics only: this row projects the model-resident "
    "definition of a method-conformance vocabulary concept at the bound "
    "source revision. It carries no instance-level fact - no obligation "
    "satisfaction, no method-phase completion, no acceptance or approval "
    "decision, no evidence validity or freshness, no tested-scope equality, "
    "no evaluation success - and instantiation elsewhere in the model does "
    "not create one. Boundary statements carried by the model documentation "
    "remain recorded verbatim in the definition documentation."
)

#: Uniform model/external boundary statement for O2.1 concept rows.
MODEL_EXTERNAL_BOUNDARY = (
    "Model-resident definition. External identities referenced by the "
    "concept (retained records, policies, registries) remain external; "
    "generation neither absorbs nor evaluates them."
)

#: Identity-resolution contract recorded per row: exactly the ingestion
#: validation rule that yields a ``KernelElementBinding`` (ADR 0011). This
#: string is provenance/resolution metadata, never a semantic field.
_IDENTITY_RESOLUTION = (
    "ingestion-validated kernel binding: exactly one API element whose "
    "declaredName and @type match the governed declaration and whose "
    "serializer-recorded source document equals the bound source file; "
    "multiple candidates are ambiguous and zero candidates is unresolved "
    "(both fail closed); the runtime consumes the resulting "
    "KernelElementBinding through KernelBindingIndex, never a name-based "
    "fallback"
)

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_ATTRIBUTE = re.compile(
    r"attribute\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<type>[^=]+?)"
    r"\s*(?:=\s*(?P<default>.+))?\Z"
)


# ---------------------------------------------------------------------------
# Admission manifest (governance boundary)
# ---------------------------------------------------------------------------


def load_admission_manifest(path: Path) -> dict[str, Any]:
    """Load and shape-check the machine-locked O2.1 admission manifest."""
    if not path.is_file():
        raise ProjectionV1Error(f"O2.1 admission manifest not found: {path}")
    try:
        value = yaml.load(
            path.read_text(encoding="utf-8"), Loader=_DuplicateKeyLoader
        )
    except ProjectionV1Error:
        raise
    except yaml.YAMLError as exc:
        raise ProjectionV1Error(f"O2.1 admission manifest is not valid YAML: {exc}")
    if not isinstance(value, dict):
        raise ProjectionV1Error("O2.1 admission manifest must be a YAML mapping")
    if value.get("schema") != ADMISSION_SCHEMA_ID:
        raise ProjectionV1Error(
            f"admission schema must be {ADMISSION_SCHEMA_ID!r}, "
            f"got {value.get('schema')!r}"
        )
    return value


def validate_admission(manifest: dict[str, Any]) -> None:
    """Machine-lock the O2.1 admission boundary; fail closed on any drift.

    Locks (each direction): admitted set equals the frozen
    :data:`O21_ADMITTED_IDENTITIES` (order and set); the sequencing union
    equals the 13-identity overall O2 admission; ``o2.1`` equals ``admitted``;
    no identity is both admitted and excluded; every excluded entry carries a
    non-empty reason and a kind in {class, relationship}.
    """
    admitted = manifest.get("admitted")
    if not isinstance(admitted, list) or not all(
        isinstance(item, str) and item for item in admitted
    ):
        raise ProjectionV1Error("admission manifest `admitted` must be a list of identities")
    if tuple(admitted) != O21_ADMITTED_IDENTITIES:
        raise ProjectionV1Error(
            "admission manifest `admitted` does not equal the frozen O2.1 "
            f"lock: manifest={tuple(admitted)!r} lock={O21_ADMITTED_IDENTITIES!r}"
        )

    sequencing = manifest.get("sequencing")
    if not isinstance(sequencing, dict):
        raise ProjectionV1Error("admission manifest `sequencing` must be a mapping")
    expected_keys = set(O2_SEQUENCING)
    if set(sequencing) != expected_keys:
        raise ProjectionV1Error(
            f"admission sequencing keys must be exactly {sorted(expected_keys)}"
        )
    for phase, identities in O2_SEQUENCING.items():
        declared = sequencing.get(phase)
        if not isinstance(declared, list) or tuple(declared) != identities:
            raise ProjectionV1Error(
                f"admission sequencing {phase!r} must equal {identities!r}"
            )
    union = tuple(
        identity
        for phase in ("o2.1", "o2.2", "o2.3")
        for identity in O2_SEQUENCING[phase]
    )
    if len(union) != 13 or len(set(union)) != 13:
        raise ProjectionV1Error(
            "the overall O2 admission must remain exactly 13 distinct identities"
        )

    excluded = manifest.get("excluded")
    if not isinstance(excluded, list) or not excluded:
        raise ProjectionV1Error("admission manifest `excluded` must be a non-empty list")
    seen: set[str] = set()
    for entry in excluded:
        if not isinstance(entry, dict):
            raise ProjectionV1Error("excluded entries must be mappings")
        identity = str(entry.get("identity") or "")
        if not identity:
            raise ProjectionV1Error("excluded entry without an identity")
        if identity in seen:
            raise ProjectionV1Error(f"duplicate excluded identity {identity!r}")
        seen.add(identity)
        if entry.get("kind") not in {"class", "relationship"}:
            raise ProjectionV1Error(
                f"excluded identity {identity!r} must declare kind class|relationship"
            )
        if not str(entry.get("reason") or "").strip():
            raise ProjectionV1Error(f"excluded identity {identity!r} has no reason")
    if set(seen) != set(O21_EXCLUDED_IDENTITIES):
        raise ProjectionV1Error(
            "the manifest `excluded` set must equal the frozen O2.1 guard "
            f"set: manifest-only={sorted(set(seen) - set(O21_EXCLUDED_IDENTITIES))} "
            f"lock-only={sorted(set(O21_EXCLUDED_IDENTITIES) - set(seen))}"
        )
    both = set(admitted) & seen
    if both:
        raise ProjectionV1Error(f"identities both admitted and excluded: {sorted(both)}")


# ---------------------------------------------------------------------------
# Model-side derivation (governed declarations only)
# ---------------------------------------------------------------------------


def _matching_brace(block: str, open_index: int) -> int:
    """Index of the brace closing the one opened at ``open_index``.

    Comment- and string-aware: braces inside comments or string content are
    structurally inert. Unbalanced input fails closed.
    """
    depth = 0
    index = open_index
    length = len(block)
    while index < length:
        if block.startswith("/*", index):
            end = block.find("*/", index + 2)
            if end == -1:
                raise ProjectionV1Error("unterminated block comment in a declaration body")
            index = end + 2
            continue
        if block.startswith("//", index):
            end = block.find("\n", index)
            index = length if end == -1 else end + 1
            continue
        char = block[index]
        if char == '"':
            index = _skip_string_literal(block, index)
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ProjectionV1Error("unbalanced braces in a declaration body")


def direct_member_records(block: str) -> list[dict[str, Any]]:
    """Direct-lexical-depth member records of one declaration body block.

    One bounded deterministic scan (comment- and string-aware), in source
    order. Records:

    - ``{"kind": "documentation", "body": str}`` — a ``doc`` comment at the
      block's direct lexical depth (owned by the declaration, per SysML v2
      documentation ownership: a doc comment is owned by the element whose
      body it lexically sits in);
    - ``{"kind": "attribute", "name", "type_text", "default_text"}`` — an
      ``attribute <name> : <Type> [= <default>]`` member;
    - ``{"kind": "literal", "name", "member_docs"}`` — an enumeration
      literal (braced or bodyless); ``member_docs`` are the ``doc`` comments
      inside the literal's own body (member-owned, never definition text);
    - ``{"kind": "other", "text": str}`` — any other member form; the
      builder fails closed on it (an unexpected member kind requires an
      explicit reviewed extension of this bounded stage).
    """
    records: list[dict[str, Any]] = []
    index = 1  # skip the opening '{' of the declaration block
    length = len(block)
    start = 1
    while index < length:
        if block.startswith("/*", index):
            end = block.find("*/", index + 2)
            if end == -1:
                raise ProjectionV1Error("unterminated block comment in a declaration body")
            behind = " ".join(block[start:index].split())
            if re.search(r"(?<![A-Za-z0-9_])doc\Z", behind):
                records.append({"kind": "documentation", "body": block[index + 2:end]})
            elif behind:
                records.append(
                    {
                        "kind": "other",
                        "text": " ".join(
                            (block[start:index] + block[index:end + 2]).split()
                        ),
                    }
                )
            index = end + 2
            start = index
            continue
        if block.startswith("//", index):
            end = block.find("\n", index)
            index = length if end == -1 else end + 1
            start = index
            continue
        char = block[index]
        if char == '"':
            index = _skip_string_literal(block, index)
            continue
        if char == "{":
            raw = " ".join(block[start:index].split())
            close = _matching_brace(block, index)
            if _IDENTIFIER.fullmatch(raw):
                member_block = block[index:close + 1]
                records.append(
                    {
                        "kind": "literal",
                        "name": raw,
                        "member_docs": _owned_doc_bodies(member_block),
                    }
                )
            else:
                records.append(
                    {"kind": "other", "text": raw + " { ... }"}
                )
            index = close + 1
            start = index
            continue
        if char == "}":
            break
        if char == ";":
            raw = " ".join(block[start:index].split())
            if raw:
                match = _ATTRIBUTE.fullmatch(raw)
                if match:
                    records.append(
                        {
                            "kind": "attribute",
                            "name": match.group("name"),
                            "type_text": match.group("type").strip(),
                            "default_text": (match.group("default") or "").strip(),
                        }
                    )
                elif _IDENTIFIER.fullmatch(raw):
                    records.append({"kind": "literal", "name": raw, "member_docs": []})
                else:
                    records.append({"kind": "other", "text": raw})
            index += 1
            start = index
            continue
        index += 1
    return records


def _normalized_text(text: str) -> str:
    """Cosmetic whitespace/line-wrap normalization only (no content change)."""
    return " ".join(text.split())


def _resolve_member_type(type_text: str, contract: KernelContract) -> dict[str, str]:
    """Resolve one attribute's declared type without any name heuristic.

    Governed model classes resolve by identity against the ontology/kernel
    contract's class set (the ingestion binding validation then proves the
    element); the closed set of Kernel/SysML library scalar types resolves to
    its pinned library identity (out-of-export target in the validated API
    representation). Anything else fails closed.
    """
    if "::" in type_text:
        raise ProjectionV1Error(
            f"qualified member type {type_text!r} is outside the bounded O2.1 "
            "representation; extend the reviewed scope before generating"
        )
    if type_text in contract.classes:
        return {"kind": "governed-class", "identity": type_text}
    if type_text in EXTERNAL_LIBRARY_TYPES:
        return {
            "kind": "external-library-type",
            "name": type_text,
            "library": EXTERNAL_LIBRARY_TYPES[type_text],
        }
    raise ProjectionV1Error(
        f"member type {type_text!r} is neither a governed class nor a declared "
        "Kernel/SysML library scalar type; the representation is insufficient "
        "to derive a typed structure"
    )


def locate_declaration(
    text: str, declaration: str
) -> tuple[int, int, str] | None:
    """Locate one governed declaration as ``(match_start, brace_start, block)``.

    The declaration keyword + name are matched exactly as everywhere else in
    the kernel contract (same pattern shape as the reviewed inventory
    machinery), but the located body must be ADJACENT: only whitespace may
    separate the declaration from its opening brace. A missing declaration, a
    bodyless one, or an interrupted/malformed one (keyword without its own
    body) returns ``None`` — the caller fails closed instead of latching onto
    an unrelated later block.
    """
    kind, _, name = declaration.partition(" def ")
    pattern = _declaration_pattern(kind, name)
    match = pattern.search(text)
    if not match:
        return None
    brace = text.find("{", match.end())
    if brace == -1:
        return None
    if text[match.end():brace].strip():
        return None
    close = _matching_brace(text, brace)
    return match.start(), brace, text[brace:close + 1]


def _declaration_pattern(kind: str, name: str) -> re.Pattern[str]:
    return re.compile(
        r"(?m)^[ \t]*(?:(?:public|private|protected)\s+)?(?:abstract\s+)?"
        + re.escape(kind.strip()).replace(r"\ ", r"\s+")
        + r"\s+def\s+"
        + re.escape(name.strip())
        + r"\b"
    )


def derive_concept_row(
    identity: str, contract: KernelContract, root: Path
) -> dict[str, Any]:
    """Derive one concept row from the governed model declaration.

    The declaration is located exactly as the kernel contract and the
    ingestion binding validation locate it (file + declaration mapping); the
    semantic content is read from the model file itself. Fails closed on: a
    non-file mapping, a missing or bodyless declaration, an ambiguous
    (duplicate) declaration, an unsupported declaration kind, an unsupported
    member form, an unresolved member typing, or empty definition
    documentation (meaning must be model-resident).
    """
    mapping = contract.mapping(identity)
    if not isinstance(mapping, KernelFileMapping):
        raise ProjectionV1Error(
            f"{identity}: governed mapping is not a file/declaration mapping; "
            "the bounded O2.1 stage generates only file-grounded vocabulary"
        )
    name, expected_type = declaration_identity(mapping.declaration)
    if name != identity:
        raise ProjectionV1Error(
            f"{identity}: governed declaration {mapping.declaration!r} names "
            f"{name!r}; identity drift is a generation failure"
        )
    kind_token = mapping.declaration.partition(" def ")[0].strip()
    semantic_kind = _KIND_TO_SEMANTIC.get(kind_token)
    if semantic_kind is None:
        raise ProjectionV1Error(
            f"{identity}: declaration kind {kind_token!r} is outside the "
            f"bounded O2.1 kinds {sorted(_KIND_TO_SEMANTIC)}"
        )

    file_path = root / mapping.file
    if not file_path.is_file():
        raise ProjectionV1Error(f"{identity}: model file not found: {mapping.file}")
    text = file_path.read_text(encoding="utf-8")

    located = locate_declaration(text, mapping.declaration)
    if located is None:
        raise ProjectionV1Error(
            f"{identity}: declaration {mapping.declaration!r} is not "
            f"locatable as a braced declaration in {mapping.file} (missing, "
            "bodyless, or malformed); the model does not carry its structure"
        )
    match_start, brace_start, block = located
    # Ambiguous grounding: the governed declaration must occur exactly once.
    occurrences = len(
        _declaration_pattern(kind_token, name).findall(text)
    )
    if occurrences != 1:
        raise ProjectionV1Error(
            f"{identity}: declaration {mapping.declaration!r} occurs "
            f"{occurrences} times in {mapping.file}; ambiguous grounding"
        )
    del match_start, brace_start  # used only for the span contract above

    records = direct_member_records(block)
    for record in records:
        if record["kind"] == "other":
            raise ProjectionV1Error(
                f"{identity}: unsupported member form {record['text']!r}; the "
                "bounded O2.1 stage fails closed on unrepresented structure"
            )

    documentation = [
        _normalized_text(record["body"])
        for record in records
        if record["kind"] == "documentation"
    ]
    if not documentation:
        raise ProjectionV1Error(
            f"{identity}: no model-owned documentation at the declaration's "
            "direct depth; the model does not carry the concept's meaning"
        )

    members: list[dict[str, Any]] = []
    for record in records:
        if record["kind"] == "documentation":
            continue
        if record["kind"] == "attribute":
            members.append(
                {
                    "name": record["name"],
                    "type": _resolve_member_type(record["type_text"], contract),
                    "default": _normalized_text(record["default_text"]),
                }
            )
        else:  # literal
            members.append(
                {
                    "name": record["name"],
                    "documentation": " ".join(
                        _normalized_text(body) for body in record["member_docs"]
                    ),
                }
            )

    return {
        "identity": identity,
        "semantic_kind": semantic_kind,
        "definition": {
            "documentation": " ".join(documentation),
            "documentation_witness": {
                "source_file": mapping.file,
                "declaration": mapping.declaration,
                "doc_count": len(documentation),
            },
        },
        "structure": {
            "members_kind": (
                "enumeration-literals"
                if semantic_kind == "enumeration"
                else "typed-attributes"
            ),
            "members": members,
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "model_external_boundary": MODEL_EXTERNAL_BOUNDARY,
        "grounding": {
            "kernel_binding_contract": {
                "source_file": mapping.file,
                "declaration": mapping.declaration,
                "api_metaclass": expected_type,
                "resolution": _IDENTITY_RESOLUTION,
            },
            "standard_library_base": dict(STANDARD_LIBRARY_BASE[semantic_kind]),
        },
        "support_state": "vocabulary-only",
    }


# ---------------------------------------------------------------------------
# Binding collection
# ---------------------------------------------------------------------------


def collect_bound_inputs(
    root: Path, contract: KernelContract, manifest_path: str = ADMISSION_PATH
) -> dict[str, str]:
    """Every source consumed to produce the artifacts: path -> sha256 digest.

    Program inputs are declared in :data:`BOUND_INPUT_PROGRAM_PATHS`; data
    inputs are the admission manifest, the ontology/kernel contract (locators
    only), and the governed model files of the admitted identities — derived
    mechanically so a changed admission set cannot silently drop an input.
    """
    paths: set[str] = set(BOUND_INPUT_PROGRAM_PATHS)
    paths.add(manifest_path)
    paths.add(ONTOLOGY_PATH)
    for identity in O21_ADMITTED_IDENTITIES:
        mapping = contract.mapping(identity)
        if isinstance(mapping, KernelFileMapping):
            paths.add(mapping.file)
    inputs: dict[str, str] = {}
    for path in sorted(paths):
        file = root / path
        if not file.is_file():
            raise ProjectionV1Error(f"bound input missing: {path}")
        inputs[path] = file_digest(root, path)
    return inputs


# ---------------------------------------------------------------------------
# Artifact assembly
# ---------------------------------------------------------------------------


def _binding_block(
    root: Path,
    source_revision: str,
    bound_inputs: dict[str, str],
    contract: KernelContract,
) -> dict[str, Any]:
    """Revision binding shared by the projection and the profile.

    The semantic-model revision and the generation-software revision are
    distinguished: ``bound_inputs`` lists every input, and the named views
    split them. Both are contained byte-for-byte in ``source_revision``. No
    SysML API project/commit identity is claimed — ``api_binding`` stays
    explicitly unclaimed: exact-revision API closure is a privileged/CI
    artifact, and inventing an unverified revision label is prohibited.
    """
    program_inputs = sorted(BOUND_INPUT_PROGRAM_PATHS)
    model_inputs = sorted(
        {
            mapping.file
            for identity in O21_ADMITTED_IDENTITIES
            if isinstance(mapping := contract.mapping(identity), KernelFileMapping)
        }
    )
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
                "program inputs byte-for-byte. Distinguished from the "
                "semantic-model revision so generator changes are never "
                "confused with model changes."
            ),
        },
        "semantic_model_revision": {
            "model_inputs": model_inputs,
            "note": (
                "Semantic-model revision: the governed model declarations "
                "these artifacts were generated from, contained "
                "byte-for-byte in source_revision. The ontology/kernel "
                "contract supplies declaration locators only; the model "
                "files carry the semantics."
            ),
        },
        "api_binding": {
            "status": "unclaimed",
            "note": (
                "O2.1 produces no validated SysML API project/commit closure. "
                "Element identity is resolved at a bound API revision through "
                "ingestion-validated kernel bindings (KernelBindingIndex, "
                "fail closed); the exact-revision API closure belongs to the "
                "privileged ingestion path and a later reviewed step."
            ),
        },
        "admission_manifest": {
            "path": ADMISSION_PATH,
            "digest": bound_inputs[ADMISSION_PATH],
        },
        "ontology_contract_locator": {
            "path": ONTOLOGY_PATH,
            "digest": bound_inputs[ONTOLOGY_PATH],
        },
        "bound_inputs": bound_inputs,
    }


def _scope_block(manifest: dict[str, Any]) -> dict[str, Any]:
    """The machine-locked admission boundary, echoed for reviewability."""
    return {
        "admission": "O2.1 bounded generation stage (settled c1 identities)",
        "admitted": list(O21_ADMITTED_IDENTITIES),
        "sequencing": {
            phase: list(identities) for phase, identities in O2_SEQUENCING.items()
        },
        "excluded": [
            {
                "identity": str(entry["identity"]),
                "kind": str(entry["kind"]),
                "reason": " ".join(str(entry["reason"]).split()),
            }
            for entry in manifest["excluded"]
        ],
        "admission_note": (
            "Machine-locked reviewed migration boundary: the emission path "
            "iterates the admitted set only (no heuristic query); an eighth "
            "identity or a missing admitted identity is a generation failure."
        ),
    }


def _build_pair(
    root: Path,
    *,
    source_revision: str | None = None,
    manifest: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build both artifacts over identical inputs (single source of truth)."""
    if manifest is None:
        manifest = load_admission_manifest(root / ADMISSION_PATH)
    validate_admission(manifest)
    contract = KernelContract.load(root / ONTOLOGY_PATH)
    if source_revision is None:
        source_revision = resolve_source_revision(root)
    bound_inputs = collect_bound_inputs(root, contract)
    verify_source_revision_contains_inputs(root, source_revision, bound_inputs)

    concepts = [
        derive_concept_row(identity, contract, root)
        for identity in O21_ADMITTED_IDENTITIES
    ]

    # Fail-closed output guard: exactly the admitted set, none of the guarded
    # exclusions, whatever the model contains.
    emitted = [row["identity"] for row in concepts]
    if tuple(emitted) != O21_ADMITTED_IDENTITIES:
        raise ProjectionV1Error(
            f"emitted identities {tuple(emitted)!r} do not equal the frozen "
            f"O2.1 admission {O21_ADMITTED_IDENTITIES!r}"
        )
    leaked = sorted(set(emitted) & set(O21_EXCLUDED_IDENTITIES))
    if leaked:
        raise ProjectionV1Error(f"excluded identities leaked into O2.1 output: {leaked}")

    binding = _binding_block(root, source_revision, bound_inputs, contract)
    projection = {
        "schema": PROJECTION_V1_SCHEMA,
        "status": (
            "generated O2.1 bounded semantic projection (seven settled c1 "
            "method-conformance identities)"
        ),
        "warning": (
            "Generated artifact. Generation is NOT authority activation: this "
            "projection does not switch runtime dispatch, does not retire "
            "authored YAML authority, and promotes no support state. The O1 "
            "migration inventory is governance, never semantic authority, and "
            "is not read by this generator. The runtime does not read this "
            "artifact. Generated by scripts/generate_semantic_projection_v1.py."
        ),
        "binding": binding,
        "scope": _scope_block(manifest),
        "concepts": concepts,
    }
    profile = {
        "schema": PROFILE_V1_SCHEMA,
        "profile_version": "v1",
        "status": (
            "generated O2.1 SysML API Representation Profile v1 (representation "
            "mechanics for the seven settled c1 identities)"
        ),
        "warning": (
            "Generated artifact. Representation mechanics only: this profile "
            "cannot redefine domain, range, direction, semantic strength, "
            "exclusions, or claim boundaries - those live in the Semantic "
            "Projection. The runtime does not read this artifact."
        ),
        "binding": binding,
        "evidence_basis": {
            "kind": "retained privileged full-model API ingestion run",
            "run": "10195168006",
            "candidate_revision": "0a23902370de9fc74d6118afe480382e0b0d8aa0",
            "scope": (
                "Serializer representation shapes only (membership kinds, "
                "property paths, implied grounding, external-reference "
                "mechanics). That retained run's model text predates the c1 "
                "documentation reconciliation and is NOT a semantic source "
                "for generation."
            ),
        },
        "representation_contract": _representation_contract(),
        "profiles": [
            _profile_entry(row) for row in concepts
        ],
    }
    assert_profile_compatible_v1(projection, profile)
    return projection, profile


def _representation_contract() -> dict[str, Any]:
    """The O2.1 representation mechanics, witnessed by the evidence basis."""
    return {
        "identity_resolution": {
            "rule": _IDENTITY_RESOLUTION,
            "prohibited_fallbacks": [
                "declaredName alone",
                "qualifiedName alone",
                "package path",
                "source filename",
                "doc text",
                "string matching",
            ],
        },
        "definition_membership": (
            "definition-owned membership objects appear in the element's "
            "ownedRelationship; member element resolution uses memberElement "
            "(ownedRelatedElement is a compatible variant)"
        ),
        "documentation_membership": (
            "definition-level documentation materializes as Documentation "
            "elements owned by the definition via OwningMembership, one "
            "membership per doc comment, in authored source order; "
            "documentation inside a nested member body is owned by that "
            "member and never joins the definition text"
        ),
        "attribute_representation": (
            "attribute members serialize as FeatureMembership (memberName = "
            "attribute name) whose member element is an AttributeUsage "
            "carrying the authored FeatureTyping"
        ),
        "attribute_typing": (
            "an attribute's declared type resolves through the authored "
            "FeatureTyping: in-model types resolve to the target element "
            "(type|general reference); Kernel/SysML library scalar types are "
            "out-of-export targets recorded in the export's "
            "external_references (type|general property path) with the pinned "
            "library document uri"
        ),
        "enumeration_literal_representation": (
            "enumeration literals serialize as VariantMembership members "
            "whose member element is an EnumerationUsage; each literal "
            "carries an implied FeatureTyping to the owning enumeration "
            "definition and an implied Subsetting to the Kernel Base library "
            "(recorded via external_references)"
        ),
        "implied_standard_library_grounding": (
            "the definition's standard-library base identity is materialized "
            "as an implied Subclassification (isImplied=true): enumerations "
            "ground in the Kernel Semantic Library Base.kerml; item "
            "definitions ground in the Systems Model Library Items.sysml; the "
            "superclassifier reference is out-of-export and recorded in "
            "external_references (general|superclassifier)"
        ),
        "external_reference_mechanics": (
            "references to elements outside the export are recorded as "
            "{source_element_id, property_path, target_id, uri}; a pruned "
            "reference names its exact source property path and the pinned "
            "library document; pruning a required witness is a completeness "
            "failure for the affected claim"
        ),
        "external_library_type_targets": {
            "note": (
                "Witnessed target identities of the closed library scalar "
                "types in the pinned toolchain library set (representation "
                "identities, never semantic redefinitions)"
            ),
            "targets": {
                "String": {
                    "target_id": "76028d3d-69a4-5e12-9002-ce403e0244bd",
                    "library": "Kernel Data Type Library (ScalarValues.kerml)",
                },
                "Natural": {
                    "target_id": "34b2d27c-06f3-5ca6-b3a4-09d5b63787b1",
                    "library": "Kernel Data Type Library (ScalarValues.kerml)",
                },
                "Boolean": {
                    "target_id": "d1e9242d-b2e3-5270-bf69-4f4fb0447193",
                    "library": "Kernel Data Type Library (ScalarValues.kerml)",
                },
            },
        },
        "serializer_importer_compatibility": {
            "uuid_preservation": "single-transaction-required",
            "known_omissions": [],
            "out_of_export_risk": (
                "the definition element, its owned memberships and member "
                "elements, the authored typings, and the definition "
                "documentation must survive official export, API import, and "
                "read-back; pruning any required witness makes the identity "
                "unsupported for that revision"
            ),
        },
        "completeness_check": (
            "fail closed: a missing ingestion-validated binding, a missing or "
            "ambiguous declaration block, an unsupported member kind, an "
            "unresolved member typing, or empty definition documentation "
            "blocks generation for that identity"
        ),
    }


def _profile_entry(concept: dict[str, Any]) -> dict[str, Any]:
    """Per-identity representation profile (mechanics, keyed to semantics)."""
    semantic_kind = concept["semantic_kind"]
    witness_forms = [
        "ownedRelationship -> FeatureMembership (attribute members) -> "
        "AttributeUsage -> authored FeatureTyping",
        "ownedRelationship -> OwningMembership -> Documentation "
        "(definition documentation, authored source order)",
        "implied Subclassification -> standard-library base "
        "(general|superclassifier external reference)",
    ]
    if semantic_kind == "enumeration":
        witness_forms.insert(
            0,
            "ownedRelationship -> VariantMembership (literals) -> "
            "EnumerationUsage -> implied FeatureTyping to the owning "
            "enumeration; implied Subsetting to the Kernel Base library",
        )
    return {
        "profile_identity": (
            f"{PROFILE_V1_SCHEMA}#{concept['identity']}"
        ),
        "for_concept": concept["identity"],
        "representation_class": (
            "enumeration-definition"
            if semantic_kind == "enumeration"
            else "item-definition"
        ),
        "binding_contract_echo": dict(
            concept["grounding"]["kernel_binding_contract"]
        ),
        "witness_forms": witness_forms,
    }


def assert_profile_compatible_v1(
    projection: dict[str, Any], profile: dict[str, Any]
) -> None:
    """Compatibility gate: mechanics must not contradict the projection.

    The profile's per-identity binding-contract echo and representation class
    must exactly match the projection's model-derived grounding and semantic
    kind; every external-library member type referenced by the projection
    must be declared in the profile's witnessed target table. A contradiction
    raises: representation mechanics can never silently redefine meaning
    (UG-25 analogue for the vocabulary slice).
    """
    projection_by_identity = {
        row["identity"]: row for row in projection["concepts"]
    }
    profile_by_identity = {
        entry["for_concept"]: entry for entry in profile["profiles"]
    }
    if set(projection_by_identity) != set(profile_by_identity):
        raise ProjectionV1Error(
            "profile identities do not match the projection identities: "
            f"projection-only={sorted(set(projection_by_identity) - set(profile_by_identity))} "
            f"profile-only={sorted(set(profile_by_identity) - set(projection_by_identity))}"
        )
    targets = profile["representation_contract"]["external_library_type_targets"][
        "targets"
    ]
    for identity, row in projection_by_identity.items():
        entry = profile_by_identity[identity]
        expected_echo = dict(row["grounding"]["kernel_binding_contract"])
        if entry["binding_contract_echo"] != expected_echo:
            raise ProjectionV1Error(
                f"{identity}: profile binding contract contradicts the "
                "model-derived projection grounding"
            )
        expected_class = (
            "enumeration-definition"
            if row["semantic_kind"] == "enumeration"
            else "item-definition"
        )
        if entry["representation_class"] != expected_class:
            raise ProjectionV1Error(
                f"{identity}: profile representation class "
                f"{entry['representation_class']!r} contradicts the semantic "
                f"kind {row['semantic_kind']!r}"
            )
        for member in row["structure"]["members"]:
            member_type = member.get("type")
            if member_type is None:
                continue
            if member_type["kind"] == "external-library-type":
                if member_type["name"] not in targets:
                    raise ProjectionV1Error(
                        f"{identity}: member type {member_type['name']!r} is "
                        "not declared in the profile's witnessed library "
                        "target table"
                    )


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def build_pair(
    root: Path,
    *,
    source_revision: str | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build both artifacts from the given checkout (single deterministic pass)."""
    projection, profile = _build_pair(
        root, source_revision=source_revision, manifest=manifest
    )
    return {"projection": projection, "profile": profile}


def build_projection_v1(
    root: Path, *, source_revision: str | None = None
) -> dict[str, Any]:
    """Build the Semantic Projection v1 artifact."""
    return _build_pair(root, source_revision=source_revision)[0]


def build_representation_profile_v1(
    root: Path, *, source_revision: str | None = None
) -> dict[str, Any]:
    """Build the SysML API Representation Profile v1 artifact."""
    return _build_pair(root, source_revision=source_revision)[1]


# ---------------------------------------------------------------------------
# Committed-artifact consistency gate (--check)
# ---------------------------------------------------------------------------


def run_check_errors(root: Path) -> list[str]:
    """Check that the committed artifacts equal regeneration from inputs.

    Validates the recorded source-revision binding against the repository
    (commit existence, ancestry of the checked-out revision, per-input
    content equality, recorded digests), then regenerates with the recorded
    source revision and compares bytes for both artifacts. Any uncommitted
    input change, stale binding, coverage failure, or hand edit of a
    generated file is an error.

    If the O2 directory has no committed artifacts yet (O2.1 pre-generation
    state), the check reports the missing artifacts — the artifacts are part
    of the delivered O2.1 state.
    """
    import json

    errors: list[str] = []
    projection_path = root / PROJECTION_V1_JSON_PATH
    profile_path = root / PROFILE_V1_JSON_PATH
    if not projection_path.is_file():
        errors.append(f"semantic projection v1 missing: {PROJECTION_V1_JSON_PATH}")
    if not profile_path.is_file():
        errors.append(
            f"api representation profile v1 missing: {PROFILE_V1_JSON_PATH}"
        )
    if errors:
        return errors
    try:
        committed = json.loads(projection_path.read_text(encoding="utf-8"))
        binding = committed["binding"]
    except (KeyError, ValueError) as exc:
        return [
            f"{PROJECTION_V1_JSON_PATH}: cannot read binding for validation: {exc}"
        ]
    binding_errors = validate_source_binding(root, binding)
    if binding_errors:
        return [
            f"{PROJECTION_V1_JSON_PATH}: source-revision binding invalid: {error}"
            for error in binding_errors
        ]
    try:
        artifacts = build_pair(root, source_revision=binding["source_revision"])
    except ProjectionV1Error as exc:
        return [f"semantic projection v1 generation failed: {exc}"]
    if canonical_json(artifacts["projection"]) != projection_path.read_text(
        encoding="utf-8"
    ):
        errors.append(
            f"{PROJECTION_V1_JSON_PATH}: committed projection differs from "
            "regeneration from current inputs (regenerate and commit)"
        )
    if canonical_json(artifacts["profile"]) != profile_path.read_text(
        encoding="utf-8"
    ):
        errors.append(
            f"{PROFILE_V1_JSON_PATH}: committed profile differs from "
            "regeneration from current inputs (regenerate and commit)"
        )
    return errors