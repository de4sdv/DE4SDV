"""O4 definition-admission batch 1: governed definition projection + API profile.

ONE reusable, governed representation for the admitted definition family of
the pinned ``definition-admission.yaml`` batch (22 rows after the
batch-1 amendment): each admitted
identity is backed by a model-resident SysML v2 definition declaration whose
owned documentation carries — or is bounded-review-equivalent to — the
reviewed definition:

* **Model side (witness):** the owning definition declaration and its
  directly owned ``doc`` bodies (``ownedRelationship -> OwningMembership ->
  Documentation``), collected in authored source order by the verified O1
  documentation-ownership machinery. The declaration block must exist and be
  non-bodyless, and at least one owned documentation body is required.
* **Projection side (semantic meaning):** the identity, the recomputed
  documentation observation (``normalized-exact`` / ``differs`` with a
  recorded ``reviewed-equivalent`` bounded review), and the kernel-binding
  contract (file + declaration) as grounding.
* **Profile side (representation mechanics only):** the declaration-form
  representation class and API metaclass echo; never a second semantic
  statement, never an API element identity or UUID claim.
* **Bound inputs:** the four executed program inputs — this module
  (``de4sdv/semantic/definition_projection.py``),
  ``scripts/generate_definition_projection.py``, and the two shared modules
  this machinery executes (``de4sdv/semantic/authority_inventory.py`` for
  declaration/doc-scan normalization, digests and the revision containment
  check, and ``de4sdv/semantic/projection_o2p.py`` for canonical JSON) — plus
  the admission document, the design record, and the governed model files
  carrying the admitted declarations. Every one is digest-bound and must be
  contained byte-for-byte in the bound source revision.
* **Runtime:** ``vocabulary-only``; NO traversal is implemented or claimed,
  no runtime module reads these artifacts, and admission is NOT an authority
  transition (O3 owns that), NOT authored-YAML retirement (O4 closure owns
  that), and NOT support promotion.

Fail-closed: the manifest shape (exact admitted-row keys, identity
uniqueness, ``semantic_kind == class``, wave, declaration resolution, the
observation/equivalence rule), the recomputed documentation observation
matching ``expected_documentation_observation``, the bound-input digests,
and the source-revision containment check are all machine-checked. No O1
artifact is read anywhere in this module; the reviewed definition in the
manifest is the parity oracle only. A review or model edit that invalidates
any admitted assumption breaks generation instead of silently changing an
output.

Generated artifacts: ``build_artifact_pair`` emits the definition Projection
and Profile documents bound to a Git source revision, reusing the verified
O1/O2+ binding machinery (bound-input digests, revision containment check,
regeneration equality). ``run_check_errors`` refuses a repository where the
admissions exist but the artifacts are missing or stale.

Read-only and offline; never imported by the runtime.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ADMISSION_PATH = "docs/method-conformance/o4/definition-admission.yaml"
PROJECTION_PATH = "docs/method-conformance/o4/definition-projection.json"
PROFILE_PATH = "docs/method-conformance/o4/definition-profile.json"
MODULE_PATH = "de4sdv/semantic/definition_projection.py"
GENERATOR_PATH = "scripts/generate_definition_projection.py"
AUTHORITY_INVENTORY_PATH = "de4sdv/semantic/authority_inventory.py"
PROJECTION_O2P_PATH = "de4sdv/semantic/projection_o2p.py"
DESIGN_PATH = "docs/method-conformance/o4/definition-admission-design.md"
PROJECTION_SCHEMA = "de4sdv.o4-definition-projection/v1"
PROFILE_SCHEMA = "de4sdv.o4-definition-profile/v1"

ADMISSION_SCHEMA = "de4sdv.o4-definition-admission/v1"
SUPPORT = "vocabulary-only"
WARNING = (
    "vocabulary-only, no traversal, no runtime read, no authority retirement"
)

#: Declaration keyword -> representation class / API metaclass. Only the
#: declaration forms carried by this admitted batch are supported; an
#: unknown form is refused (fail-closed), never silently mapped.
REPRESENTATION_CLASSES = {
    "part": "part-definition",
    "requirement": "requirement-definition",
    "item": "item-definition",
    "allocation": "allocation-definition",
    "enum": "enumeration-definition",
}
API_METACLASSES = {
    "part": "PartDefinition",
    "requirement": "RequirementDefinition",
    "item": "ItemDefinition",
    "allocation": "AllocationDefinition",
    "enum": "EnumerationDefinition",
}

WITNESS_FORMS = [
    "ownedRelationship -> OwningMembership -> Documentation "
    "(definition documentation, authored source order)"
]

_ADMITTED_ROW_KEYS = frozenset(
    {
        "identity",
        "semantic_kind",
        "wave",
        "stage",
        "declaration",
        "evidence_state",
        "authority_current",
        "reviewed_definition",
        "expected_documentation_observation",
        "semantic_text_equivalence",
        "required_runtime_support_target",
    }
)
_OBSERVATIONS = frozenset({"normalized-exact", "differs"})
_REVIEWED_EQUIVALENT = "reviewed-equivalent"
_WAVES = frozenset({"W2", "W5"})


class DefinitionAdmissionError(ValueError):
    """The admission document or an admitted row violates the governed contract."""


def load_admission(path: Path) -> dict[str, Any]:
    """Load and shape-lock the governed definition-admission document."""
    import yaml

    if not path.is_file():
        raise DefinitionAdmissionError(f"definition-admission document missing: {path}")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise DefinitionAdmissionError(f"definition-admission document malformed: {path}")
    if document.get("schema") != ADMISSION_SCHEMA:
        raise DefinitionAdmissionError(
            f"definition-admission schema must be {ADMISSION_SCHEMA}: "
            f"{document.get('schema')!r}"
        )
    status = document.get("status")
    if not isinstance(status, str) or not status.strip():
        raise DefinitionAdmissionError("definition-admission status is required")
    admitted = document.get("admitted")
    if not isinstance(admitted, list) or not admitted:
        raise DefinitionAdmissionError(
            "definition-admission admitted rows are required (non-empty list)"
        )
    seen: set[str] = set()
    for row in admitted:
        if not isinstance(row, dict):
            raise DefinitionAdmissionError("admitted rows must be mappings")
        extra = set(row) - _ADMITTED_ROW_KEYS
        if extra:
            raise DefinitionAdmissionError(
                f"admitted row carries unknown keys: {sorted(extra)}"
            )
        missing = _ADMITTED_ROW_KEYS - set(row)
        if missing:
            raise DefinitionAdmissionError(
                f"admitted row missing keys: {sorted(missing)}"
            )
        identity = row["identity"]
        if not isinstance(identity, str) or not identity.strip():
            raise DefinitionAdmissionError("admitted row missing identity")
        if identity in seen:
            raise DefinitionAdmissionError(f"{identity}: duplicate admitted identity")
        seen.add(identity)
        if row["semantic_kind"] != "class":
            raise DefinitionAdmissionError(
                f"{identity}: semantic_kind must be 'class'"
            )
        if row["wave"] not in _WAVES:
            raise DefinitionAdmissionError(
                f"{identity}: wave must be one of {sorted(_WAVES)}"
            )
        declaration = row["declaration"]
        if not isinstance(declaration, dict) or set(declaration) != {"file", "declaration"}:
            raise DefinitionAdmissionError(
                f"{identity}: declaration must carry exactly file and declaration"
            )
        for key in ("file", "declaration"):
            value = declaration.get(key)
            if not isinstance(value, str) or not value.strip():
                raise DefinitionAdmissionError(
                    f"{identity}: declaration.{key} must be a non-empty string"
                )
        for key in (
            "stage",
            "evidence_state",
            "authority_current",
            "required_runtime_support_target",
        ):
            value = row[key]
            if not isinstance(value, str) or not value.strip():
                raise DefinitionAdmissionError(f"{identity}: {key} is required")
        reviewed = row["reviewed_definition"]
        if not isinstance(reviewed, str) or not reviewed.strip():
            raise DefinitionAdmissionError(f"{identity}: reviewed_definition is required")
        observation = row["expected_documentation_observation"]
        if observation not in _OBSERVATIONS:
            raise DefinitionAdmissionError(
                f"{identity}: expected_documentation_observation must be one of "
                f"{sorted(_OBSERVATIONS)}"
            )
        equivalence = row["semantic_text_equivalence"]
        if observation == "differs":
            if equivalence != _REVIEWED_EQUIVALENT:
                raise DefinitionAdmissionError(
                    f"{identity}: a 'differs' observation requires a recorded "
                    f"'{_REVIEWED_EQUIVALENT}' bounded review"
                )
        elif equivalence is not None:
            raise DefinitionAdmissionError(
                f"{identity}: a 'normalized-exact' observation requires a null "
                "semantic_text_equivalence"
            )
    return document


def load_document(root: Path) -> dict[str, Any]:
    return load_admission(root / ADMISSION_PATH)


def _authority_inventory():  # type: ignore[no-untyped-def]
    """The verified O1 normalization/doc-scan machinery (read-only reuse)."""
    import sys

    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from de4sdv.semantic import authority_inventory

    return authority_inventory


def _projection_row(root: Path, row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate one admitted row against the model and emit its two outputs."""
    identity = row["identity"]
    declaration = row["declaration"]
    file_rel = declaration["file"]
    declaration_text = declaration["declaration"]
    keyword = declaration_text.split()[0]
    if keyword not in REPRESENTATION_CLASSES:
        raise DefinitionAdmissionError(
            f"{identity}: unsupported declaration kind {keyword!r}; supported kinds: "
            f"{sorted(REPRESENTATION_CLASSES)}"
        )
    path = root / file_rel
    if not path.is_file():
        raise DefinitionAdmissionError(
            f"{identity}: declaration file missing: {file_rel}"
        )
    file_text = path.read_text(encoding="utf-8")
    inventory = _authority_inventory()
    block, bodyless = inventory.declaration_block(file_text, declaration_text)
    if not block or bodyless:
        raise DefinitionAdmissionError(
            f"{identity}: declaration not found (or bodyless): {declaration_text}"
        )
    bodies = inventory._owned_doc_bodies(block)
    if not bodies:
        raise DefinitionAdmissionError(
            f"{identity}: declaration owns no documentation body: {declaration_text}"
        )
    observation = inventory.doc_text_observation(
        file_text, declaration_text, row["reviewed_definition"]
    )
    if observation != row["expected_documentation_observation"]:
        raise DefinitionAdmissionError(
            f"{identity}: recomputed documentation observation {observation!r} does "
            f"not match expected_documentation_observation "
            f"{row['expected_documentation_observation']!r} (reviewed definition "
            "text and model documentation disagree)"
        )
    projection_row = {
        "identity": identity,
        "semantic_kind": row["semantic_kind"],
        "wave": row["wave"],
        "definition": {
            "documentation": " ".join(bodies),
            "documentation_witness": {
                "source_file": file_rel,
                "declaration": declaration_text,
                "doc_count": len(bodies),
            },
            "documentation_observation": observation,
            "semantic_text_equivalence": row["semantic_text_equivalence"],
        },
        "grounding": {
            "kernel_binding_contract": {
                "source_file": file_rel,
                "declaration": declaration_text,
            }
        },
        "support": SUPPORT,
        "traversal": False,
        "api_identity": "unclaimed",
    }
    profile_entry = {
        "profile_identity": f"{PROFILE_SCHEMA}#{identity}",
        "for_concept": identity,
        "representation_class": REPRESENTATION_CLASSES[keyword],
        "binding_contract_echo": {
            "source_file": file_rel,
            "declaration": declaration_text,
            "api_metaclass": API_METACLASSES[keyword],
        },
        "witness_forms": list(WITNESS_FORMS),
    }
    return projection_row, profile_entry


def build_outputs(root: Path, document: dict[str, Any]) -> dict[str, Any]:
    """Validate every admitted row and emit the separated projection/profile rows."""
    admitted = document.get("admitted")
    if not isinstance(admitted, list):
        raise DefinitionAdmissionError("admitted must be a list")
    projection_rows: list[dict[str, Any]] = []
    profile_entries: list[dict[str, Any]] = []
    for row in admitted:
        projection_row, profile_entry = _projection_row(root, row)
        projection_rows.append(projection_row)
        profile_entries.append(profile_entry)
    projection_rows.sort(key=lambda item: item["identity"])
    profile_entries.sort(key=lambda item: item["for_concept"])
    return {
        "admitted": sorted(row["identity"] for row in admitted),
        "projection_rows": projection_rows,
        "profile_entries": profile_entries,
    }


def collect_bound_inputs(root: Path, outputs: dict[str, Any]) -> dict[str, str]:
    """Every input the generated artifacts depend on, as path -> sha256."""
    from de4sdv.semantic.authority_inventory import file_digest

    paths = {
        ADMISSION_PATH,
        DESIGN_PATH,
        MODULE_PATH,
        GENERATOR_PATH,
        AUTHORITY_INVENTORY_PATH,
        PROJECTION_O2P_PATH,
    }
    for row in outputs["projection_rows"]:
        paths.add(row["grounding"]["kernel_binding_contract"]["source_file"])
    bound: dict[str, str] = {}
    for relative in sorted(paths):
        path = root / relative
        if not path.is_file():
            raise DefinitionAdmissionError(f"bound input missing: {relative}")
        bound[relative] = file_digest(root, relative)
    return bound


def build_artifact_pair(root: Path, *, source_revision: str) -> dict[str, Any]:
    """Build both definition artifacts bound to one Git source revision.

    Reuses the verified O1/O2+ binding machinery: the source revision must
    contain every bound input byte-for-byte, and the artifact records the
    bound-input digests so a stale revision cannot pass by string reuse.
    """
    from de4sdv.semantic.authority_inventory import (
        InventoryError,
        verify_source_revision_contains_inputs,
    )
    from de4sdv.semantic.projection_o2p import canonical_json  # noqa: F401 (re-export)

    document = load_document(root)
    outputs = build_outputs(root, document)
    bound_inputs = collect_bound_inputs(root, outputs)
    try:
        verify_source_revision_contains_inputs(root, source_revision, bound_inputs)
    except InventoryError as exc:
        raise DefinitionAdmissionError(str(exc)) from exc
    binding = {
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
            "program_inputs": [
                MODULE_PATH,
                GENERATOR_PATH,
                AUTHORITY_INVENTORY_PATH,
                PROJECTION_O2P_PATH,
            ],
            "note": (
                "Generation-software revision: the commit containing these "
                "program inputs byte-for-byte. Both shared modules are listed "
                "because this machinery executes them at generation time "
                "(declaration/doc-scan normalization, digests, revision "
                "containment, canonical JSON)."
            ),
        },
        "semantic_model_revision": {
            "model_inputs": sorted(
                {
                    row["grounding"]["kernel_binding_contract"]["source_file"]
                    for row in outputs["projection_rows"]
                }
            ),
            "note": (
                "Semantic-model revision: ONLY the governed model files "
                "carrying the admitted definition declarations, contained "
                "byte-for-byte in source_revision."
            ),
        },
        "admission_document": {
            "path": ADMISSION_PATH,
            "digest": bound_inputs[ADMISSION_PATH],
        },
        "design_record": {
            "path": DESIGN_PATH,
            "digest": bound_inputs[DESIGN_PATH],
        },
        "api_binding": {
            "status": "unclaimed",
            "note": (
                "No SysML API element UUID is claimed for these definitions; "
                "the profile entries state representation mechanics only."
            ),
        },
        "bound_inputs": bound_inputs,
    }
    projection = {
        "schema": PROJECTION_SCHEMA,
        "status": "admitted",
        "warning": WARNING,
        "binding": binding,
        "scope": {
            "admission": "O4 definition-admission batch 1 (definition-admission.yaml)",
            "admitted": outputs["admitted"],
            "note": "no frozen O3 or gated identity is admitted",
        },
        "rows": outputs["projection_rows"],
    }
    profile = {
        "schema": PROFILE_SCHEMA,
        "status": "admitted",
        "warning": WARNING,
        "binding": binding,
        "entries": outputs["profile_entries"],
    }
    return {"projection": projection, "profile": profile}


def run_check_errors(root: Path) -> list[str]:
    """Fail-closed repository check for the definition admissions and artifacts.

    Inputs are always validated. Once admissions exist, the generated
    artifacts are required: missing artifacts, an invalid source binding, or
    committed bytes differing from regeneration are all errors.
    """
    from de4sdv.semantic.authority_inventory import validate_source_binding
    from de4sdv.semantic.projection_o2p import canonical_json

    try:
        document = load_document(root)
        outputs = build_outputs(root, document)
    except DefinitionAdmissionError as exc:
        return [f"{ADMISSION_PATH}: {exc}"]
    if not outputs["admitted"]:
        return []
    missing = [
        relative
        for relative in (PROJECTION_PATH, PROFILE_PATH)
        if not (root / relative).is_file()
    ]
    if missing:
        return [
            f"{relative}: definition-projection artifacts not generated yet for "
            f"{len(outputs['admitted'])} admitted identities; commit the admission "
            "inputs first, then run scripts/generate_definition_projection.py "
            "(two-commit source binding)"
            for relative in missing
        ]
    try:
        committed = json.loads((root / PROJECTION_PATH).read_text(encoding="utf-8"))
        binding = committed["binding"]
    except (KeyError, ValueError) as exc:
        return [f"{PROJECTION_PATH}: cannot read binding for validation: {exc}"]
    binding_errors = validate_source_binding(root, binding)
    if binding_errors:
        return [
            f"{PROJECTION_PATH}: source-revision binding invalid: {error}"
            for error in binding_errors
        ]
    source_revision = binding["source_revision"]
    try:
        artifacts = build_artifact_pair(root, source_revision=source_revision)
    except DefinitionAdmissionError as exc:
        return [f"definition-projection artifact generation failed: {exc}"]
    errors: list[str] = []
    if canonical_json(artifacts["projection"]) != (
        root / PROJECTION_PATH
    ).read_text(encoding="utf-8"):
        errors.append(
            f"{PROJECTION_PATH}: committed projection differs from regeneration "
            "from current inputs (regenerate and commit)"
        )
    if canonical_json(artifacts["profile"]) != (
        root / PROFILE_PATH
    ).read_text(encoding="utf-8"):
        errors.append(
            f"{PROFILE_PATH}: committed profile differs from regeneration from "
            "current inputs (regenerate and commit)"
        )
    return errors