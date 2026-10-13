"""Live definition admission: model-owned projection + API profile.

Each admitted identity is grounded in its named, non-bodyless definition
and its directly owned documentation, collected in authored source order.
The model is the documentation authority; admission carries locators and
scope, not a copied definition or a second text-parity oracle.

Projection rows carry meaning, ownership witnesses and kernel grounding.
Profile entries carry declaration-form representation mechanics and API
metaclass echoes only. Support remains vocabulary-only: no traversal proof,
API identity, authority transition or support promotion is claimed.

Construction is deterministic from the current source tree, including
uncommitted edits. Live artifacts contain no Git source-revision binding.
The repository gate validates every admitted row and requires both exact
regenerated artifact byte strings; missing and stale artifacts fail closed.
Frozen evidence retains its separate revision-bound contract unchanged.

Read-only and offline; never imported by the runtime.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

ADMISSION_PATH = "docs/method-conformance/o4/definition-admission.yaml"
PROJECTION_PATH = "docs/method-conformance/o4/definition-projection.json"
PROFILE_PATH = "docs/method-conformance/o4/definition-profile.json"
MODULE_PATH = "de4sdv/semantic/definition_projection.py"
GENERATOR_PATH = "scripts/generate_definition_projection.py"
AUTHORITY_INVENTORY_PATH = "de4sdv/semantic/authority_inventory.py"
PROJECTION_O2P_PATH = "de4sdv/semantic/projection_o2p.py"
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
        "required_runtime_support_target",
    }
)
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
    if not any(body.strip() for body in bodies):
        raise DefinitionAdmissionError(
            f"{identity}: declaration owns empty documentation: {declaration_text}"
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
            "documentation_observation": "model-owned-documentation",
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
    """Legacy diagnostic input inventory; live construction emits no digest binding."""
    from de4sdv.semantic.authority_inventory import file_digest

    paths = {
        ADMISSION_PATH,
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


def build_artifact_pair(root: Path) -> dict[str, Any]:
    """Build the live pair deterministically from current admitted model sources.

    No Git commit is a prerequisite or part of the generated payload. Frozen
    evidence keeps its separate revision-bound construction contract.
    """
    document = load_document(root)
    outputs = build_outputs(root, document)
    projection = {
        "schema": PROJECTION_SCHEMA,
        "status": "admitted",
        "warning": WARNING,
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
        "entries": outputs["profile_entries"],
    }
    return {"projection": projection, "profile": profile}


def run_check_errors(root: Path) -> list[str]:
    """Require the live pair to equal deterministic regeneration byte-for-byte.

    Current admitted sources are validated even when artifacts are missing.
    Uncommitted model edits are allowed; missing or stale outputs are not.
    """
    from de4sdv.semantic.projection_o2p import canonical_json

    try:
        artifacts = build_artifact_pair(root)
    except DefinitionAdmissionError as exc:
        return [f"{ADMISSION_PATH}: {exc}"]
    errors: list[str] = []
    for key, relative in (("projection", PROJECTION_PATH), ("profile", PROFILE_PATH)):
        path = root / relative
        if not path.is_file():
            errors.append(
                f"{relative}: definition artifact missing; run "
                "scripts/generate_definition_projection.py (regenerate and commit "
                "with the current sources)"
            )
        elif canonical_json(artifacts[key]).encode("utf-8") != path.read_bytes():
            errors.append(
                f"{relative}: committed {key} differs from regeneration from "
                "current inputs; run scripts/generate_definition_projection.py "
                "and commit the output with the source change "
                "(docs/guides/generated-semantic-assets.md)"
            )
    return errors
