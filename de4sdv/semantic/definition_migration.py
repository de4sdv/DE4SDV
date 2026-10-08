"""O4 definition layer verification — the admitted definition pair and its API closure.

The model-authority runtime serves the admitted definition identities from
the verified definition pair (``definition-projection.json`` /
``definition-profile.json``). This module provides:

* **Verification.** The candidate pair is loaded and verified through
  :mod:`de4sdv.semantic.definition_candidate` (structural pair contract, the
  recorded source-revision binding, regeneration equality, and disjointness
  from the frozen O2-chain identities).
* **Closure.** :func:`validate_candidate_closure` computes the fresh
  exact-revision API closure: the validated revision binding for the exact
  revision must carry an ingestion-validated kernel binding for every
  admitted identity whose ``source_file``/``declaration`` agree with the
  pair, and the binding's semantic-authority identity must equal the
  model-built contract's. The model-authority runtime refuses to construct
  unless the closure is closed.
* **Probe.** :func:`probe_definition_migration` is the read-only report the
  privileged ingestion records (``closure.closed`` gates bundle closure):
  per-identity pair-vs-contract mappings and, when a retained export is
  supplied, declaration-form matches (representation evidence only).

There is no other provider and no fallback (O4 Wave C2).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .definition_candidate import (
    DefinitionCandidate,
    load_definition_candidate,
)
from .definition_candidate_provider import DefinitionCandidateProvider
from .kernel_contract import KernelContract, declaration_identity
from .model_contract import O2_CHAIN_IDENTITIES

ROOT = Path(__file__).resolve().parents[2]

PROBE_SCHEMA = "de4sdv.o4-definition-migration-probe/v2"


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
    authority_matches: bool = False

    @property
    def closed(self) -> bool:
        return (
            not self.missing
            and not self.mismatched
            and self.binding_validated
            and self.binding_scope == "full-model"
            and self.revision_matches
            and self.authority_matches
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
        if not self.authority_matches:
            parts.append("the binding semantic-authority identity must match the "
                         "model-built contract")
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
            "admitted declarations at the bound revision. Until then the "
            "model-authority runtime refuses to construct."
        )


@dataclass(frozen=True)
class DefinitionMigrationAuthority:
    """Verified definition pair + its provider + the API-closure state."""

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
    expected_authority: Any = None,
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
        authority_matches=(
            expected_authority is not None
            and expected_authority == getattr(binding, "semantic_authority", None)
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
    binding: Any = None,
    candidate: DefinitionCandidate | None = None,
    require_activation_eligible: bool = False,
    expected_git_revision: str | None = None,
    expected_authority: Any = None,
) -> DefinitionMigrationAuthority:
    """Load the verified definition pair, its provider and its closure state.

    ``expected_authority`` is the semantic-authority identity the binding must
    carry (default: the model-built contract of ``root``). With
    ``require_activation_eligible`` the call refuses unless the fresh
    exact-revision API closure is present, naming the exact prerequisite.
    """
    root = Path(root)
    if candidate is None:
        candidate = load_definition_candidate(root)
    overlap = sorted(set(candidate.identities) & set(O2_CHAIN_IDENTITIES))
    if overlap:
        raise DefinitionMigrationError(
            "candidate identities overlap the frozen O2-chain identity "
            f"set: {overlap}"
        )
    if expected_authority is None and binding is not None:
        expected_authority = KernelContract.from_layers(root).identity
    provider = DefinitionCandidateProvider(candidate=candidate)
    closure = validate_candidate_closure(
        candidate, binding, expected_git_revision=expected_git_revision,
        expected_authority=expected_authority,
    )
    if require_activation_eligible and not closure.closed:
        raise DefinitionMigrationError(
            "definition layer cannot activate: " + closure.prerequisite()
        )
    return DefinitionMigrationAuthority(
        candidate=candidate, provider=provider, closure=closure
    )


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
    admitted identity's pair mapping against the model-built contract,
    reports the fresh exact-revision closure state, and — when a retained export
    is supplied — reports declaration-form matches in that export as
    representation evidence. It claims no runtime identity and selects
    nothing.
    """
    root = Path(root)
    if contract is None:
        contract = KernelContract.from_layers(root)
    if candidate is None:
        candidate = load_definition_candidate(root)
    authority = load_definition_migration_authority(
        root, binding=binding, candidate=candidate,
        expected_git_revision=expected_git_revision,
        expected_authority=contract.identity,
    )
    overlap = sorted(set(candidate.identities) & set(O2_CHAIN_IDENTITIES))
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
        contract_mapping: dict[str, str] | None
        try:
            mapping = contract.class_mapping(name)
            contract_mapping = {
                "source_file": mapping.file,
                "declaration": mapping.declaration,
            }
        except (KeyError, ValueError):
            contract_mapping = None
        entry = bindings_by_class.get(name)
        record: dict[str, Any] = {
            "identity": name,
            "candidate": candidate_mapping,
            "contract": contract_mapping,
            "contract_present": contract_mapping is not None,
            "mapping_equal": contract_mapping == candidate_mapping,
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
        "o2_chain_overlap": overlap,
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
            "authority_matches": authority.closure.authority_matches,
        },
        "semantic_authority": contract.identity.to_dict(),
        "selection": "none; this probe selects nothing",
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