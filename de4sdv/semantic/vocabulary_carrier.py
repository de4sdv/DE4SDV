"""Vocabulary-relationship definition carriers (O4 W4 preparation machinery).

ONE reusable, governed carrier representation for reviewed vocabulary-only
relationships — the ``recordsGap``/``recordsAssumption``/``addressesConcern``/
``selectedViewpoint``/``producesView`` family:

* **Model side (carrier):** a kernel declaration whose owned documentation
  carries the reviewed definition, with typed ends carrying the predicate's
  domain and range — the accepted ``connection def`` pattern established by
  the requirement-derivation connection.
* **Projection side (semantic meaning):** the identity, the reviewed
  definition, the domain/range lineage, and the review's claim boundary.
* **Profile side (representation mechanics only):** the carrier construct
  mechanics; never a second semantic statement, never a UUID claim.
* **Runtime:** ``vocabulary-only``; NO traversal is implemented or claimed,
  and a record containing ``sysml_mapping`` is refused outright — that field
  carries implemented runtime-strategy meaning elsewhere and must never be
  overloaded here.

Fail-closed: the curated candidate family, the reviewed definition text
(normalized-exact against the carrier's owned documentation), the reviewed
output flags, the accepted-reference requirement, the declaration/end
resolution, and the ``sysml_mapping`` ban are all machine-checked. A review
edit that invalidates any curated assumption breaks generation instead of
silently changing an output.

Acceptance: an admission's ``accepted_ref`` must resolve to a repository
governance document that carries the engineering-review acceptance marker and
records the identity; free-text references and personal owner-approval
claims are refused. The five admitted definitions close as engineering
review evidence (see the bounded acceptance review document), never as a
personal approval.

Generated artifacts: ``build_artifact_pair`` emits the carrier Projection and
Profile documents bound to a Git source revision, reusing the verified
O1/O2+ binding machinery (bound-input digests, revision containment check,
regeneration equality). ``run_check_errors`` refuses a repository where the
admissions exist but the artifacts are missing or stale.

Read-only and offline; never imported by the runtime.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CARRIERS_PATH = "docs/method-conformance/o4/vocabulary-carriers.yaml"
REVIEW_PATH = "docs/method-conformance/o4/ontology-review/integrated-review.json"
PROJECTION_CARRIER_PATH = "docs/method-conformance/o4/vocabulary-carriers-projection.json"
PROFILE_CARRIER_PATH = "docs/method-conformance/o4/vocabulary-carriers-profile.json"
DESIGN_CARRIER_PATH = "docs/method-conformance/o4/vocabulary-carrier-design.md"
MODULE_CARRIER_PATH = "de4sdv/semantic/vocabulary_carrier.py"
GENERATOR_CARRIER_PATH = "scripts/generate_vocabulary_carriers.py"

#: The acceptance document must carry this marker verbatim; a free-text
#: acceptance reference or a personal owner-approval claim is refused.
ACCEPTANCE_MARKER = "accepted-as-engineering-review-evidence"
ACCEPTANCE_ROOT = "docs/"

EXPECTED_AUTHORITY = "DE4SDV model-resident method vocabulary"
SUPPORT = "vocabulary-only"

_DECLARATION_PATTERN = re.compile(
    r"^\s*(?:abstract\s+)?(?:part|item|enum|attribute|requirement|concern|viewpoint|view|connection|interface|action|state|allocation)\s+def\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)


class CarrierError(ValueError):
    """The carrier document or an admission violates the governed contract."""


def load_carriers(path: Path) -> dict[str, Any]:
    import yaml

    if not path.is_file():
        raise CarrierError(f"vocabulary-carrier document missing: {path}")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise CarrierError(f"vocabulary-carrier document malformed: {path}")
    if document.get("schema") != "de4sdv.o4-vocabulary-carriers/v1":
        raise CarrierError(
            f"vocabulary-carrier schema must be de4sdv.o4-vocabulary-carriers/v1: {document.get('schema')!r}"
        )
    return document


def load_review(root: Path) -> dict[str, Any]:
    path = root / REVIEW_PATH
    if not path.is_file():
        raise CarrierError(f"canonical review missing: {REVIEW_PATH}")
    return json.loads(path.read_text(encoding="utf-8"))


def _review_rows(review: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = review.get("rows")
    if not isinstance(rows, list):
        raise CarrierError("canonical review has no rows")
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        identity = row.get("identity")
        if identity in index:
            raise CarrierError(f"canonical review carries duplicate identity {identity!r}")
        index[identity] = row
    return index


def validate_candidate_family(document: dict[str, Any], review: dict[str, Any]) -> None:
    """Machine-lock the curated candidate family against the governed review.

    The family is DERIVED from the review: every relationship whose reviewed
    target is exactly the carrier profile (KEEP_VOCABULARY_ONLY, model-resident
    method vocabulary authority, projection + profile required, no traversal,
    vocabulary-only support). A review edit that adds or removes such a row
    breaks generation instead of silently changing the family.
    """
    expected = document.get("expected_candidates")
    if not isinstance(expected, list) or not expected:
        raise CarrierError("expected_candidates must be a non-empty list")
    if len(set(expected)) != len(expected):
        raise CarrierError("expected_candidates must not carry duplicates")
    derived: set[str] = set()
    for identity, row in _review_rows(review).items():
        if row.get("kind") != "relationship":
            continue
        target = row.get("target") or {}
        if (
            target.get("disposition") == "KEEP_VOCABULARY_ONLY"
            and target.get("authority") == EXPECTED_AUTHORITY
            and target.get("projection_required") is True
            and target.get("api_profile_required") is True
            and target.get("traversal_required") is False
            and target.get("runtime_support_target") == SUPPORT
        ):
            derived.add(identity)
    declared = set(expected)
    if declared != derived:
        raise CarrierError(
            "candidate family drift vs the canonical review: "
            f"missing {sorted(derived - declared)}; unexpected {sorted(declared - derived)}"
        )
    excluded = document.get("excluded")
    if excluded is None:
        excluded = []
    if not isinstance(excluded, list):
        raise CarrierError("excluded must be a list when present")
    seen: set[str] = set()
    for item in excluded:
        if not isinstance(item, dict) or item.get("identity") not in declared:
            raise CarrierError("excluded entries must name a candidate-family identity")
        if item["identity"] in seen:
            raise CarrierError(f"excluded carries duplicate identity {item['identity']!r}")
        seen.add(item["identity"])
        reason = item.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise CarrierError(f"excluded {item['identity']}: a governed reason is required")


def declaration_index(root: Path) -> dict[str, list[str]]:
    """Names of every model declaration under the SysML model roots (read-only)."""
    index: dict[str, list[str]] = {}
    for model_root in (root / "textual-notation-of-model", root / "model-based-product-line-engineering"):
        if not model_root.is_dir():
            continue
        for path in sorted(model_root.rglob("*.sysml")):
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in _DECLARATION_PATTERN.finditer(text):
                index.setdefault(match.group(1), []).append(
                    str(path.relative_to(root))
                )
    return index


def _authority_inventory():  # type: ignore[no-untyped-def]
    """The verified O1 normalization/doc-scan machinery (read-only reuse)."""
    import sys

    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from de4sdv.semantic import authority_inventory

    return authority_inventory


def _normalized(text: str) -> str:
    return _authority_inventory().normalize_text(text)


def _owned_doc_bodies(block: str) -> list[str]:
    return _authority_inventory()._owned_doc_bodies(block)


def _ontology_kernel_index(root: Path) -> dict[str, tuple[str, str] | None]:
    """Reviewed-identity -> ontology kernel mapping (fail-closed source).

    Every class identity of the authored ontology maps either to a
    ``(file, declaration)`` pair (repo-resident semantics) or to ``None``
    (native/external semantics with no kernel declaration). An end whose
    reviewed identity is not an ontology class at all is refused by the
    caller: the reviewed domain/range must be a governed identity.
    """
    from de4sdv.semantic.kernel_contract import KernelContract

    contract = KernelContract.load(
        root / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )
    index: dict[str, tuple[str, str] | None] = {}
    for name, spec in contract.classes.items():
        kernel = (spec or {}).get("kernel") or {}
        if "file" in kernel and "declaration" in kernel:
            index[str(name)] = (str(kernel["file"]), str(kernel["declaration"]))
        elif "native" in kernel or "external" in kernel:
            index[str(name)] = None
    return index


def _validate_entry(
    root: Path,
    entry: dict[str, Any],
    review_row: dict[str, Any],
    index: dict[str, list[str]],
    kernel_index: dict[str, tuple[str, str] | None],
) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise CarrierError("admitted entries must be mappings")
    allowed = {"identity", "carrier", "ends", "accepted_ref", "library_types"}
    extra = set(entry) - allowed
    if extra:
        raise CarrierError(f"admitted entry carries unknown keys: {sorted(extra)}")
    if "sysml_mapping" in entry:
        raise CarrierError(
            "admitted entry must not carry sysml_mapping (no executable traversal claim)"
        )
    identity = entry.get("identity")
    if not isinstance(identity, str) or not identity:
        raise CarrierError("admitted entry missing identity")
    accepted_ref = entry.get("accepted_ref")
    if not isinstance(accepted_ref, str) or not accepted_ref.strip():
        raise CarrierError(
            f"{identity}: acceptance not recorded (accepted_ref required before admission)"
        )
    accepted_path = accepted_ref.split("#", 1)[0].strip()
    parts = Path(accepted_path).parts
    if not accepted_path.startswith(ACCEPTANCE_ROOT) or ".." in parts:
        raise CarrierError(
            f"{identity}: accepted_ref must name a repository governance document "
            f"under {ACCEPTANCE_ROOT} without parent traversal (got {accepted_ref!r})"
        )
    acceptance_doc = (root / accepted_path).resolve()
    acceptance_root = (root / ACCEPTANCE_ROOT).resolve()
    if acceptance_doc != acceptance_root and acceptance_root not in acceptance_doc.parents:
        raise CarrierError(
            f"{identity}: accepted_ref must resolve inside {ACCEPTANCE_ROOT} "
            f"(got {accepted_ref!r})"
        )
    if not acceptance_doc.is_file():
        raise CarrierError(
            f"{identity}: accepted_ref does not resolve to a repository document: "
            f"{accepted_path}"
        )
    acceptance_text = acceptance_doc.read_text(encoding="utf-8")
    if ACCEPTANCE_MARKER not in acceptance_text:
        raise CarrierError(
            f"{identity}: acceptance document {accepted_path} does not carry the "
            f"engineering-review acceptance marker ({ACCEPTANCE_MARKER})"
        )
    fragment = accepted_ref.split("#", 1)[1].strip() if "#" in accepted_ref else None
    if fragment is not None and fragment != identity:
        raise CarrierError(
            f"{identity}: accepted_ref fragment must equal the identity (got {fragment!r})"
        )
    if not re.search(rf"^\s*\|\s*{re.escape(identity)}\s*\|", acceptance_text, re.MULTILINE):
        raise CarrierError(
            f"{identity}: acceptance document {accepted_path} does not record this "
            "identity as a table row"
        )
    carrier = entry.get("carrier") or {}
    file_rel = carrier.get("file")
    declaration = carrier.get("declaration")
    if not isinstance(file_rel, str) or not isinstance(declaration, str):
        raise CarrierError(f"{identity}: carrier file/declaration required")
    carrier_path = root / file_rel
    if not carrier_path.is_file():
        raise CarrierError(f"{identity}: carrier file missing: {file_rel}")
    if str(carrier_path).startswith(str(root / "docs")) or str(carrier_path).startswith(str(root / "approach")):
        raise CarrierError(f"{identity}: carrier must be a model declaration file, not governance data")

    target = review_row.get("target") or {}
    definition = target.get("definition")
    if not isinstance(definition, str) or not definition.strip():
        raise CarrierError(f"{identity}: reviewed definition missing")

    text = carrier_path.read_text(encoding="utf-8")
    block, bodyless = _authority_inventory().declaration_block(text, declaration)
    if not block or bodyless:
        raise CarrierError(
            f"{identity}: carrier declaration not found (or bodyless): {declaration}"
        )
    bodies = _owned_doc_bodies(block)
    if not any(_normalized(body) == _normalized(definition) for body in bodies):
        raise CarrierError(
            f"{identity}: carrier documentation does not carry the reviewed definition "
            "(normalized-exact)"
        )

    ends = entry.get("ends") or {}
    if set(ends) != {"domain", "range"}:
        raise CarrierError(f"{identity}: ends must declare exactly domain and range")
    library_types = set(entry.get("library_types") or [])
    for item in sorted(library_types):
        parts = item.split("::")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise CarrierError(
                f"{identity}: library_types entries must be package-qualified "
                f"(Package::Type): {item!r}"
            )
    library_names = {item.split("::")[1]: item for item in library_types}
    end_rows = {}
    for role in ("domain", "range"):
        spec = ends.get(role) or {}
        if not isinstance(spec, dict) or set(spec) - {"feature", "type", "declaration"}:
            raise CarrierError(
                f"{identity}: ends.{role} carries unknown keys: "
                f"{sorted(set(spec) - {'feature', 'type', 'declaration'}) if isinstance(spec, dict) else spec!r}"
            )
        feature = spec.get("feature")
        type_name = spec.get("type")
        if not isinstance(feature, str) or not isinstance(type_name, str):
            raise CarrierError(f"{identity}: ends.{role} needs feature and type")
        if not re.search(rf"^\s*end\s+{re.escape(feature)}\s*:\s*{re.escape(type_name)}\s*;", block, re.MULTILINE):
            raise CarrierError(
                f"{identity}: ends.{role} typing `end {feature} : {type_name}` not found in the carrier declaration"
            )
        if type_name in index and type_name in library_names:
            raise CarrierError(
                f"{identity}: ends.{role} type {type_name!r} is both a model "
                "declaration and a listed accepted-library type"
            )
        reviewed_name = target.get(role)
        if reviewed_name not in kernel_index:
            raise CarrierError(
                f"{identity}: reviewed ends.{role} identity {reviewed_name!r} is not "
                "an ontology class identity; the reviewed domain/range must be a "
                "governed identity"
            )
        expected = kernel_index[reviewed_name]
        pin = spec.get("declaration")
        if pin is not None:
            if (
                not isinstance(pin, dict)
                or set(pin) != {"file", "declaration"}
                or not isinstance(pin.get("file"), str)
                or not isinstance(pin.get("declaration"), str)
            ):
                raise CarrierError(
                    f"{identity}: ends.{role} declaration pin must carry exactly "
                    "file and declaration"
                )
            pin_file = str(pin["file"])
            pin_declaration = str(pin["declaration"])
            if pin_declaration.split()[-1] != type_name:
                raise CarrierError(
                    f"{identity}: ends.{role} declaration pin names "
                    f"{pin_declaration.split()[-1]!r} but the end type is {type_name!r}"
                )
            if pin_file not in index.get(type_name, []):
                raise CarrierError(
                    f"{identity}: ends.{role} declaration pin {pin_file}#{pin_declaration} "
                    f"does not resolve to the end type {type_name!r}"
                )
            if expected is not None and (pin_file, pin_declaration) != expected:
                raise CarrierError(
                    f"{identity}: ends.{role} declaration pin disagrees with the "
                    f"ontology kernel mapping {expected}"
                )
        if expected is not None:
            expected_file, expected_declaration = expected
            if type_name != expected_declaration.split()[-1]:
                raise CarrierError(
                    f"{identity}: ends.{role} type {type_name!r} is not the "
                    f"ontology-mapped declaration for {reviewed_name!r} "
                    f"({expected_declaration!r} in {expected_file})"
                )
            if expected_file not in index.get(type_name, []):
                raise CarrierError(
                    f"{identity}: ontology-mapped declaration {expected_file}"
                    f"#{expected_declaration} does not resolve to the end type "
                    f"{type_name!r}"
                )
        elif pin is None and type_name not in library_names:
            raise CarrierError(
                f"{identity}: ends.{role} identity {reviewed_name!r} has no "
                "repo-resident ontology declaration; the end type must be a listed "
                "accepted-library type or carry an explicit declaration pin"
            )
        if type_name not in index and type_name not in library_names:
            raise CarrierError(
                f"{identity}: ends.{role} type {type_name!r} is not a model declaration "
                "and is not marked as an accepted-library type"
            )
        if type_name in library_names:
            entry_name = library_names[type_name]
            package = entry_name.split("::", 1)[0]
            if not re.search(
                rf"^\s*(?:private\s+|public\s+)?import\s+{re.escape(package)}\s*::",
                text,
                re.MULTILINE,
            ):
                raise CarrierError(
                    f"{identity}: ends.{role} library type {entry_name!r} is not "
                    f"imported by the carrier file (no `import {package}::` statement)"
                )
        end_rows[role] = {"identity": reviewed_name, "type": type_name}
    return {
        "identity": identity,
        "definition": definition,
        "domain": end_rows["domain"],
        "range": end_rows["range"],
        "direction": target.get("direction"),
        "semantic_strength": target.get("semantic_strength"),
        "support": SUPPORT,
        "traversal": False,
        "accepted_ref": accepted_ref,
        "carrier": {"file": file_rel, "declaration": declaration},
    }


def build_carrier_outputs(
    root: Path, document: dict[str, Any], review: dict[str, Any]
) -> dict[str, Any]:
    """Validate every admission and emit the separated projection/profile outputs."""
    validate_candidate_family(document, review)
    review_index = _review_rows(review)
    decls = declaration_index(root)
    kernel_index = _ontology_kernel_index(root)
    excluded = {
        item["identity"]: item.get("reason")
        for item in (document.get("excluded") or [])
    }
    admitted = document.get("admitted")
    if not isinstance(admitted, list):
        raise CarrierError("admitted must be a list")
    seen: set[str] = set()
    projection_rows: list[dict[str, Any]] = []
    profile_entries: list[dict[str, Any]] = []
    for entry in admitted:
        identity = entry.get("identity") if isinstance(entry, dict) else None
        if not isinstance(identity, str) or identity not in (
            document.get("expected_candidates") or []
        ):
            raise CarrierError(
                f"{identity!r} is outside the reviewed candidate family"
            )
        if identity in seen:
            raise CarrierError(f"{identity}: duplicate admission")
        if identity in excluded:
            raise CarrierError(
                f"{identity}: excluded from admission by governance: {excluded[identity]}"
            )
        seen.add(identity)
        row = _validate_entry(root, entry, review_index[identity], decls, kernel_index)
        projection_rows.append(row)
        profile_entries.append(
            {
                "identity": identity,
                "representation_class": "model-resident-connection-carrier",
                "mechanics": (
                    "Typed-end connection definition in the method kernel; the owned "
                    "documentation carries the reviewed definition and claim boundary; "
                    "representation mechanics only, no API element identity claimed."
                ),
                "carrier": row["carrier"],
            }
        )
    projection_rows.sort(key=lambda item: item["identity"])
    profile_entries.sort(key=lambda item: item["identity"])
    return {
        "schema": "de4sdv.o4-vocabulary-carrier-outputs/v1",
        "warning": (
            "Generated from governed admissions only. Vocabulary-only: no runtime "
            "traversal or support promotion is implemented or claimed."
        ),
        "candidates": sorted(document.get("expected_candidates") or []),
        "admitted": sorted(seen),
        "projection_rows": projection_rows,
        "profile_entries": profile_entries,
    }


def collect_bound_inputs(
    root: Path, document: dict[str, Any], outputs: dict[str, Any]
) -> dict[str, str]:
    """Every input the generated artifacts depend on, as path -> sha256."""
    from de4sdv.semantic.authority_inventory import file_digest

    paths = {
        CARRIERS_PATH,
        REVIEW_PATH,
        DESIGN_CARRIER_PATH,
        MODULE_CARRIER_PATH,
        GENERATOR_CARRIER_PATH,
    }
    for row in outputs["projection_rows"]:
        paths.add(row["carrier"]["file"])
        # The accepted-reference document is a governance input: the admitted
        # definitions' acceptance evidence is part of the artifact lineage.
        paths.add(row["accepted_ref"].split("#", 1)[0].strip())
    bound: dict[str, str] = {}
    for relative in sorted(paths):
        path = root / relative
        if not path.is_file():
            raise CarrierError(f"bound input missing: {relative}")
        bound[relative] = file_digest(root, relative)
    return bound


def build_artifact_pair(root: Path, *, source_revision: str) -> dict[str, Any]:
    """Build both carrier artifacts bound to one Git source revision.

    Reuses the verified O1/O2+ binding machinery: the source revision must
    contain every bound input byte-for-byte, and the artifact records the
    bound-input digests so a stale revision cannot pass by string reuse.
    """
    from de4sdv.semantic.authority_inventory import (
        InventoryError,
        verify_source_revision_contains_inputs,
    )
    from de4sdv.semantic.projection_o2p import canonical_json  # noqa: F401 (re-export)

    document = load_carriers(root / CARRIERS_PATH)
    review = load_review(root)
    outputs = build_carrier_outputs(root, document, review)
    bound_inputs = collect_bound_inputs(root, document, outputs)
    try:
        verify_source_revision_contains_inputs(root, source_revision, bound_inputs)
    except InventoryError as exc:
        raise CarrierError(str(exc)) from exc
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
            "program_inputs": [MODULE_CARRIER_PATH, GENERATOR_CARRIER_PATH],
            "note": (
                "Generation-software revision: the commit containing these "
                "program inputs byte-for-byte."
            ),
        },
        "semantic_model_revision": {
            "model_inputs": sorted(
                {row["carrier"]["file"] for row in outputs["projection_rows"]}
            ),
            "note": (
                "Semantic-model revision: ONLY the governed model files "
                "carrying the admitted carrier declarations, contained "
                "byte-for-byte in source_revision."
            ),
        },
        "admission_document": {
            "path": CARRIERS_PATH,
            "digest": bound_inputs[CARRIERS_PATH],
        },
        "acceptance_review": {
            "paths": sorted(
                {row["accepted_ref"].split("#", 1)[0].strip() for row in outputs["projection_rows"]}
            ),
            "note": (
                "Engineering-review acceptance evidence bound as a governed "
                "input; the marker and identity records are machine-checked."
            ),
        },
        "api_binding": {
            "status": "unclaimed",
            "note": (
                "No SysML API element UUID is claimed for these carriers; the "
                "profile entries state representation mechanics only."
            ),
        },
        "bound_inputs": bound_inputs,
    }
    projection = {
        "schema": "de4sdv.vocabulary-carrier-projection/v1",
        "status": (
            "generated O4 W4 vocabulary-relationship carrier projection "
            "(reviewed definitions, model-resident carriers)"
        ),
        "warning": (
            "Generated artifact. Vocabulary-only: every row carries an "
            "admitted reviewed definition with its carrier lineage; no "
            "traversal is implemented or claimed, no support state is "
            "promoted, and the runtime does not read this artifact."
        ),
        "binding": binding,
        "candidates": outputs["candidates"],
        "admitted": outputs["admitted"],
        "rows": outputs["projection_rows"],
    }
    profile = {
        "schema": "de4sdv.vocabulary-carrier-profile/v1",
        "status": (
            "generated O4 W4 API Representation Profile (representation "
            "mechanics for the admitted carrier rows)"
        ),
        "warning": (
            "Generated artifact. Representation mechanics only: this profile "
            "cannot redefine domain, range, direction, semantic strength, "
            "exclusions, or claim boundaries. The runtime does not read this "
            "artifact."
        ),
        "binding": binding,
        "entries": outputs["profile_entries"],
    }
    return {"projection": projection, "profile": profile}


def run_check_errors(root: Path) -> list[str]:
    """Fail-closed repository check for the carrier admissions and artifacts.

    Inputs are always validated. Once admissions exist, the generated
    artifacts are required: missing artifacts, an invalid source binding, or
    committed bytes differing from regeneration are all errors.
    """
    from de4sdv.semantic.authority_inventory import validate_source_binding
    from de4sdv.semantic.projection_o2p import canonical_json

    try:
        document = load_carriers(root / CARRIERS_PATH)
        review = load_review(root)
        validate_candidate_family(document, review)
        outputs = build_carrier_outputs(root, document, review)
    except CarrierError as exc:
        return [f"{CARRIERS_PATH}: {exc}"]
    if not outputs["admitted"]:
        return []
    missing = [
        relative
        for relative in (PROJECTION_CARRIER_PATH, PROFILE_CARRIER_PATH)
        if not (root / relative).is_file()
    ]
    if missing:
        return [
            f"{relative}: carrier artifacts not generated yet for "
            f"{len(outputs['admitted'])} admitted identities; commit the admission "
            "inputs first, then run scripts/generate_vocabulary_carriers.py "
            "(two-commit source binding)"
            for relative in missing
        ]
    try:
        committed = json.loads((root / PROJECTION_CARRIER_PATH).read_text(encoding="utf-8"))
        binding = committed["binding"]
    except (KeyError, ValueError) as exc:
        return [f"{PROJECTION_CARRIER_PATH}: cannot read binding for validation: {exc}"]
    binding_errors = validate_source_binding(root, binding)
    if binding_errors:
        return [
            f"{PROJECTION_CARRIER_PATH}: source-revision binding invalid: {error}"
            for error in binding_errors
        ]
    source_revision = binding["source_revision"]
    try:
        artifacts = build_artifact_pair(root, source_revision=source_revision)
    except CarrierError as exc:
        return [f"vocabulary-carrier artifact generation failed: {exc}"]
    errors: list[str] = []
    if canonical_json(artifacts["projection"]) != (
        root / PROJECTION_CARRIER_PATH
    ).read_text(encoding="utf-8"):
        errors.append(
            f"{PROJECTION_CARRIER_PATH}: committed projection differs from "
            "regeneration from current inputs (regenerate and commit)"
        )
    if canonical_json(artifacts["profile"]) != (
        root / PROFILE_CARRIER_PATH
    ).read_text(encoding="utf-8"):
        errors.append(
            f"{PROFILE_CARRIER_PATH}: committed profile differs from "
            "regeneration from current inputs (regenerate and commit)"
        )
    return errors