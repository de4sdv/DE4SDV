"""Real Phase-10 pilot binding for INC-AEBS-009D (Lane C input assembly).

Assembles the typed evaluation context for the governed pilot declared in
``docs/method-conformance/pilot-scope.md``: the model branch binds the six
declared verification usages through the merged Lane B primitives
(``de4sdv.semantic.method_contract.bind_pilot_usages``), and the evidence
branch reads the retained campaign artifacts at the evaluated revision.

Boundaries:

- no second graph, no second binding mechanism, no candidate re-selection:
  model identities resolve through the existing explicit-identity resolver;
- all reads are read-only against an explicit :class:`FileSource` (a checkout
  directory or a Git revision object store);
- the conservative-scope-equality candidate side is assembled from the
  candidate revision's own committed identity artifacts, and the tested-input
  reconstruction rule is pinned with its provenance;
- a candidate that modifies the policy-bearing contract closure is refused
  (migration blocker), never silently accepted.
"""

from __future__ import annotations

import functools
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from de4sdv.semantic.method_contract import (
    _generalization_parents,
    _metadata_witnesses,
    _subject_members,
    bind_pilot_usages,
)
from de4sdv.sysml_api.identity import resolve_identity

from .method_evaluator import (
    APPLICABILITY_CANDIDATE_SCOPE,
    APPLICABILITY_UNCONDITIONAL,
    EVALUATION_SOURCE_MODEL,
    EVALUATION_SOURCE_REPOSITORY,
    INPUT_UNAVAILABLE,
    DeclaredEvaluationScope,
    EvaluationContext,
    FileSource,
    MethodContract,
    ObligationSpec,
    RegistryScan,
    RevisionIdentity,
    SELECTOR_DEFINITION_SUBJECT,
    SELECTOR_PROFILE_SET,
    SELECTOR_SCOPE_SUBJECT,
    SELECTOR_SCOPE_USAGES,
    SELECTOR_TESTED_SCOPE_SUBJECT,
    SELECTOR_UPSTREAM,
    ScopeEqualityComparison,
    verify_candidate_policy_closure,
)

# ---------------------------------------------------------------------------
# Governed pilot constants (aebs_override_verification.sysml; pilot-scope.md)
# ---------------------------------------------------------------------------

PILOT_INCREMENT = "INC-AEBS-009D"
PILOT_SCOPE_RECORD = "PSC-009D"
PILOT_SCOPE_USAGES: tuple[str, ...] = (
    "VC-AEBS-009D-01",
    "VC-AEBS-009D-02",
    "VC-AEBS-009D-03",
    "VC-AEBS-009D-04",
    "VC-AEBS-009D-05",
    "VC-AEBS-009D-06",
)
PILOT_DEFINITION = "VC-AEBS-009D-DE"
PILOT_REQUIREMENT_SHORTS: tuple[str, ...] = ("EC-009D-01", "EC-009D-02", "EC-009D-03")
PILOT_PROFILES: tuple[str, ...] = (
    "fresh_false_control",
    "fresh_true_conscious_override",
    "stale",
    "missing",
    "malformed",
    "future_stamped",
)
PILOT_EXPECTED_DISPOSITIONS: Mapping[str, str] = {
    "fresh_false_control": "control_clear",
    "fresh_true_conscious_override": "conscious_override",
    "stale": "degraded_stale_source",
    "missing": "inconclusive_missing_source",
    "malformed": "error_malformed_source",
    "future_stamped": "error_future_source",
}
PILOT_DEFINITION_ACTION_KINDS: Mapping[str, tuple[str, ...]] = {
    "collectData": ("test",),
    "processData": ("analyze",),
    "evaluateData": ("analyze",),
}

BENCH_ROOT = "implementation/aebs-autoware-nominal-vehicle-target-bench"
MANIFEST_PATH = f"{BENCH_ROOT}/evidence/009d/campaign-manifest.json"
REGISTRY_PATH = "docs/acceptance-decisions"
BENCH_DEFINITION_NAME = "OverrideMatrixBench"

#: Conservative tested-input rule (provenance-pinned).
#:
#: Source: the identity declaration committed at the tested head
#: ``01d9f586`` (``{BENCH_ROOT}/scripts/execution_identity.py``,
#: blob sha256 9be9c063...). The rule enumerates the file set whose digests
#: the record's execution-manifest values are computed over. It is pinned here
#: as contract data because the evaluator must not execute candidate-revision
#: code; reproduction against the retained records is verified by
#: ``scripts/run_method_conformance.py`` at the declared tested head.
TESTED_INPUT_RULE: Mapping[str, Any] = {
    "source": f"{BENCH_ROOT}/scripts/execution_identity.py@01d9f586",
    "source_blob_sha256": "9be9c0634bac437d1c6d8ae034d8b51ad9c07e4bcb3a1a45a9a1d6de1e17d0a6",
    "top_level": (
        "runtime-lock.yaml",
        "compose.yaml",
        "cyclonedds.xml",
        "config/scenario-009b-moving-vehicle-target.yaml",
        "config/scenario-009d-conscious-override-matrix.yaml",
        "config/scenario-009d-moving-vehicle-target.yaml",
        "config/aebs-009b.param.yaml",
        "workspace/.gitkeep",
    ),
    "recursive_roots": ("scripts", "src"),
    "optional_recursive_roots": ("schemas",),
    "virtual_inherited_key": "@inherited-009a-execution-manifest",
    "virtual_inherited_value": "a06657a0a98eea21862ce94bf79a5b49509b1d7f0f7581af6cd3bee9bdcb2e8a",
    "profile_key": "@009d-override-profile",
}

#: Pinned fingerprint field names of the record provenance (pilot-scope.md).
SCOPE_EQUALITY_FIELDS: tuple[str, ...] = (
    "repository_head",
    "override_matrix_sha256",
    "override_execution_manifest_sha256",
    "execution_manifest_sha256",
    "runtime_lock_sha256",
    "inherited_009a.execution_manifest_sha256",
    "inherited_009a.runtime_lock_sha256",
    "image_digest",
    "map_digest",
    "host_arch",
)

#: Python ``platform.machine()`` spelling of the container platform pins.
_PLATFORM_ARCH_NORMALIZATION: Mapping[str, str] = {
    "arm64": "aarch64",
    "amd64": "x86_64",
}


# ---------------------------------------------------------------------------
# File sources (read-only, revision-explicit)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DirectoryFileSource:
    """Read files below one directory root (test/candidate checkout source)."""

    root: Path

    def read_bytes(self, relative_path: str) -> bytes | None:
        candidate = self.root / relative_path
        if not candidate.is_file():
            return None
        return candidate.read_bytes()

    def exists(self, relative_path: str) -> bool:
        return (self.root / relative_path).is_file()

    def list_files(self, prefix: str) -> list[str] | None:
        base = self.root / prefix
        if not base.exists():
            return None
        if base.is_file():
            return [prefix]
        return sorted(
            str(path.relative_to(self.root))
            for path in base.rglob("*")
            if path.is_file()
        )


@dataclass(frozen=True)
class GitRevisionFileSource:
    """Read committed blobs of one Git revision (no working-tree reads)."""

    repository: Path
    revision: str

    def _git(self, *args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", "-C", str(self.repository), *args],
            capture_output=True,
        )

    @functools.lru_cache(maxsize=None)  # noqa: B019 - per-source instance cache
    def read_bytes(self, relative_path: str) -> bytes | None:
        if not re.fullmatch(r"[0-9a-f]{40}", self.revision):
            return None
        completed = self._git("show", f"{self.revision}:{relative_path}")
        if completed.returncode != 0:
            return None
        return completed.stdout

    def exists(self, relative_path: str) -> bool:
        return self.read_bytes(relative_path) is not None

    @functools.lru_cache(maxsize=None)  # noqa: B019 - per-source instance cache
    def list_files(self, prefix: str) -> list[str] | None:
        completed = self._git(
            "ls-tree", "-r", "--name-only", self.revision, "--", prefix
        )
        if completed.returncode != 0:
            return None
        files = [line for line in completed.stdout.decode().splitlines() if line]
        if not files:
            return None
        return sorted(files)


# ---------------------------------------------------------------------------
# Approved contract decode (from the committed A specification twin)
# ---------------------------------------------------------------------------

_SELECTOR_STRINGS: Mapping[str, tuple[str, str | None]] = {
    "declared-pilot-scope": (SELECTOR_SCOPE_SUBJECT, None),
    "scope usages": (SELECTOR_SCOPE_USAGES, None),
    "ConsciousOverrideVerification": (SELECTOR_DEFINITION_SUBJECT, None),
    "declared-tested-scope": (SELECTOR_TESTED_SCOPE_SUBJECT, None),
    "declared profiles": (SELECTOR_PROFILE_SET, None),
    "each profile in the declared tested scope": (SELECTOR_PROFILE_SET, None),
    "canonical records": (SELECTOR_UPSTREAM, "PC-009D-EXECUTION-RECORD"),
    "each profile's canonical record": (SELECTOR_UPSTREAM, "PC-009D-EXECUTION-RECORD"),
}

_APPLICABILITY_STRINGS: Mapping[str, str] = {
    "(no applicability condition)": APPLICABILITY_UNCONDITIONAL,
    "candidate revision declares the INC-AEBS-009D pilot scope": APPLICABILITY_CANDIDATE_SCOPE,
    "candidate declares the INC-AEBS-009D tested-scope manifest": APPLICABILITY_CANDIDATE_SCOPE,
}

_EVALUATION_SOURCE_STRINGS: Mapping[str, str] = {
    "pinned-model-record": EVALUATION_SOURCE_MODEL,
    "pinned-repository-artifact": EVALUATION_SOURCE_REPOSITORY,
    "pinned-repository-artifact+candidate-declared-manifest": EVALUATION_SOURCE_REPOSITORY,
}

#: Typed target filters decoded from the A obligation table (pilot-scope.md).
_PILOT_TARGET_FILTERS: Mapping[str, tuple[str, ...]] = {
    "PC-009D-SCOPE-POPULATION": ("element type VerificationCaseUsage",),
    "PC-009D-VC-BINDING": (),
    "PC-009D-SUBJECT-MEMBERSHIP": ("element type OverrideMatrixBench specialization",),
    "PC-009D-OBJECTIVE-CONTRACTS": ("pinned requirement set", "full-witness-path"),
    "PC-009D-USAGE-METHOD-METADATA": ("method-kind value set exactly {test, analyze}",),
    "PC-009D-DEFINITION-METHOD-METADATA": ("per-action kind",),
    "PC-009D-PROFILE-POPULATION": ("profile identity equality (pinned set, exact)",),
    "PC-009D-EXECUTION-RECORD": ("record integrity: manifest sha256",),
    "PC-009D-EXECUTION-OUTCOME": ("pinned disposition",),
    "PC-009D-SCOPE-EQUALITY": ("all pinned fields",),
    "PC-009D-ACCEPTANCE-AUTHORITY": ("decision population completeness",),
}


def decode_approved_contract(
    twin: Mapping[str, Any], *, method_id: str = "de4sdv.method-conformance.pilot.009d.v1"
) -> MethodContract:
    """Decode the structured twin (pilot-obligations.yaml) into a MethodContract.

    Unknown selector/applicability/evaluation-source strings are contract
    validation errors (raised here as ``ValueError``), never silent skips.
    """
    phase = str(twin.get("phase_literal") or "")
    if not phase:
        raise ValueError("approved contract twin is missing phase_literal")
    dependency_graph = twin.get("dependency_graph") or {}
    obligations: list[ObligationSpec] = []
    for row in twin.get("obligations") or []:
        obligation_id = str(row.get("id") or "")
        selector = str(row.get("subject_selector") or "")
        if selector not in _SELECTOR_STRINGS:
            raise ValueError(
                f"unsupported subject selector {selector!r} for {obligation_id}"
            )
        selector_kind, upstream_id = _SELECTOR_STRINGS[selector]
        applicability = str(row.get("applicability") or "")
        if applicability not in _APPLICABILITY_STRINGS:
            raise ValueError(
                f"unsupported applicability form {applicability!r} for {obligation_id}"
            )
        source = str(row.get("evaluation_source") or "")
        if source not in _EVALUATION_SOURCE_STRINGS:
            raise ValueError(
                f"unsupported evaluation source {source!r} for {obligation_id}"
            )
        cardinality = row.get("per_subject_cardinality") or [0, 0]
        minimum_population = int(row.get("subjects") or 0)
        permitted_empty = False
        permitted_empty_disposition = None
        attestation_policy = ""
        if obligation_id == "PC-009D-ACCEPTANCE-AUTHORITY":
            attestation_policy = str(twin.get("attestation_policy") or "")
        obligations.append(
            ObligationSpec(
                obligation_id=obligation_id,
                phase=phase,
                subject_selector=selector,
                selector_kind=selector_kind,
                applicability=applicability,
                applicability_kind=_APPLICABILITY_STRINGS[applicability],
                minimum_population=minimum_population,
                permitted_empty=permitted_empty,
                permitted_empty_disposition=permitted_empty_disposition,
                predicate=str(row.get("predicate") or ""),
                target_filters=_PILOT_TARGET_FILTERS.get(obligation_id, ()),
                cardinality=(int(cardinality[0]), int(cardinality[1])),
                required=bool(row.get("required", True)),
                evaluation_source=_EVALUATION_SOURCE_STRINGS[source],
                attestation_policy_ref=attestation_policy,
                claim_boundary=f"{PILOT_INCREMENT} declared pilot scope",
                depends_on=tuple(dependency_graph.get(obligation_id) or ()),
                upstream_obligation_id=upstream_id,
            )
        )
    return MethodContract(
        method_id=method_id,
        contract_id=PILOT_INCREMENT,
        phase=phase,
        obligations=tuple(obligations),
        policy_bundle_id=str(twin.get("attestation_policy") or ""),
    )


def load_approved_contract_from_yaml(path: Path) -> MethodContract:
    import yaml  # local import: the evaluator core avoids a hard yaml dependency

    twin = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(twin, Mapping):
        raise ValueError("approved contract twin must be a mapping")
    return decode_approved_contract(twin)


# ---------------------------------------------------------------------------
# Model-branch decoders (serializer shapes; shared with the Lane B read-back)
# ---------------------------------------------------------------------------


def _elements_by_id(elements: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(e.get("@id")): e for e in elements if e.get("@id")}


def _refs(value: object) -> list[str]:
    if isinstance(value, dict):
        candidate = value.get("@id")
        return [str(candidate)] if candidate else []
    if isinstance(value, list):
        return [
            str(item.get("@id"))
            for item in value
            if isinstance(item, dict) and item.get("@id")
        ]
    return []


def _by_short(elements: Sequence[Mapping[str, Any]], short_name: str) -> Mapping[str, Any] | None:
    matches = [e for e in elements if str(e.get("declaredShortName") or "") == short_name]
    if len(matches) == 1:
        return matches[0]
    return None


def _membership_member(
    by_id: Mapping[str, Mapping[str, Any]], parent: Mapping[str, Any], member_name: str
) -> str | None:
    for reference in parent.get("ownedRelationship") or []:
        relationship = by_id.get(str(reference.get("@id")))
        if relationship is None:
            continue
        if not str(relationship.get("@type") or "").endswith("Membership"):
            continue
        name = str(
            relationship.get("memberName") or relationship.get("declaredName") or ""
        )
        if name != member_name:
            continue
        member = relationship.get("memberElement")
        member_ids = _refs(member)
        if member_ids:
            return member_ids[0]
    return None


def _value_text(
    by_id: Mapping[str, Mapping[str, Any]], value_id: str
) -> str | None:
    element = by_id.get(value_id)
    if element is None:
        return None
    kind = str(element.get("@type") or "")
    if kind.startswith("Literal"):
        value = element.get("value")
        if value is None:
            return None
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)
    return None


def _member_text_value(
    by_id: Mapping[str, Mapping[str, Any]], parent: Mapping[str, Any], member_name: str
) -> tuple[str | None, str | None]:
    member_id = _membership_member(by_id, parent, member_name)
    if member_id is None:
        return None, None
    feature = by_id.get(member_id) or {}
    for reference in feature.get("ownedRelationship") or []:
        relationship = by_id.get(str(reference.get("@id")))
        if relationship is None or str(relationship.get("@type")) != "FeatureValue":
            continue
        member = relationship.get("memberElement") or relationship.get("value")
        for value_id in _refs(member):
            text = _value_text(by_id, value_id)
            if text is not None:
                return member_id, text
    return member_id, None


def decode_declared_tested_scope(
    elements: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any] | None, tuple[str, ...], list[str]]:
    """Decode the model-resident ``testedScope`` declaration.

    Returns (item element, declared profile identities, diagnostics).
    """
    diagnostics: list[str] = []
    scope = None
    matches = [
        e
        for e in elements
        if str(e.get("declaredName") or "") == "testedScope"
        and str(e.get("@type")) == "ItemUsage"
    ]
    if len(matches) != 1:
        diagnostics.append(
            f"expected exactly one testedScope item; found {len(matches)}"
        )
        return None, (), diagnostics
    scope = matches[0]
    by_id = _elements_by_id(elements)
    _, execution_head = _member_text_value(by_id, scope, "executionHead")
    _, profile_text = _member_text_value(by_id, scope, "profileIdentities")
    profiles = tuple(
        item.strip() for item in (profile_text or "").split(",") if item.strip()
    )
    if execution_head is None:
        diagnostics.append("testedScope executionHead value is unresolved")
    if not profiles:
        diagnostics.append("testedScope profileIdentities value is unresolved")
    return scope, profiles, diagnostics


def decode_model_obligation_closure(
    elements: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Decode the candidate revision's model-resident obligation records.

    These records are the candidate's declared policy-bearing closure; they
    are verified against the approved contract and never used as the
    governing contract themselves.
    """
    closure: list[dict[str, str]] = []
    by_id = _elements_by_id(elements)
    for element in elements:
        if str(element.get("@type")) != "ItemUsage":
            continue
        name = str(element.get("declaredName") or "")
        if not name.startswith("obligation"):
            continue
        values: dict[str, str] = {}
        for field_name in (
            "obligationId",
            "predicate",
            "cardinalityMinimum",
            "cardinalityMaximum",
            "required",
            "attestationPolicyRef",
        ):
            _, text = _member_text_value(by_id, element, field_name)
            if text is not None:
                values[field_name] = text
        if "obligationId" in values:
            closure.append(values)
    return closure


def resolve_pilot_identities(
    elements: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Resolve the governed pilot identities in the bound revision."""
    diagnostics: list[str] = []
    by_id = _elements_by_id(elements)
    scope_element = _by_short(elements, PILOT_SCOPE_RECORD)
    definition_element = _by_short(elements, PILOT_DEFINITION)
    requirement_ids: list[tuple[str, str]] = []
    for short in PILOT_REQUIREMENT_SHORTS:
        match = _by_short(elements, short)
        if match is None:
            diagnostics.append(f"requirement usage {short!r} is absent or ambiguous")
            continue
        requirement_ids.append((short, str(match["@id"])))
    bench_definitions = [
        e
        for e in elements
        if str(e.get("declaredName") or "") == BENCH_DEFINITION_NAME
        and str(e.get("@type")) == "PartDefinition"
    ]
    bench_definition_id: str | None = None
    if len(bench_definitions) == 1:
        bench_definition_id = str(bench_definitions[0]["@id"])
    elif len(bench_definitions) > 1:
        diagnostics.append(f"ambiguous {BENCH_DEFINITION_NAME} definition identity")
    else:
        diagnostics.append(f"{BENCH_DEFINITION_NAME} definition is absent")
    return {
        "scope_element_id": str(scope_element["@id"]) if scope_element else None,
        "definition_id": str(definition_element["@id"]) if definition_element else None,
        "requirement_target_ids": tuple(sorted(rid for _, rid in requirement_ids)),
        "requirement_shorts_by_id": {
            rid: short for short, rid in requirement_ids
        },
        "bench_definition_id": bench_definition_id,
        "diagnostics": diagnostics,
    }


def _objective_targets(
    elements: Sequence[Mapping[str, Any]],
    usage_id: str,
    definition_id: str,
    requirement_short_by_id: Mapping[str, str],
) -> tuple[tuple[str, ...], tuple[str, ...], list[str]]:
    """Inherited objective/verify witness path: usage -> definition -> objective
    -> RequirementVerificationMembership -> (reference shadow) -> requirement.

    Returns (requirement target ids, witness ids, diagnostics). The witness
    path is returned in full; no direct fabricated membership is implied
    (UG-07).
    """
    diagnostics: list[str] = []
    by_id = _elements_by_id(elements)
    usage = by_id.get(usage_id)
    if usage is None:
        return (), (), [f"usage {usage_id!r} is absent"]
    if definition_id not in _generalization_parents(usage_id, [dict(e) for e in elements]):
        return (), (), [
            f"usage {usage_id!r} does not specialize the declared definition; "
            "inherited witness path is broken"
        ]
    objective_ids: list[str] = []
    for relationship in _memberships_referencing(by_id, "ObjectiveMembership", definition_id):
        objective_ids.extend(_refs(relationship.get("memberElement")))
    if not objective_ids:
        diagnostics.append("definition has no objective membership")
    targets: list[str] = []
    witnesses: list[str] = []
    for objective_id in objective_ids:
        for relationship in _memberships_referencing(
            by_id, "RequirementVerificationMembership", objective_id
        ):
            witness_id = str(relationship.get("@id") or "")
            members = _refs(relationship.get("memberElement")) or _refs(
                relationship.get("verifiedRequirement")
            )
            for member in members:
                resolved = _resolve_reference_shadow(by_id, member)
                short = requirement_short_by_id.get(resolved)
                if short is None:
                    declared = by_id.get(resolved) or {}
                    short = str(declared.get("declaredShortName") or "")
                if short in PILOT_REQUIREMENT_SHORTS:
                    targets.append(resolved)
                    witnesses.append(witness_id)
                else:
                    diagnostics.append(
                        f"objective witness {witness_id} does not resolve to a pinned "
                        "requirement usage"
                    )
    return tuple(sorted(set(targets))), tuple(witnesses), diagnostics


def _memberships_referencing(
    by_id: Mapping[str, Mapping[str, Any]], membership_type: str, owner_id: str
) -> list[Mapping[str, Any]]:
    """Memberships of one type owned by ``owner_id``.

    Representation-tolerant: matches the owned-relationship listing and the
    flat reference shape (``owningRelatedElement``/``owner``), mirroring the
    lane B traversal families without hard-coding one serializer form.
    """
    found: list[Mapping[str, Any]] = []
    owner = by_id.get(owner_id)
    if owner is not None:
        for relationship in _owned_relationships(by_id, owner):
            if str(relationship.get("@type")) == membership_type:
                found.append(relationship)
    for element in by_id.values():
        if str(element.get("@type")) != membership_type:
            continue
        if element in found:
            continue
        owners = set(_refs(element.get("owningRelatedElement"))) | set(
            _refs(element.get("owner"))
        )
        if owner_id in owners:
            found.append(element)
    return found


def _resolve_reference_shadow(
    by_id: Mapping[str, Mapping[str, Any]], element_id: str, *, depth: int = 3
) -> str:
    """Follow ReferenceSubsetting to the declared feature (reference shadows)."""
    current = element_id
    for _ in range(depth):
        element = by_id.get(current)
        if element is None:
            return current
        referenced = []
        for relationship in _owned_relationships(by_id, element):
            if str(relationship.get("@type")) == "ReferenceSubsetting":
                referenced.extend(
                    _refs(relationship.get("referencedFeature"))
                    or _refs(relationship.get("subsettedFeature"))
                )
        if not referenced or referenced[0] == current:
            return current
        current = referenced[0]
    return current


def _owned_relationships(
    by_id: Mapping[str, Mapping[str, Any]], owner: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    return [
        by_id[str(reference.get("@id"))]
        for reference in owner.get("ownedRelationship") or []
        if str(reference.get("@id")) in by_id
    ]


def build_usage_bindings(
    elements: Sequence[Mapping[str, Any]],
    *,
    definition_id: str | None,
    requirement_short_by_id: Mapping[str, str],
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    """Bind the declared scope usages via Lane B primitives and enrich with
    the inherited objective witness path and metadata expectations."""
    diagnostics: list[str] = []
    declared = {
        "scope_usages": list(PILOT_SCOPE_USAGES),
        "definition_short_name": PILOT_DEFINITION,
    }
    binding = bind_pilot_usages([dict(e) for e in elements], declared)
    diagnostics.extend(binding.diagnostics)
    bindings: dict[str, Mapping[str, Any]] = {}
    element_by_explicit: dict[str, Mapping[str, Any]] = {}
    for usage in binding.usages:
        element_by_explicit[usage.explicit_id] = {
            "@id": usage.element_id,
            "@type": "VerificationCaseUsage",
        }
        objective_targets: tuple[str, ...] = ()
        objective_witnesses: tuple[str, ...] = ()
        if definition_id is not None:
            objective_targets, objective_witnesses, objective_diagnostics = (
                _objective_targets(
                    elements, usage.element_id, definition_id, requirement_short_by_id
                )
            )
            diagnostics.extend(objective_diagnostics)
        bindings[usage.explicit_id] = {
            "element_id": usage.element_id,
            "resolution_level": usage.resolution_level,
            "element_type": "VerificationCaseUsage",
            "subject_members": usage.subject_members,
            "metadata_owners": usage.method_metadata_owners,
            "objective_targets": objective_targets,
            "objective_witnesses": objective_witnesses,
            "expected_kind_values": ("test", "analyze"),
        }
    for usage_id in PILOT_SCOPE_USAGES:
        if usage_id not in bindings:
            diagnostics.append(
                f"declared scope usage {usage_id!r} is unresolved in the bound revision"
            )
    # Definition-level: action metadata (observed) and declared kinds (expected).
    if definition_id is not None:
        by_id = _elements_by_id(elements)
        actions: dict[str, str] = {}
        for relationship in _owned_relationships(by_id, by_id[definition_id]):
            member_ids = _refs(relationship.get("memberElement"))
            for member_id in member_ids:
                member = by_id.get(member_id)
                if member is None or str(member.get("@type")) != "ActionUsage":
                    continue
                name = str(member.get("declaredName") or "")
                if name:
                    actions[name] = member_id
        observed: dict[str, str] = {}
        for action_name, action_id in actions.items():
            metadata = _metadata_witnesses(action_id, [dict(e) for e in elements])
            if metadata:
                observed[action_name] = metadata[0]
            else:
                diagnostics.append(
                    f"definition action {action_name!r} has no metadata witness"
                )
        bindings[f"definition:{definition_id}"] = {
            "element_id": definition_id,
            "action_metadata": {
                "expected": {
                    name: kinds for name, kinds in PILOT_DEFINITION_ACTION_KINDS.items()
                },
                "observed": observed,
            },
        }
    return bindings, diagnostics


# ---------------------------------------------------------------------------
# Evidence-branch readers
# ---------------------------------------------------------------------------


def load_campaign_manifest(source: FileSource) -> tuple[Mapping[str, Any] | None, list[str]]:
    blob = source.read_bytes(MANIFEST_PATH)
    if blob is None:
        return None, [f"{MANIFEST_PATH} is absent at the evaluated revision"]
    try:
        manifest = json.loads(blob)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return None, [f"{MANIFEST_PATH} is unreadable: {error}"]
    if not isinstance(manifest, Mapping):
        return None, [f"{MANIFEST_PATH} is not a JSON object"]
    return manifest, []


def load_records(
    source: FileSource, manifest: Mapping[str, Any] | None
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    records: dict[str, Mapping[str, Any]] = {}
    diagnostics: list[str] = []
    if manifest is None:
        return records, diagnostics
    for profile in sorted((manifest.get("profiles") or {}).keys()):
        entry = (manifest.get("profiles") or {}).get(profile) or {}
        path = str(entry.get("path") or "")
        blob = source.read_bytes(
            f"{BENCH_ROOT}/{path}" if path else path
        )
        if blob is None:
            diagnostics.append(f"record for profile {profile!r} is absent from storage")
            continue
        try:
            record = json.loads(blob)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            diagnostics.append(f"record for profile {profile!r} is unreadable: {error}")
            continue
        if isinstance(record, Mapping):
            records[profile] = record
        else:
            diagnostics.append(f"record for profile {profile!r} is not a JSON object")
    return records, diagnostics


def _decode_decision(blob: bytes) -> tuple[Mapping[str, Any] | None, str | None]:
    """Decode and schema-check one acceptance decision record.

    Returns (record, error). The schema is the one declared by
    ``docs/method-conformance/acceptance-policy.md``.
    """
    import yaml

    try:
        value = yaml.safe_load(blob)
    except yaml.YAMLError as error:  # pragma: no cover - defensive
        return None, f"unparseable decision record: {error}"
    if not isinstance(value, Mapping):
        return None, "decision record is not a mapping"
    required = (
        "schema",
        "policy_id",
        "decision_id",
        "campaign_scope",
        "covered_profiles",
        "outcome",
        "decider",
        "decision_date",
    )
    for field_name in required:
        if not value.get(field_name):
            return None, f"decision record missing {field_name!r}"
    if str(value.get("schema")) != "de4sdv.acceptance-decision.v1":
        return None, f"unknown decision schema {value.get('schema')!r}"
    if str(value.get("outcome")) not in {"accepted", "rejected"}:
        return None, f"invalid decision outcome {value.get('outcome')!r}"
    return value, None


def scan_acceptance_registry(source: FileSource) -> RegistryScan:
    """Scan the pinned decision registry (acceptance-policy.md semantics)."""
    if not source.exists(REGISTRY_PATH):
        listing = source.list_files(REGISTRY_PATH)
        if listing is None:
            return RegistryScan(
                path=REGISTRY_PATH,
                state="missing",
                diagnostics=(
                    f"decision registry {REGISTRY_PATH!r} is missing; a missing "
                    "registry is not a known-empty registry and no FAIL may be "
                    "derived from an incompletely scanned registry",
                ),
            )
    listing = source.list_files(REGISTRY_PATH)
    if listing is None:
        return RegistryScan(
            path=REGISTRY_PATH,
            state="missing",
            diagnostics=(f"decision registry {REGISTRY_PATH!r} is missing",),
        )
    decisions: list[Mapping[str, Any]] = []
    for relative in listing:
        if not relative.endswith((".yaml", ".yml", ".json")):
            continue
        blob = source.read_bytes(relative)
        if blob is None:
            return RegistryScan(
                path=REGISTRY_PATH,
                state="unreadable",
                diagnostics=(f"registry entry {relative!r} could not be read",),
            )
        if relative.endswith(".json"):
            try:
                record = json.loads(blob)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                return RegistryScan(
                    path=REGISTRY_PATH,
                    state="invalid-record",
                    diagnostics=(f"registry entry {relative!r} is invalid: {error}",),
                )
            record, error = (record, None) if isinstance(record, Mapping) else (None, "not a mapping")
            if error:
                return RegistryScan(
                    path=REGISTRY_PATH,
                    state="invalid-record",
                    diagnostics=(f"registry entry {relative!r}: {error}",),
                )
        else:
            record, error = _decode_decision(blob)
            if error:
                return RegistryScan(
                    path=REGISTRY_PATH,
                    state="invalid-record",
                    diagnostics=(f"registry entry {relative!r}: {error}",),
                )
        record = dict(record or {})
        record["_path"] = relative
        decisions.append(record)
    # Supersession resolution: cycles are a policy-integrity violation.
    by_id = {str(d.get("decision_id")): d for d in decisions}
    superseded: set[str] = set()
    for decision in decisions:
        for target in decision.get("supersedes") or ():
            if str(target) in by_id:
                superseded.add(str(target))
    # cycle detection over supersession edges
    colour: dict[str, int] = {}
    cycle_found: list[str] | None = None

    def visit(node: str, stack: list[str]) -> None:
        nonlocal cycle_found
        colour[node] = 1
        stack.append(node)
        for target in by_id.get(node, {}).get("supersedes") or ():
            target = str(target)
            if target not in by_id:
                continue
            if colour.get(target) == 1:
                cycle_found = stack[stack.index(target):] + [target]
                return
            if colour.get(target) is None:
                visit(target, stack)
                if cycle_found:
                    return
        stack.pop()
        colour[node] = 2

    for decision_id in by_id:
        if colour.get(decision_id) is None:
            visit(decision_id, [])
            if cycle_found:
                break
    if cycle_found:
        return RegistryScan(
            path=REGISTRY_PATH,
            state="invalid-record",
            diagnostics=(
                "supersession cycle: " + " -> ".join(cycle_found),
            ),
        )
    effective = [
        decision for decision in decisions if str(decision.get("decision_id")) not in superseded
    ]
    return RegistryScan(
        path=REGISTRY_PATH,
        state="scanned-clean",
        decisions=tuple(effective),
        diagnostics=(f"registry scanned completely; {len(effective)} effective decision(s)",),
    )


# ---------------------------------------------------------------------------
# Conservative scope equality (candidate-declared tested-scope identity)
# ---------------------------------------------------------------------------


def _claimed_input_paths(
    tested_source: FileSource,
) -> tuple[list[str], list[str]]:
    """Enumerate the tested-input set at the declared tested head.

    Returns (paths, diagnostics). The rule is the pinned, provenance-annotated
    tested-input rule; diagnostics explain missing pieces.
    """
    diagnostics: list[str] = []
    paths: list[str] = []
    for relative in TESTED_INPUT_RULE["top_level"]:
        full = f"{BENCH_ROOT}/{relative}"
        if tested_source.exists(full):
            paths.append(full)
        else:
            diagnostics.append(f"tested input {relative!r} is absent at the tested head")
    for root in TESTED_INPUT_RULE["recursive_roots"]:
        listing = tested_source.list_files(f"{BENCH_ROOT}/{root}")
        if listing is None:
            diagnostics.append(f"tested input root {root!r} is absent at the tested head")
            continue
        paths.extend(listing)
    for root in TESTED_INPUT_RULE["optional_recursive_roots"]:
        listing = tested_source.list_files(f"{BENCH_ROOT}/{root}")
        if listing:
            paths.extend(listing)
    return sorted(set(paths)), diagnostics


def reconstruct_manifest_sha256(
    input_map: Mapping[str, str], profile: str | None = None
) -> str:
    """Canonical execution-identity reconstruction (sha256 over the digest map).

    Mirrors the pinned identity computation: sorted-key compact JSON of
    path->sha256 plus the virtual inherited entry (and the profile entry for
    the override variant). This is the C-owned reconstruction rule; its
    reproduction against the retained records is verified by the runner.
    """
    data = dict(input_map)
    data[TESTED_INPUT_RULE["virtual_inherited_key"]] = TESTED_INPUT_RULE[
        "virtual_inherited_value"
    ]
    if profile is not None:
        data[TESTED_INPUT_RULE["profile_key"]] = profile
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def compare_scope_equality(
    *,
    record: Mapping[str, Any],
    profile: str,
    declared_execution_head: str | None,
    candidate_source: FileSource,
    tested_source: FileSource,
) -> ScopeEqualityComparison:
    """Per-profile conservative-scope-equality comparison.

    Every pinned field is compared; none may be skipped. Missing information
    on either side is INDETERMINATE material; a known mismatch is FAIL
    material; only full, established equality is PASS material.
    """
    provenance = record.get("provenance") or {}
    if not isinstance(provenance, Mapping):
        return ScopeEqualityComparison(
            status="indeterminate",
            compared_fields=(),
            missing_fields=("provenance",),
            diagnostics=("record carries no provenance object",),
        )
    compared: list[str] = []
    mismatched: list[str] = []
    missing: list[str] = []
    diagnostics: list[str] = []

    def compare_direct(field: str, candidate_value: str | None) -> None:
        compared.append(field)
        record_value = provenance.get(field)
        if record_value is None or candidate_value is None:
            missing.append(field)
            return
        if str(record_value) != str(candidate_value):
            mismatched.append(field)
            diagnostics.append(
                f"{field}: record {record_value!r} != candidate {candidate_value!r}"
            )

    # 1. repository_head vs the candidate's declared tested head.
    compare_direct("repository_head", declared_execution_head)

    # 2. Candidate runtime identity artifacts (lock file + matrix config).
    lock_rel = f"{BENCH_ROOT}/runtime-lock.yaml"
    lock_blob = candidate_source.read_bytes(lock_rel)
    lock: Mapping[str, Any] | None = None
    if lock_blob is None:
        missing.append("runtime-lock.yaml")
        diagnostics.append("candidate revision has no runtime-lock.yaml")
    else:
        try:
            import yaml

            lock_value = yaml.safe_load(lock_blob)
            lock = lock_value if isinstance(lock_value, Mapping) else None
        except Exception:  # pragma: no cover - defensive
            lock = None
        if lock is None:
            missing.append("runtime-lock.yaml (unparseable)")
    matrix_blob = candidate_source.read_bytes(
        f"{BENCH_ROOT}/config/scenario-009d-conscious-override-matrix.yaml"
    )
    if matrix_blob is None:
        missing.append("override_matrix_sha256 (config unavailable)")
    else:
        compare_direct(
            "override_matrix_sha256", hashlib.sha256(matrix_blob).hexdigest()
        )
    if lock_blob is not None:
        compare_direct(
            "runtime_lock_sha256", hashlib.sha256(lock_blob).hexdigest()
        )
    container = (lock or {}).get("container") or {}
    if isinstance(container, Mapping):
        compare_direct("image_digest", str(container.get("index_digest") or "") or None)
        platform = str(container.get("platform") or "")
        arch = _PLATFORM_ARCH_NORMALIZATION.get(platform.split("/")[-1], platform.split("/")[-1])
        compare_direct("host_arch", arch or None)
    else:
        missing.append("image_digest (lock container pin missing)")
        missing.append("host_arch (lock container pin missing)")
    map_pin = (lock or {}).get("map") or {}
    if isinstance(map_pin, Mapping) and map_pin.get("sha256"):
        compare_direct("map_digest", f"sha256:{map_pin['sha256']}")
    else:
        missing.append("map_digest (lock map pin missing)")
    inherited = (lock or {}).get("inherited_009a") or {}
    record_inherited = provenance.get("inherited_009a") or {}
    if not isinstance(record_inherited, Mapping):
        record_inherited = {}

    def compare_inherited(field: str, candidate_value: str | None) -> None:
        compared.append(field)
        record_value = record_inherited.get(field.split(".", 1)[1])
        if record_value is None or candidate_value is None:
            missing.append(field)
            return
        if str(record_value) != str(candidate_value):
            mismatched.append(field)
            diagnostics.append(
                f"{field}: record {record_value!r} != candidate {candidate_value!r}"
            )

    if isinstance(inherited, Mapping) and inherited:
        compare_inherited(
            "inherited_009a.execution_manifest_sha256",
            str(inherited.get("execution_manifest_sha256") or "") or None,
        )
        compare_inherited(
            "inherited_009a.runtime_lock_sha256",
            str(inherited.get("runtime_lock_sha256") or "") or None,
        )
    else:
        missing.append("inherited_009a.execution_manifest_sha256")
        missing.append("inherited_009a.runtime_lock_sha256")
        diagnostics.append("candidate revision lock carries no inherited_009a pins")

    # 3. Execution-identity manifests: reconstruct at the declared tested head
    #    with the pinned rule; the candidate side must reproduce the recorded
    #    identity over an unchanged, fully present tested-input set.
    input_paths, input_diagnostics = _claimed_input_paths(tested_source)
    if not input_paths:
        missing.append("execution_manifest_sha256 (tested input set unavailable)")
        missing.append("override_execution_manifest_sha256 (tested input set unavailable)")
        diagnostics.extend(input_diagnostics)
    else:
        input_map: dict[str, str] = {}
        absent_at_candidate: list[str] = []
        changed: list[str] = []
        for relative in input_paths:
            tested_blob = tested_source.read_bytes(relative)
            candidate_blob = candidate_source.read_bytes(relative)
            if candidate_blob is None:
                absent_at_candidate.append(relative)
                continue
            if tested_blob is None:
                continue
            input_map[relative.replace(f"{BENCH_ROOT}/", "")] = hashlib.sha256(
                tested_blob
            ).hexdigest()
            if hashlib.sha256(candidate_blob).hexdigest() != hashlib.sha256(
                tested_blob
            ).hexdigest():
                changed.append(relative)
        for field, is_override in (
            ("execution_manifest_sha256", False),
            ("override_execution_manifest_sha256", True),
        ):
            compared.append(field)
            record_value = provenance.get(field)
            if input_diagnostics or absent_at_candidate or changed:
                mismatched.append(field)
                detail = []
                if input_diagnostics:
                    detail.extend(input_diagnostics)
                if absent_at_candidate:
                    detail.append(
                        "tested inputs absent at the candidate revision: "
                        f"{sorted(absent_at_candidate)}"
                    )
                if changed:
                    detail.append(
                        "identity inputs changed between the declared tested head "
                        f"and the candidate revision: {sorted(changed)}"
                    )
                diagnostics.append(f"{field}: " + "; ".join(detail))
                continue
            if record_value is None:
                missing.append(field)
                continue
            candidate_value = reconstruct_manifest_sha256(
                input_map, profile if is_override else None
            )
            if str(record_value) != candidate_value:
                mismatched.append(field)
                diagnostics.append(
                    f"{field}: record {record_value!r} != reconstructed candidate "
                    f"identity {candidate_value!r}"
                )

    if mismatched:
        return ScopeEqualityComparison(
            status="mismatch",
            compared_fields=tuple(compared),
            mismatched_fields=tuple(mismatched),
            missing_fields=tuple(missing),
            diagnostics=tuple(diagnostics),
        )
    if missing:
        return ScopeEqualityComparison(
            status="indeterminate",
            compared_fields=tuple(compared),
            missing_fields=tuple(missing),
            diagnostics=tuple(diagnostics),
        )
    return ScopeEqualityComparison(
        status="equal",
        compared_fields=tuple(compared),
        diagnostics=tuple(diagnostics),
    )


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


class PolicyClosureError(RuntimeError):
    """Candidate policy-bearing closure diverges from the approved contract.

    A migration candidate is not its own judge (MC-23): the evaluation is
    refused instead of silently using candidate-modified rules.
    """

    def __init__(self, mismatches: Sequence[str]) -> None:
        self.mismatches = tuple(mismatches)
        super().__init__(
            "candidate policy-bearing closure differs from the approved contract: "
            + "; ".join(mismatches)
        )


@dataclass(frozen=True)
class PilotAssembly:
    """Assembled pilot evaluation inputs with assembly diagnostics."""

    contract: MethodContract
    context: "EvaluationContext"
    closure_mismatches: tuple[str, ...]
    diagnostics: tuple[str, ...]


def assemble_pilot_context(
    *,
    approved_contract: MethodContract,
    elements: Sequence[Mapping[str, Any]],
    revision: RevisionIdentity,
    candidate_source: FileSource,
    tested_source: FileSource | None,
    candidate_scope_declared: bool | None = None,
) -> PilotAssembly:
    """Assemble the typed evaluation context for the governed pilot."""
    diagnostics: list[str] = []
    identities = resolve_pilot_identities(elements)
    diagnostics.extend(identities["diagnostics"])
    closure = decode_model_obligation_closure(elements)
    closure_mismatches = tuple(
        verify_candidate_policy_closure(approved_contract, closure)
    )
    scope_item, declared_profiles, scope_diagnostics = decode_declared_tested_scope(
        elements
    )
    diagnostics.extend(scope_diagnostics)
    declared_head: str | None = None
    if scope_item is not None:
        by_id = _elements_by_id(elements)
        _, declared_head = _member_text_value(by_id, scope_item, "executionHead")

    usage_bindings, usage_diagnostics = build_usage_bindings(
        elements,
        definition_id=identities["definition_id"],
        requirement_short_by_id=identities["requirement_shorts_by_id"],
    )
    diagnostics.extend(usage_diagnostics)

    manifest, manifest_diagnostics = load_campaign_manifest(candidate_source)
    diagnostics.extend(manifest_diagnostics)
    records, record_diagnostics = load_records(candidate_source, manifest)
    diagnostics.extend(record_diagnostics)
    registry_scan = scan_acceptance_registry(candidate_source)

    scope_equality: dict[str, ScopeEqualityComparison] = {}
    if tested_source is not None and manifest is not None:
        for profile in PILOT_PROFILES:
            record = records.get(profile)
            if record is None:
                continue
            scope_equality[profile] = compare_scope_equality(
                record=record,
                profile=profile,
                declared_execution_head=declared_head,
                candidate_source=candidate_source,
                tested_source=tested_source,
            )

    if candidate_scope_declared is None:
        scope_declared: bool | None
        scope_record = _by_short(elements, PILOT_SCOPE_RECORD)
        if scope_record is None:
            scope_declared = None
            diagnostics.append(
                "candidate declares no pilot scope record; applicability unresolved"
            )
        else:
            by_id = _elements_by_id(elements)
            _, increment_value = _member_text_value(by_id, scope_record, "incrementId")
            scope_declared = increment_value == PILOT_INCREMENT
            if not scope_declared:
                diagnostics.append(
                    f"candidate scope record declares increment {increment_value!r}"
                )
    else:
        scope_declared = candidate_scope_declared

    declared_profile_set = set(declared_profiles)
    if declared_profiles and declared_profile_set != set(PILOT_PROFILES):
        diagnostics.append(
            "model tested-scope declaration differs from the pinned profile set: "
            f"{sorted(declared_profile_set)}"
        )

    context = EvaluationContext(
        revision=revision,
        elements=tuple(elements),
        scope=DeclaredEvaluationScope(
            scope_id=PILOT_SCOPE_RECORD,
            increment_id=PILOT_INCREMENT,
            usage_ids=PILOT_SCOPE_USAGES,
            contribution_ids=frozenset({PILOT_SCOPE_RECORD}),
            profiles=PILOT_PROFILES,
            scope_element_id=identities["scope_element_id"],
        ),
        usage_bindings=usage_bindings,
        definition_id=identities["definition_id"],
        requirement_target_ids=identities["requirement_target_ids"],
        bench_definition_id=identities["bench_definition_id"],
        artifact_source=candidate_source,
        bench_root=BENCH_ROOT,
        campaign_manifest=manifest,
        records=records,
        expected_dispositions=dict(PILOT_EXPECTED_DISPOSITIONS),
        registry_scan=registry_scan,
        scope_equality=scope_equality,
        pilot_scope_declared=scope_declared,
        candidate_missing_inputs=tuple(
            sorted(set(usage_diagnostics + manifest_diagnostics + record_diagnostics))
        ),
        diagnostics=tuple(diagnostics),
    )
    return PilotAssembly(
        contract=approved_contract,
        context=context,
        closure_mismatches=closure_mismatches,
        diagnostics=tuple(diagnostics),
    )


def refusal_diagnostics(mismatches: Sequence[str]) -> list[str]:
    """Diagnostics for a refused evaluation (kept for reporting parity)."""
    return [
        "governing-policy mismatch: candidate policy-bearing closure differs from "
        "the approved contract; explicit method-migration decision required "
        "(no self-acceptance)",
        *mismatches,
    ]


__all__ = [
    "BENCH_ROOT",
    "MANIFEST_PATH",
    "PILOT_DEFINITION",
    "PILOT_EXPECTED_DISPOSITIONS",
    "PILOT_INCREMENT",
    "PILOT_PROFILES",
    "PILOT_REQUIREMENT_SHORTS",
    "PILOT_SCOPE_RECORD",
    "PILOT_SCOPE_USAGES",
    "DirectoryFileSource",
    "GitRevisionFileSource",
    "PolicyClosureError",
    "PilotAssembly",
    "SCOPE_EQUALITY_FIELDS",
    "TESTED_INPUT_RULE",
    "assemble_pilot_context",
    "build_usage_bindings",
    "compare_scope_equality",
    "decode_approved_contract",
    "decode_declared_tested_scope",
    "decode_model_obligation_closure",
    "load_approved_contract_from_yaml",
    "load_campaign_manifest",
    "load_records",
    "reconstruct_manifest_sha256",
    "resolve_pilot_identities",
    "scan_acceptance_registry",
]
