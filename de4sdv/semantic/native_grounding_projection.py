"""Native-grounding projection: identities grounded in native or standard-library
SysML v2 constructs, with their API representation profile.

Governed by: ontology review Deliverable 8 wave 3 (native/library projection
rows over already-native constructs) + the ontology identity register rows for
the admitted identities. The layer records exact-fit standard-construct grounding
for already-native/library constructs and generates vocabulary-only projection
rows and API-representation profile entries over them.

Canonical artifacts:

- ``de4sdv/semantic/contract-data/native-grounding-projection.json``
  (the projection: one row per admitted identity, grounded in the
  reviewed construct witness, support stays vocabulary-only);
- ``de4sdv/semantic/contract-data/native-grounding-profile.json``
  (representation mechanics entries for the ``api_profile_required`` rows).

Deterministic freshness: identical current source inputs produce
byte-identical output. The live artifacts carry no Git revision or input
digest binding. ``--check`` validates the governed current inputs, regenerates
both documents, and compares exact bytes; construction needs no input commit.

Boundaries: offline and read-only; no network; no runtime semantic change;
generation is not authority activation; the runtime reads these artifacts to
build the kernel contract; support is never promoted beyond vocabulary-only;
no traversal is implemented or claimed; the identities served from the frozen
records (projection v1, v1.1 and v1.2) are never re-emitted (machine-locked).

Usage:

    python scripts/generate_native_grounding_projection.py              # write
    python scripts/generate_native_grounding_projection.py --check      # verify
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

from de4sdv.semantic.authority_inventory import file_digest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ADMISSION_PATH = "de4sdv/semantic/contract-data/native-grounding-admission.yaml"
PROJECTION_PATH = "de4sdv/semantic/contract-data/native-grounding-projection.json"
PROFILE_PATH = "de4sdv/semantic/contract-data/native-grounding-profile.json"
MODULE_PATH = "de4sdv/semantic/native_grounding_projection.py"
GENERATOR_PATH = "scripts/generate_native_grounding_projection.py"
SYSIDE_WORKFLOW_PATH = ".github/workflows/privileged-syside-validation.yml"

PROJECTION_SCHEMA = "de4sdv.semantic-projection.o2plus/v1"
PROFILE_SCHEMA = "de4sdv.api-representation-profile.o2plus/v1"

#: The identities of the frozen projection records (v1 seven + v1.1 three +
#: v1.2 three).
FROZEN_PROJECTION_ROW_IDENTITIES: tuple[str, ...] = (
    # projection v1
    "MethodContractObligation",
    "MethodPhase",
    "EvaluationScopeMembership",
    "EvaluationSourceKind",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
    # projection v1.1
    "VerificationCase",
    "hasSubject",
    "verifiedBy",
    # projection v1.2
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
    "hasRelevantArchitecture",
)

#: Machine lock: the exact reviewed safe subset this layer admits.
ADMITTED_SPEC: dict[str, dict[str, Any]] = {
    "VariationPoint": {
        "category": "native",
        "projection_required": False,
        "api_profile_required": True,
        "traversal_required": False,
    },
    "Variant": {
        "category": "native",
        "projection_required": False,
        "api_profile_required": True,
        "traversal_required": False,
    },
    "Concern": {
        "category": "native",
        "projection_required": True,
        "api_profile_required": False,
        "traversal_required": False,
    },
    "Viewpoint": {
        "category": "native",
        "projection_required": True,
        "api_profile_required": False,
        "traversal_required": False,
    },
    "View": {
        "category": "native",
        "projection_required": True,
        "api_profile_required": False,
        "traversal_required": False,
    },
    "VerificationMethod": {
        "category": "library-mapped-native",
        "projection_required": False,
        "api_profile_required": False,
        "traversal_required": False,
    },
    "usesVerificationMethod": {
        "category": "library-mapped-native",
        "projection_required": False,
        "api_profile_required": False,
        "traversal_required": False,
    },
    "IncrementSize": {
        "category": "model-resident-vocabulary",
        "projection_required": True,
        "api_profile_required": False,
        "traversal_required": False,
    },
}


class NativeGroundingError(RuntimeError):
    """Raised when native-grounding generation cannot proceed safely."""


def validate_row_outputs(identity: str, outputs: dict[str, Any]) -> None:
    """Fail closed when emitted outputs disagree with the reviewed flags.

    A grounding/admission record is NOT a projection output: rows whose
    reviewed ``projection_required`` is false must never claim a projection
    row, rows whose ``api_profile_required`` is false must never claim a
    profile entry, and traversal stays false everywhere unless the review
    explicitly requires it.
    """
    spec = ADMITTED_SPEC.get(identity)
    if spec is None:
        raise NativeGroundingError(f"{identity}: not an admitted identity")
    expected = {
        "projection_row": bool(spec["projection_required"]),
        "api_profile_entry": bool(spec["api_profile_required"]),
        "traversal": bool(spec["traversal_required"]),
    }
    if {key: bool(value) for key, value in outputs.items()} != expected:
        raise NativeGroundingError(
            f"{identity}: emitted outputs {outputs!r} contradict the reviewed "
            f"flags {expected!r}"
        )


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def resolve_source_revision(root: Path) -> str:
    """Legacy Git helper for existing consumers; unused by live construction."""
    result = _git(root, "rev-parse", "HEAD")
    if result.returncode != 0:
        raise NativeGroundingError(f"cannot resolve HEAD: {result.stderr.strip()}")
    return result.stdout.strip()


def canonical_json(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=False) + "\n"


# ---------------------------------------------------------------------------
# Admission manifest
# ---------------------------------------------------------------------------


def load_admission(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise NativeGroundingError(f"admission manifest missing: {path}")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise NativeGroundingError("admission manifest must be a mapping")
    return document


def validate_admission(manifest: dict[str, Any]) -> None:
    """Machine-lock the admission boundary (fail closed)."""
    if manifest.get("schema") != "de4sdv.o2plus-admission/v1":
        raise NativeGroundingError("admission manifest schema mismatch")
    admitted = manifest.get("admitted")
    if not isinstance(admitted, list) or not admitted:
        raise NativeGroundingError("admission manifest has no admitted rows")
    identities = [row.get("identity") for row in admitted]
    if len(set(identities)) != len(identities):
        raise NativeGroundingError("duplicate admitted identity")
    if set(identities) != set(ADMITTED_SPEC):
        raise NativeGroundingError(
            "admitted set must be EXACTLY the reviewed safe subset: "
            f"got {sorted(identities)!r}"
        )
    for row in admitted:
        identity = row["identity"]
        spec = ADMITTED_SPEC[identity]
        for key in ("projection_required", "api_profile_required", "traversal_required"):
            if bool(row.get(key)) is not bool(spec[key]):
                raise NativeGroundingError(
                    f"{identity}: {key} must equal the reviewed value {spec[key]!r}"
                )
        if row.get("category") != spec["category"]:
            raise NativeGroundingError(
                f"{identity}: category must equal the reviewed value {spec['category']!r}"
            )
        if row.get("support") != "vocabulary-only":
            raise NativeGroundingError(
                f"{identity}: support must stay vocabulary-only"
            )
        if row.get("traversal_required") is not False:
            raise NativeGroundingError(f"{identity}: traversal must not be required")
        witness = row.get("witness")
        if not isinstance(witness, dict) or not witness.get("file") or not witness.get("contains"):
            raise NativeGroundingError(f"{identity}: witness file/contains required")
        for field in ("construct", "exact_fit", "standard_construct", "claim_boundary"):
            if not row.get(field):
                raise NativeGroundingError(f"{identity}: {field} required")

    excluded = manifest.get("excluded")
    if not isinstance(excluded, list) or not excluded:
        raise NativeGroundingError("admission manifest has no excluded rows")
    excluded_ids = [row.get("identity") for row in excluded]
    if len(set(excluded_ids)) != len(excluded_ids):
        raise NativeGroundingError("duplicate excluded identity")
    overlap = set(excluded_ids) & set(identities)
    if overlap:
        raise NativeGroundingError(f"admitted/excluded overlap: {sorted(overlap)!r}")
    for row in excluded:
        if not row.get("reason"):
            raise NativeGroundingError(
                f"{row.get('identity')}: excluded rows require a reason"
            )
    # Hard gates that must never be admitted by this layer.
    for gated in (
        "allocatedTo",
        "EvidenceStatus",
        "variesAt",
        "FeatureConfiguration",
        "instantiatesCanonicalArchitecture",
    ):
        if gated not in set(excluded_ids):
            raise NativeGroundingError(
                f"hard-gated identity {gated} must remain in the excluded set"
            )
    # Frozen surfaces are never admitted here.
    for frozen in FROZEN_PROJECTION_ROW_IDENTITIES:
        if frozen in set(identities):
            raise NativeGroundingError(
                f"frozen projection row identity {frozen} must never be admitted"
            )


def _served_frozen_identities() -> frozenset[str]:
    """The identities the runtime serves from the frozen records."""
    from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES

    return frozenset(O2_CHAIN_IDENTITIES)


def verify_witnesses(root: Path, manifest: dict[str, Any]) -> None:
    """Every admitted row's construct witness must exist in the model."""
    for row in manifest["admitted"]:
        identity = row["identity"]
        witness = row["witness"]
        path = root / witness["file"]
        if not path.is_file():
            raise NativeGroundingError(
                f"{identity}: witness file missing: {witness['file']}"
            )
        if witness["contains"] not in path.read_text(encoding="utf-8"):
            raise NativeGroundingError(
                f"{identity}: witness construct not found in {witness['file']}: "
                f"{witness['contains']!r}"
            )
        frozen = _served_frozen_identities()
        if identity in frozen:
            raise NativeGroundingError(
                f"{identity}: an identity served from the frozen records must never be admitted"
            )


def read_syside_pin(root: Path) -> str:
    workflow = root / SYSIDE_WORKFLOW_PATH
    if not workflow.is_file():
        raise NativeGroundingError(f"syside workflow missing: {SYSIDE_WORKFLOW_PATH}")
    match = re.search(
        r'SYSIDE_VERSION="([^"]+)"', workflow.read_text(encoding="utf-8")
    )
    if not match:
        raise NativeGroundingError("syside version pin not found in the workflow")
    return match.group(1)


# ---------------------------------------------------------------------------
# Legacy input inventory (compatibility for existing consumers)
# ---------------------------------------------------------------------------


def collect_bound_inputs(root: Path, manifest: dict[str, Any]) -> dict[str, str]:
    """Legacy path/digest inventory; live construction/check emits no binding."""
    paths: set[str] = {
        ADMISSION_PATH,
        MODULE_PATH,
        GENERATOR_PATH,
        SYSIDE_WORKFLOW_PATH,
    }
    for row in manifest["admitted"]:
        paths.add(row["witness"]["file"])
    inputs: dict[str, str] = {}
    for path in sorted(paths):
        file = root / path
        if not file.is_file():
            raise NativeGroundingError(f"bound input missing: {path}")
        inputs[path] = file_digest(root, path)
    return inputs


# ---------------------------------------------------------------------------
# Row derivation and pair build
# ---------------------------------------------------------------------------


def derive_rows(
    root: Path, manifest: dict[str, Any], source_revision: str | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Derive from current model witnesses; legacy source_revision is ignored."""
    rows: list[dict[str, Any]] = []
    profile_entries: list[dict[str, Any]] = []
    syside_pin = read_syside_pin(root)
    for row in manifest["admitted"]:
        identity = row["identity"]
        witness = row["witness"]
        outputs = {
            "projection_row": bool(row["projection_required"]),
            "api_profile_entry": bool(row["api_profile_required"]),
            "traversal": bool(row["traversal_required"]),
        }
        validate_row_outputs(identity, outputs)
        rows.append(
            {
                "identity": identity,
                # No separate semantic-kind field: the governed category
                # (native / library-mapped-native / model-resident-vocabulary)
                # carries the precise distinction; a duplicated kind field
                # would invite misclassification.
                "category": row["category"],
                "construct": row["construct"],
                "grounding": {
                    "exact_fit": row["exact_fit"],
                    "standard_construct": row["standard_construct"],
                    "witness": {
                        "file": witness["file"],
                        "contains": witness["contains"],
                        "found": True,
                    },
                },
                "outputs": outputs,
                "support": "vocabulary-only",
                "claim_boundary": " ".join(str(row["claim_boundary"]).split()),
                "review_ref": {
                    "wave": "W3",
                    "evidence": (
                        "exact-fit + standard-construct grounding record from "
                        "current model inputs"
                    ),
                },
            }
        )
        if row["api_profile_required"]:
            profile_entries.append(
                {
                    "identity": identity,
                    "representation": {
                        "construct": row["construct"],
                        "mechanics": (
                            "Native SysML v2 variation/variant notation as "
                            "carried by the model: a `variation part def` "
                            "whose owned members are `variant part` usages; "
                            "membership is owned-member notation, not a "
                            "project-local variation-point taxonomy."
                        ),
                        "toolchain": {
                            "syside_modeler_cli": syside_pin,
                            "library_pins_note": (
                                "pinned library dependencies are recorded in "
                                ".sysand (sensmetry-syside-views, "
                                "mbse4u-sysmod, node4hera-requirements-management)"
                            ),
                        },
                        "notes": (
                            "Representation mechanics only: no semantics are "
                            "redefined; no API element UUID is claimed."
                        ),
                    },
                }
            )
    return rows, profile_entries


def build_artifact_pair(
    root: Path, *, source_revision: str | None = None
) -> dict[str, Any]:
    """Build from current inputs; accept but ignore legacy source_revision."""
    manifest = load_admission(root / ADMISSION_PATH)
    validate_admission(manifest)
    verify_witnesses(root, manifest)

    rows, profile_entries = derive_rows(root, manifest, source_revision)
    # Defense in depth: a derivation bug must not be able to silently emit a
    # projection row (or profile entry, or traversal claim) beyond the
    # reviewed flags.
    for row in rows:
        validate_row_outputs(row["identity"], row["outputs"])
    profile_identities = {entry["identity"] for entry in profile_entries}
    expected_profile_identities = {
        identity
        for identity, spec in ADMITTED_SPEC.items()
        if spec["api_profile_required"]
    }
    if profile_identities != expected_profile_identities:
        raise NativeGroundingError(
            "profile entries must exist for exactly the api_profile_required "
            f"rows: got {sorted(profile_identities)!r}"
        )
    admitted = sorted(row["identity"] for row in manifest["admitted"])

    projection_outputs = sorted(
        row["identity"] for row in rows if row["outputs"]["projection_row"]
    )
    api_profile_outputs = sorted(
        row["identity"] for row in rows if row["outputs"]["api_profile_entry"]
    )
    grounding_record_only = sorted(
        row["identity"]
        for row in rows
        if not row["outputs"]["projection_row"]
        and not row["outputs"]["api_profile_entry"]
    )
    traversal_outputs = sorted(
        row["identity"] for row in rows if row["outputs"]["traversal"]
    )

    projection = {
        "schema": PROJECTION_SCHEMA,
        "status": (
            "generated O2+ native/library grounding projection (accelerated "
            "safe-set 1, W3 safe subset)"
        ),
        "warning": (
            "Generated artifact. Rows are grounding/admission records; a row's "
            "outputs block states which outputs it actually carries - a "
            "grounding record for a row with projection_required false is NOT "
            "a semantic projection output. Generation is NOT authority "
            "activation: this projection does not switch runtime dispatch, "
            "does not retire authored YAML authority, promotes no support "
            "state, and implements/claims no traversal. The runtime reads this "
            "artifact to build the kernel contract. "
            "The identities served from the frozen records (projection v1, "
            "v1.1 and v1.2) are never re-emitted. Generated by "
            "scripts/generate_native_grounding_projection.py."
        ),
        "scope": {
            "layer": "o2plus",
            "admitted": admitted,
            "projection_outputs": projection_outputs,
            "api_profile_outputs": api_profile_outputs,
            "grounding_record_only": grounding_record_only,
            "traversal_outputs": traversal_outputs,
            "frozen_o2_note": (
                "The frozen O2 projection surface (v1 seven + v1.1 three + "
                "v1.2 three = thirteen identities) is machine-locked as "
                "never-emitted by this layer."
            ),
            "o3_note": (
                "The frozen O3 migrated set is machine-locked as "
                "never-emitted by this layer."
            ),
        },
        "rows": rows,
    }
    profile = {
        "schema": PROFILE_SCHEMA,
        "status": (
            "generated O2+ API Representation Profile (representation "
            "mechanics for the api_profile_required rows)"
        ),
        "warning": (
            "Generated artifact. Representation mechanics only: this profile "
            "cannot redefine domain, range, direction, semantic strength, "
            "exclusions, or claim boundaries. The runtime reads this artifact "
            "to build the kernel contract."
        ),
        "entries": profile_entries,
    }
    return {"projection": projection, "profile": profile}


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------


def run_check_errors(root: Path) -> list[str]:
    """Check that the native-grounding artifacts equal regeneration from inputs."""
    errors: list[str] = []
    projection_path = root / PROJECTION_PATH
    profile_path = root / PROFILE_PATH
    if not projection_path.is_file():
        errors.append(
            f"{PROJECTION_PATH}: native-grounding projection missing; run "
            "scripts/generate_native_grounding_projection.py and commit the output "
            "with the source change (docs/guides/generated-semantic-assets.md)"
        )
    if not profile_path.is_file():
        errors.append(
            f"{PROFILE_PATH}: native-grounding profile missing; run "
            "scripts/generate_native_grounding_projection.py and commit the output "
            "with the source change (docs/guides/generated-semantic-assets.md)"
        )
    if errors:
        return errors
    try:
        artifacts = build_artifact_pair(root)
    except NativeGroundingError as exc:
        return [f"native-grounding projection generation failed: {exc}"]
    if canonical_json(artifacts["projection"]).encode("utf-8") != (
        projection_path.read_bytes()
    ):
        errors.append(
            f"{PROJECTION_PATH}: committed projection differs from "
            "regeneration from current inputs; run "
            "scripts/generate_native_grounding_projection.py and commit the output "
            "with the source change (docs/guides/generated-semantic-assets.md)"
        )
    if canonical_json(artifacts["profile"]).encode("utf-8") != (
        profile_path.read_bytes()
    ):
        errors.append(
            f"{PROFILE_PATH}: committed profile differs from regeneration "
            "from current inputs; run scripts/generate_native_grounding_projection.py "
            "and commit the output with the source change "
            "(docs/guides/generated-semantic-assets.md)"
        )
    return errors
