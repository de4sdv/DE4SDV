"""External evidence-reference contract: fail-closed validation of supplied records.

Governed machinery for the reviewed external-boundary rows ``EvidenceArtifact``,
``hasEvidence`` and ``capturedInBaseline`` (with ``Baseline`` as the referenced
boundary identity). The governed semantics are the reviewed definitions:

* an evidence reference carries explicit case identity, artifact identity,
  exact revision, digest, run and tested scope;
* a baseline inclusion is explicit membership of that exact version identity in
  an identified immutable external manifest;
* the model owns the typed reference schema only — artifact bytes, artifact
  status, acceptance decisions and baseline contents stay external.

The contract validates SUPPLIED records and the committed prepared profile
artifact only:

* no network fetch, no content mirroring, no artifact byte claims;
* association, validity and inclusion never imply a pass, a verdict or an
  acceptance — those flags are machine-locked ``False`` in every output;
* malformed, incomplete, claim-inflating or foreign-shaped records fail closed;
* the evidence-lineage external-boundary family is DERIVED from the governed
  register/review, so family drift breaks generation instead of silently
  changing the contract.

Read-only; never imported by the runtime; grants no authority.

Acceptance: every profile entry must carry an ``accepted_ref`` that resolves to
a repository governance document under ``docs/`` carrying the
engineering-review acceptance marker, recording the identity as both the
reference fragment and a table row; free-text references and personal
owner-approval claims are refused. Recording acceptance changes nothing
operational: ``activation`` stays ``none`` and no traversal, mirroring or
baseline list is introduced.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DECLARATION_PATTERN = re.compile(
    r"^\s*(?:abstract\s+)?(?:part|item|enum|attribute|requirement|concern|viewpoint|view|connection|interface|action|state|allocation)\s+def\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)

PROFILE_PATH = "docs/method-conformance/o4/external-reference-profile.yaml"
REGISTER_PATH = "docs/method-conformance/o4/o4-execution-register.json"
REVIEW_PATH = "docs/method-conformance/o4/ontology-review/integrated-review.json"

PROFILE_SCHEMA = "de4sdv.o4-external-reference-profile/v1"
TYPED_REFERENCE_SCHEMA = "de4sdv.evidence-reference/v1"
BASELINE_MANIFEST_SCHEMA = "de4sdv.baseline-manifest-reference/v1"

#: The acceptance document must carry this marker verbatim; a free-text
#: acceptance reference or a personal owner-approval claim is refused.
ACCEPTANCE_MARKER = "accepted-as-engineering-review-evidence"
ACCEPTANCE_ROOT = "docs/"

#: ``prepared`` is the pre-acceptance state; the accepted state records
#: engineering-review evidence. Neither state activates anything.
PROFILE_STATUS_PREPARED = "prepared"
PROFILE_STATUS_ACCEPTED = "accepted-engineering-review-evidence"
PROFILE_STATUSES = (PROFILE_STATUS_PREPARED, PROFILE_STATUS_ACCEPTED)

VERSION_IDENTITY_FORM = "<artifact_identity>@<artifact_revision>"

REQUIRED_REFERENCE_FIELDS = (
    "case_identity",
    "artifact_identity",
    "artifact_revision",
    "digest",
    "run",
    "tested_scope",
)
FORBIDDEN_RECORD_FIELDS = frozenset(
    {
        "verdict",
        "passed",
        "accepted",
        "approval",
        "status",
        "traversal",
        "sysml_mapping",
        "implies_pass",
        "implies_acceptance",
        "implies_approval",
    }
)
REPRESENTATION_CLASSES = frozenset(
    {"external-reference-record", "model-resident-boundary-identity"}
)
MACHINE_LOCKED = {
    "implies_pass": False,
    "implies_verification": False,
    "implies_acceptance": False,
    "implies_approval": False,
    "traversal": False,
    "runtime_support": "external",
    "content_mirrored": False,
}


class EvidenceReferenceError(ValueError):
    """A supplied evidence reference, manifest, profile or family violates the contract."""


def _require_text(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EvidenceReferenceError(f"{context}: {key} must be a non-empty string")
    return value


def _refuse_forbidden(record: dict[str, Any], context: str) -> None:
    extra = sorted(FORBIDDEN_RECORD_FIELDS & set(record))
    if extra:
        raise EvidenceReferenceError(
            f"{context}: record carries claim-inflating or traversal-overloading fields: {extra}"
        )


def normalize_digest(value: Any, context: str) -> dict[str, str]:
    """Normalize a digest to {algorithm: sha256, value: lowercase hex64}."""
    if isinstance(value, str):
        candidate = value.strip().lower()
        if not _SHA256.match(candidate):
            raise EvidenceReferenceError(f"{context}: digest must be a sha256 hex string")
        return {"algorithm": "sha256", "value": candidate}
    if isinstance(value, dict) and value.get("algorithm") == "sha256":
        candidate = str(value.get("value", "")).strip().lower()
        if not _SHA256.match(candidate):
            raise EvidenceReferenceError(f"{context}: digest.value must be a sha256 hex string")
        return {"algorithm": "sha256", "value": candidate}
    raise EvidenceReferenceError(
        f"{context}: digest must be a sha256 hex string or {{algorithm: sha256, value}}"
    )


def version_identity(artifact_identity: str, artifact_revision: str) -> str:
    """The exact version identity form the baseline manifest must carry."""
    return f"{artifact_identity}@{artifact_revision}"


def validate_typed_reference(record: dict[str, Any]) -> dict[str, Any]:
    """Validate one supplied typed evidence reference; returns a normalized record."""
    if not isinstance(record, dict):
        raise EvidenceReferenceError("evidence reference must be a mapping")
    _refuse_forbidden(record, "reference")
    case_identity = _require_text(record, "case_identity", "reference")
    artifact_identity = _require_text(record, "artifact_identity", "reference")
    artifact_revision = _require_text(record, "artifact_revision", "reference")
    for field, value in (
        ("artifact_identity", artifact_identity),
        ("artifact_revision", artifact_revision),
    ):
        if "@" in value:
            raise EvidenceReferenceError(
                f"reference: {field} must not contain '@'; the version identity "
                f"form {VERSION_IDENTITY_FORM} must stay unambiguous"
            )
    digest = normalize_digest(record.get("digest"), "reference")
    run = _require_text(record, "run", "reference")
    scope = record.get("tested_scope")
    if (
        not isinstance(scope, list)
        or not scope
        or not all(isinstance(item, str) and item.strip() for item in scope)
    ):
        raise EvidenceReferenceError(
            "reference: tested_scope must be a non-empty list of scope references"
        )
    return {
        "schema": TYPED_REFERENCE_SCHEMA,
        "case_identity": case_identity,
        "artifact_identity": artifact_identity,
        "artifact_revision": artifact_revision,
        "version_identity": version_identity(artifact_identity, artifact_revision),
        "digest": digest,
        "run": run,
        "tested_scope": sorted(item.strip() for item in scope),
        # Machine-locked: a validated reference implies nothing further.
        "implies_pass": False,
        "implies_verification": False,
        "implies_acceptance": False,
        "traversal": False,
        "runtime_support": "external",
        "content_mirrored": False,
    }


def validate_evidence_reference(record: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible name for the single typed-reference contract."""
    return validate_typed_reference(record)


def validate_baseline_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate one supplied baseline manifest (identity + immutable version entries)."""
    if not isinstance(manifest, dict):
        raise EvidenceReferenceError("baseline manifest must be a mapping")
    _refuse_forbidden(manifest, "baseline")
    identity = _require_text(manifest, "baseline_identity", "baseline")
    digest = normalize_digest(manifest.get("manifest_digest"), "baseline")
    entries = manifest.get("entries")
    if (
        not isinstance(entries, list)
        or not entries
        or not all(isinstance(item, str) and item.strip() for item in entries)
    ):
        raise EvidenceReferenceError(
            "baseline: entries must be a non-empty list of artifact version identities"
        )
    normalized_entries: list[str] = []
    for item in entries:
        candidate = item.strip()
        parts = candidate.split("@")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise EvidenceReferenceError(
                f"baseline: entry {candidate!r} is not an exact "
                f"{VERSION_IDENTITY_FORM} version identity"
            )
        normalized_entries.append(candidate)
    return {
        "schema": BASELINE_MANIFEST_SCHEMA,
        "baseline_identity": identity,
        "manifest_digest": digest,
        "entries": sorted(normalized_entries),
        "version_identity_form": VERSION_IDENTITY_FORM,
        "second_baseline_list": False,
    }


def baseline_inclusion(reference: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """Explicit baseline inclusion of a validated reference — never approval.

    Membership is exact: the reference's version identity must appear verbatim in
    the identified manifest. A different revision of the same artifact identity
    is not included (no carry-forward).
    """
    normalized_reference = validate_typed_reference(reference)
    normalized_manifest = validate_baseline_manifest(manifest)
    included = normalized_reference["version_identity"] in set(normalized_manifest["entries"])
    return {
        "artifact_identity": normalized_reference["artifact_identity"],
        "artifact_revision": normalized_reference["artifact_revision"],
        "version_identity": normalized_reference["version_identity"],
        "baseline_identity": normalized_manifest["baseline_identity"],
        "included": included,
        # Machine-locked: inclusion does not approve evidence.
        "implies_approval": False,
        "implies_pass": False,
        "implies_acceptance": False,
        "traversal": False,
    }


def association_state(reference: dict[str, Any]) -> dict[str, Any]:
    """The only state an association may expose from a supplied reference."""
    normalized = validate_typed_reference(reference)
    return {
        "external_reference_validated": True,
        "case_identity": normalized["case_identity"],
        "artifact_identity": normalized["artifact_identity"],
        "artifact_revision": normalized["artifact_revision"],
        "version_identity": normalized["version_identity"],
        "run": normalized["run"],
        "implies_pass": False,
        "implies_verification": False,
        "implies_acceptance": False,
        "traversal": False,
        "runtime_support": "external",
    }


def external_boundary_state(identity: str) -> dict[str, Any]:
    """Blocked-state surface: what a query may report for these rows."""
    if not isinstance(identity, str) or not identity.strip():
        raise EvidenceReferenceError("boundary state requires a row identity")
    return {
        "identity": identity.strip(),
        "runtime_support": "external",
        "traversal": False,
        "content_mirrored": False,
        "external_facts_retained": True,
        "blocked_reason": (
            "external evidence/configuration systems hold the content and the "
            "decision; the model owns the typed reference schema only"
        ),
        "implies_pass": False,
        "implies_acceptance": False,
    }


# --------------------------------------------------------------------------- #
# Prepared profile artifact: fail-closed family lock + profile entry validation
# --------------------------------------------------------------------------- #

def load_profile(path: Path) -> dict[str, Any]:
    import yaml

    if not path.is_file():
        raise EvidenceReferenceError(f"external-reference profile missing: {path}")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise EvidenceReferenceError(f"external-reference profile malformed: {path}")
    if document.get("schema") != PROFILE_SCHEMA:
        raise EvidenceReferenceError(
            f"external-reference profile schema must be {PROFILE_SCHEMA}: "
            f"{document.get('schema')!r}"
        )
    if (
        document.get("status") not in PROFILE_STATUSES
        or document.get("activation") != "none"
    ):
        raise EvidenceReferenceError(
            "external-reference profile must stay prepared-or-accepted "
            f"(status one of {sorted(PROFILE_STATUSES)}) with activation none"
        )
    return document


def load_register(root: Path) -> dict[str, Any]:
    path = root / REGISTER_PATH
    if not path.is_file():
        raise EvidenceReferenceError(f"O4 execution register missing: {REGISTER_PATH}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("rows"), list):
        raise EvidenceReferenceError("O4 execution register has no rows")
    return document


def load_review(root: Path) -> dict[str, Any]:
    path = root / REVIEW_PATH
    if not path.is_file():
        raise EvidenceReferenceError(f"canonical review missing: {REVIEW_PATH}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("rows"), list):
        raise EvidenceReferenceError("canonical review has no rows")
    return document


def _index_rows(rows: list[Any], context: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise EvidenceReferenceError(f"{context} carries a non-mapping row")
        identity = row.get("identity")
        if identity in index:
            raise EvidenceReferenceError(f"{context} carries duplicate identity {identity!r}")
        index[identity] = row
    return index


def derived_evidence_reference_family(register: dict[str, Any]) -> set[str]:
    """The DERIVED family: evidence-lineage external-boundary rows, no traversal.

    A register/review edit that adds or removes such a row changes this set, so
    the prepared profile breaks instead of silently changing its scope. The
    discriminator keys are REQUIRED on every row: a row that loses a key fails
    generation instead of silently dropping out of the family.
    """
    required_row_keys = (
        "identity",
        "final_disposition",
        "dependency_flags",
        "required_semantic_projection_change",
        "required_api_representation_profile_change",
        "required_runtime_or_consumer_change",
    )
    family: set[str] = set()
    for row in register["rows"]:
        missing = [key for key in required_row_keys if key not in row]
        if missing:
            raise EvidenceReferenceError(
                f"register row {row.get('identity')!r} is missing discriminator "
                f"keys {missing}; the family cannot be derived fail-closed"
            )
        flags = row["dependency_flags"]
        runtime = row["required_runtime_or_consumer_change"]
        if "evidence_lineage" not in flags:
            raise EvidenceReferenceError(
                f"register row {row['identity']!r}: dependency_flags.evidence_lineage missing"
            )
        for key in ("traversal_required", "runtime_support_target"):
            if key not in runtime:
                raise EvidenceReferenceError(
                    f"register row {row['identity']!r}: "
                    f"required_runtime_or_consumer_change.{key} missing"
                )
        if (
            row["final_disposition"] == "KEEP_EXTERNAL_REFERENCE"
            and flags["evidence_lineage"] is True
            and row["required_semantic_projection_change"] is False
            and row["required_api_representation_profile_change"] is False
            and runtime["traversal_required"] is False
            and runtime["runtime_support_target"] == "external"
        ):
            family.add(str(row["identity"]))
    if not family:
        raise EvidenceReferenceError("derived evidence-reference family is empty")
    return family


def _declaration_index(root: Path) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for model_root in (
        root / "textual-notation-of-model",
        root / "model-based-product-line-engineering",
    ):
        if not model_root.is_dir():
            continue
        for path in sorted(model_root.rglob("*.sysml")):
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in _DECLARATION_PATTERN.finditer(text):
                name = match.group(1)
                if name:
                    index.setdefault(name, []).append(str(path.relative_to(root)))
    return index


def _validate_schema_block(document: dict[str, Any]) -> None:
    if (
        document.get("status") not in PROFILE_STATUSES
        or document.get("activation") != "none"
    ):
        raise EvidenceReferenceError(
            "external-reference profile must stay prepared-or-accepted "
            f"(status one of {sorted(PROFILE_STATUSES)}) with activation none"
        )
    schema = document.get("typed_reference_schema")
    if not isinstance(schema, dict) or schema.get("identity") != TYPED_REFERENCE_SCHEMA:
        raise EvidenceReferenceError(
            f"typed_reference_schema.identity must be {TYPED_REFERENCE_SCHEMA}"
        )
    fields = schema.get("required_fields")
    if not isinstance(fields, dict) or tuple(sorted(fields)) != tuple(
        sorted(REQUIRED_REFERENCE_FIELDS)
    ):
        raise EvidenceReferenceError(
            "typed_reference_schema.required_fields must be exactly "
            f"{sorted(REQUIRED_REFERENCE_FIELDS)}"
        )
    forbidden = schema.get("forbidden_record_fields")
    if not isinstance(forbidden, list) or set(forbidden) != FORBIDDEN_RECORD_FIELDS:
        raise EvidenceReferenceError(
            "typed_reference_schema.forbidden_record_fields must be exactly "
            f"{sorted(FORBIDDEN_RECORD_FIELDS)}"
        )
    locked = schema.get("machine_locked")
    if not isinstance(locked, dict):
        raise EvidenceReferenceError("typed_reference_schema.machine_locked required")
    unknown_locked = sorted(set(locked) - set(MACHINE_LOCKED))
    if unknown_locked:
        raise EvidenceReferenceError(
            f"typed_reference_schema.machine_locked carries unknown keys: {unknown_locked}"
        )
    for key, expected in MACHINE_LOCKED.items():
        if locked.get(key) != expected:
            raise EvidenceReferenceError(
                f"typed_reference_schema.machine_locked.{key} must be {expected!r}"
            )
    manifest = document.get("baseline_manifest_schema")
    if not isinstance(manifest, dict) or manifest.get("identity") != BASELINE_MANIFEST_SCHEMA:
        raise EvidenceReferenceError(
            f"baseline_manifest_schema.identity must be {BASELINE_MANIFEST_SCHEMA}"
        )


def _validate_accepted_ref(root: Path, identity: str, entry: dict[str, Any]) -> str:
    """Machine-check one entry's recorded acceptance (fail closed).

    Mirrors the acceptance-reference validation proven for the vocabulary
    carriers: the reference must resolve to a repository governance document
    under ``docs/`` carrying the engineering-review acceptance marker, its
    fragment must equal the identity, and the document must record the identity
    as a table row. A free-text reference or a personal owner-approval claim is
    refused. The acceptance document is a READ INPUT of this check; no revision
    binding is claimed for it.
    """
    accepted_ref = entry.get("accepted_ref")
    if not isinstance(accepted_ref, str) or not accepted_ref.strip():
        raise EvidenceReferenceError(
            f"{identity}: acceptance not recorded (accepted_ref required on every "
            "profile entry)"
        )
    accepted_ref = accepted_ref.strip()
    accepted_path = accepted_ref.split("#", 1)[0].strip()
    parts = Path(accepted_path).parts
    if not accepted_path.startswith(ACCEPTANCE_ROOT) or ".." in parts:
        raise EvidenceReferenceError(
            f"{identity}: accepted_ref must name a repository governance document "
            f"under {ACCEPTANCE_ROOT} without parent traversal "
            f"(got {accepted_ref!r})"
        )
    acceptance_doc = (root / accepted_path).resolve()
    acceptance_root = (root / ACCEPTANCE_ROOT).resolve()
    if acceptance_doc != acceptance_root and acceptance_root not in acceptance_doc.parents:
        raise EvidenceReferenceError(
            f"{identity}: accepted_ref must resolve inside {ACCEPTANCE_ROOT} "
            f"(got {accepted_ref!r})"
        )
    if not acceptance_doc.is_file():
        raise EvidenceReferenceError(
            f"{identity}: accepted_ref does not resolve to a repository document: "
            f"{accepted_path}"
        )
    acceptance_text = acceptance_doc.read_text(encoding="utf-8")
    if ACCEPTANCE_MARKER not in acceptance_text:
        raise EvidenceReferenceError(
            f"{identity}: acceptance document {accepted_path} does not carry the "
            f"engineering-review acceptance marker ({ACCEPTANCE_MARKER})"
        )
    fragment = accepted_ref.split("#", 1)[1].strip() if "#" in accepted_ref else None
    if fragment != identity:
        raise EvidenceReferenceError(
            f"{identity}: accepted_ref fragment must equal the identity (got {fragment!r})"
        )
    if not re.search(rf"^\s*\|\s*{re.escape(identity)}\s*\|", acceptance_text, re.MULTILINE):
        raise EvidenceReferenceError(
            f"{identity}: acceptance document {accepted_path} does not record this "
            "identity as a table row"
        )
    return accepted_ref


def validate_profile(
    root: Path, document: dict[str, Any], register: dict[str, Any], review: dict[str, Any]
) -> dict[str, Any]:
    """Machine-lock the prepared profile against the governed register and review."""
    _validate_schema_block(document)
    derived = derived_evidence_reference_family(register)
    expected = document.get("expected_rows")
    if not isinstance(expected, list) or not expected:
        raise EvidenceReferenceError("expected_rows must be a non-empty list")
    if len(set(expected)) != len(expected):
        raise EvidenceReferenceError("expected_rows must not carry duplicates")
    if set(expected) != derived:
        raise EvidenceReferenceError(
            "evidence-reference family drift vs the governed register: "
            f"missing {sorted(derived - set(expected))}; "
            f"unexpected {sorted(set(expected) - derived)}"
        )
    scope = document.get("scope_rows")
    if not isinstance(scope, list) or not scope:
        raise EvidenceReferenceError("scope_rows must be a non-empty list")
    if not set(scope) <= derived:
        raise EvidenceReferenceError(
            f"scope_rows outside the derived family: {sorted(set(scope) - derived)}"
        )

    register_index = _index_rows(register["rows"], "O4 execution register")
    review_index = _index_rows(review["rows"], "canonical review")
    declarations = _declaration_index(root)

    entries = document.get("profile_entries")
    if not isinstance(entries, list) or not entries:
        raise EvidenceReferenceError("profile_entries must be a non-empty list")
    seen: set[str] = set()
    profile_rows: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise EvidenceReferenceError("profile entries must be mappings")
        allowed = {
            "identity",
            "representation_class",
            "mechanics",
            "declaration",
            "accepted_ref",
        }
        extra = set(entry) - allowed
        if extra:
            raise EvidenceReferenceError(f"profile entry carries unknown keys: {sorted(extra)}")
        identity = entry.get("identity")
        if identity not in derived:
            raise EvidenceReferenceError(
                f"profile entry {identity!r} is outside the derived family"
            )
        if identity in seen:
            raise EvidenceReferenceError(f"profile entry {identity}: duplicate")
        seen.add(identity)
        accepted_ref = _validate_accepted_ref(root, identity, entry)
        mechanics = entry.get("mechanics")
        if not isinstance(mechanics, str) or not mechanics.strip():
            raise EvidenceReferenceError(f"{identity}: mechanics must be non-empty")
        representation_class = entry.get("representation_class")
        if representation_class not in REPRESENTATION_CLASSES:
            raise EvidenceReferenceError(
                f"{identity}: representation_class must be one of "
                f"{sorted(REPRESENTATION_CLASSES)}"
            )

        review_row = review_index.get(identity)
        if review_row is None:
            raise EvidenceReferenceError(f"{identity}: missing from the canonical review")
        target = review_row.get("target") or {}
        if target.get("disposition") != "KEEP_EXTERNAL_REFERENCE":
            raise EvidenceReferenceError(
                f"{identity}: reviewed disposition is not KEEP_EXTERNAL_REFERENCE"
            )
        for flag in ("projection_required", "api_profile_required", "traversal_required"):
            if target.get(flag) is not False:
                raise EvidenceReferenceError(
                    f"{identity}: reviewed target {flag} must be false for this profile"
                )
        if target.get("runtime_support_target") != "external":
            raise EvidenceReferenceError(
                f"{identity}: reviewed runtime_support_target must be external"
            )
        definition = target.get("definition")
        if not isinstance(definition, str) or not definition.strip():
            raise EvidenceReferenceError(f"{identity}: reviewed definition missing")
        register_row = register_index.get(identity)
        if register_row is None:
            raise EvidenceReferenceError(f"{identity}: missing from the O4 execution register")
        if register_row.get("final_disposition") != "KEEP_EXTERNAL_REFERENCE":
            raise EvidenceReferenceError(
                f"{identity}: register disposition is not KEEP_EXTERNAL_REFERENCE"
            )
        if (register_row.get("required_runtime_or_consumer_change") or {}).get(
            "traversal_required"
        ) is not False:
            raise EvidenceReferenceError(f"{identity}: register must not require traversal")

        declaration = entry.get("declaration")
        row: dict[str, Any] = {
            "identity": identity,
            "representation_class": representation_class,
            "definition": definition,
            "mechanics": mechanics,
            "accepted_ref": accepted_ref,
            "support": "external",
            "traversal": False,
            "runtime_support": "external",
            "implies_pass": False,
            "implies_acceptance": False,
        }
        if representation_class == "model-resident-boundary-identity":
            if not isinstance(declaration, dict):
                raise EvidenceReferenceError(
                    f"{identity}: boundary identity requires a declaration file/name"
                )
            file_rel = declaration.get("file")
            name = declaration.get("name")
            if not isinstance(file_rel, str) or not isinstance(name, str):
                raise EvidenceReferenceError(f"{identity}: declaration file/name required")
            if not (root / file_rel).is_file():
                raise EvidenceReferenceError(f"{identity}: declaration file missing: {file_rel}")
            if file_rel not in declarations.get(name, []):
                raise EvidenceReferenceError(
                    f"{identity}: declaration {name!r} not found in {file_rel}"
                )
            row["declaration"] = {"file": file_rel, "name": name}
        elif declaration is not None:
            raise EvidenceReferenceError(
                f"{identity}: external-reference-record entries carry no declaration"
            )
        profile_rows.append(row)

    missing = derived - seen
    if missing:
        raise EvidenceReferenceError(
            f"derived family rows without a profile entry: {sorted(missing)}"
        )
    if not set(scope) <= seen:
        raise EvidenceReferenceError(
            f"scope_rows without a profile entry: {sorted(set(scope) - seen)}"
        )
    profile_rows.sort(key=lambda item: item["identity"])
    return {
        "schema": "de4sdv.o4-external-reference-profile-outputs/v1",
        "warning": (
            "Prepared profile only. External boundary retained: no traversal, no "
            "content mirroring, no baseline list, no pass/verification/acceptance/"
            "approval implication."
        ),
        "family": sorted(derived),
        "scope_rows": sorted(scope),
        "acceptance_documents": sorted(
            {row["accepted_ref"].split("#", 1)[0].strip() for row in profile_rows}
        ),
        "profile_rows": profile_rows,
    }


def build_profile_outputs(root: Path) -> dict[str, Any]:
    """Validate the committed prepared profile and emit its profile rows."""
    document = load_profile(root / PROFILE_PATH)
    register = load_register(root)
    review = load_review(root)
    return validate_profile(root, document, register, review)


def run_check_errors(root: Path) -> list[str]:
    """Fail-closed repository check for the committed external-reference profile."""
    try:
        build_profile_outputs(root)
    except EvidenceReferenceError as exc:
        return [f"{PROFILE_PATH}: {exc}"]
    return []
