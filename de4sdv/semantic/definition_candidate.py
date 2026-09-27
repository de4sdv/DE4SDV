"""O4 definition-candidate loader — fail-closed offline read of the admitted definition pair.

Read-only consumer of the generated O4 definition-admission artifacts
(``definition-projection.json`` + ``definition-profile.json``): exposes the
admitted definition identities and their already-governed definition and
mapping records for offline candidate consumption. It creates no semantics —
rows and entries are returned exactly as published; no traversal is claimed,
no runtime module reads them, and this is not an authority transition.

Fail-closed contract:

* both artifacts must exist, parse as JSON objects, and carry their published
  schemas and the ``admitted`` status;
* the two artifacts must share ONE identical binding and ONE identical
  identity set in both directions (rows, profile entries, and
  ``scope.admitted``), with no duplicates anywhere and one ``profile_identity``
  per row;
* every projection row's kernel binding contract must agree with its profile
  entry echo (source file + declaration);
* the pair must not overlap the frozen O3 migrated identity set — imported
  from :mod:`de4sdv.semantic.o3_bundle` (the single reviewed list), never
  re-listed here;
* the recorded revision binding is always
  validated through the existing ``authority_inventory.validate_source_binding``
  and the committed bytes are checked against regeneration through the
  existing ``definition_projection.run_check_errors``; a tampered artifact or
  a stale revision is refused instead of loaded;
* returned mappings are recursively immutable; nested lists become tuples.

Never imported by the runtime.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from collections.abc import Mapping
from typing import Any

PROJECTION_PATH = "docs/method-conformance/o4/definition-projection.json"
PROFILE_PATH = "docs/method-conformance/o4/definition-profile.json"
PROJECTION_SCHEMA = "de4sdv.o4-definition-projection/v1"
PROFILE_SCHEMA = "de4sdv.o4-definition-profile/v1"

_SUPPORT = "vocabulary-only"
_OBSERVATIONS = frozenset({"normalized-exact", "differs"})
_REVIEWED_EQUIVALENT = "reviewed-equivalent"
_WAVES = frozenset({"W2", "W5"})
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

_ROW_KEYS = frozenset(
    {
        "identity",
        "semantic_kind",
        "wave",
        "definition",
        "grounding",
        "support",
        "traversal",
        "api_identity",
    }
)
_DEFINITION_KEYS = frozenset(
    {
        "documentation",
        "documentation_witness",
        "documentation_observation",
        "semantic_text_equivalence",
    }
)
_WITNESS_KEYS = frozenset({"source_file", "declaration", "doc_count"})
_ENTRY_KEYS = frozenset(
    {
        "profile_identity",
        "for_concept",
        "representation_class",
        "binding_contract_echo",
        "witness_forms",
    }
)
_ECHO_KEYS = frozenset({"source_file", "declaration", "api_metaclass"})
_CONTRACT_KEYS = frozenset({"source_file", "declaration"})


class DefinitionCandidateError(ValueError):
    """The candidate pair violates the governed contract or failed verification."""


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class DefinitionCandidate:
    """The verified admitted definition pair, ready for offline consumption."""

    source_revision: str
    bound_inputs: Mapping[str, str]
    identities: tuple[str, ...]
    rows: tuple[Mapping[str, Any], ...]
    entries: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        for field in ("bound_inputs", "identities", "rows", "entries"):
            object.__setattr__(self, field, _freeze(getattr(self, field)))

    def row_for(self, identity: str) -> Mapping[str, Any]:
        """The published projection row for one admitted identity."""
        for row in self.rows:
            if row["identity"] == identity:
                return row
        raise DefinitionCandidateError(
            f"{identity}: not an admitted definition identity"
        )

    def entry_for(self, identity: str) -> Mapping[str, Any]:
        """The published profile entry for one admitted identity."""
        for entry in self.entries:
            if entry["for_concept"] == identity:
                return entry
        raise DefinitionCandidateError(
            f"{identity}: not an admitted definition identity"
        )


def _repo_module(stem: str):  # type: ignore[no-untyped-def]
    """Import one existing repository module (read-only reuse)."""
    import sys

    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    import importlib

    return importlib.import_module(f"de4sdv.semantic.{stem}")


def _load_document(root: Path, relative: str, expected_schema: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise DefinitionCandidateError(
            f"{relative}: definition candidate artifact missing: {path}"
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise DefinitionCandidateError(f"{relative}: malformed JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise DefinitionCandidateError(f"{relative}: artifact must be a JSON object")
    if document.get("schema") != expected_schema:
        raise DefinitionCandidateError(
            f"{relative}: schema must be {expected_schema}: {document.get('schema')!r}"
        )
    if document.get("status") != "admitted":
        raise DefinitionCandidateError(
            f"{relative}: status must be 'admitted': {document.get('status')!r}"
        )
    return document


def _binding_errors(binding: Any) -> list[str]:
    if not isinstance(binding, dict):
        return ["binding must be a mapping"]
    errors: list[str] = []
    source_revision = binding.get("source_revision")
    if not isinstance(source_revision, str) or not source_revision.strip():
        errors.append("binding.source_revision is required")
    bound_inputs = binding.get("bound_inputs")
    if not isinstance(bound_inputs, dict) or not bound_inputs:
        errors.append("binding.bound_inputs must be a non-empty path -> sha256 mapping")
    else:
        for relative, digest in sorted(bound_inputs.items()):
            if not isinstance(relative, str) or not relative.strip():
                errors.append("binding.bound_inputs carries a non-string path")
            if not isinstance(digest, str) or not _DIGEST.match(digest):
                errors.append(f"binding.bound_inputs digest invalid for {relative!r}")
    return errors


def _row_errors(row: dict[str, Any]) -> list[str]:
    identity = row.get("identity")
    label = identity if isinstance(identity, str) and identity.strip() else "<row without identity>"
    errors: list[str] = []
    extra = set(row) - _ROW_KEYS
    missing = _ROW_KEYS - set(row)
    if extra:
        errors.append(f"{label}: projection row carries unknown keys: {sorted(extra)}")
    if missing:
        errors.append(f"{label}: projection row missing keys: {sorted(missing)}")
    if not isinstance(identity, str) or not identity.strip():
        errors.append("projection row missing identity")
    if row.get("semantic_kind") != "class":
        errors.append(f"{label}: semantic_kind must be 'class'")
    if row.get("wave") not in _WAVES:
        errors.append(f"{label}: wave must be one of {sorted(_WAVES)}")
    if row.get("support") != _SUPPORT:
        errors.append(f"{label}: support must be {_SUPPORT!r}")
    if row.get("traversal") is not False:
        errors.append(f"{label}: traversal must be false")
    if row.get("api_identity") != "unclaimed":
        errors.append(f"{label}: api_identity must be 'unclaimed'")
    definition = row.get("definition")
    if not isinstance(definition, dict):
        errors.append(f"{label}: definition must be a mapping")
    else:
        extra = set(definition) - _DEFINITION_KEYS
        missing = _DEFINITION_KEYS - set(definition)
        if extra:
            errors.append(f"{label}: definition carries unknown keys: {sorted(extra)}")
        if missing:
            errors.append(f"{label}: definition missing keys: {sorted(missing)}")
        documentation = definition.get("documentation")
        if not isinstance(documentation, str) or not documentation.strip():
            errors.append(f"{label}: definition.documentation is required")
        witness = definition.get("documentation_witness")
        if not isinstance(witness, dict):
            errors.append(f"{label}: definition.documentation_witness must be a mapping")
        else:
            if set(witness) != _WITNESS_KEYS:
                errors.append(
                    f"{label}: definition.documentation_witness must carry exactly "
                    f"{sorted(_WITNESS_KEYS)}"
                )
            for key in ("source_file", "declaration"):
                value = witness.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{label}: documentation_witness.{key} is required")
            doc_count = witness.get("doc_count")
            if not isinstance(doc_count, int) or isinstance(doc_count, bool) or doc_count < 1:
                errors.append(f"{label}: documentation_witness.doc_count must be a positive integer")
        observation = definition.get("documentation_observation")
        if observation not in _OBSERVATIONS:
            errors.append(
                f"{label}: documentation_observation must be one of {sorted(_OBSERVATIONS)}"
            )
        equivalence = definition.get("semantic_text_equivalence")
        if observation == "differs":
            if equivalence != _REVIEWED_EQUIVALENT:
                errors.append(
                    f"{label}: a 'differs' observation requires a recorded "
                    f"'{_REVIEWED_EQUIVALENT}' bounded review"
                )
        elif equivalence is not None:
            errors.append(
                f"{label}: a 'normalized-exact' observation requires a null "
                "semantic_text_equivalence"
            )
    grounding = row.get("grounding")
    if not isinstance(grounding, dict):
        errors.append(f"{label}: grounding must be a mapping")
    else:
        contract = grounding.get("kernel_binding_contract")
        if not isinstance(contract, dict) or set(contract) != _CONTRACT_KEYS:
            errors.append(
                f"{label}: grounding.kernel_binding_contract must carry exactly "
                f"{sorted(_CONTRACT_KEYS)}"
            )
        else:
            for key in ("source_file", "declaration"):
                value = contract.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{label}: kernel_binding_contract.{key} is required")
    return errors


def _entry_errors(entry: dict[str, Any]) -> list[str]:
    concept = entry.get("for_concept")
    label = concept if isinstance(concept, str) and concept.strip() else "<entry without concept>"
    errors: list[str] = []
    extra = set(entry) - _ENTRY_KEYS
    missing = _ENTRY_KEYS - set(entry)
    if extra:
        errors.append(f"{label}: profile entry carries unknown keys: {sorted(extra)}")
    if missing:
        errors.append(f"{label}: profile entry missing keys: {sorted(missing)}")
    if not isinstance(concept, str) or not concept.strip():
        errors.append("profile entry missing for_concept")
    profile_identity = entry.get("profile_identity")
    if not isinstance(profile_identity, str) or not profile_identity.strip():
        errors.append(f"{label}: profile_identity is required")
    elif isinstance(concept, str) and concept.strip():
        if profile_identity != f"{PROFILE_SCHEMA}#{concept}":
            errors.append(
                f"{label}: profile_identity must be {PROFILE_SCHEMA}#{concept}"
            )
    representation_class = entry.get("representation_class")
    if not isinstance(representation_class, str) or not representation_class.strip():
        errors.append(f"{label}: representation_class is required")
    echo = entry.get("binding_contract_echo")
    if not isinstance(echo, dict) or set(echo) != _ECHO_KEYS:
        errors.append(
            f"{label}: binding_contract_echo must carry exactly {sorted(_ECHO_KEYS)}"
        )
    else:
        for key in ("source_file", "declaration", "api_metaclass"):
            value = echo.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}: binding_contract_echo.{key} is required")
    witness_forms = entry.get("witness_forms")
    if (
        not isinstance(witness_forms, list)
        or not witness_forms
        or not all(isinstance(form, str) and form.strip() for form in witness_forms)
    ):
        errors.append(f"{label}: witness_forms must be a non-empty string list")
    return errors


def _pair_errors(projection: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    projection_binding = projection.get("binding")
    profile_binding = profile.get("binding")
    if projection_binding != profile_binding:
        errors.append("projection and profile bindings differ (one pair, one binding)")
    errors.extend(
        _binding_errors(projection_binding if isinstance(projection_binding, dict) else {})
    )

    rows = projection.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append("projection rows must be a non-empty list")
        rows = []
    entries = profile.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("profile entries must be a non-empty list")
        entries = []

    row_identities: list[str] = []
    rows_by_identity: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            errors.append("projection row must be a mapping")
            continue
        errors.extend(_row_errors(row))
        identity = row.get("identity")
        if isinstance(identity, str) and identity.strip():
            row_identities.append(identity)
            rows_by_identity.setdefault(identity, row)

    entry_identities: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("profile entry must be a mapping")
            continue
        errors.extend(_entry_errors(entry))
        concept = entry.get("for_concept")
        if isinstance(concept, str) and concept.strip():
            entry_identities.append(concept)
        row = rows_by_identity.get(concept) if isinstance(concept, str) else None
        if row is None:
            continue
        contract = row.get("grounding", {}).get("kernel_binding_contract")
        echo = entry.get("binding_contract_echo")
        if isinstance(contract, dict) and isinstance(echo, dict):
            for key in ("source_file", "declaration"):
                if contract.get(key) != echo.get(key):
                    errors.append(
                        f"{concept}: profile binding_contract_echo.{key} does not "
                        "match the projection kernel binding contract"
                    )

    for label, identities in (
        ("projection row", row_identities),
        ("profile entry", entry_identities),
    ):
        seen: set[str] = set()
        for identity in identities:
            if identity in seen:
                errors.append(f"{identity}: duplicate {label} identity")
            seen.add(identity)

    row_set = set(row_identities)
    entry_set = set(entry_identities)
    for identity in sorted(row_set - entry_set):
        errors.append(f"{identity}: admitted projection row has no profile entry")
    for identity in sorted(entry_set - row_set):
        errors.append(f"{identity}: profile entry has no admitted projection row")

    scope = projection.get("scope")
    if not isinstance(scope, dict):
        errors.append("projection scope must be a mapping")
    else:
        admitted = scope.get("admitted")
        if (
            not isinstance(admitted, list)
            or not admitted
            or not all(isinstance(item, str) and item.strip() for item in admitted)
        ):
            errors.append("projection scope.admitted must be a non-empty identity list")
        else:
            if sorted(set(admitted)) != sorted(admitted):
                errors.append("projection scope.admitted must be sorted and duplicate-free")
            admitted_set = set(admitted)
            for identity in sorted(admitted_set - row_set):
                errors.append(f"{identity}: scope.admitted identity has no projection row")
            for identity in sorted(row_set - admitted_set):
                errors.append(f"{identity}: projection row missing from scope.admitted")

    o3_bundle = _repo_module("o3_bundle")
    for identity in sorted(row_set & set(o3_bundle.MIGRATED_IDENTITIES)):
        errors.append(
            f"{identity}: admitted identity overlaps the frozen O3 migrated "
            "identity set"
        )
    return errors


def load_definition_candidate(root: Path) -> DefinitionCandidate:
    """Load the admitted definition pair for offline candidate consumption.

    Structural pair validation always runs. The recorded revision binding is validated through
    ``authority_inventory.validate_source_binding`` and the committed bytes
    are checked against regeneration through
    ``definition_projection.run_check_errors``; any tamper or stale binding is
    refused. There is no verification bypass in the public loader.
    """
    projection = _load_document(root, PROJECTION_PATH, PROJECTION_SCHEMA)
    profile = _load_document(root, PROFILE_PATH, PROFILE_SCHEMA)
    errors = _pair_errors(projection, profile)
    if errors:
        raise DefinitionCandidateError(
            "definition candidate pair rejected:\n  - " + "\n  - ".join(errors)
        )
    authority_inventory = _repo_module("authority_inventory")
    definition_projection = _repo_module("definition_projection")
    binding_errors = authority_inventory.validate_source_binding(
        root, projection["binding"]
    )
    if binding_errors:
        raise DefinitionCandidateError(
            f"{PROJECTION_PATH}: source-revision binding invalid:\n  - "
            + "\n  - ".join(binding_errors)
        )
    tamper_errors = definition_projection.run_check_errors(root)
    if tamper_errors:
        raise DefinitionCandidateError(
            "definition candidate pair failed repository verification:\n  - "
            + "\n  - ".join(tamper_errors)
        )
    if (
        projection != _load_document(root, PROJECTION_PATH, PROJECTION_SCHEMA)
        or profile != _load_document(root, PROFILE_PATH, PROFILE_SCHEMA)
    ):
        raise DefinitionCandidateError("definition candidate artifacts changed during validation")
    rows = tuple(sorted(projection["rows"], key=lambda row: row["identity"]))
    entries = tuple(sorted(profile["entries"], key=lambda entry: entry["for_concept"]))
    return DefinitionCandidate(
        source_revision=projection["binding"]["source_revision"],
        bound_inputs=dict(projection["binding"]["bound_inputs"]),
        identities=tuple(sorted({row["identity"] for row in rows})),
        rows=rows,
        entries=entries,
    )
