"""O2+ native/library grounding & projection layer (accelerated safe-set 1).

Governed by: ontology review Deliverable 8 wave 3 (native/library projection
rows over already-native constructs) + the O4 execution register rows for the
admitted identities. The layer records exact-fit standard-construct grounding
for already-native/library constructs and generates vocabulary-only projection
rows and API-representation profile entries over them.

Canonical artifacts:

- ``docs/method-conformance/o2plus/semantic-projection-o2plus.json``
  (the O2+ projection: one row per admitted identity, grounded in the
  reviewed construct witness, support stays vocabulary-only);
- ``docs/method-conformance/o2plus/api-representation-profile-o2plus.json``
  (representation mechanics entries for the ``api_profile_required`` rows).

Determinism and revision binding: identical inputs produce byte-identical
output. The artifacts bind a ``source_revision`` — a Git commit that contains
every bound input byte-for-byte — plus per-input content digests. ``--check``
validates the binding against the repository (commit existence, ancestry,
per-input content equality, recorded digests) and then regenerates with the
recorded source revision and compares bytes.

Boundaries: offline and read-only; no network; no runtime semantic change;
generation is not authority activation; the runtime never reads these
artifacts; support is never promoted beyond vocabulary-only; no traversal is
implemented or claimed; the frozen O2 (v1/v1.1/v1.2) and O3 surfaces are never
re-emitted (machine-locked).

Usage:

    python scripts/generate_semantic_projection_o2p.py              # write
    python scripts/generate_semantic_projection_o2p.py --check      # verify
    python scripts/generate_semantic_projection_o2p.py \\
        --source-revision <40-hex commit id>
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

from de4sdv.semantic.authority_inventory import (
    file_digest,
    validate_source_binding,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ADMISSION_O2P_PATH = "docs/method-conformance/o2plus/o2p-admission.yaml"
PROJECTION_O2P_PATH = "docs/method-conformance/o2plus/semantic-projection-o2plus.json"
PROFILE_O2P_PATH = "docs/method-conformance/o2plus/api-representation-profile-o2plus.json"
DESIGN_O2P_PATH = "docs/method-conformance/o2plus/o2plus-design.md"
MODULE_O2P_PATH = "de4sdv/semantic/projection_o2p.py"
GENERATOR_O2P_PATH = "scripts/generate_semantic_projection_o2p.py"
SYSIDE_WORKFLOW_PATH = ".github/workflows/privileged-syside-validation.yml"

PROJECTION_O2P_SCHEMA = "de4sdv.semantic-projection.o2plus/v1"
PROFILE_O2P_SCHEMA = "de4sdv.api-representation-profile.o2plus/v1"

#: The frozen O2 projection surface (v1 seven + v1.1 three + v1.2 three).
FROZEN_O2_IDENTITIES: tuple[str, ...] = (
    # O2.1 (v1)
    "MethodContractObligation",
    "MethodPhase",
    "EvaluationScopeMembership",
    "EvaluationSourceKind",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
    # O2.2 (v1.1)
    "VerificationCase",
    "hasSubject",
    "verifiedBy",
    # O2.3 (v1.2)
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


class ProjectionO2PError(RuntimeError):
    """Raised when O2+ generation cannot proceed safely."""


def validate_row_outputs_o2p(identity: str, outputs: dict[str, Any]) -> None:
    """Fail closed when emitted outputs disagree with the reviewed flags.

    A grounding/admission record is NOT a projection output: rows whose
    reviewed ``projection_required`` is false must never claim a projection
    row, rows whose ``api_profile_required`` is false must never claim a
    profile entry, and traversal stays false everywhere unless the review
    explicitly requires it.
    """
    spec = ADMITTED_SPEC.get(identity)
    if spec is None:
        raise ProjectionO2PError(f"{identity}: not an admitted identity")
    expected = {
        "projection_row": bool(spec["projection_required"]),
        "api_profile_entry": bool(spec["api_profile_required"]),
        "traversal": bool(spec["traversal_required"]),
    }
    if {key: bool(value) for key, value in outputs.items()} != expected:
        raise ProjectionO2PError(
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
    result = _git(root, "rev-parse", "HEAD")
    if result.returncode != 0:
        raise ProjectionO2PError(f"cannot resolve HEAD: {result.stderr.strip()}")
    return result.stdout.strip()


def canonical_json(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=False) + "\n"


# ---------------------------------------------------------------------------
# Admission manifest
# ---------------------------------------------------------------------------


def load_admission_o2p(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ProjectionO2PError(f"admission manifest missing: {path}")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ProjectionO2PError("admission manifest must be a mapping")
    return document


def validate_admission_o2p(manifest: dict[str, Any]) -> None:
    """Machine-lock the admission boundary (fail closed)."""
    if manifest.get("schema") != "de4sdv.o2plus-admission/v1":
        raise ProjectionO2PError("admission manifest schema mismatch")
    admitted = manifest.get("admitted")
    if not isinstance(admitted, list) or not admitted:
        raise ProjectionO2PError("admission manifest has no admitted rows")
    identities = [row.get("identity") for row in admitted]
    if len(set(identities)) != len(identities):
        raise ProjectionO2PError("duplicate admitted identity")
    if set(identities) != set(ADMITTED_SPEC):
        raise ProjectionO2PError(
            "admitted set must be EXACTLY the reviewed safe subset: "
            f"got {sorted(identities)!r}"
        )
    for row in admitted:
        identity = row["identity"]
        spec = ADMITTED_SPEC[identity]
        for key in ("projection_required", "api_profile_required", "traversal_required"):
            if bool(row.get(key)) is not bool(spec[key]):
                raise ProjectionO2PError(
                    f"{identity}: {key} must equal the reviewed value {spec[key]!r}"
                )
        if row.get("category") != spec["category"]:
            raise ProjectionO2PError(
                f"{identity}: category must equal the reviewed value {spec['category']!r}"
            )
        if row.get("support") != "vocabulary-only":
            raise ProjectionO2PError(
                f"{identity}: support must stay vocabulary-only"
            )
        if row.get("traversal_required") is not False:
            raise ProjectionO2PError(f"{identity}: traversal must not be required")
        witness = row.get("witness")
        if not isinstance(witness, dict) or not witness.get("file") or not witness.get("contains"):
            raise ProjectionO2PError(f"{identity}: witness file/contains required")
        for field in ("construct", "exact_fit", "standard_construct", "claim_boundary"):
            if not row.get(field):
                raise ProjectionO2PError(f"{identity}: {field} required")

    excluded = manifest.get("excluded")
    if not isinstance(excluded, list) or not excluded:
        raise ProjectionO2PError("admission manifest has no excluded rows")
    excluded_ids = [row.get("identity") for row in excluded]
    if len(set(excluded_ids)) != len(excluded_ids):
        raise ProjectionO2PError("duplicate excluded identity")
    overlap = set(excluded_ids) & set(identities)
    if overlap:
        raise ProjectionO2PError(f"admitted/excluded overlap: {sorted(overlap)!r}")
    for row in excluded:
        if not row.get("reason"):
            raise ProjectionO2PError(
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
            raise ProjectionO2PError(
                f"hard-gated identity {gated} must remain in the excluded set"
            )
    # Frozen surfaces are never admitted here.
    for frozen in FROZEN_O2_IDENTITIES:
        if frozen in set(identities):
            raise ProjectionO2PError(
                f"frozen O2 identity {frozen} must never be admitted"
            )


def _frozen_o3_identities() -> frozenset[str]:
    from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

    return frozenset(MIGRATED_IDENTITIES)


def verify_witnesses(root: Path, manifest: dict[str, Any]) -> None:
    """Every admitted row's construct witness must exist in the model."""
    for row in manifest["admitted"]:
        identity = row["identity"]
        witness = row["witness"]
        path = root / witness["file"]
        if not path.is_file():
            raise ProjectionO2PError(
                f"{identity}: witness file missing: {witness['file']}"
            )
        if witness["contains"] not in path.read_text(encoding="utf-8"):
            raise ProjectionO2PError(
                f"{identity}: witness construct not found in {witness['file']}: "
                f"{witness['contains']!r}"
            )
        frozen = _frozen_o3_identities()
        if identity in frozen:
            raise ProjectionO2PError(
                f"{identity}: frozen O3 identity must never be admitted"
            )


def read_syside_pin(root: Path) -> str:
    workflow = root / SYSIDE_WORKFLOW_PATH
    if not workflow.is_file():
        raise ProjectionO2PError(f"syside workflow missing: {SYSIDE_WORKFLOW_PATH}")
    match = re.search(
        r'SYSIDE_VERSION="([^"]+)"', workflow.read_text(encoding="utf-8")
    )
    if not match:
        raise ProjectionO2PError("syside version pin not found in the workflow")
    return match.group(1)


# ---------------------------------------------------------------------------
# Bound inputs and binding block
# ---------------------------------------------------------------------------


def collect_bound_inputs_o2p(root: Path, manifest: dict[str, Any]) -> dict[str, str]:
    """Every source consumed to produce the O2+ artifacts."""
    paths: set[str] = {
        ADMISSION_O2P_PATH,
        MODULE_O2P_PATH,
        GENERATOR_O2P_PATH,
        SYSIDE_WORKFLOW_PATH,
    }
    for row in manifest["admitted"]:
        paths.add(row["witness"]["file"])
    inputs: dict[str, str] = {}
    for path in sorted(paths):
        file = root / path
        if not file.is_file():
            raise ProjectionO2PError(f"bound input missing: {path}")
        inputs[path] = file_digest(root, path)
    return inputs


def _binding_block_o2p(
    source_revision: str,
    bound_inputs: dict[str, str],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    program_inputs = sorted(
        {ADMISSION_O2P_PATH, MODULE_O2P_PATH, GENERATOR_O2P_PATH}
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
                "program inputs byte-for-byte."
            ),
        },
        "semantic_model_revision": {
            "model_inputs": sorted(
                {row["witness"]["file"] for row in manifest["admitted"]}
            ),
            "note": (
                "Semantic-model revision: ONLY the governed model files "
                "carrying the admitted constructs' witnesses, contained "
                "byte-for-byte in source_revision. Tooling/toolchain "
                "provenance is classified separately below."
            ),
        },
        "tooling_revision": {
            "tooling_inputs": [SYSIDE_WORKFLOW_PATH],
            "note": (
                "Tooling/toolchain provenance: the pinned Syside "
                "workflow/version reference is revision-bound for "
                "reproducibility but is NOT a semantic-model input and "
                "supplies no semantics."
            ),
        },
        "api_binding": {
            "status": "unclaimed",
            "note": (
                "No validated SysML API project/commit closure is produced and "
                "no current API element UUID is claimed; the pinned toolchain "
                "reference is recorded in the profile entries."
            ),
        },
        "admission_manifest": {
            "path": ADMISSION_O2P_PATH,
            "digest": bound_inputs[ADMISSION_O2P_PATH],
        },
        "bound_inputs": bound_inputs,
    }


# ---------------------------------------------------------------------------
# Row derivation and pair build
# ---------------------------------------------------------------------------


def derive_rows_o2p(
    root: Path, manifest: dict[str, Any], source_revision: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
        validate_row_outputs_o2p(identity, outputs)
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
                        "exact-fit + standard-construct grounding record at a "
                        "bound revision"
                    ),
                    "bound_revision": source_revision,
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


def build_pair_o2p(root: Path, *, source_revision: str) -> dict[str, Any]:
    manifest = load_admission_o2p(root / ADMISSION_O2P_PATH)
    validate_admission_o2p(manifest)
    verify_witnesses(root, manifest)
    bound_inputs = collect_bound_inputs_o2p(root, manifest)

    from de4sdv.semantic.authority_inventory import verify_source_revision_contains_inputs

    verify_source_revision_contains_inputs(root, source_revision, bound_inputs)

    rows, profile_entries = derive_rows_o2p(root, manifest, source_revision)
    # Defense in depth: a derivation bug must not be able to silently emit a
    # projection row (or profile entry, or traversal claim) beyond the
    # reviewed flags.
    for row in rows:
        validate_row_outputs_o2p(row["identity"], row["outputs"])
    profile_identities = {entry["identity"] for entry in profile_entries}
    expected_profile_identities = {
        identity
        for identity, spec in ADMITTED_SPEC.items()
        if spec["api_profile_required"]
    }
    if profile_identities != expected_profile_identities:
        raise ProjectionO2PError(
            "profile entries must exist for exactly the api_profile_required "
            f"rows: got {sorted(profile_identities)!r}"
        )
    admitted = sorted(row["identity"] for row in manifest["admitted"])
    binding = _binding_block_o2p(source_revision, bound_inputs, manifest)
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
        "schema": PROJECTION_O2P_SCHEMA,
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
            "state, and implements/claims no traversal. The runtime does not "
            "read this artifact. The frozen O2 (v1/v1.1/v1.2) and O3 surfaces "
            "are never re-emitted. Generated by "
            "scripts/generate_semantic_projection_o2p.py."
        ),
        "binding": binding,
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
        "schema": PROFILE_O2P_SCHEMA,
        "status": (
            "generated O2+ API Representation Profile (representation "
            "mechanics for the api_profile_required rows)"
        ),
        "warning": (
            "Generated artifact. Representation mechanics only: this profile "
            "cannot redefine domain, range, direction, semantic strength, "
            "exclusions, or claim boundaries. The runtime does not read this "
            "artifact."
        ),
        "binding": binding,
        "entries": profile_entries,
    }
    return {"projection": projection, "profile": profile}


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------


def run_check_errors_o2p(root: Path) -> list[str]:
    """Check that the O2+ artifacts equal regeneration from inputs."""
    errors: list[str] = []
    projection_path = root / PROJECTION_O2P_PATH
    profile_path = root / PROFILE_O2P_PATH
    if not projection_path.is_file():
        errors.append(f"o2plus semantic projection missing: {PROJECTION_O2P_PATH}")
    if not profile_path.is_file():
        errors.append(
            f"o2plus api representation profile missing: {PROFILE_O2P_PATH}"
        )
    if errors:
        return errors
    try:
        committed = json.loads(projection_path.read_text(encoding="utf-8"))
        committed_profile = json.loads(profile_path.read_text(encoding="utf-8"))
        binding = committed["binding"]
    except (KeyError, ValueError) as exc:
        return [f"{PROJECTION_O2P_PATH}: cannot read binding for validation: {exc}"]
    binding_errors = validate_source_binding(root, binding)
    if binding_errors:
        return [
            f"{PROJECTION_O2P_PATH}: source-revision binding invalid: {error}"
            for error in binding_errors
        ]
    source_revision = binding["source_revision"]
    try:
        artifacts = build_pair_o2p(root, source_revision=source_revision)
    except ProjectionO2PError as exc:
        return [f"o2plus projection generation failed: {exc}"]
    if canonical_json(artifacts["projection"]) != projection_path.read_text(
        encoding="utf-8"
    ):
        errors.append(
            f"{PROJECTION_O2P_PATH}: committed projection differs from "
            "regeneration from current inputs (regenerate and commit)"
        )
    if canonical_json(artifacts["profile"]) != profile_path.read_text(
        encoding="utf-8"
    ):
        errors.append(
            f"{PROFILE_O2P_PATH}: committed profile differs from regeneration "
            "from current inputs (regenerate and commit)"
        )
    return errors
