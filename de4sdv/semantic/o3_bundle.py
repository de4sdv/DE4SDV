"""O3 candidate authority bundle — revision-bound verification and the
Projection/Profile-backed authority façade (Stage A; read-only).

This module implements the CANDIDATE O3 authority path for the reviewed
13-identity migrated set. It does not activate anything:

- production runtime selection is unchanged (the legacy authored
  ``KernelContract`` path stays the production default);
- the authored ontology YAML stays present (O4 owns retirement);
- no bundle produced by this machinery is accepted cutover authority until
  a privileged exact-revision ingestion and the same-revision comparison
  have run against the permanent post-merge revision.

Authority split (the invariant this module enforces):

    semantic meaning        <- Semantic Projection v1 → v1.1 → v1.2
    representation mapping  <- API Representation Profile v1 → v1.1 → v1.2

for exactly the migrated identities; every other identity delegates
explicitly to the legacy ``KernelContract``. No implicit fallback, no
name-based routing, never two providers for one identity.

Bundle states:

- a candidate bundle CORE is constructible offline (exact Git revision +
  migrated identity set + Projection/Profile chain digests + runtime build
  identity + the authored ontology's ingestion-compatibility identity);
- an EXECUTABLE CLOSED bundle additionally carries a structured API closure
  attestation (``de4sdv.o3-api-closure-attestation/v1``) bound to the core
  bundle ID. Only closed bundles may drive candidate execution outside
  synthetic fixtures; an unclosed bundle fails closed.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .impact import ImpactService
from .kernel_contract import (
    KernelContract,
    KernelFileMapping,
    KernelNativeMapping,
    RelationshipMapping,
)

O3_BUNDLE_SCHEMA = "de4sdv.o3-authority-bundle/v1"
O3_ATTESTATION_SCHEMA = "de4sdv.o3-api-closure-attestation/v1"

ONTOLOGY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"

#: The reviewed migrated identity set — exactly these, no fourteenth.
MIGRATED_IDENTITIES = (
    "MethodPhase",
    "MethodContractObligation",
    "EvaluationScopeMembership",
    "EvaluationSourceKind",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
    "VerificationCase",
    "hasSubject",
    "verifiedBy",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
    "hasRelevantArchitecture",
)
MIGRATED_CLASSES = (
    "MethodPhase",
    "MethodContractObligation",
    "EvaluationScopeMembership",
    "EvaluationSourceKind",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
    "VerificationCase",
)
MIGRATED_RELATIONSHIPS = (
    "hasSubject",
    "verifiedBy",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
    "hasRelevantArchitecture",
)

#: The Projection/Profile chain (paths + schemas), dependency order.
PROJECTION_CHAIN = (
    ("docs/method-conformance/o2/semantic-projection-v1.json", "de4sdv.semantic-projection.v1"),
    ("docs/method-conformance/o2/semantic-projection-v1.1.json", "de4sdv.semantic-projection.v1.1"),
    ("docs/method-conformance/o2/semantic-projection-v1.2.json", "de4sdv.semantic-projection.v1.2"),
)
PROFILE_CHAIN = (
    ("docs/method-conformance/o2/api-representation-profile-v1.json", "de4sdv.api-representation-profile.v1"),
    ("docs/method-conformance/o2/api-representation-profile-v1.1.json", "de4sdv.api-representation-profile.v1.1"),
    ("docs/method-conformance/o2/api-representation-profile-v1.2.json", "de4sdv.api-representation-profile.v1.2"),
)

#: Files whose bytes define the candidate-path runtime build identity.
#: Changing any of them changes the bundle ID (semantic-authority-critical).
RUNTIME_BUILD_FILES = (
    "de4sdv/semantic/runtime.py",
    "de4sdv/semantic/query.py",
    "de4sdv/semantic/traversal.py",
    "de4sdv/semantic/impact.py",
    "de4sdv/semantic/api_binding.py",
    "de4sdv/semantic/kernel_binding_index.py",
    "de4sdv/semantic/kernel_contract.py",
    "de4sdv/semantic/authority_ids.py",
    "de4sdv/semantic/o3_bundle.py",
    "de4sdv/sysml_api/revisions.py",
)

LEGACY_AUTHORITY_ID = "de4sdv.o0-o1-authored-v1"

_BUNDLE_ID_COMPONENTS = (
    "schema",
    "git_revision",
    "migrated_identities",
    "projection_chain",
    "profile_chain",
    "runtime_build",
)


class O3BundleError(ValueError):
    """Candidate bundle verification failed (fail closed)."""


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def candidate_provenance(
    binding: Any, authority_id: str, derived_source: str
) -> list[dict[str, str]]:
    """Candidate-path provenance: the authored ontology is never semantic
    authority — semantics come from the Projection, mechanics from the
    Profile, and the ontology appears only as the ingestion compatibility
    identity."""
    return [
        {
            "authority": "authoritative",
            "source": f"git://{binding.git_repository}/{binding.git_commit}",
        },
        {
            "authority": "authoritative",
            "source": f"sysml://{binding.sysml_project_id}/{binding.sysml_commit_id}",
        },
        {
            "authority": "semantic-authority",
            "source": f"projection://{authority_id}",
        },
        {
            "authority": "representation-authority",
            "source": f"profile://{authority_id}",
        },
        {
            "authority": "compatibility",
            "source": (
                f"git://{binding.git_repository}/{binding.git_commit}/"
                f"{binding.ontology.path}"
            ),
            "sha256": binding.ontology.sha256,
        },
        {"authority": "derived", "source": derived_source},
    ]


class O3ImpactService(ImpactService):
    """Candidate-path impact surface.

    ``ImpactService`` is an O1 recorded bound input and stays byte-untouched;
    this subclass preserves its behavior exactly and rewrites ONLY the
    provenance list, so the authored ontology is never falsely presented as
    semantic authority when the explicit candidate path is exercised.
    """

    semantic_authority_id: str = ""

    def impact(self, identifier: str, *, git_revision: str) -> dict[str, Any]:
        report = super().impact(identifier, git_revision=git_revision)
        report["provenance"] = candidate_provenance(
            self.binding, self.semantic_authority_id, "de4sdv.semantic.impact"
        )
        return report


def compute_runtime_build(root: Path) -> dict[str, Any]:
    """The candidate-path runtime build identity for the checkout at ``root``."""
    files = {}
    for rel in RUNTIME_BUILD_FILES:
        path = root / rel
        if not path.exists():
            raise O3BundleError(f"runtime build file missing: {rel}")
        files[rel] = sha256_file(path)
    build_id = "rb-" + hashlib.sha256(
        canonical_json(files).encode("utf-8")
    ).hexdigest()[:32]
    return {
        "id": build_id,
        "files": files,
        "policy": (
            "runtime build identity over the candidate-path implementation "
            "files; any byte change yields a new build id and therefore a new "
            "bundle id"
        ),
    }


def _chain_record(root: Path, chain: tuple[tuple[str, str], ...]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for rel, schema in chain:
        path = root / rel
        if not path.exists():
            raise O3BundleError(f"chain artifact missing: {rel}")
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("schema") != schema:
            raise O3BundleError(
                f"chain schema mismatch for {rel}: {document.get('schema')!r}"
            )
        records.append(
            {
                "path": rel,
                "schema": schema,
                "source_revision": str(
                    (document.get("binding") or {}).get("source_revision") or ""
                ),
                "sha256": sha256_file(path),
            }
        )
    return records


def build_candidate_bundle(
    root: Path,
    *,
    git_revision: str,
) -> dict[str, Any]:
    """Assemble the candidate bundle CORE for one exact Git revision.

    The bundle records identity/digests only; it invents no semantics. The
    authored ontology appears exclusively as the ingestion compatibility
    identity (never as semantic authority for the migrated set).
    """
    if len(git_revision) != 40 or any(
        character not in "0123456789abcdef" for character in git_revision
    ):
        raise O3BundleError(f"git_revision must be a full lowercase SHA: {git_revision!r}")
    bundle = {
        "schema": O3_BUNDLE_SCHEMA,
        "state": "core",
        "git_revision": git_revision,
        "migrated_identities": list(MIGRATED_IDENTITIES),
        "projection_chain": _chain_record(root, PROJECTION_CHAIN),
        "profile_chain": _chain_record(root, PROFILE_CHAIN),
        "runtime_build": compute_runtime_build(root),
        "ontology_compatibility_identity": {
            "path": ONTOLOGY_PATH,
            # Bare lowercase SHA-256, mirroring the revision binding's own
            # OntologyIdentity shape so equality is directly checkable. This
            # is the ingestion COMPATIBILITY identity, never semantic
            # authority for the migrated set.
            "sha256": hashlib.sha256(
                (root / ONTOLOGY_PATH).read_bytes()
            ).hexdigest(),
        },
        "api_closure": None,
        "evidence": {
            "comparison_manifest_schema": "de4sdv.o3-comparison-manifest/v1",
            "bundle_id_policy": (
                "the bundle ID digests the Git revision, the exact migrated "
                "identity set, the Projection and Profile chain identities, and "
                "the runtime build identity; the API closure attestation is "
                "bound TO this ID (it is not part of the core digest, which "
                "avoids circular identity) "
            ),
        },
    }
    bundle["bundle_id"] = compute_bundle_id(bundle)
    return bundle


def compute_bundle_id(bundle: dict[str, Any]) -> str:
    """Deterministic content/revision-bound bundle ID."""
    components = {key: bundle.get(key) for key in _BUNDLE_ID_COMPONENTS}
    digest = hashlib.sha256(canonical_json(components).encode("utf-8")).hexdigest()
    return "o3b-" + digest[:32]


def compute_import_closure_digest(
    *,
    git_revision: str,
    binding_sha256: str,
    sysml_project_id: str,
    sysml_commit_id: str,
    element_count: int,
    export_identity_sha256: str | None = None,
) -> str:
    """Digest of the import/export closure identity of one ingestion."""
    return _sha256_bytes(
        canonical_json(
            {
                "git_revision": git_revision,
                "binding_sha256": binding_sha256,
                "sysml_project_id": sysml_project_id,
                "sysml_commit_id": sysml_commit_id,
                "element_count": element_count,
                "export_identity_sha256": export_identity_sha256,
            }
        ).encode("utf-8")
    )


REQUIRED_VALIDATIONS = (
    "full_model_semantic_queries",
    "product_line_scope",
    "semantic_mcp",
)

_VALIDATION_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def build_closure_attestation(
    bundle: dict[str, Any],
    *,
    binding: Any,
    binding_sha256: str,
    element_count: int,
    export_identity_sha256: str | None,
    validations: dict[str, dict[str, Any]],
    verification_case_grounding: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Structured exact-revision API closure attestation for one bundle ID.

    Validation records are structured evidence bindings — each carries
    ``status`` (must be exactly ``passed`` for an executable closure),
    ``artifact`` (the validation evidence name), ``path`` and the ``sha256``
    of the exact produced validation output. Raw CLI text alone can never
    satisfy closure verification.
    """
    grounding_result = str(verification_case_grounding.get("result") or "")
    validation_records = {name: dict(record) for name, record in validations.items()}
    activation_eligible = grounding_result == "EQUIVALENT" and all(
        record.get("status") == "passed" for record in validation_records.values()
    )
    return {
        "schema": O3_ATTESTATION_SCHEMA,
        "bundle_id": bundle["bundle_id"],
        "git_revision": bundle["git_revision"],
        "binding_sha256": binding_sha256,
        "sysml_project_id": str(binding.sysml_project_id),
        "sysml_commit_id": str(binding.sysml_commit_id),
        "element_count": int(element_count),
        "export_identity_sha256": export_identity_sha256,
        "import_closure_digest": compute_import_closure_digest(
            git_revision=str(bundle["git_revision"]),
            binding_sha256=binding_sha256,
            sysml_project_id=str(binding.sysml_project_id),
            sysml_commit_id=str(binding.sysml_commit_id),
            element_count=int(element_count),
            export_identity_sha256=export_identity_sha256,
        ),
        "validation": validation_records,
        "activation_eligible": activation_eligible,
        "verification_case_grounding": dict(verification_case_grounding),
        "generated_at": generated_at,
    }


def close_bundle(bundle: dict[str, Any], attestation: dict[str, Any]) -> dict[str, Any]:
    """Return the executable closed bundle (core + bound attestation)."""
    if attestation.get("schema") != O3_ATTESTATION_SCHEMA:
        raise O3BundleError("closure attestation schema mismatch")
    if attestation.get("bundle_id") != bundle.get("bundle_id"):
        raise O3BundleError("closure attestation is bound to a different bundle id")
    closed = dict(bundle)
    closed["state"] = "closed"
    closed["api_closure"] = dict(attestation)
    return closed


# ---------------------------------------------------------------------------
# Bundle verification (fail closed)
# ---------------------------------------------------------------------------


def verify_bundle_document(
    bundle: dict[str, Any],
    *,
    root: Path,
    binding: Any = None,
    binding_sha256: str | None = None,
    require_closed: bool = False,
    validation_artifacts: dict[str, Path] | None = None,
) -> list[str]:
    """Verify a candidate bundle document against the checkout at ``root``.

    Returns a list of errors (empty = valid). ``require_closed`` makes the
    exact-revision API closure mandatory — the executable state. Any
    mismatch fails closed. ``validation_artifacts`` re-verifies the recorded
    validation evidence digests against the actual produced outputs.
    """
    errors: list[str] = []
    if bundle.get("schema") != O3_BUNDLE_SCHEMA:
        return [f"bundle schema mismatch: {bundle.get('schema')!r}"]
    state = bundle.get("state")
    if state not in ("core", "closed"):
        errors.append(f"bundle state must be core|closed, got {state!r}")
    if list(bundle.get("migrated_identities") or []) != list(MIGRATED_IDENTITIES):
        errors.append(
            "migrated identity set differs from the reviewed 13 "
            "(missing or extra identities)"
        )
    if bundle.get("bundle_id") != compute_bundle_id(bundle):
        errors.append("bundle id does not match the recomputed content digest")

    # Chain records: exact paths/schemas, recomputed digests, recorded
    # source revisions reproduced from the artifacts themselves.
    for label, chain in (("projection", PROJECTION_CHAIN), ("profile", PROFILE_CHAIN)):
        recorded = bundle.get(f"{label}_chain")
        expected: list[dict[str, Any]]
        try:
            expected = _chain_record(root, chain)
        except (O3BundleError, ValueError) as exc:
            errors.append(f"{label} chain unavailable: {exc}")
            continue
        if recorded != expected:
            errors.append(
                f"{label} chain records differ from the checkout "
                "(path, schema, source revision, or digest)"
            )

    # Runtime build identity.
    try:
        expected_build = compute_runtime_build(root)
    except O3BundleError as exc:
        errors.append(f"runtime build unavailable: {exc}")
    else:
        if bundle.get("runtime_build") != expected_build:
            errors.append("runtime build identity does not match the checkout")

    # Ontology ingestion-compatibility identity (never semantic authority).
    ontology_record = bundle.get("ontology_compatibility_identity") or {}
    if ontology_record.get("path") != ONTOLOGY_PATH:
        errors.append("ontology compatibility identity path mismatch")
    elif ontology_record.get("sha256") != hashlib.sha256(
        (root / ONTOLOGY_PATH).read_bytes()
    ).hexdigest():
        errors.append("ontology compatibility identity digest mismatch")

    # API closure.
    closure = bundle.get("api_closure")
    if require_closed and state != "closed":
        errors.append(
            "candidate bundle is not closed: no exact-revision API closure "
            "attestation; candidate execution outside synthetic fixtures is "
            "refused"
        )
    if state == "closed":
        if not isinstance(closure, dict):
            errors.append("closed bundle carries no API closure attestation")
        else:
            errors.extend(
                _attestation_errors(
                    closure, validation_artifacts=validation_artifacts
                )
            )
            if binding is not None:
                errors.extend(
                    _binding_closure_errors(
                        bundle, closure, binding, binding_sha256=binding_sha256
                    )
                )
    elif binding is not None:
        errors.append(
            "binding verification requires a closed bundle carrying the "
            "exact-revision API closure"
        )
    return errors


def _attestation_errors(
    closure: dict[str, Any],
    *,
    validation_artifacts: dict[str, Path] | None = None,
) -> list[str]:
    errors: list[str] = []
    if closure.get("schema") != O3_ATTESTATION_SCHEMA:
        errors.append(f"closure attestation schema mismatch: {closure.get('schema')!r}")
    for field in (
        "bundle_id",
        "git_revision",
        "binding_sha256",
        "sysml_project_id",
        "sysml_commit_id",
        "import_closure_digest",
    ):
        if not closure.get(field):
            errors.append(f"closure attestation missing {field}")

    # The closure digest must reproduce from its own structured fields —
    # a recorded string is never accepted on its own.
    element_count = closure.get("element_count")
    if not isinstance(element_count, int) or isinstance(element_count, bool):
        errors.append("closure attestation element_count is not an integer")
    elif closure.get("import_closure_digest"):
        expected_digest = compute_import_closure_digest(
            git_revision=str(closure.get("git_revision") or ""),
            binding_sha256=str(closure.get("binding_sha256") or ""),
            sysml_project_id=str(closure.get("sysml_project_id") or ""),
            sysml_commit_id=str(closure.get("sysml_commit_id") or ""),
            element_count=element_count,
            export_identity_sha256=closure.get("export_identity_sha256"),
        )
        if closure.get("import_closure_digest") != expected_digest:
            errors.append(
                "closure import_closure_digest does not reproduce from its "
                "structured fields (tampered or inconsistent attestation)"
            )

    # Validation evidence: structured records with exactly-successful status
    # bound to the exact produced output digests.
    validations = closure.get("validation")
    if not isinstance(validations, dict):
        errors.append("closure attestation lacks structured validation results")
        validations = {}
    for name in REQUIRED_VALIDATIONS:
        record = validations.get(name)
        if not isinstance(record, dict):
            errors.append(f"validation {name} has no structured evidence record")
            continue
        status = record.get("status")
        if status != "passed":
            errors.append(
                f"validation {name} status is not 'passed' (got {status!r}); "
                "unresolved evidence can never close an executable bundle"
            )
        artifact = record.get("artifact")
        if not isinstance(artifact, str) or not artifact:
            errors.append(f"validation {name} record lacks an artifact name")
        digest = record.get("sha256")
        if not isinstance(digest, str) or not _VALIDATION_DIGEST_RE.match(digest):
            errors.append(
                f"validation {name} record lacks a well-formed sha256 digest "
                "of the exact validation output"
            )
        if not isinstance(record.get("path"), str) or not record.get("path"):
            errors.append(f"validation {name} record lacks the evidence path")
        if validation_artifacts is not None and name in validation_artifacts:
            path = Path(validation_artifacts[name])
            if not path.is_file():
                errors.append(
                    f"validation {name} evidence artifact is missing: {path}"
                )
            elif isinstance(digest, str) and sha256_file(path) != digest:
                errors.append(
                    f"validation {name} evidence digest does not match the "
                    "attested sha256 of the produced output"
                )
    for name, record in validations.items():
        if name in REQUIRED_VALIDATIONS:
            continue
        if not isinstance(record, dict) or record.get("status") != "passed":
            errors.append(
                f"validation {name} record must carry an exactly-passed status"
            )

    grounding = closure.get("verification_case_grounding")
    if not isinstance(grounding, dict) or grounding.get("result") not in (
        "EQUIVALENT",
        "NOT_YET_COMPARABLE",
        "BLOCKING_MISMATCH",
    ):
        errors.append("closure attestation lacks a structured grounding result")

    # Activation eligibility is recomputed, never accepted on trust.
    recorded_eligible = closure.get("activation_eligible")
    if not isinstance(recorded_eligible, bool):
        errors.append("closure attestation lacks an explicit activation_eligible")
    else:
        grounding_result = (
            str(grounding.get("result")) if isinstance(grounding, dict) else ""
        )
        expected_eligible = grounding_result == "EQUIVALENT" and all(
            isinstance(record, dict) and record.get("status") == "passed"
            for record in validations.values()
        )
        if recorded_eligible != expected_eligible:
            errors.append(
                "closure activation_eligible does not reproduce from the "
                "grounding result and validation statuses"
            )
        if grounding_result == "BLOCKING_MISMATCH" and recorded_eligible:
            errors.append(
                "a BLOCKING_MISMATCH grounding result can never be activation "
                "eligible"
            )
    return errors


def _binding_closure_errors(
    bundle: dict[str, Any],
    closure: dict[str, Any],
    binding: Any,
    *,
    binding_sha256: str | None,
) -> list[str]:
    errors: list[str] = []
    if binding.git_commit != bundle.get("git_revision"):
        errors.append(
            "binding git_commit does not equal the bundle git revision"
        )
    if binding.semantic_validation != "passed":
        errors.append("binding semantic_validation is not passed")
    if str(binding.sysml_project_id) != str(closure.get("sysml_project_id")):
        errors.append("binding sysml_project_id differs from the closure attestation")
    if str(binding.sysml_commit_id) != str(closure.get("sysml_commit_id")):
        errors.append("binding sysml_commit_id differs from the closure attestation")
    if binding.ontology.to_dict() != bundle.get("ontology_compatibility_identity"):
        errors.append(
            "binding ontology identity differs from the bundle ingestion "
            "compatibility identity"
        )
    if not binding_sha256:
        errors.append("binding digest was not supplied for verification")
    elif binding_sha256 != closure.get("binding_sha256"):
        errors.append("binding digest differs from the closure attestation")
    if closure.get("bundle_id") != bundle.get("bundle_id"):
        errors.append("closure attestation is bound to a different bundle id")
    if closure.get("git_revision") != bundle.get("git_revision"):
        errors.append("closure attestation git revision differs from the bundle")
    return errors


# ---------------------------------------------------------------------------
# Projection/Profile-backed authority façade
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class O3Authority:
    """The verified candidate authority for one closed bundle."""

    facade: "O3AuthorityFacade"
    bundle_id: str
    authority_id: str
    activation_blocked: bool
    grounding_result: str


class O3AuthorityFacade:
    """Authority façade with explicit, non-overlapping providers.

    Migrated identities resolve EXCLUSIVELY through the Projection (semantic
    meaning) and Profile (representation mechanics); every other identity
    delegates explicitly to the legacy ``KernelContract``. There is no
    fallback path between the two providers and never two providers for one
    identity.
    """

    def __init__(
        self,
        *,
        legacy: KernelContract,
        bundle: dict[str, Any],
        projection_rows: dict[str, dict[str, Any]],
        profile_entries: dict[str, dict[str, Any]],
    ) -> None:
        self._legacy = legacy
        self._bundle = bundle
        self._projection_rows = projection_rows
        self._profile_entries = profile_entries
        self.bundle_id = str(bundle["bundle_id"])
        self.authority_id = f"o3-candidate:{self.bundle_id}"
        from de4sdv.sysml_api.revisions import OntologyIdentity

        self.identity = OntologyIdentity.from_dict(
            bundle["ontology_compatibility_identity"]
        )
        self._relationship_mappings: dict[str, RelationshipMapping] = {}
        self._class_mappings: dict[str, KernelFileMapping | KernelNativeMapping] = {}
        self._build_migrated()
        self.relationships = self._merged_relationships()
        self.classes = self._merged_classes()

    # -- construction ----------------------------------------------------
    def _build_migrated(self) -> None:
        for name in MIGRATED_RELATIONSHIPS:
            row = self._projection_rows.get(name)
            entry = self._profile_entries.get(name)
            if row is None or entry is None:
                raise O3BundleError(
                    f"migrated identity {name!r} lacks a Projection row or "
                    f"Profile entry; the façade refuses partial providers"
                )
            relation = row.get("relation") or {}
            mechanics = dict(entry.get("serializer_mechanics") or {})
            strategy = str(mechanics.pop("strategy", "") or "")
            if not strategy:
                raise O3BundleError(
                    f"migrated identity {name!r} lacks profile serializer "
                    f"mechanics (strategy)"
                )
            mechanics.pop("semantic_strength", None)
            domain = str((relation.get("domain") or {}).get("ontology_class") or "")
            range_ = str((relation.get("range") or {}).get("ontology_class") or "")
            strength = str(relation.get("semantic_strength") or "")
            if not domain or not range_ or not strength:
                raise O3BundleError(
                    f"migrated identity {name!r} lacks a complete Projection "
                    f"semantic declaration"
                )
            self._relationship_mappings[name] = RelationshipMapping(
                name=name,
                strategy=strategy,
                semantic_strength=strength,
                configuration=mechanics,
                domain=domain,
                range=range_,
            )
        for name in MIGRATED_CLASSES:
            row = self._projection_rows.get(name)
            if row is None:
                raise O3BundleError(
                    f"migrated class {name!r} lacks a Projection row"
                )
            if name == "VerificationCase":
                construct = row.get("construct") or {}
                native_text = str(
                    (construct.get("native_grounding") or {}).get("identity") or ""
                )
                if str(construct.get("kind") or "") != "native" or not native_text:
                    raise O3BundleError(
                        "VerificationCase Projection row lacks native grounding"
                    )
                self._class_mappings[name] = KernelNativeMapping(native_text)
            else:
                grounding = row.get("grounding") or {}
                contract = grounding.get("kernel_binding_contract") or {}
                source_file = str(contract.get("source_file") or "")
                declaration = str(contract.get("declaration") or "")
                if not source_file or not declaration:
                    raise O3BundleError(
                        f"migrated class {name!r} lacks a file/declaration "
                        f"grounding contract"
                    )
                self._class_mappings[name] = KernelFileMapping(
                    source_file, declaration
                )

    def _merged_relationships(self) -> dict[str, Any]:
        merged = dict(self._legacy.relationships)
        for name, mapping in self._relationship_mappings.items():
            merged[name] = {
                "sysml_mapping": {"strategy": mapping.strategy, **mapping.configuration},
                "domain": mapping.domain,
                "range": mapping.range,
                "semantic_strength": mapping.semantic_strength,
            }
        return merged

    def _merged_classes(self) -> dict[str, Any]:
        merged = dict(self._legacy.classes)
        for name, mapping in self._class_mappings.items():
            if isinstance(mapping, KernelFileMapping):
                merged[name] = {
                    "kernel": {
                        "file": mapping.file,
                        "declaration": mapping.declaration,
                    }
                }
            else:
                merged[name] = {"kernel": {"native": mapping.native}}
        return merged

    # -- KernelContract-compatible surface -------------------------------
    def mapping(self, ontology_class: str) -> Any:
        if ontology_class in MIGRATED_CLASSES:
            return self._class_mappings[ontology_class]
        return self._legacy.mapping(ontology_class)

    def class_mapping(self, ontology_class: str) -> KernelFileMapping:
        if ontology_class in MIGRATED_CLASSES:
            mapping = self._class_mappings[ontology_class]
            if not isinstance(mapping, KernelFileMapping):
                raise ValueError(
                    f"ontology class {ontology_class} is not file-mapped"
                )
            return mapping
        return self._legacy.class_mapping(ontology_class)

    def relationship_mapping(self, relationship: str) -> RelationshipMapping:
        if relationship in MIGRATED_RELATIONSHIPS:
            return self._relationship_mappings[relationship]
        return self._legacy.relationship_mapping(relationship)


def _load_chain_rows(
    root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: dict[str, dict[str, Any]] = {}
    entries: dict[str, dict[str, Any]] = {}
    for rel, _schema in PROJECTION_CHAIN:
        document = json.loads((root / rel).read_text(encoding="utf-8"))
        for section in ("concepts", "predicates"):
            for row in document.get(section, []):
                identity = row.get("identity") or row.get("for_concept")
                if identity:
                    rows[identity] = row
    for rel, _schema in PROFILE_CHAIN:
        document = json.loads((root / rel).read_text(encoding="utf-8"))
        for entry in document.get("profiles", []):
            identity = entry.get("for_identity") or entry.get("for_concept")
            if identity:
                entries[identity] = entry
    return rows, entries


def load_o3_authority(
    source: "dict[str, Any] | str | Path",
    *,
    root: Path,
    contract: KernelContract,
    binding: Any,
    binding_sha256: str,
    expected_git_revision: str | None = None,
    validation_artifacts: dict[str, Path] | None = None,
) -> O3Authority:
    """Verify a CLOSED candidate bundle and build the authority façade.

    Unclosed bundles and any verification error fail closed. The resulting
    authority is the only provider for the migrated 13; all other identities
    delegate to ``contract``. ``validation_artifacts`` re-verifies the
    closure's validation evidence against the actual produced outputs.
    """
    if isinstance(source, (str, Path)):
        bundle = json.loads(Path(source).read_text(encoding="utf-8"))
    else:
        bundle = dict(source)
    errors = verify_bundle_document(
        bundle,
        root=root,
        binding=binding,
        binding_sha256=binding_sha256,
        require_closed=True,
        validation_artifacts=validation_artifacts,
    )
    if expected_git_revision is not None and binding.git_commit != expected_git_revision:
        errors.append(
            "binding git_commit does not equal the expected runtime revision"
        )
    if errors:
        raise O3BundleError("; ".join(errors))
    closure = bundle["api_closure"]
    grounding = closure.get("verification_case_grounding") or {}
    grounding_result = str(grounding.get("result") or "")
    if grounding_result == "BLOCKING_MISMATCH":
        raise O3BundleError(
            "closure attests a BLOCKING_MISMATCH in the VerificationCase "
            "grounding proof; candidate execution is refused"
        )
    projection_rows, profile_entries = _load_chain_rows(root)
    facade = O3AuthorityFacade(
        legacy=contract,
        bundle=bundle,
        projection_rows=projection_rows,
        profile_entries=profile_entries,
    )
    return O3Authority(
        facade=facade,
        bundle_id=str(bundle["bundle_id"]),
        authority_id=facade.authority_id,
        activation_blocked=grounding_result != "EQUIVALENT",
        grounding_result=grounding_result,
    )

