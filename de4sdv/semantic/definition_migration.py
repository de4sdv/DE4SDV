"""O4 definition-migration path — verified, explicitly selected, fail-closed.

Moves the admitted 22-identity definition consumption out of an isolated
candidate seam into ONE migration path with four governed properties:

* **Verification.** The candidate pair is loaded and verified through
  :mod:`de4sdv.semantic.definition_candidate` (structural pair contract, the
  recorded source-revision binding, regeneration equality, and frozen-O3
  disjointness). Nothing here re-implements or bypasses that verification.
* **Construction.** The verified pair builds the explicit
  :class:`~de4sdv.semantic.definition_candidate_provider.DefinitionCandidateProvider`:
  admitted identities resolve EXCLUSIVELY from the candidate artifacts, and
  every other identity delegates explicitly to the authored
  ``KernelContract`` — the remaining legacy dependency stays visible and is
  never hidden.
* **Selection.** The path is selected EXPLICITLY (``DE4SDV_DEFINITION_MIGRATION``
  or the explicit ``selection`` argument). Unset means OFF: the production
  default (legacy authority) is unchanged and the accepted O3 bundle route
  (``authority_selection``: ``legacy`` | ``o3``) is untouched. This module
  never adds a production selector and never falls back silently.
* **Activation.** Activating the migration path requires a FRESH
  exact-revision API closure: the validated revision binding for the exact
  revision must carry an ingestion-validated kernel binding for every
  admitted identity whose ``source_file``/``declaration`` agree with the
  candidate pair. The admitted rows are published ``api_identity:
  unclaimed`` / ``traversal: false`` (vocabulary-only), so this prerequisite
  is genuinely unmet until a privileged ingestion validates the admitted
  declarations at the bound revision. Until then activation FAILS CLOSED
  with the exact prerequisite and no production surface changes.

Consumption: an assembled migration runtime passes the verified provider
through the existing runtime seam into the real consumers
(:class:`~de4sdv.semantic.api_binding.OntologyApiBinder`,
:class:`~de4sdv.semantic.kernel_binding_index.KernelBindingIndex`,
:class:`~de4sdv.semantic.traversal.SemanticTraversal`,
:class:`~de4sdv.semantic.query.SemanticQueryService` and the impact-service
provenance) — the same consumer classes the production paths use.

Probe: :func:`probe_definition_migration` is the read-only, offline
comparison/probe over the real candidate pair and the authored contract —
and, when a retained export / validated binding is supplied, over those
bytes. It reports per-identity candidate-vs-legacy mappings, the closure
prerequisite state, and the remaining legacy dependency. Export matches are
representation evidence only: the probe claims no runtime identity.

This is NOT a migration-complete claim: a partial migration retires nothing.
The authored authority stays active, every runtime/validation consumer
ledger row stays ``pending``, and no production default changes here.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from de4sdv.sysml_api.revisions import OntologyIdentity

from .definition_candidate import (
    DefinitionCandidate,
    load_definition_candidate,
)
from .definition_candidate_provider import DefinitionCandidateProvider
from .kernel_contract import KernelContract, declaration_identity
from .o3_bundle import MIGRATED_IDENTITIES

ROOT = Path(__file__).resolve().parents[2]

#: Explicit, non-production selection surface. Unset means OFF.
MIGRATION_ENV = "DE4SDV_DEFINITION_MIGRATION"
MIGRATION_SELECTED = "definition-candidate"
MIGRATION_OFF = "off"

#: The authored contract, read ONLY as the explicit fallback for unadmitted
#: identities and as the probe's comparison oracle — never semantic authority
#: for the admitted set.
LEGACY_ONTOLOGY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"

PROBE_SCHEMA = "de4sdv.o4-definition-migration-probe/v1"


class DefinitionMigrationError(ValueError):
    """The explicit definition-migration request failed closed."""


@dataclass(frozen=True)
class MigrationClosureStatus:
    """Exact-revision API-closure state for the admitted definition set."""

    missing: tuple[str, ...] = ()
    mismatched: tuple[str, ...] = ()
    checked_against: str = "no revision binding supplied"
    binding_validated: bool = False
    binding_scope: str = ""
    admitted_count: int = 0
    expected_git_revision: str | None = None
    binding_git_revision: str | None = None
    revision_matches: bool = False
    ontology_matches: bool = False

    @property
    def closed(self) -> bool:
        return (
            not self.missing
            and not self.mismatched
            and self.binding_validated
            and self.binding_scope == "full-model"
            and self.revision_matches
            and self.ontology_matches
        )

    def prerequisite(self) -> str:
        """The exact, structured prerequisite for activation ('' when closed)."""
        if self.closed:
            return ""
        parts: list[str] = []
        if not self.revision_matches:
            parts.append(
                "an explicit expected Git revision must match the validated "
                f"binding revision (expected={self.expected_git_revision!r}, "
                f"binding={self.binding_git_revision!r})"
            )
        if not self.ontology_matches:
            parts.append("the binding ontology identity must match the executed contract")
        if not self.binding_validated:
            parts.append(
                "the exact-revision revision binding is missing or not "
                "ingestion-validated (semantic_validation != 'passed')"
            )
        elif self.binding_scope != "full-model":
            parts.append(
                f"the revision binding scope is {self.binding_scope!r}, not "
                "'full-model'"
            )
        if self.missing:
            parts.append(
                f"{len(self.missing)} of {self.admitted_count} admitted "
                "definition identities carry no ingestion-validated kernel "
                f"binding: {', '.join(self.missing)}"
            )
        if self.mismatched:
            parts.append(
                f"{len(self.mismatched)} admitted identities carry a validated "
                "binding that is ambiguous, has a blank element identity, or "
                "disagrees with the candidate "
                f"source_file/declaration: {', '.join(self.mismatched)}"
            )
        return (
            "activation requires a fresh exact-revision API closure: "
            + "; ".join(parts)
            + ". Run the privileged ingestion/binding validation for the "
            "admitted declarations at the bound revision and select the "
            "definition-candidate migration path explicitly with the "
            "resulting binding. Until then the path stays non-activatable "
            "and the production default (legacy authority) is unchanged."
        )


@dataclass(frozen=True)
class DefinitionMigrationAuthority:
    """Verified migration authority: candidate pair + explicit fallback provider."""

    candidate: DefinitionCandidate
    provider: DefinitionCandidateProvider
    closure: MigrationClosureStatus

    @property
    def authority_id(self) -> str:
        return self.provider.authority_id

    @property
    def identities(self) -> tuple[str, ...]:
        return self.candidate.identities

    @property
    def activation_eligible(self) -> bool:
        return self.closure.closed

    def activation_blocked_reason(self) -> str:
        return self.closure.prerequisite()


def validate_candidate_closure(
    candidate: DefinitionCandidate, binding: Any = None,
    *, expected_git_revision: str | None = None,
    expected_ontology: OntologyIdentity | None = None,
) -> MigrationClosureStatus:
    """Compute the fresh exact-revision API-closure state for the candidate.

    A closure entry is satisfied only by an ingestion-validated kernel
    binding whose ``source_file`` and ``declaration`` agree with the
    candidate pair's own contract for that identity — a binding for the same
    class name with different bytes does not close the identity.
    """
    admitted_count = len(candidate.identities)
    if binding is None:
        return MigrationClosureStatus(
            missing=tuple(sorted(candidate.identities)),
            admitted_count=admitted_count,
            expected_git_revision=expected_git_revision,
        )
    by_class: dict[str, Any] = {}
    duplicates: set[str] = set()
    for item in getattr(binding, "kernel_bindings", ()) or ():
        name = getattr(item, "ontology_class", None)
        if isinstance(name, str) and name:
            if name in by_class:
                duplicates.add(name)
            else:
                by_class[name] = item
    missing: list[str] = []
    mismatched: list[str] = []
    for name in sorted(candidate.identities):
        contract = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        item = by_class.get(name)
        if item is None:
            missing.append(name)
            continue
        if (
            name in duplicates
            or not isinstance(getattr(item, "element_id", None), str)
            or not item.element_id.strip()
            or getattr(item, "source_file", None) != contract["source_file"]
            or getattr(item, "declaration", None) != contract["declaration"]
        ):
            mismatched.append(name)
    return MigrationClosureStatus(
        missing=tuple(missing),
        mismatched=tuple(mismatched),
        checked_against="revision binding kernel bindings",
        binding_validated=(
            str(getattr(binding, "semantic_validation", "")) == "passed"
        ),
        binding_scope=str(getattr(binding, "scope", "")),
        admitted_count=admitted_count,
        expected_git_revision=expected_git_revision,
        binding_git_revision=getattr(binding, "git_commit", None),
        ontology_matches=(
            expected_ontology is not None
            and expected_ontology == getattr(binding, "ontology", None)
        ),
        revision_matches=(
            isinstance(expected_git_revision, str)
            and re.fullmatch(r"[0-9a-f]{40}", expected_git_revision) is not None
            and expected_git_revision == getattr(binding, "git_commit", None)
        ),
    )


def load_definition_migration_authority(
    root: Path,
    *,
    contract: KernelContract,
    binding: Any = None,
    candidate: DefinitionCandidate | None = None,
    require_activation_eligible: bool = False,
    expected_git_revision: str | None = None,
) -> DefinitionMigrationAuthority:
    """Load the verified candidate pair and build the explicit provider.

    ``root`` is the repository checkout holding the verified candidate
    artifacts. The authored ``KernelContract`` is required: the migration
    path keeps an EXPLICIT fallback for every unadmitted identity instead of
    hiding it. With ``require_activation_eligible`` the call refuses unless
    the fresh exact-revision API closure is present, naming the exact
    prerequisite.
    """
    root = Path(root)
    if not isinstance(contract, KernelContract):
        raise DefinitionMigrationError(
            "the definition-migration path requires the authored "
            "KernelContract for the explicit fallback of every unadmitted "
            "identity"
        )
    if candidate is None:
        candidate = load_definition_candidate(root)
    overlap = sorted(set(candidate.identities) & set(MIGRATED_IDENTITIES))
    if overlap:
        raise DefinitionMigrationError(
            "candidate identities overlap the frozen O3 migrated identity "
            f"set: {overlap}"
        )
    provider = DefinitionCandidateProvider(legacy=contract, candidate=candidate)
    closure = validate_candidate_closure(
        candidate, binding, expected_git_revision=expected_git_revision,
        expected_ontology=contract.identity,
    )
    if require_activation_eligible and not closure.closed:
        raise DefinitionMigrationError(
            "definition-candidate migration cannot activate: " + closure.prerequisite()
        )
    return DefinitionMigrationAuthority(
        candidate=candidate, provider=provider, closure=closure
    )


def resolve_definition_migration_selection(
    *, selection: str | None = None, environ: Mapping[str, str] | None = None
) -> str:
    """Resolve the explicit migration selection (fail closed).

    Explicit arguments win over the environment. The default — unset or
    empty — is OFF. Any other value than ``off`` / ``definition-candidate``
    is refused: this path is never selected implicitly, and the production
    surfaces never consult it.
    """
    env = os.environ if environ is None else environ
    raw = selection if selection is not None else env.get(MIGRATION_ENV, "")
    value = str(raw or "").strip().lower()
    if value in ("", MIGRATION_OFF):
        return MIGRATION_OFF
    if value != MIGRATION_SELECTED:
        raise DefinitionMigrationError(
            f"unknown {MIGRATION_ENV} value {raw!r}: expected "
            f"{MIGRATION_OFF!r} or {MIGRATION_SELECTED!r}; the "
            "definition-migration path is never selected implicitly"
        )
    return MIGRATION_SELECTED


def build_definition_migration_runtime(
    *,
    api_url: str,
    binding_path: Path,
    expected_git_revision: str,
    ontology_path: Path,
    selection: str | None = None,
    environ: Mapping[str, str] | None = None,
    require_activation_eligible: bool = True,
    api_timeout: float = 600.0,
    method_conformance: Any = None,
    method_context_provider: Any = None,
    root: Path = ROOT,
) -> "tuple[Any, DefinitionMigrationAuthority]":
    """Assemble the migration runtime under the explicit selection.

    One call site for the migration path: resolve the explicit selection,
    load the exact-revision binding, verify the candidate pair, enforce the
    fresh exact-revision API closure (fail closed with the exact
    prerequisite), then assemble the runtime through the existing seam with
    the verified provider. The returned service is the same
    :class:`~de4sdv.semantic.query.SemanticQueryService` the production path
    builds; it is non-production until a reviewed activation decision makes
    the path the selected authority.
    """
    selected = resolve_definition_migration_selection(
        selection=selection, environ=environ
    )
    if selected != MIGRATION_SELECTED:
        raise DefinitionMigrationError(
            f"definition migration is not selected (set {MIGRATION_ENV}="
            f"{MIGRATION_SELECTED} or pass selection explicitly); the "
            "production default remains legacy and is never replaced "
            "implicitly"
        )
    from de4sdv.sysml_api.errors import RevisionMismatchError
    from de4sdv.sysml_api.revisions import RevisionBinding

    from .runtime import build_semantic_runtime

    binding_path = Path(binding_path)
    ontology_path = Path(ontology_path)
    binding = RevisionBinding.load(binding_path)
    try:
        binding.require_current(expected_git_revision)
    except RevisionMismatchError as exc:
        raise DefinitionMigrationError(
            "definition migration revision mismatch: " + str(exc)
        ) from exc
    contract = KernelContract.load(ontology_path)
    binding.require_ontology(contract.identity)
    authority = load_definition_migration_authority(
        root,
        contract=contract,
        binding=binding,
        require_activation_eligible=require_activation_eligible,
        expected_git_revision=expected_git_revision,
    )
    service = build_semantic_runtime(
        api_url=api_url,
        binding_path=binding_path,
        expected_git_revision=expected_git_revision,
        ontology_path=ontology_path,
        api_timeout=api_timeout,
        method_conformance=method_conformance,
        method_context_provider=method_context_provider,
        definition_candidate_authority=authority.provider,
    )
    return service, authority


def _load_export_elements(export: Any) -> list[dict[str, Any]] | None:
    """Load retained export elements from a path, a list, or ``None``."""
    if export is None:
        return None
    if isinstance(export, (list, tuple)):
        return [item for item in export if isinstance(item, dict)]
    path = Path(export)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DefinitionMigrationError(
            f"retained export is not readable JSON: {path}: {exc}"
        ) from exc
    if isinstance(document, list):
        elements = document
    elif isinstance(document, dict) and isinstance(document.get("elements"), list):
        elements = document["elements"]
    else:
        raise DefinitionMigrationError(
            f"{path}: retained export must be a JSON element list or an "
            "object carrying an 'elements' list"
        )
    return [item for item in elements if isinstance(item, dict)]


def _matching_export_ids(
    elements: list[dict[str, Any]],
    sources: Mapping[str, str] | None,
    mapping: Mapping[str, str],
) -> list[str]:
    """Declaration-form matches in a retained export (evidence, not identity)."""
    declared_name, expected_type = declaration_identity(mapping["declaration"])
    found: list[str] = []
    for element in elements:
        if str(element.get("@type")) != expected_type:
            continue
        declared = str(element.get("declaredName") or element.get("name") or "")
        if declared != declared_name:
            continue
        element_id_value = (
            element.get("@id") or element.get("elementId") or element.get("id")
        )
        if sources is not None:
            if sources.get(str(element_id_value)) != mapping["source_file"]:
                continue
        found.append(str(element_id_value) if element_id_value is not None else "")
    return sorted(found)


def probe_definition_migration(
    root: Path,
    *,
    contract: KernelContract | None = None,
    binding: Any = None,
    export: Any = None,
    element_sources: Mapping[str, str] | None = None,
    candidate: DefinitionCandidate | None = None,
    expected_git_revision: str | None = None,
) -> dict[str, Any]:
    """Executable offline comparison/probe over the real retained artifacts.

    Read-only and offline: loads the verified candidate pair, compares every
    admitted identity's candidate mapping against the authored contract
    (the comparison oracle only), reports the fresh exact-revision closure
    state and the remaining legacy dependency, and — when a retained export
    is supplied — reports declaration-form matches in that export as
    representation evidence. It claims no runtime identity and selects
    nothing.
    """
    root = Path(root)
    if contract is None:
        contract = KernelContract.load(root / LEGACY_ONTOLOGY_PATH)
    if candidate is None:
        candidate = load_definition_candidate(root)
    authority = load_definition_migration_authority(
        root, contract=contract, binding=binding, candidate=candidate,
        expected_git_revision=expected_git_revision,
    )
    overlap = sorted(set(candidate.identities) & set(MIGRATED_IDENTITIES))
    if overlap:
        raise DefinitionMigrationError(
            f"candidate identities overlap the frozen O3 migrated set: {overlap}"
        )
    bindings_by_class: dict[str, Any] = {}
    if binding is not None:
        for item in getattr(binding, "kernel_bindings", ()) or ():
            name = getattr(item, "ontology_class", None)
            if isinstance(name, str) and name:
                bindings_by_class.setdefault(name, item)
    elements = _load_export_elements(export)
    sources = dict(element_sources) if element_sources is not None else None

    records: list[dict[str, Any]] = []
    resolved_count = 0
    for name in candidate.identities:
        contract_row = candidate.row_for(name)["grounding"][
            "kernel_binding_contract"
        ]
        candidate_mapping = {
            "source_file": contract_row["source_file"],
            "declaration": contract_row["declaration"],
        }
        legacy_mapping: dict[str, str] | None
        try:
            mapping = contract.class_mapping(name)
            legacy_mapping = {
                "source_file": mapping.file,
                "declaration": mapping.declaration,
            }
        except KeyError:
            legacy_mapping = None
        entry = bindings_by_class.get(name)
        record: dict[str, Any] = {
            "identity": name,
            "candidate": candidate_mapping,
            "legacy": legacy_mapping,
            "legacy_present": legacy_mapping is not None,
            "mapping_equal": legacy_mapping == candidate_mapping,
            "validated_binding_element_id": (
                str(getattr(entry, "element_id", "")) or None
                if entry is not None
                else None
            ),
        }
        if elements is not None:
            matched = _matching_export_ids(elements, sources, candidate_mapping)
            record["export_matched_element_ids"] = matched
            record["export_resolved"] = bool(matched)
            if matched:
                resolved_count += 1
        records.append(record)

    report: dict[str, Any] = {
        "schema": PROBE_SCHEMA,
        "offline": True,
        "read_only": True,
        "source_revision": candidate.source_revision,
        "authority_id": authority.authority_id,
        "admitted_count": len(candidate.identities),
        "o3_overlap": overlap,
        "activation_eligible": authority.activation_eligible,
        "activation_prerequisite": authority.closure.prerequisite(),
        "closure": {
            "closed": authority.closure.closed,
            "checked_against": authority.closure.checked_against,
            "missing": list(authority.closure.missing),
            "mismatched": list(authority.closure.mismatched),
            "binding_validated": authority.closure.binding_validated,
            "binding_scope": authority.closure.binding_scope,
            "expected_git_revision": authority.closure.expected_git_revision,
            "binding_git_revision": authority.closure.binding_git_revision,
            "revision_matches": authority.closure.revision_matches,
            "ontology_matches": authority.closure.ontology_matches,
        },
        "legacy_contract_identity": contract.identity.to_dict(),
        "legacy_only_class_count": len(
            set(contract.classes) - set(candidate.identities)
        ),
        "production_default": "legacy (unchanged); this probe selects nothing",
        "identities": records,
    }
    if elements is None:
        report["export"] = {
            "provided": False,
            "resolved_count": None,
            "prerequisite": (
                "no retained export was supplied; an export-backed probe "
                "requires the privileged exact-revision ingestion/export "
                "covering the admitted declarations"
            ),
        }
    else:
        report["export"] = {
            "provided": True,
            "element_count": len(elements),
            "resolved_count": resolved_count,
            "identity_claim": "none (declaration-form evidence only)",
        }
    return report