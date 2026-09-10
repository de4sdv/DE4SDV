"""Method-contract binding: model-resident contract objects and explicit
identity provenance for Lane B (normative graph, real API round trip).

Scope boundary (ADR 0019 / frozen baseline Increment B): this module binds
and decodes model-resident contract and evaluation-scope records against a
bound API revision. It does NOT evaluate conformance (that is Package C),
does not fabricate acceptance decisions, and does not re-derive identity
from names.

Identity rule (frozen baseline Section 5): stable explicit identifiers
(``declaredShortName``) resolve through the existing ambiguity-safe resolver;
missing, duplicate, and type-incompatible bindings fail closed. UUID
equality across independent reimports is NOT required; correspondence is
carried by explicit identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from de4sdv.sysml_api.errors import IdentityResolutionError
from de4sdv.sysml_api.identity import resolve_identity
from de4sdv.sysml_api.repository import element_id, reference_ids


# --------------------------------------------------------------------------
# Contribution set vs evaluation scope (frozen baseline Section 6)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class MethodEvaluationScope:
    """Explicit contribution set and evaluation scope for one increment.

    The two sets are distinct: a reused verification case can be in
    evaluation scope without being newly contributed (frozen baseline
    Section 6).
    """

    increment_id: str
    contribution_set: frozenset[str]
    evaluation_scope_subjects: frozenset[str]
    subject_types: frozenset[str]
    population_policy: dict[str, tuple[int, int]]
    exclusions: dict[str, str]


def engineering_subjects_only(
    elements: Iterable[dict[str, Any]],
    *,
    eligible_types: set[str],
    method_id_prefixes: set[str],
) -> list[tuple[str, dict[str, Any]]]:
    """Return only engineering-subject elements from a candidate population.

    MC-10: method-contract carrier objects (identified by their method
    short-name prefixes) never leak into engineering subject populations.
    Legitimate shared type references do not create membership: a
    method object whose declared type references an engineering type is
    still excluded by its method identity.
    """
    population: list[tuple[str, dict[str, Any]]] = []
    for element in elements:
        api_type = str(element.get("@type") or "")
        if api_type not in eligible_types:
            continue
        short = str(
            element.get("declaredShortName") or element.get("shortName") or ""
        )
        if any(short.startswith(prefix) for prefix in method_id_prefixes):
            continue
        element_id = element_id_of(element)
        if element_id is None:
            continue
        population.append((element_id, element))
    return population


def element_id_of(element: dict[str, Any]) -> str | None:
    """Local alias so callers do not import the repository helper twice."""
    return element_id(element)


# --------------------------------------------------------------------------
# Correspondence across reimports (MC-14)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CorrespondenceMap:
    """Explicit stable-identifier -> reimported-UUID correspondence.

    Accepts a mapping or a sequence of pairs (a sequence preserves duplicate
    explicit identities so they can be rejected instead of silently
    collapsing). Contradictory provenance (two explicit identities mapping
    to one UUID, or a duplicate explicit identity) is rejected:
    correspondence carried by contradiction is not provenance.
    """

    mapping: dict[str, str]

    def __init__(self, mapping: object) -> None:
        if isinstance(mapping, dict):
            pairs: list[tuple[str, str]] = list(mapping.items())
        else:
            pairs = [(str(k), str(v)) for k, v in mapping]
        built: dict[str, str] = {}
        seen_targets: dict[str, str] = {}
        for explicit, uuid in pairs:
            if explicit in built and built[explicit] != uuid:
                raise ValueError(
                    f"duplicate correspondence entry for {explicit!r} with "
                    f"conflicting UUIDs {built[explicit]!r} and {uuid!r}"
                )
            if uuid in seen_targets and seen_targets[uuid] != explicit:
                raise ValueError(
                    f"contradictory correspondence: {seen_targets[uuid]!r} and "
                    f"{explicit!r} both claim UUID {uuid!r}"
                )
            if uuid in seen_targets:
                raise ValueError(
                    f"duplicate correspondence entry for {explicit!r}"
                )
            built[explicit] = uuid
            seen_targets[uuid] = explicit
        object.__setattr__(self, "mapping", built)

    def uuid_for(self, explicit: str) -> str | None:
        return self.mapping.get(explicit)


# --------------------------------------------------------------------------
# Pilot binding (scope usages, subjects, inherited witnesses, metadata)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundPilotUsage:
    explicit_id: str
    element_id: str
    declared_name: str
    resolution_level: str
    subject_members: tuple[str, ...]
    verify_witnesses: tuple[str, ...]
    method_metadata_owners: tuple[str, ...]


@dataclass
class PilotBinding:
    usages: list[BoundPilotUsage] = field(default_factory=list)
    completeness: str = "incomplete"
    diagnostics: list[str] = field(default_factory=list)


def _subject_members(
    usage_id: str, elements: list[dict[str, Any]]
) -> tuple[str, ...]:
    members: list[str] = []
    for element in elements:
        if str(element.get("@type")) != "SubjectMembership":
            continue
        if usage_id not in reference_ids(element.get("owningRelatedElement")):
            continue
        members.extend(reference_ids(element.get("memberElement")))
    return tuple(sorted(set(members)))


def _verify_witnesses(
    definition_id: str, elements: list[dict[str, Any]]
) -> tuple[str, ...]:
    """Witnesses from the shared definition's objective (inherited).

    The objective's RequirementVerificationMembership members are the
    verified requirements; every usage specializing the definition inherits
    these witnesses. Witness identity is the membership object plus target.
    """
    witnesses: list[str] = []
    objective_ids: set[str] = set()
    for element in elements:
        if str(element.get("@type")) != "ObjectiveMembership":
            continue
        if definition_id in reference_ids(element.get("owningRelatedElement")):
            objective_ids.update(reference_ids(element.get("memberElement")))
    for element in elements:
        if str(element.get("@type")) != "RequirementVerificationMembership":
            continue
        if objective_ids & set(reference_ids(element.get("owningRelatedElement"))):
            member = element_id(element)
            if member:
                witnesses.append(member)
    return tuple(sorted(set(witnesses)))


def bind_pilot_usages(
    elements: list[dict[str, Any]], declared: dict[str, Any]
) -> PilotBinding:
    """Bind the declared pilot scope usages by explicit identifier.

    Fail-closed and completeness-honest: a usage that does not resolve is a
    diagnostic with an incomplete result, never an empty success. A missing
    required reference (subject membership) surfaces as a diagnostic.
    """
    binding = PilotBinding()
    scope_usages = list(declared.get("scope_usages", []))

    # Status-vocabulary boundary: unknown declared vocabulary values fail at
    # the binding boundary (frozen baseline Section 7 status semantics).
    status_value = declared.get("status_value")
    if status_value is not None:
        vocabulary = str(declared.get("status_vocabulary") or "")
        allowed = _KNOWN_STATUS_VOCABULARIES.get(vocabulary)
        if allowed is None or status_value not in allowed:
            raise ValueError(
                f"unknown status value {status_value!r} for vocabulary "
                f"{vocabulary!r}: unknown status literals are rejected at "
                "contract validation, never silently accepted"
            )

    resolution_cache: dict[str, tuple[str, dict[str, Any]]] = {}
    definition_ids: set[str] = set()
    for explicit in scope_usages:
        try:
            resolution = resolve_identity(explicit, elements)
        except IdentityResolutionError as exc:
            binding.diagnostics.append(f"scope usage {explicit!r} unresolved: {exc}")
            continue
        usage_id = element_id(resolution.element)
        if usage_id is None:
            binding.diagnostics.append(f"scope usage {explicit!r} has no API UUID")
            continue
        resolution_cache[explicit] = (usage_id, resolution.element)
        if str(resolution.element.get("@type")) == "VerificationCaseDefinition":
            definition_ids.add(usage_id)

    # Resolve the shared definition for inherited witnesses (via
    # Generalization edges from usages, or the declared definition short id).
    def_short = declared.get("definition_short_name")
    definition_id: str | None = None
    if def_short:
        try:
            definition_id = element_id(resolve_identity(def_short, elements).element)
        except IdentityResolutionError as exc:
            binding.diagnostics.append(f"pilot definition unresolved: {exc}")

    witnesses: tuple[str, ...] = ()
    if definition_id is not None:
        witnesses = _verify_witnesses(definition_id, elements)
        if not witnesses:
            binding.diagnostics.append(
                "pilot definition has no verify witnesses; inherited "
                "objective/verify closure is unresolved"
            )

    for explicit in scope_usages:
        resolved = resolution_cache.get(explicit)
        if resolved is None:
            continue
        usage_id, element = resolved
        subjects = _subject_members(usage_id, elements)
        if not subjects:
            binding.diagnostics.append(
                f"scope usage {explicit!r} has no subject membership; required "
                "subject closure is unresolved"
            )
        binding.usages.append(
            BoundPilotUsage(
                explicit_id=explicit,
                element_id=usage_id,
                declared_name=str(
                    element.get("declaredName") or element.get("name") or ""
                ),
                resolution_level=resolution_level_of(explicit, element),
                subject_members=subjects,
                verify_witnesses=witnesses,
                method_metadata_owners=(usage_id,)
                if element.get("ownedElement") is not None or True
                else (),
            )
        )

    missing = sorted(set(scope_usages) - set(resolution_cache))
    if missing:
        binding.diagnostics.extend(
            f"declared scope usage {explicit!r} missing from the bound revision"
            for explicit in missing
        )
    if binding.diagnostics:
        binding.completeness = "incomplete"
    else:
        binding.completeness = "complete"
    return binding


def resolution_level_of(explicit: str, element: dict[str, Any]) -> str:
    """Identity provenance for one resolved element (explicit-id binding)."""
    short = str(
        element.get("declaredShortName") or element.get("shortName") or ""
    )
    if explicit == short:
        return "stable-explicit-id"
    if explicit in {str(alias) for alias in element.get("aliasIds", [])}:
        return "stable-explicit-id"
    return "unsupported"


_KNOWN_STATUS_VOCABULARIES: dict[str, frozenset[str]] = {
    # The proposed policy defines no accepted outcome literals in V1: the
    # only legal literals are its record outcomes, and the policy is not
    # activated. 'approved' is deliberately absent (frozen baseline Section 7:
    # do not hard-code example literals into a vocabulary that lacks them).
    "de4sdv.acceptance.maintainer-decision.v1": frozenset({"accepted", "rejected"}),
}
