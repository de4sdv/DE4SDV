"""Deterministic method-conformance evaluator (Lane C).

Implements the frozen result algebra and the generic, phase-neutral evaluation
engine specified by ``docs/method-conformance/`` (conformance-baseline.md,
result-algebra.md, pilot-scope.md) under ADR 0019. Scope boundary:

- this module evaluates approved method contracts against one bound revision
  and explicitly typed supporting inputs; it performs no writes, no snapshot
  handling, and no delivery/PR composition (Package D);
- contract data comes from the approved specification (decoded by
  :mod:`de4sdv.semantic.method_pilot` or constructed by tests); the evaluator
  contains no phase-number branches and never reads candidate source text;
- every result satisfies the normative state/reason compatibility table;
  missing information is never turned into PASS or FAIL.

The engine is phase-neutral across P0-P12: phase identity is contract data
(the contract's phase literal), never an evaluator condition.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

# ---------------------------------------------------------------------------
# Result algebra (frozen: docs/method-conformance/result-algebra.md)
# ---------------------------------------------------------------------------

CONTRACT_UNAVAILABLE = "CONTRACT_UNAVAILABLE"
OUTSIDE_REQUESTED_SCOPE = "OUTSIDE_REQUESTED_SCOPE"
NOT_ATTEMPTED = "NOT_ATTEMPTED"
APPLICABILITY_UNRESOLVED = "APPLICABILITY_UNRESOLVED"
INPUT_UNAVAILABLE = "INPUT_UNAVAILABLE"
INVALID_CONTRACT = "INVALID_CONTRACT"
BINDING_MISMATCH = "BINDING_MISMATCH"
SCOPE_RESOLUTION_ERROR = "SCOPE_RESOLUTION_ERROR"
POPULATION_POLICY_VIOLATION = "POPULATION_POLICY_VIOLATION"
EVIDENCE_SCOPE_MISMATCH = "EVIDENCE_SCOPE_MISMATCH"
ACCEPTANCE_AUTHORITY_MISSING = "ACCEPTANCE_AUTHORITY_MISSING"
STALE_INPUT = "STALE_INPUT"
REQUIRED_RELATION_MISSING = "REQUIRED_RELATION_MISSING"
EXECUTION_FAILED = "EXECUTION_FAILED"
EVALUATOR_FAILURE = "EVALUATOR_FAILURE"
NOT_APPLICABLE_REASON = "NOT_APPLICABLE_REASON"

REASON_CODES: frozenset[str] = frozenset(
    {
        CONTRACT_UNAVAILABLE,
        OUTSIDE_REQUESTED_SCOPE,
        NOT_ATTEMPTED,
        APPLICABILITY_UNRESOLVED,
        INPUT_UNAVAILABLE,
        INVALID_CONTRACT,
        BINDING_MISMATCH,
        SCOPE_RESOLUTION_ERROR,
        POPULATION_POLICY_VIOLATION,
        EVIDENCE_SCOPE_MISMATCH,
        ACCEPTANCE_AUTHORITY_MISSING,
        STALE_INPUT,
        REQUIRED_RELATION_MISSING,
        EXECUTION_FAILED,
        EVALUATOR_FAILURE,
        NOT_APPLICABLE_REASON,
    }
)

NO_ELIGIBLE_SUBJECTS = "NO_ELIGIBLE_SUBJECTS"
EXPLICIT_DISPOSITION = "EXPLICIT_DISPOSITION"

PERMITTED_EMPTY_DISPOSITIONS: frozenset[str] = frozenset(
    {NO_ELIGIBLE_SUBJECTS, EXPLICIT_DISPOSITION}
)

COVERAGE_ASSESSED = "ASSESSED"
COVERAGE_UNASSESSED = "UNASSESSED"
STATE_COMPLETE = "COMPLETE"
STATE_INDETERMINATE = "INDETERMINATE"
STATE_ERROR = "ERROR"
VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_NOT_APPLICABLE = "NOT_APPLICABLE"

#: Normative state/reason compatibility table (single source of legality).
#: key: (coverage, state, verdict) -> {required_any_of, forbidden, exact?}
_COMPATIBILITY: dict[tuple[str, str | None, str | None], dict[str, Any]] = {
    (COVERAGE_ASSESSED, STATE_COMPLETE, VERDICT_PASS): {
        "required_any_of": frozenset(),
        "forbidden": frozenset(REASON_CODES),
        "empty_only": True,
    },
    (COVERAGE_ASSESSED, STATE_COMPLETE, VERDICT_FAIL): {
        "required_any_of": frozenset(
            {
                REQUIRED_RELATION_MISSING,
                EXECUTION_FAILED,
                EVIDENCE_SCOPE_MISMATCH,
                ACCEPTANCE_AUTHORITY_MISSING,
                POPULATION_POLICY_VIOLATION,
            }
        ),
        "forbidden": frozenset({CONTRACT_UNAVAILABLE, BINDING_MISMATCH}),
    },
    (COVERAGE_ASSESSED, STATE_COMPLETE, VERDICT_NOT_APPLICABLE): {
        "required_any_of": frozenset({NOT_APPLICABLE_REASON}),
        "forbidden": frozenset(REASON_CODES - {NOT_APPLICABLE_REASON}),
        "exactly_one_of": frozenset({NOT_APPLICABLE_REASON}),
    },
    (COVERAGE_ASSESSED, STATE_INDETERMINATE, None): {
        "required_any_of": frozenset(
            {APPLICABILITY_UNRESOLVED, INPUT_UNAVAILABLE, ACCEPTANCE_AUTHORITY_MISSING}
        ),
        "forbidden": frozenset(
            {OUTSIDE_REQUESTED_SCOPE, NOT_ATTEMPTED, CONTRACT_UNAVAILABLE, STALE_INPUT}
        ),
    },
    (COVERAGE_ASSESSED, STATE_ERROR, None): {
        "required_any_of": frozenset(
            {INVALID_CONTRACT, BINDING_MISMATCH, SCOPE_RESOLUTION_ERROR, EVALUATOR_FAILURE}
        ),
        "forbidden": frozenset({INPUT_UNAVAILABLE}),
    },
    (COVERAGE_UNASSESSED, None, None): {
        "required_any_of": frozenset(
            {CONTRACT_UNAVAILABLE, OUTSIDE_REQUESTED_SCOPE, NOT_ATTEMPTED}
        ),
        "forbidden": frozenset({STALE_INPUT}),
    },
}


class ResultValidationError(ValueError):
    """Illegal result-field combination; rejected before serialization (MC-38)."""

    def __init__(self, violations: Sequence[str]) -> None:
        self.violations = tuple(violations)
        super().__init__("; ".join(self.violations))


@dataclass(frozen=True)
class EvaluationResult:
    """One unit result with the frozen fields and reason legality.

    ``reason_codes`` carry the finite vocabulary; ``diagnostics`` carry
    machine-readable detail (including the PERMITTED_EMPTY sub-code for
    NOT_APPLICABLE results), never a second verdict channel.
    """

    unit_id: str
    coverage: str
    state: str | None
    verdict: str | None
    reason_codes: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    subject_id: str | None = None
    targets: tuple[str, ...] = ()
    witnesses: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    claim_boundary: str = ""

    def validate(self) -> None:
        violations: list[str] = []
        if self.coverage not in {COVERAGE_ASSESSED, COVERAGE_UNASSESSED}:
            violations.append(f"illegal assessment_coverage {self.coverage!r}")
        if self.state not in {None, STATE_COMPLETE, STATE_INDETERMINATE, STATE_ERROR}:
            violations.append(f"illegal evaluation_state {self.state!r}")
        if self.verdict not in {None, VERDICT_PASS, VERDICT_FAIL, VERDICT_NOT_APPLICABLE}:
            violations.append(f"illegal conformance_verdict {self.verdict!r}")
        if self.verdict is not None and self.state != STATE_COMPLETE:
            violations.append("conformance_verdict is non-null only when evaluation_state is COMPLETE")
        if self.state is None and self.coverage != COVERAGE_UNASSESSED:
            violations.append("evaluation_state is null only when assessment_coverage is UNASSESSED")
        if self.coverage == COVERAGE_UNASSESSED and self.verdict is not None:
            violations.append("UNASSESSED results carry a null conformance_verdict")
        for code in self.reason_codes:
            if code not in REASON_CODES:
                violations.append(f"unknown reason code {code!r}")
        row = _COMPATIBILITY.get((self.coverage, self.state, self.verdict))
        if row is None:
            violations.append(
                f"illegal field combination {self.coverage!r}/{self.state!r}/{self.verdict!r}"
            )
        else:
            codes = set(self.reason_codes)
            if row.get("empty_only"):
                if self.reason_codes:
                    violations.append("PASS carries no reason codes")
            else:
                if not codes & set(row["required_any_of"]):
                    violations.append(
                        f"missing required reason content for {self.state or 'UNASSESSED'}: "
                        f"need one of {sorted(row['required_any_of'])}"
                    )
                forbidden = codes & set(row["forbidden"])
                if forbidden:
                    violations.append(f"illegal reason codes for this state: {sorted(forbidden)}")
            exactly = row.get("exactly_one_of")
            if exactly and codes != set(exactly):
                violations.append(
                    f"NOT_APPLICABLE requires exactly {sorted(exactly)} as reason codes"
                )
        if self.verdict == VERDICT_NOT_APPLICABLE:
            sub = [d for d in self.diagnostics if d in PERMITTED_EMPTY_DISPOSITIONS]
            if len(sub) != 1:
                violations.append(
                    "NOT_APPLICABLE requires exactly one PERMITTED_EMPTY sub-code in diagnostics"
                )
        if violations:
            raise ResultValidationError(violations)

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        payload: dict[str, Any] = {
            "unit_id": self.unit_id,
            "assessment_coverage": self.coverage,
            "evaluation_state": self.state,
            "conformance_verdict": self.verdict,
            "reason_codes": list(self.reason_codes),
            "diagnostics": list(self.diagnostics),
        }
        for key, value in (
            ("subject_id", self.subject_id),
            ("targets", list(self.targets) or None),
            ("witnesses", list(self.witnesses) or None),
            ("missing", list(self.missing) or None),
            ("claim_boundary", self.claim_boundary or None),
        ):
            if value is not None:
                payload[key] = value
        return payload


# ---------------------------------------------------------------------------
# Contract schema (frozen baseline Section 7; result-algebra spelling)
# ---------------------------------------------------------------------------

#: Typed subject-selector kinds. Selector strings are contract data; the
#: registry below is the evaluator's typed meaning for them. An unregistered
#: selector string is a contract validation error, never a silent skip.
SELECTOR_SCOPE_SUBJECT = "scope-subject"
SELECTOR_SCOPE_USAGES = "scope-usages"
SELECTOR_DEFINITION_SUBJECT = "definition-subject"
SELECTOR_TESTED_SCOPE_SUBJECT = "tested-scope-subject"
SELECTOR_PROFILE_SET = "profile-set"
SELECTOR_UPSTREAM = "upstream-targets"

SELECTOR_REGISTRY: dict[str, str] = {
    "declared-pilot-scope": SELECTOR_SCOPE_SUBJECT,
    "scope usages": SELECTOR_SCOPE_USAGES,
    "declared-tested-scope": SELECTOR_TESTED_SCOPE_SUBJECT,
    "declared profiles": SELECTOR_PROFILE_SET,
    "ConsciousOverrideVerification": SELECTOR_DEFINITION_SUBJECT,
}

_UPSTREAM_SELECTOR_PREFIX = "upstream:"

#: Evaluation sources (frozen baseline Section 7). ``live-delivery-adapter``
#: obligations are outside deterministic evaluation (Package D) and are
#: rejected at contract validation.
EVALUATION_SOURCE_MODEL = "pinned-model-record"
EVALUATION_SOURCE_REPOSITORY = "pinned-repository-artifact"
EVALUATION_SOURCE_LIVE = "live-delivery-adapter"
EVALUATION_SOURCES = frozenset(
    {EVALUATION_SOURCE_MODEL, EVALUATION_SOURCE_REPOSITORY, EVALUATION_SOURCE_LIVE}
)

APPLICABILITY_UNCONDITIONAL = "unconditional"
APPLICABILITY_CANDIDATE_SCOPE = "candidate-declares-scope"
APPLICABILITY_FORMS = frozenset({APPLICABILITY_UNCONDITIONAL, APPLICABILITY_CANDIDATE_SCOPE})

#: Resolvable authorization-policy identities (acceptance obligations only).
POLICY_DEFINITIONS: frozenset[str] = frozenset(
    {"de4sdv.acceptance.maintainer-decision.v1"}
)


class ContractValidationError(ValueError):
    """Contract failed validation before normative evaluation (MC-09)."""

    def __init__(self, violations: Sequence[str]) -> None:
        self.violations = tuple(violations)
        super().__init__("; ".join(violations))


@dataclass(frozen=True)
class ObligationSpec:
    """One decoded, validated contract obligation row."""

    obligation_id: str
    phase: str
    subject_selector: str
    selector_kind: str
    applicability: str
    applicability_kind: str
    minimum_population: int
    permitted_empty: bool
    permitted_empty_disposition: str | None
    predicate: str
    target_filters: tuple[str, ...]
    cardinality: tuple[int, int]
    required: bool
    evaluation_source: str
    attestation_policy_ref: str
    claim_boundary: str
    depends_on: tuple[str, ...] = ()
    upstream_obligation_id: str | None = None
    expected_reason_default: tuple[str, ...] = ()


@dataclass(frozen=True)
class MethodContract:
    """Approved method contract for one phase (decoded; candidate-independent)."""

    method_id: str
    contract_id: str
    phase: str
    obligations: tuple[ObligationSpec, ...]
    policy_bundle_id: str = ""

    def digest(self) -> str:
        return contract_digest(self)

    def by_id(self, obligation_id: str) -> ObligationSpec:
        for obligation in self.obligations:
            if obligation.obligation_id == obligation_id:
                return obligation
        raise KeyError(obligation_id)


def contract_digest(contract: MethodContract) -> str:
    """Canonical digest of the decoded contract (evaluation identity input)."""
    payload = {
        "method_id": contract.method_id,
        "contract_id": contract.contract_id,
        "phase": contract.phase,
        "policy_bundle_id": contract.policy_bundle_id,
        "obligations": [
            {
                "obligation_id": o.obligation_id,
                "phase": o.phase,
                "subject_selector": o.subject_selector,
                "selector_kind": o.selector_kind,
                "applicability": o.applicability,
                "applicability_kind": o.applicability_kind,
                "minimum_population": o.minimum_population,
                "permitted_empty": o.permitted_empty,
                "permitted_empty_disposition": o.permitted_empty_disposition,
                "predicate": o.predicate,
                "target_filters": sorted(o.target_filters),
                "cardinality": list(o.cardinality),
                "required": o.required,
                "evaluation_source": o.evaluation_source,
                "attestation_policy_ref": o.attestation_policy_ref,
                "claim_boundary": o.claim_boundary,
                "depends_on": sorted(o.depends_on),
                "upstream_obligation_id": o.upstream_obligation_id,
            }
            for o in sorted(contract.obligations, key=lambda o: o.obligation_id)
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _blocking_cycle(edges: Mapping[str, Iterable[str]]) -> list[str] | None:
    """Return a blocking prerequisite cycle (as a node path), or None."""
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in edges}
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = GREY
        stack.append(node)
        for nxt in edges.get(node, ()):  # noqa: B905
            if nxt not in color:
                continue
            if color[nxt] == GREY:
                return stack[stack.index(nxt) :] + [nxt]
            if color[nxt] == WHITE:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        color[node] = BLACK
        return None

    for node in list(edges):
        if color[node] == WHITE:
            found = visit(node)
            if found:
                return found
    return None


def validate_contract(
    contract: MethodContract, predicate_names: Iterable[str] | None = None
) -> None:
    """Validate contract rows; raise ContractValidationError on any violation.

    Rejects (frozen baseline Section 7 / MC-09): duplicate IDs, unknown
    predicates, type/selector mismatches, invalid bounds, unknown status
    literals / unresolved policy references, unsupported applicability or
    evaluation-source forms, and invalid dependency structures (unknown or
    cyclic blocking prerequisites; MC-27).
    """

    violations: list[str] = []
    known_predicates = set(predicate_names or PREDICATES)
    seen: set[str] = set()
    for obligation in contract.obligations:
        oid = obligation.obligation_id
        if not oid:
            violations.append("obligation with empty obligation_id")
            continue
        if oid in seen:
            violations.append(f"duplicate obligation_id {oid!r}")
        seen.add(oid)
        if not obligation.phase:
            violations.append(f"{oid}: missing phase reference")
        if (
            obligation.selector_kind not in {
                SELECTOR_SCOPE_SUBJECT,
                SELECTOR_SCOPE_USAGES,
                SELECTOR_DEFINITION_SUBJECT,
                SELECTOR_TESTED_SCOPE_SUBJECT,
                SELECTOR_PROFILE_SET,
                SELECTOR_UPSTREAM,
            }
        ):
            violations.append(
                f"{oid}: unsupported subject_selector kind {obligation.selector_kind!r} "
                f"(selector {obligation.subject_selector!r})"
            )
        if obligation.applicability_kind not in APPLICABILITY_FORMS:
            violations.append(
                f"{oid}: unsupported applicability form {obligation.applicability!r}"
            )
        if obligation.evaluation_source not in EVALUATION_SOURCES:
            violations.append(
                f"{oid}: unknown evaluation_source {obligation.evaluation_source!r}"
            )
        elif obligation.evaluation_source == EVALUATION_SOURCE_LIVE:
            violations.append(
                f"{oid}: live-delivery-adapter obligations are outside deterministic "
                "V1 evaluation"
            )
        if obligation.predicate not in known_predicates:
            violations.append(f"{oid}: unknown predicate {obligation.predicate!r}")
        minimum, maximum = obligation.cardinality
        if (
            not isinstance(minimum, int)
            or not isinstance(maximum, int)
            or minimum < 0
            or maximum < minimum
        ):
            violations.append(
                f"{oid}: invalid cardinality bounds {obligation.cardinality!r}"
            )
        if obligation.minimum_population < 0:
            violations.append(f"{oid}: invalid minimum_population")
        if obligation.permitted_empty and obligation.permitted_empty_disposition not in (
            PERMITTED_EMPTY_DISPOSITIONS
        ):
            violations.append(
                f"{oid}: permitted-empty requires an explicit disposition from "
                f"{sorted(PERMITTED_EMPTY_DISPOSITIONS)}"
            )
        if (
            obligation.attestation_policy_ref
            and obligation.attestation_policy_ref not in POLICY_DEFINITIONS
        ):
            violations.append(
                f"{oid}: unresolved policy reference "
                f"{obligation.attestation_policy_ref!r}"
            )
        if obligation.selector_kind == SELECTOR_UPSTREAM:
            upstream = obligation.upstream_obligation_id
            if not upstream:
                violations.append(f"{oid}: upstream selector without upstream obligation")
            elif upstream not in {o.obligation_id for o in contract.obligations}:
                violations.append(f"{oid}: unknown upstream obligation {upstream!r}")
    for obligation in contract.obligations:
        for dependency in obligation.depends_on:
            if dependency not in seen:
                violations.append(
                    f"{obligation.obligation_id}: unknown prerequisite {dependency!r}"
                )
    edges = {
        obligation.obligation_id: obligation.depends_on
        for obligation in contract.obligations
    }
    cycle = _blocking_cycle(edges)
    if cycle is not None:
        violations.append(f"blocking prerequisite cycle: {' -> '.join(cycle)}")
    if violations:
        raise ContractValidationError(violations)


# ---------------------------------------------------------------------------
# Evaluation context and predicate outcomes
# ---------------------------------------------------------------------------


class FileSource(Protocol):
    """Read-only source for pinned repository artifacts at one revision."""

    def read_bytes(self, relative_path: str) -> bytes | None:  # pragma: no cover
        ...

    def exists(self, relative_path: str) -> bool:  # pragma: no cover
        ...

    def list_files(self, prefix: str) -> list[str] | None:  # pragma: no cover
        """Files under a prefix, or None when the prefix is absent."""
        ...


@dataclass(frozen=True)
class RevisionIdentity:
    git_commit: str
    sysml_project_id: str
    sysml_commit_id: str
    scope: str


@dataclass(frozen=True)
class DeclaredEvaluationScope:
    """The declared evaluation scope for one increment (typed inputs).

    ``usage_ids`` are the declared scope subjects (contribution set distinct
    from evaluation scope is carried by ``contribution_ids``); ``profiles``
    are the pinned tested-scope profile identities.
    """

    scope_id: str
    increment_id: str
    usage_ids: tuple[str, ...]
    contribution_ids: frozenset[str]
    profiles: tuple[str, ...]
    scope_element_id: str | None = None

    def declared_scope_closure(self) -> frozenset[str]:
        return frozenset(self.usage_ids) | frozenset({self.scope_id})


@dataclass(frozen=True)
class RegistryScan:
    """Acceptance-decision registry scan state (acceptance-policy.md)."""

    path: str
    state: str
    #: state in {"scanned-clean", "missing", "unreadable", "truncated", "invalid-record"}
    decisions: tuple[Mapping[str, Any], ...] = ()
    diagnostics: tuple[str, ...] = ()


@dataclass
class EvaluationContext:
    """Explicit typed inputs for one evaluation (no ambient/global state)."""

    revision: RevisionIdentity
    elements: tuple[Mapping[str, Any], ...]
    scope: DeclaredEvaluationScope
    #: per-usage bound facts assembled by the pilot binding (model branch)
    usage_bindings: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    definition_id: str | None = None
    requirement_target_ids: tuple[str, ...] = ()
    bench_definition_id: str | None = None
    #: evidence branch: repository artifact access at the evaluated revision
    artifact_source: FileSource | None = None
    bench_root: str = ""
    campaign_manifest: Mapping[str, Any] | None = None
    records: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    expected_dispositions: Mapping[str, str] = field(default_factory=dict)
    registry_scan: RegistryScan | None = None
    #: conservative scope equality: per-profile declared fingerprints and
    #: per-field comparison results computed by the pilot binding
    scope_equality: Mapping[str, "ScopeEqualityComparison"] = field(default_factory=dict)
    #: task-entry readiness inputs (corrective tasks): task id -> established
    task_entry_prerequisites: Mapping[str, Mapping[str, bool]] = field(default_factory=dict)
    #: candidate-declared scope availability for applicability resolution
    pilot_scope_declared: bool | None = None
    candidate_missing_inputs: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScopeEqualityComparison:
    """Per-profile result of the conservative-scope-equality field comparison."""

    status: str  # "equal" | "mismatch" | "indeterminate"
    compared_fields: tuple[str, ...]
    mismatched_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class PredicateOutcome:
    """One predicate invocation result for one subject."""

    status: str
    #: "satisfied" | "violated" | "indeterminate" | "error" | "not-applicable"
    reason_codes: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()
    witnesses: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {
            "satisfied",
            "violated",
            "indeterminate",
            "error",
            "not-applicable",
        }:
            raise ValueError(f"illegal predicate status {self.status!r}")


class Predicate(Protocol):
    def __call__(
        self, ctx: EvaluationContext, spec: ObligationSpec, subject_id: str
    ) -> PredicateOutcome:  # pragma: no cover
        ...


def _eligible_target_ids(
    ctx: EvaluationContext, obligation: ObligationSpec, candidate_ids: Iterable[str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Filter target ids by the obligation's declared target filters; returns
    (qualifying distinct ids, diagnostics). Distinctness is over element or
    record identities; duplicate witnesses for one target count once (MC-04).
    """

    def by_id(target_id: str) -> Mapping[str, Any]:
        for element in ctx.elements:
            if str(element.get("@id")) == target_id:
                return element
        return {}

    qualifying: set[str] = set()
    diagnostics: list[str] = []
    filters = set(obligation.target_filters)
    for target_id in candidate_ids:
        element = by_id(target_id)
        if "element type VerificationCaseUsage" in filters:
            if str(element.get("@type")) != "VerificationCaseUsage":
                diagnostics.append(f"target {target_id} is not a VerificationCaseUsage")
                continue
        if "element type OverrideMatrixBench specialization" in filters:
            if not _is_bench_specialization(ctx, target_id):
                diagnostics.append(
                    f"target {target_id} is not an OverrideMatrixBench specialization"
                )
                continue
        qualifying.add(target_id)
    return tuple(sorted(qualifying)), tuple(diagnostics)


def _is_bench_specialization(ctx: EvaluationContext, element_id: str) -> bool:
    """True when an element is a PartUsage typed by the bench definition.

    Accepts the serializer's direct FeatureTyping shape and the real
    `verifiedBench :> override<Scenario>Bench` shadow chain (ReferenceUsage
    whose Subsetting/Redefinition reaches a typed bench PartUsage).
    """
    bench_definition = ctx.bench_definition_id
    if bench_definition is None:
        # Model data does not carry the bench definition id; fall back to the
        # declared short-name-free resolution already performed by the pilot
        # binding, which fails closed upstream. Without it, no target qualifies.
        return False
    by_id = {
        str(e.get("@id")): e for e in ctx.elements if e.get("@id")
    }

    def typed_by_bench(element_id: str) -> bool:
        element = by_id.get(element_id)
        if element is None:
            return False
        for relationship in _relationship_objects(ctx, element, "FeatureTyping"):
            for key in ("type", "general", "superclassifier"):
                for value in _refs(relationship.get(key)):
                    if value == bench_definition:
                        return True
        return False

    if typed_by_bench(element_id):
        return True
    # Walk subsetting/redefinition targets (bounded transitive closure).
    frontier = [element_id]
    seen = {element_id}
    for _ in range(4):
        next_frontier: list[str] = []
        for current in frontier:
            element = by_id.get(current)
            if element is None:
                continue
            for family in ("Subsetting", "Redefinition", "ReferenceSubsetting"):
                for relationship in _relationship_objects(ctx, element, family):
                    for key in ("subsettedFeature", "redefinedFeature", "referencedFeature", "general"):
                        for value in _refs(relationship.get(key)):
                            if value in seen:
                                continue
                            seen.add(value)
                            if typed_by_bench(value):
                                return True
                            next_frontier.append(value)
        frontier = next_frontier
        if not frontier:
            break
    return False


def _refs(value: object) -> list[str]:
    if isinstance(value, dict):
        candidate = value.get("@id") or value.get("elementId") or value.get("id")
        return [str(candidate)] if candidate else []
    if isinstance(value, list):
        return [
            str(item.get("@id"))
            for item in value
            if isinstance(item, dict) and item.get("@id")
        ]
    return []


def _relationship_objects(
    ctx: EvaluationContext, owner: Mapping[str, Any], kind: str
) -> list[Mapping[str, Any]]:
    by_id = {str(e.get("@id")): e for e in ctx.elements if e.get("@id")}
    found: list[Mapping[str, Any]] = []
    for reference in owner.get("ownedRelationship") or []:
        relationship = by_id.get(str(reference.get("@id")))
        if relationship is None:
            continue
        if str(relationship.get("@type") or "") == kind:
            found.append(relationship)
    return found


# ---------------------------------------------------------------------------
# Predicates (typed; registered by the frozen predicate identifiers)
# ---------------------------------------------------------------------------


def _predicate_binding_resolution(
    ctx: EvaluationContext, spec: ObligationSpec, subject_id: str
) -> PredicateOutcome:
    """Usage identity -> API element, explicit-identity only (no name fallback)."""
    binding = ctx.usage_bindings.get(subject_id)
    if binding is None:
        return PredicateOutcome(
            status="error",
            reason_codes=(SCOPE_RESOLUTION_ERROR,),
            diagnostics=(f"declared usage {subject_id!r} has no binding record",),
        )
    level = str(binding.get("resolution_level") or "")
    element_id = str(binding.get("element_id") or "")
    if not element_id:
        return PredicateOutcome(
            status="error",
            reason_codes=(SCOPE_RESOLUTION_ERROR,),
            diagnostics=(f"declared usage {subject_id!r} unresolved in the bound revision",),
        )
    if level != "stable-explicit-id":
        return PredicateOutcome(
            status="error",
            reason_codes=(SCOPE_RESOLUTION_ERROR,),
            diagnostics=(
                f"declared usage {subject_id!r} resolved without explicit-identity "
                f"provenance (level {level!r}); name-based binding is not provenance",
            ),
        )
    element_type = str(binding.get("element_type") or "")
    if element_type != "VerificationCaseUsage":
        return PredicateOutcome(
            status="error",
            reason_codes=(BINDING_MISMATCH,),
            diagnostics=(
                f"declared usage {subject_id!r} bound to {element_type!r}; "
                "VerificationCaseUsage required",
            ),
        )
    return PredicateOutcome(status="satisfied", targets=(element_id,), witnesses=(element_id,))


def _predicate_scope_composition(
    ctx: EvaluationContext, spec: ObligationSpec, subject_id: str
) -> PredicateOutcome:
    """Scope composition: declared set equality as distinct identities.

    Sub-predicate by ``target_filters``: usage populations (model branch) or
    profile identities (evidence branch). The declared comparison set is
    pinned contract/scope data; observed members come from the bound revision
    or the declared tested-scope manifest.
    """
    filters = set(spec.target_filters)
    if "profile identity equality (pinned set, exact)" in filters:
        return _profile_population(ctx)
    observed: list[str] = []
    diagnostics: list[str] = []
    for usage_id in ctx.scope.usage_ids:
        binding = ctx.usage_bindings.get(usage_id)
        if binding is None or not binding.get("element_id"):
            diagnostics.append(f"declared scope usage {usage_id!r} is absent from the bound revision")
            continue
        observed.append(str(binding["element_id"]))
    qualifying, filter_diagnostics = _eligible_target_ids(ctx, spec, observed)
    diagnostics.extend(filter_diagnostics)
    duplicated = len(observed) != len(set(observed))
    if duplicated:
        diagnostics.append("scope composition resolved duplicate identities")
        return PredicateOutcome(
            status="error",
            reason_codes=(SCOPE_RESOLUTION_ERROR,),
            targets=qualifying,
            diagnostics=tuple(diagnostics),
        )
    return PredicateOutcome(
        status="satisfied" if qualifying else "violated",
        reason_codes=() if qualifying else (REQUIRED_RELATION_MISSING,),
        targets=qualifying,
        witnesses=tuple(sorted(ctx.scope.usage_ids)),
        diagnostics=tuple(diagnostics),
    )


def _profile_population(ctx: EvaluationContext) -> PredicateOutcome:
    manifest = ctx.campaign_manifest
    if manifest is None:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(INPUT_UNAVAILABLE,),
            missing=("campaign-manifest.json",),
            diagnostics=("declared tested-scope manifest is unavailable",),
        )
    declared = set((manifest.get("profiles") or {}).keys())
    pinned = set(ctx.scope.profiles)
    extra = sorted(declared - pinned)
    missing = sorted(pinned - declared)
    diagnostics: list[str] = []
    if missing:
        diagnostics.append(f"declared tested scope is missing pinned profiles: {missing}")
    if extra:
        diagnostics.append(f"declared tested scope carries undeclared profiles: {extra}")
    if extra:
        return PredicateOutcome(
            status="violated",
            reason_codes=(EVIDENCE_SCOPE_MISMATCH,),
            targets=tuple(sorted(declared)),
            diagnostics=tuple(diagnostics),
        )
    if missing:
        return PredicateOutcome(
            status="violated",
            reason_codes=(REQUIRED_RELATION_MISSING,),
            targets=tuple(sorted(declared)),
            diagnostics=tuple(diagnostics),
        )
    return PredicateOutcome(
        status="satisfied", targets=tuple(sorted(declared)), witnesses=(str(manifest.get("execution_head") or ""),)
    )


def _predicate_subject_membership(
    ctx: EvaluationContext, spec: ObligationSpec, subject_id: str
) -> PredicateOutcome:
    binding = ctx.usage_bindings.get(subject_id)
    if binding is None:
        return PredicateOutcome(
            status="error",
            reason_codes=(SCOPE_RESOLUTION_ERROR,),
            diagnostics=(f"no binding record for {subject_id!r}",),
        )
    members = tuple(binding.get("subject_members") or ())
    if not members:
        return PredicateOutcome(
            status="violated",
            reason_codes=(REQUIRED_RELATION_MISSING,),
            diagnostics=(
                f"usage {subject_id!r} has no verification-subject membership in "
                "the complete bound scope",
            ),
        )
    qualifying, filter_diagnostics = _eligible_target_ids(ctx, spec, members)
    if not qualifying:
        return PredicateOutcome(
            status="violated",
            reason_codes=(REQUIRED_RELATION_MISSING,),
            targets=(),
            witnesses=members,
            diagnostics=tuple(filter_diagnostics)
            or (f"usage {subject_id!r} subject member is not a bench specialization",),
        )
    return PredicateOutcome(
        status="satisfied", targets=qualifying, witnesses=members
    )


def _predicate_objective_contracts(
    ctx: EvaluationContext, spec: ObligationSpec, subject_id: str
) -> PredicateOutcome:
    binding = ctx.usage_bindings.get(subject_id)
    if binding is None:
        return PredicateOutcome(
            status="error",
            reason_codes=(SCOPE_RESOLUTION_ERROR,),
            diagnostics=(f"no binding record for {subject_id!r}",),
        )
    witnesses = tuple(binding.get("objective_targets") or ())
    expected = set(ctx.requirement_target_ids)
    observed = set(witnesses)
    if not witnesses:
        return PredicateOutcome(
            status="violated",
            reason_codes=(REQUIRED_RELATION_MISSING,),
            diagnostics=(
                f"usage {subject_id!r} has no inherited objective/verify witness path "
                "in the complete bound scope",
            ),
        )
    foreign = sorted(observed - expected)
    if foreign:
        return PredicateOutcome(
            status="violated",
            reason_codes=(REQUIRED_RELATION_MISSING,),
            targets=tuple(sorted(observed)),
            witnesses=witnesses,
            diagnostics=(f"objective witnesses outside the pinned requirement set: {foreign}",),
        )
    if "full-witness-path" not in set(spec.target_filters) and expected:
        # Witness completeness: every expected requirement must be reached.
        pass
    missing = sorted(expected - observed)
    if missing:
        return PredicateOutcome(
            status="violated",
            reason_codes=(REQUIRED_RELATION_MISSING,),
            targets=tuple(sorted(observed)),
            witnesses=witnesses,
            diagnostics=(f"missing objective witnesses for {missing}",),
        )
    return PredicateOutcome(
        status="satisfied", targets=tuple(sorted(observed)), witnesses=witnesses
    )


def _metadata_kind_values(
    ctx: EvaluationContext, metadata_id: str
) -> tuple[tuple[str, ...] | None, tuple[str, ...], tuple[str, ...]]:
    """Decode the ``kind`` value set of one @VerificationMethod metadata usage.

    Returns (value_names | None, witness ids, unresolved references). ``None``
    means the value expression's referenced literals are outside the exported
    closure (license-side library literals): the value set is not establishable
    from the artifact, never inferred.
    """
    by_id = {str(e.get("@id")): e for e in ctx.elements if e.get("@id")}

    def refs(value: object) -> list[str]:
        return _refs(value)

    # locate the "kind" member through its FeatureMembership(memberName="kind")
    kind_member: str | None = None
    for reference in by_id[metadata_id].get("ownedRelationship") or []:
        relationship = by_id.get(str(reference.get("@id")))
        if relationship is None:
            continue
        if str(relationship.get("@type") or "").endswith("Membership") and str(
            relationship.get("memberName") or ""
        ) == "kind":
            member = refs(relationship.get("memberElement"))
            if member:
                kind_member = member[0]
                break
    if kind_member is None:
        return (), (), ()
    feature = by_id.get(kind_member) or {}
    value_targets: list[str] = []
    for reference in feature.get("ownedRelationship") or []:
        relationship = by_id.get(str(reference.get("@id")))
        if relationship is None or str(relationship.get("@type")) != "FeatureValue":
            continue
        value_targets.extend(refs(relationship.get("memberElement")) or refs(relationship.get("value")))

    names: set[str] = set()
    unresolved: list[str] = []
    witness_ids: list[str] = []

    def resolve_expression(expression_id: str) -> None:
        expression = by_id.get(expression_id)
        if expression is None:
            unresolved.append(expression_id)
            return
        kind = str(expression.get("@type") or "")
        if kind == "FeatureReferenceExpression":
            target: str | None = None
            for reference in expression.get("ownedRelationship") or []:
                relationship = by_id.get(str(reference.get("@id")))
                if relationship is None:
                    continue
                if str(relationship.get("@type") or "").endswith("Membership"):
                    member = refs(relationship.get("memberElement"))
                    if member:
                        target = member[0]
                        break
            if target is None:
                unresolved.append(expression_id)
                return
            target_element = by_id.get(target) or {}
            name = target_element.get("declaredName") or target_element.get("name")
            if name:
                names.add(str(name))
                witness_ids.append(expression_id)
            else:
                unresolved.append(expression_id)
            return
        if kind == "OperatorExpression":
            for reference in expression.get("ownedRelationship") or []:
                relationship = by_id.get(str(reference.get("@id")))
                if relationship is None:
                    continue
                if str(relationship.get("@type") or "").endswith("Membership"):
                    for member in refs(relationship.get("memberElement")):
                        resolve_expression(member)
            return
        # operands wrapped in a Feature/parameter: follow FeatureValue chains
        for reference in expression.get("ownedRelationship") or []:
            relationship = by_id.get(str(reference.get("@id")))
            if relationship is None:
                continue
            if str(relationship.get("@type")) == "FeatureValue":
                for value in refs(relationship.get("memberElement")) or refs(relationship.get("value")):
                    resolve_expression(value)

    for target in value_targets:
        resolve_expression(target)
    if unresolved:
        return None, tuple(witness_ids), tuple(sorted(set(unresolved)))
    return tuple(sorted(names)), tuple(witness_ids), ()


def _predicate_method_metadata(
    ctx: EvaluationContext, spec: ObligationSpec, subject_id: str
) -> PredicateOutcome:
    """@VerificationMethod metadata observation with kind-value verification.

    Witness presence is checked first; the kind value set is verified only
    when the referenced literals are inside the exported closure. Unclosed
    literal references make the value check untestable (INPUT_UNAVAILABLE),
    never a pass and never an absence-based fail (UG-06 / closure rule C4).
    """
    filters = set(spec.target_filters)
    if "per-action kind" in " ".join(filters):
        binding = ctx.usage_bindings.get(f"definition:{subject_id}")
        metadata_by_action = binding.get("action_metadata") if binding else None
        if not metadata_by_action:
            return PredicateOutcome(
                status="violated",
                reason_codes=(REQUIRED_RELATION_MISSING,),
                diagnostics=(
                    f"definition {subject_id!r} carries no action-level method metadata "
                    "in the complete bound scope",
                ),
            )
        expected = dict(metadata_by_action.get("expected") or {})
        observed = dict(metadata_by_action.get("observed") or {})
        missing_actions = sorted(set(expected) - set(observed))
        if missing_actions:
            return PredicateOutcome(
                status="violated",
                reason_codes=(REQUIRED_RELATION_MISSING,),
                diagnostics=(f"actions without metadata witnesses: {missing_actions}",),
            )
        values: dict[str, tuple[str, ...] | None] = {}
        unresolved: list[str] = []
        witnesses: list[str] = []
        for action, metadata_id in sorted(observed.items()):
            names, witness_ids, unresolved_refs = _metadata_kind_values(ctx, metadata_id)
            values[action] = names
            witnesses.extend(witness_ids)
            if names is None:
                unresolved.append(f"{action}: {list(unresolved_refs)}")
        if unresolved:
            return PredicateOutcome(
                status="indeterminate",
                reason_codes=(INPUT_UNAVAILABLE,),
                witnesses=tuple(witnesses),
                missing=("VerificationMethodKind literal references",),
                diagnostics=tuple(
                    "method-kind value not establishable from the exported closure: " + item
                    for item in unresolved
                ),
            )
        mismatched = {
            action: values[action]
            for action, expected_kind in expected.items()
            if values.get(action) != (expected_kind,) and values.get(action) != expected_kind
        }
        if mismatched:
            return PredicateOutcome(
                status="violated",
                reason_codes=(REQUIRED_RELATION_MISSING,),
                witnesses=tuple(witnesses),
                diagnostics=(
                    "action method-kind values beyond the declared kinds: "
                    + json.dumps({k: list(v or ()) for k, v in mismatched.items()}, sort_keys=True),
                ),
            )
        return PredicateOutcome(
            status="satisfied", targets=tuple(sorted(observed.values())), witnesses=tuple(witnesses)
        )

    # Usage-level: one metadata observation per usage, kind value set check.
    binding = ctx.usage_bindings.get(subject_id)
    if binding is None:
        return PredicateOutcome(
            status="error",
            reason_codes=(SCOPE_RESOLUTION_ERROR,),
            diagnostics=(f"no binding record for {subject_id!r}",),
        )
    metadata_witnesses = tuple(binding.get("metadata_owners") or ())
    if not metadata_witnesses:
        return PredicateOutcome(
            status="violated",
            reason_codes=(REQUIRED_RELATION_MISSING,),
            diagnostics=(
                f"usage {subject_id!r} has no owned @VerificationMethod metadata witness "
                "in the complete bound scope",
            ),
        )
    expected_values = tuple(binding.get("expected_kind_values") or ())
    unresolved: list[str] = []
    value_sets: list[tuple[str, ...] | None] = []
    decoded_witnesses: list[str] = []
    for witness in metadata_witnesses:
        names, witness_ids, unresolved_refs = _metadata_kind_values(ctx, witness)
        value_sets.append(names)
        decoded_witnesses.extend(witness_ids)
        if names is None:
            unresolved.append(f"{witness}: {list(unresolved_refs)}")
    if unresolved:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(INPUT_UNAVAILABLE,),
            targets=metadata_witnesses,
            witnesses=tuple(decoded_witnesses),
            missing=("VerificationMethodKind literal references",),
            diagnostics=tuple(
                "method-kind value not establishable from the exported closure: " + item
                for item in unresolved
            ),
        )
    if expected_values:
        observed = sorted({name for names in value_sets if names is not None for name in names})
        if tuple(observed) != tuple(sorted(expected_values)):
            return PredicateOutcome(
                status="violated",
                reason_codes=(REQUIRED_RELATION_MISSING,),
                targets=metadata_witnesses,
                witnesses=tuple(decoded_witnesses),
                diagnostics=(
                    f"method-kind value set {observed} does not equal the declared "
                    f"{sorted(expected_values)}",
                ),
            )
    elif any(not names for names in value_sets):
        return PredicateOutcome(
            status="violated",
            reason_codes=(REQUIRED_RELATION_MISSING,),
            targets=metadata_witnesses,
            diagnostics=(f"usage {subject_id!r} metadata carries no kind value",),
        )
    return PredicateOutcome(
        status="satisfied",
        targets=metadata_witnesses,
        witnesses=(*metadata_witnesses, *decoded_witnesses),
    )


def _predicate_external_evidence_reference(
    ctx: EvaluationContext, spec: ObligationSpec, subject_id: str
) -> PredicateOutcome:
    """Canonical record presence + digest-verified integrity per profile.

    ``subject_id`` is the profile identity. Absent manifest entry is a
    required-relation failure; unreadable bytes are INPUT_UNAVAILABLE (never
    an absence-based pass); digest mismatch is BINDING_MISMATCH (MC-08/MC-15
    distinction preserved).
    """
    manifest = ctx.campaign_manifest
    if manifest is None:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(INPUT_UNAVAILABLE,),
            missing=("campaign-manifest.json",),
            diagnostics=("declared tested-scope manifest is unavailable",),
        )
    entry = (manifest.get("profiles") or {}).get(subject_id)
    if not isinstance(entry, Mapping):
        return PredicateOutcome(
            status="violated",
            reason_codes=(REQUIRED_RELATION_MISSING,),
            diagnostics=(f"no canonical record declared for profile {subject_id!r}",),
        )
    path = str(entry.get("path") or "")
    expected_digest = str(entry.get("sha256") or "")
    run_id = str(entry.get("run_id") or "")
    if ctx.artifact_source is None or not path:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(INPUT_UNAVAILABLE,),
            missing=(path or "record path",),
            diagnostics=(f"retained storage is not bound for profile {subject_id!r}",),
        )
    blob = ctx.artifact_source.read_bytes(f"{ctx.bench_root}/{path}" if ctx.bench_root else path)
    if blob is None:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(INPUT_UNAVAILABLE,),
            missing=(path,),
            diagnostics=(
                f"canonical record for profile {subject_id!r} is absent from retained "
                "storage; a missing record is not an empty result",
            ),
        )
    digest = hashlib.sha256(blob).hexdigest()
    if expected_digest and digest != expected_digest:
        return PredicateOutcome(
            status="error",
            reason_codes=(BINDING_MISMATCH,),
            diagnostics=(
                f"record digest mismatch for {subject_id!r}: manifest {expected_digest}, "
                f"observed {digest}",
            ),
        )
    return PredicateOutcome(
        status="satisfied",
        targets=(run_id or path,),
        witnesses=(f"sha256:{digest}",),
    )


def _predicate_execution_outcome(
    ctx: EvaluationContext, spec: ObligationSpec, subject_id: str
) -> PredicateOutcome:
    """Execution-outcome observation for one canonical record.

    ``subject_id`` is the record identity (run id or record path). Requires
    ``evaluation.passed == true`` AND the pinned per-profile disposition.
    """
    record, profile = _record_for_subject(ctx, subject_id)
    if record is None:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(INPUT_UNAVAILABLE,),
            missing=(subject_id,),
            diagnostics=(f"canonical record {subject_id!r} is unavailable",),
        )
    evaluation = record.get("evaluation") or {}
    disposition = str(evaluation.get("disposition") or "")
    expected = ctx.expected_dispositions.get(profile)
    if not disposition:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(INPUT_UNAVAILABLE,),
            missing=(f"{subject_id}:evaluation.disposition",),
            diagnostics=(f"record {subject_id!r} carries no disposition",),
        )
    if expected is None:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(INPUT_UNAVAILABLE,),
            missing=(f"expected disposition for {profile!r}",),
            diagnostics=(f"no pinned disposition for profile {profile!r}",),
        )
    if disposition != expected:
        # Unknown literals cannot be validated against the pinned vocabulary
        # from here; a differing-but-valid literal is an execution failure.
        return PredicateOutcome(
            status="violated",
            reason_codes=(EXECUTION_FAILED,),
            diagnostics=(
                f"record {subject_id!r} disposition {disposition!r} does not equal "
                f"the pinned {expected!r}",
            ),
        )
    if evaluation.get("passed") is not True:
        return PredicateOutcome(
            status="violated",
            reason_codes=(EXECUTION_FAILED,),
            diagnostics=(f"record {subject_id!r} is not a passing execution",),
        )
    return PredicateOutcome(
        status="satisfied",
        targets=(subject_id,),
        witnesses=(f"disposition:{disposition}",),
    )


def _record_for_subject(
    ctx: EvaluationContext, subject_id: str
) -> tuple[Mapping[str, Any] | None, str]:
    for profile, record in ctx.records.items():
        run_id = str(
            ((ctx.campaign_manifest or {}).get("profiles") or {}).get(profile, {}).get("run_id")
            or ""
        )
        if subject_id == run_id or subject_id == profile or subject_id.endswith(profile):
            return record, profile
    return None, ""


def _predicate_scope_equality(
    ctx: EvaluationContext, spec: ObligationSpec, subject_id: str
) -> PredicateOutcome:
    """Conservative equality of the record fingerprint vs the candidate's
    declared tested-scope identity; all pinned fields compared, none skipped."""
    _, profile = _record_for_subject(ctx, subject_id)
    comparison = ctx.scope_equality.get(profile)
    if comparison is None:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(INPUT_UNAVAILABLE,),
            missing=(f"declared tested-scope values for {profile!r}",),
            diagnostics=(
                f"no candidate-side tested-scope comparison values for profile {profile!r}",
            ),
        )
    if comparison.status == "equal":
        return PredicateOutcome(
            status="satisfied",
            targets=(subject_id,),
            witnesses=comparison.compared_fields,
        )
    if comparison.status == "mismatch":
        return PredicateOutcome(
            status="violated",
            reason_codes=(EVIDENCE_SCOPE_MISMATCH,),
            targets=(subject_id,),
            diagnostics=(
                "conservative scope equality failed; mismatched fields: "
                f"{sorted(comparison.mismatched_fields)}"
                + (
                    f"; changed or removed inputs: {list(comparison.diagnostics)}"
                    if comparison.diagnostics
                    else ""
                ),
            ),
        )
    return PredicateOutcome(
        status="indeterminate",
        reason_codes=(INPUT_UNAVAILABLE,),
        missing=comparison.missing_fields,
        diagnostics=(
            "scope equality cannot be established; missing fields: "
            f"{sorted(comparison.missing_fields)}",
        ),
    )


def _predicate_acceptance_record_match(
    ctx: EvaluationContext, spec: ObligationSpec, subject_id: str
) -> PredicateOutcome:
    """Acceptance decision match under the referenced authorization policy.

    Implements the acceptance-policy.md registry table and the result-algebra
    FAIL/INDETERMINATE discriminator (evidence availability). ``subject_id``
    is the record identity; the covered profile is resolved from the context.
    """
    _, profile = _record_for_subject(ctx, subject_id)
    scan = ctx.registry_scan
    policy_ref = spec.attestation_policy_ref
    if policy_ref and policy_ref not in POLICY_DEFINITIONS:
        return PredicateOutcome(
            status="error",
            reason_codes=(INVALID_CONTRACT,),
            diagnostics=(f"unresolvable policy identity {policy_ref!r}",),
        )
    if scan is None:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(ACCEPTANCE_AUTHORITY_MISSING, INPUT_UNAVAILABLE),
            missing=(f"decision registry ({policy_ref or 'policy'})",),
            diagnostics=("no decision-registry scan was bound to the evaluation",),
        )
    if scan.state == "missing":
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(INPUT_UNAVAILABLE, ACCEPTANCE_AUTHORITY_MISSING),
            missing=(scan.path,),
            diagnostics=tuple(scan.diagnostics)
            or (f"decision registry {scan.path!r} is missing; no FAIL may be derived",),
        )
    if scan.state in {"unreadable", "truncated"}:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(INPUT_UNAVAILABLE, ACCEPTANCE_AUTHORITY_MISSING),
            missing=(scan.path,),
            diagnostics=tuple(scan.diagnostics)
            or (f"decision registry {scan.path!r} could not be scanned completely",),
        )
    if scan.state == "invalid-record":
        return PredicateOutcome(
            status="error",
            reason_codes=(BINDING_MISMATCH,),
            diagnostics=tuple(scan.diagnostics)
            or ("a registry record fails schema validation",),
        )
    # scanned-clean: evaluate coverage of the closed profile universe
    covering = [
        decision
        for decision in scan.decisions
        if profile in {str(item) for item in decision.get("covered_profiles") or ()}
    ]
    accepted = [d for d in covering if str(d.get("outcome")) == "accepted"]
    rejected = [d for d in covering if str(d.get("outcome")) == "rejected"]
    if accepted and rejected:
        # supersession handling happens at assembly time (conflict resolution
        # is typed data); if both survive here the conflict is unresolved.
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(ACCEPTANCE_AUTHORITY_MISSING,),
            diagnostics=(
                "conflicting decisions without valid supersession cover "
                f"profile {profile!r}: {sorted(str(d.get('decision_id')) for d in covering)}",
            ),
        )
    if len(accepted) > 1:
        return PredicateOutcome(
            status="indeterminate",
            reason_codes=(ACCEPTANCE_AUTHORITY_MISSING,),
            diagnostics=(
                f"multiple accepted decisions cover profile {profile!r} without "
                "supersession",
            ),
        )
    if accepted:
        decision = accepted[0]
        return PredicateOutcome(
            status="satisfied",
            targets=(str(decision.get("decision_id") or ""),),
            witnesses=(str(decision.get("decider") or ""),),
        )
    if rejected:
        decision = rejected[0]
        return PredicateOutcome(
            status="violated",
            reason_codes=(ACCEPTANCE_AUTHORITY_MISSING,),
            diagnostics=(
                f"decision {decision.get('decision_id')!r} rejects profile {profile!r} "
                "(retained decision, not an absence)",
            ),
        )
    return PredicateOutcome(
        status="violated",
        reason_codes=(ACCEPTANCE_AUTHORITY_MISSING,),
        diagnostics=(
            f"registry {scan.path!r} scanned completely; no decision covers "
            f"profile {profile!r}",
        ),
    )


PREDICATES: dict[str, Predicate] = {
    "binding-resolution": _predicate_binding_resolution,
    "scope-composition": _predicate_scope_composition,
    "verification-subject-membership": _predicate_subject_membership,
    "verifiedBy-reverse-witness": _predicate_objective_contracts,
    "verification-method-metadata": _predicate_method_metadata,
    "external-evidence-reference": _predicate_external_evidence_reference,
    "execution-outcome": _predicate_execution_outcome,
    "conservative-scope-equality": _predicate_scope_equality,
    "acceptance-record-match": _predicate_acceptance_record_match,
}


# ---------------------------------------------------------------------------
# The evaluator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReadinessTarget:
    target_type: str  # TASK_ENTRY | PHASE_EXIT (PR_MERGE belongs to Package D)
    target_id: str


@dataclass(frozen=True)
class ReadinessBlock:
    target: ReadinessTarget
    readiness: str  # READY | BLOCKED
    reason_codes: tuple[str, ...] = ()
    blocking_units: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "readiness_target": {"type": self.target.target_type, "id": self.target.target_id},
            "readiness": self.readiness,
            "reason_codes": list(self.reason_codes),
            "blocking_units": list(self.blocking_units),
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class CanonicalEvaluation:
    """One canonical evaluation identity with all preserved child results."""

    evaluation_key: str
    method_identity: Mapping[str, Any]
    revision_identity: Mapping[str, Any]
    scope_identity: Mapping[str, Any]
    results: tuple[EvaluationResult, ...]
    assessment_coverage: str
    evaluation_state: str | None
    conformance_verdict: str | None
    assessed_ids: tuple[str, ...]
    unassessed_ids: tuple[str, ...]
    failed_ids: tuple[str, ...]
    indeterminate_ids: tuple[str, ...]
    errored_ids: tuple[str, ...]
    not_applicable_ids: tuple[str, ...]
    readiness: tuple[ReadinessBlock, ...] = ()
    diagnostics: tuple[str, ...] = ()
    provenance: tuple[Mapping[str, str], ...] = ()
    evaluated_at: str = ""  # excluded from the canonical key (transport envelope)
    units: tuple[EvaluationResult, ...] = ()
    """Combined per-unit results (one per obligation); child results above."""
    required_units: tuple[str, ...] = ()

    # -- projections (single canonical evaluation, one identity) -----------

    def increment_status(self) -> dict[str, Any]:
        """Scoped model-contract conformance projection."""
        return {
            "query": "increment_status",
            "evaluation_key": self.evaluation_key,
            "method": dict(self.method_identity),
            "scope": dict(self.scope_identity),
            "revision": dict(self.revision_identity),
            "assessment_coverage": self.assessment_coverage,
            "evaluation_state": self.evaluation_state,
            "conformance_verdict": self.conformance_verdict,
            "assessed_ids": list(self.assessed_ids),
            "unassessed_ids": list(self.unassessed_ids),
            "counts": {
                "assessed": len(self.assessed_ids),
                "unassessed": len(self.unassessed_ids),
                "failed": len(self.failed_ids),
                "indeterminate": len(self.indeterminate_ids),
                "errored": len(self.errored_ids),
                "not_applicable": len(self.not_applicable_ids),
            },
            "results": [result.as_dict() for result in self.results],
            "readiness": [block.as_dict() for block in self.readiness],
            "diagnostics": list(self.diagnostics),
            "provenance": [dict(item) for item in self.provenance],
        }

    def method_gaps(self) -> dict[str, Any]:
        """Explicit violations, unresolved inputs, and out-of-scope obligations."""
        violations = [
            result
            for result in self.results
            if result.coverage == COVERAGE_ASSESSED and result.verdict == VERDICT_FAIL
        ]
        unresolved = [
            result
            for result in self.results
            if result.coverage == COVERAGE_ASSESSED
            and result.state in {STATE_INDETERMINATE, STATE_ERROR}
        ]
        out_of_scope = [
            result
            for result in self.results
            if result.coverage == COVERAGE_UNASSESSED
            and OUTSIDE_REQUESTED_SCOPE in result.reason_codes
        ]
        unassessed = [
            result
            for result in self.results
            if result.coverage == COVERAGE_UNASSESSED
            and OUTSIDE_REQUESTED_SCOPE not in result.reason_codes
        ]
        return {
            "query": "method_gaps",
            "evaluation_key": self.evaluation_key,
            "violations": [result.as_dict() for result in violations],
            "unresolved_inputs": [result.as_dict() for result in unresolved],
            "unassessed": [result.as_dict() for result in unassessed],
            "out_of_scope": [result.as_dict() for result in out_of_scope],
        }

    def next_obligation(self) -> dict[str, Any]:
        """Deterministic next actionable obligation (no agent assignment)."""
        priority: tuple[tuple[int, int, str], EvaluationResult] | None = None
        for index, result in enumerate(self.results):
            if result.coverage == COVERAGE_ASSESSED and result.verdict == VERDICT_FAIL:
                rank = 2
            elif result.coverage == COVERAGE_ASSESSED and result.state in {
                STATE_INDETERMINATE,
                STATE_ERROR,
            }:
                rank = 0 if result.state == STATE_INDETERMINATE else 1
            elif result.coverage == COVERAGE_UNASSESSED and OUTSIDE_REQUESTED_SCOPE not in result.reason_codes:
                rank = 0
            else:
                continue
            candidate = (rank, index, result.unit_id)
            if priority is None or candidate < priority[0]:
                priority = (candidate, result)
        if priority is None:
            return {
                "query": "next_obligation",
                "evaluation_key": self.evaluation_key,
                "next": None,
                "reason": "no failing, indeterminate, errored, or unassessed required obligation",
            }
        _, result = priority
        kind = (
            "input-problem"
            if result.state == STATE_INDETERMINATE
            or CONTRACT_UNAVAILABLE in result.reason_codes
            or NOT_ATTEMPTED in result.reason_codes
            else "violation"
        )
        return {
            "query": "next_obligation",
            "evaluation_key": self.evaluation_key,
            "next": {
                "kind": kind,
                "unit_id": result.unit_id,
                "subject_id": result.subject_id,
                "reason_codes": list(result.reason_codes),
                "diagnostics": list(result.diagnostics),
            },
        }


def _readiness_blocks(
    units: Sequence[EvaluationResult],
    required_ids: Sequence[str],
    requested: Sequence[ReadinessTarget],
    task_entry_prerequisites: Mapping[str, Mapping[str, bool]],
) -> tuple[ReadinessBlock, ...]:
    blocks: list[ReadinessBlock] = []
    required = set(required_ids)
    for target in requested:
        if target.target_type == "TASK_ENTRY":
            prerequisites = task_entry_prerequisites.get(target.target_id)
            if prerequisites is None:
                blocks.append(
                    ReadinessBlock(
                        target=target,
                        readiness="BLOCKED",
                        reason_codes=(INPUT_UNAVAILABLE,),
                        diagnostics=(
                            f"task-entry prerequisites for {target.target_id!r} are not "
                            "established/known",
                        ),
                    )
                )
                continue
            unmet = sorted(name for name, ok in prerequisites.items() if not ok)
            blocks.append(
                ReadinessBlock(
                    target=target,
                    readiness="BLOCKED" if unmet else "READY",
                    reason_codes=(NOT_ATTEMPTED,) if unmet else (),
                    diagnostics=(
                        (f"unestablished task prerequisites: {unmet}",) if unmet else ()
                    ),
                )
            )
        elif target.target_type == "PHASE_EXIT":
            blocking: list[str] = []
            codes: list[str] = []
            for result in units:
                if result.unit_id not in required:
                    continue
                acceptable = result.coverage == COVERAGE_ASSESSED and (
                    (result.state == STATE_COMPLETE and result.verdict == VERDICT_PASS)
                    or (
                        result.state == STATE_COMPLETE
                        and result.verdict == VERDICT_NOT_APPLICABLE
                    )
                )
                if not acceptable:
                    blocking.append(result.unit_id)
                    codes.extend(result.reason_codes or (NOT_ATTEMPTED,))
            blocks.append(
                ReadinessBlock(
                    target=target,
                    readiness="BLOCKED" if blocking else "READY",
                    reason_codes=tuple(dict.fromkeys(codes)),
                    blocking_units=tuple(dict.fromkeys(blocking)),
                    diagnostics=(
                        (
                            "required obligations not complete-pass: "
                            + ", ".join(sorted(set(blocking))),
                        )
                        if blocking
                        else ()
                    ),
                )
            )
        else:
            raise ValueError(
                f"readiness target type {target.target_type!r} is not produced by the "
                "model evaluator; PR-merge readiness belongs to the delivery projection"
            )
    return tuple(blocks)


def readiness_blocks(
    evaluation: "CanonicalEvaluation",
    requested: Sequence[ReadinessTarget],
    task_entry_prerequisites: Mapping[str, Mapping[str, bool]] = {},
) -> tuple[ReadinessBlock, ...]:
    """Readiness for explicit targets, derived from one canonical evaluation."""
    return _readiness_blocks(
        evaluation.units,
        evaluation.required_units,
        requested,
        task_entry_prerequisites,
    )


def _canonical_key(
    contract: MethodContract,
    ctx: EvaluationContext,
    results: Sequence[EvaluationResult],
) -> str:
    payload = {
        "contract_digest": contract.digest(),
        "method_id": contract.method_id,
        "contract_id": contract.contract_id,
        "phase": contract.phase,
        "revision": {
            "git_commit": ctx.revision.git_commit,
            "sysml_project_id": ctx.revision.sysml_project_id,
            "sysml_commit_id": ctx.revision.sysml_commit_id,
            "scope": ctx.revision.scope,
        },
        "scope": {
            "scope_id": ctx.scope.scope_id,
            "increment_id": ctx.scope.increment_id,
            "usage_ids": sorted(ctx.scope.usage_ids),
            "profiles": list(ctx.scope.profiles),  # declared order is meaningful
        },
        "results": [
            {
                "unit_id": r.unit_id,
                "subject_id": r.subject_id,
                "coverage": r.coverage,
                "state": r.state,
                "verdict": r.verdict,
                "reason_codes": sorted(r.reason_codes),
                "targets": sorted(r.targets),
                "witnesses": sorted(r.witnesses),
                "missing": sorted(r.missing),
                "diagnostics": sorted(r.diagnostics),
            }
            for r in sorted(results, key=lambda r: (r.unit_id, r.subject_id or ""))
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _evaluation_order(contract: MethodContract) -> list[ObligationSpec]:
    """Stable topological order: prerequisites evaluate before dependents.

    Declaration order is preserved among ready obligations; the validator
    rejects cycles, so an order always exists.
    """
    remaining = list(contract.obligations)
    ordered: list[ObligationSpec] = []
    done: set[str] = set()
    while remaining:
        progressed = False
        for spec in list(remaining):
            if set(spec.depends_on) <= done:
                ordered.append(spec)
                done.add(spec.obligation_id)
                remaining.remove(spec)
                progressed = True
        if not progressed:
            # Unreachable for validated contracts; fail closed on defects.
            ordered.extend(remaining)
            break
    return ordered


class MethodEvaluator:
    """Phase-neutral deterministic evaluator for one approved contract."""

    def __init__(self, contract: MethodContract) -> None:
        validate_contract(contract)
        self.contract = contract

    # -- subject resolution ------------------------------------------------

    def _subjects(
        self, spec: ObligationSpec, ctx: EvaluationContext
    ) -> tuple[list[str], list[str]]:
        """Resolve typed subjects; returns (subject ids, diagnostics)."""
        diagnostics: list[str] = []
        if spec.selector_kind == SELECTOR_SCOPE_SUBJECT:
            return [ctx.scope.scope_id], diagnostics
        if spec.selector_kind == SELECTOR_SCOPE_USAGES:
            return list(ctx.scope.usage_ids), diagnostics
        if spec.selector_kind == SELECTOR_DEFINITION_SUBJECT:
            if ctx.definition_id is None:
                diagnostics.append("the declared definition identity is unavailable")
                return [], diagnostics
            return [ctx.definition_id], diagnostics
        if spec.selector_kind == SELECTOR_TESTED_SCOPE_SUBJECT:
            return [f"tested-scope:{ctx.scope.increment_id}"], diagnostics
        if spec.selector_kind == SELECTOR_PROFILE_SET:
            return list(ctx.scope.profiles), diagnostics
        if spec.selector_kind == SELECTOR_UPSTREAM:
            upstream_id = spec.upstream_obligation_id
            subjects: list[str] = []
            # The engine resolves upstream subjects after the upstream
            # obligation evaluated; assembly here relies on the context for
            # derived subject identity (records), which keeps one evaluation.
            for profile in ctx.scope.profiles:
                run_id = str(
                    ((ctx.campaign_manifest or {}).get("profiles") or {})
                    .get(profile, {})
                    .get("run_id")
                    or ""
                )
                subjects.append(run_id or f"record:{profile}")
            return subjects, diagnostics
        diagnostics.append(f"unsupported selector kind {spec.selector_kind!r}")
        return [], diagnostics

    # -- obligation evaluation --------------------------------------------

    def _evaluate_obligation(
        self,
        spec: ObligationSpec,
        ctx: EvaluationContext,
        results_by_id: Mapping[str, EvaluationResult],
    ) -> list[EvaluationResult]:
        unit = spec.obligation_id

        def blocked(reason: str, diagnostics: Sequence[str]) -> list[EvaluationResult]:
            return [
                EvaluationResult(
                    unit_id=unit,
                    coverage=COVERAGE_UNASSESSED,
                    state=None,
                    verdict=None,
                    reason_codes=(reason,),
                    diagnostics=tuple(diagnostics),
                    claim_boundary=spec.claim_boundary,
                )
            ]

        # Prerequisite propagation: failed or unresolved prerequisites leave
        # dependents unassessed (NOT_ATTEMPTED), never NOT_APPLICABLE.
        for dependency in spec.depends_on:
            upstream = results_by_id.get(dependency)
            if upstream is None:
                continue
            resolved = (
                upstream.coverage == COVERAGE_ASSESSED
                and upstream.state == STATE_COMPLETE
                and upstream.verdict in {VERDICT_PASS, VERDICT_NOT_APPLICABLE}
            )
            if not resolved:
                return blocked(
                    NOT_ATTEMPTED,
                    (
                        f"prerequisite {dependency} is not a completed pass "
                        f"(coverage {upstream.coverage}, state {upstream.state}, "
                        f"verdict {upstream.verdict})",
                    ),
                )

        # Applicability: supported typed conditions only.
        if spec.applicability_kind == APPLICABILITY_CANDIDATE_SCOPE:
            declared = ctx.pilot_scope_declared
            if declared is None:
                return [
                    EvaluationResult(
                        unit_id=unit,
                        coverage=COVERAGE_ASSESSED,
                        state=STATE_INDETERMINATE,
                        verdict=None,
                        reason_codes=(APPLICABILITY_UNRESOLVED,),
                        missing=ctx.candidate_missing_inputs,
                        diagnostics=(
                            "candidate scope declaration cannot be established; "
                            "applicability unresolved",
                        ),
                        claim_boundary=spec.claim_boundary,
                    )
                ]
            if not declared:
                return [
                    EvaluationResult(
                        unit_id=unit,
                        coverage=COVERAGE_ASSESSED,
                        state=STATE_COMPLETE,
                        verdict=VERDICT_NOT_APPLICABLE,
                        reason_codes=(NOT_APPLICABLE_REASON,),
                        diagnostics=(EXPLICIT_DISPOSITION,),
                        claim_boundary=spec.claim_boundary,
                    )
                ]

        subject_ids, subject_diagnostics = self._subjects(spec, ctx)
        if not subject_ids:
            subject_ids = []
        if not subject_ids:
            if spec.permitted_empty and spec.permitted_empty_disposition:
                return [
                    EvaluationResult(
                        unit_id=unit,
                        coverage=COVERAGE_ASSESSED,
                        state=STATE_COMPLETE,
                        verdict=VERDICT_NOT_APPLICABLE,
                        reason_codes=(NOT_APPLICABLE_REASON,),
                        diagnostics=(spec.permitted_empty_disposition,),
                        claim_boundary=spec.claim_boundary,
                    )
                ]
            if spec.minimum_population > 0:
                return [
                    EvaluationResult(
                        unit_id=unit,
                        coverage=COVERAGE_ASSESSED,
                        state=STATE_COMPLETE,
                        verdict=VERDICT_FAIL,
                        reason_codes=(POPULATION_POLICY_VIOLATION,),
                        diagnostics=tuple(subject_diagnostics)
                        or (
                            "the declared scope resolved to no subjects while the "
                            "population policy requires a non-empty population",
                        ),
                        claim_boundary=spec.claim_boundary,
                    )
                ]
            return [
                EvaluationResult(
                    unit_id=unit,
                    coverage=COVERAGE_ASSESSED,
                    state=STATE_COMPLETE,
                    verdict=VERDICT_PASS,
                    reason_codes=(),
                    diagnostics=("empty population permitted with no minimum",),
                    claim_boundary=spec.claim_boundary,
                )
            ]

        predicate = PREDICATES[spec.predicate]
        child_results: list[EvaluationResult] = []
        for subject_id in subject_ids:
            outcome = predicate(ctx, spec, subject_id)
            child_results.append(
                self._child_result(spec, subject_id, outcome)
            )
        return child_results

    def _child_result(
        self, spec: ObligationSpec, subject_id: str, outcome: PredicateOutcome
    ) -> EvaluationResult:
        minimum, maximum = spec.cardinality
        targets = tuple(sorted(set(outcome.targets)))
        if outcome.status == "satisfied":
            if not (minimum <= len(targets) <= maximum):
                return EvaluationResult(
                    unit_id=spec.obligation_id,
                    coverage=COVERAGE_ASSESSED,
                    state=STATE_COMPLETE,
                    verdict=VERDICT_FAIL,
                    reason_codes=(REQUIRED_RELATION_MISSING,),
                    diagnostics=(
                        f"distinct qualifying targets {len(targets)} outside the declared "
                        f"cardinality [{minimum}..{maximum}] for subject {subject_id!r}; "
                        "counts are per-subject over distinct targets, not global paths",
                        *outcome.diagnostics,
                    ),
                    subject_id=subject_id,
                    targets=targets,
                    witnesses=tuple(sorted(set(outcome.witnesses))),
                    claim_boundary=spec.claim_boundary,
                )
            return EvaluationResult(
                unit_id=spec.obligation_id,
                coverage=COVERAGE_ASSESSED,
                state=STATE_COMPLETE,
                verdict=VERDICT_PASS,
                reason_codes=(),
                diagnostics=outcome.diagnostics,
                subject_id=subject_id,
                targets=targets,
                witnesses=tuple(sorted(set(outcome.witnesses))),
                claim_boundary=spec.claim_boundary,
            )
        if outcome.status == "violated":
            codes = tuple(outcome.reason_codes) or (REQUIRED_RELATION_MISSING,)
            return EvaluationResult(
                unit_id=spec.obligation_id,
                coverage=COVERAGE_ASSESSED,
                state=STATE_COMPLETE,
                verdict=VERDICT_FAIL,
                reason_codes=codes,
                diagnostics=outcome.diagnostics,
                subject_id=subject_id,
                targets=targets,
                witnesses=tuple(sorted(set(outcome.witnesses))),
                missing=outcome.missing,
                claim_boundary=spec.claim_boundary,
            )
        if outcome.status == "indeterminate":
            return EvaluationResult(
                unit_id=spec.obligation_id,
                coverage=COVERAGE_ASSESSED,
                state=STATE_INDETERMINATE,
                verdict=None,
                reason_codes=tuple(outcome.reason_codes) or (INPUT_UNAVAILABLE,),
                diagnostics=outcome.diagnostics,
                subject_id=subject_id,
                targets=targets,
                missing=outcome.missing,
                claim_boundary=spec.claim_boundary,
            )
        if outcome.status == "error":
            return EvaluationResult(
                unit_id=spec.obligation_id,
                coverage=COVERAGE_ASSESSED,
                state=STATE_ERROR,
                verdict=None,
                reason_codes=tuple(outcome.reason_codes) or (EVALUATOR_FAILURE,),
                diagnostics=outcome.diagnostics,
                subject_id=subject_id,
                targets=targets,
                claim_boundary=spec.claim_boundary,
            )
        # not-applicable
        return EvaluationResult(
            unit_id=spec.obligation_id,
            coverage=COVERAGE_ASSESSED,
            state=STATE_COMPLETE,
            verdict=VERDICT_NOT_APPLICABLE,
            reason_codes=(NOT_APPLICABLE_REASON,),
            diagnostics=(EXPLICIT_DISPOSITION, *outcome.diagnostics),
            subject_id=subject_id,
            claim_boundary=spec.claim_boundary,
        )

    # -- aggregation -------------------------------------------------------

    @staticmethod
    def _aggregate(
        contract: MethodContract, results: Sequence[EvaluationResult]
    ) -> tuple[str, str | None, str | None, dict[str, tuple[str, ...]]]:
        required_ids = [
            o.obligation_id for o in contract.obligations if o.required
        ]
        by_unit: dict[str, list[EvaluationResult]] = {}
        for result in results:
            by_unit.setdefault(result.unit_id, []).append(result)

        assessed: list[str] = []
        unassessed: list[str] = []
        failed: list[str] = []
        indeterminate: list[str] = []
        errored: list[str] = []
        not_applicable: list[str] = []
        for unit_id in required_ids:
            children = by_unit.get(unit_id, [])
            if not children:
                unassessed.append(unit_id)
                continue
            coverage = (
                COVERAGE_ASSESSED
                if all(child.coverage == COVERAGE_ASSESSED for child in children)
                else COVERAGE_UNASSESSED
            )
            if coverage == COVERAGE_UNASSESSED:
                unassessed.append(unit_id)
                continue
            assessed.append(unit_id)
            if any(child.state == STATE_ERROR for child in children):
                errored.append(unit_id)
            elif any(child.state == STATE_INDETERMINATE for child in children):
                indeterminate.append(unit_id)
            elif any(child.verdict == VERDICT_FAIL for child in children):
                failed.append(unit_id)
            elif all(child.verdict == VERDICT_NOT_APPLICABLE for child in children):
                not_applicable.append(unit_id)

        counts = {
            "assessed_ids": tuple(assessed),
            "unassessed_ids": tuple(unassessed),
            "failed_ids": tuple(failed),
            "indeterminate_ids": tuple(indeterminate),
            "errored_ids": tuple(errored),
            "not_applicable_ids": tuple(not_applicable),
        }
        if unassessed:
            return COVERAGE_UNASSESSED, None, None, counts
        if errored:
            return COVERAGE_ASSESSED, STATE_ERROR, None, counts
        if indeterminate:
            return COVERAGE_ASSESSED, STATE_INDETERMINATE, None, counts
        if failed:
            return COVERAGE_ASSESSED, STATE_COMPLETE, VERDICT_FAIL, counts
        if not_applicable and len(not_applicable) == len(required_ids):
            return COVERAGE_ASSESSED, STATE_COMPLETE, VERDICT_NOT_APPLICABLE, counts
        if len(assessed) == len(required_ids):
            return COVERAGE_ASSESSED, STATE_COMPLETE, VERDICT_PASS, counts
        return COVERAGE_ASSESSED, STATE_COMPLETE, VERDICT_FAIL, counts

    # -- entry point -------------------------------------------------------

    def evaluate(
        self,
        ctx: EvaluationContext,
        *,
        requested_readiness: Sequence[ReadinessTarget] = (),
    ) -> CanonicalEvaluation:
        """Evaluate the contract against the context; return the canonical result."""
        results: list[EvaluationResult] = []
        results_by_id: dict[str, EvaluationResult] = {}
        order = _evaluation_order(self.contract)
        for spec in order:
            children = self._evaluate_obligation(spec, ctx, results_by_id)
            results.extend(children)
            results_by_id[spec.obligation_id] = _combine_unit_result(spec, children)
        for result in results:
            result.validate()
        for result in results_by_id.values():
            result.validate()
        coverage, state, verdict, counts = self._aggregate(self.contract, results)
        combined = [
            results_by_id[spec.obligation_id]
            for spec in self.contract.obligations
            if spec.obligation_id in results_by_id
        ]
        required_ids = [
            spec.obligation_id for spec in self.contract.obligations if spec.required
        ]
        readiness = _readiness_blocks(
            combined, required_ids, requested_readiness, ctx.task_entry_prerequisites
        )
        key = _canonical_key(self.contract, ctx, results)
        provenance: list[Mapping[str, str]] = [
            {
                "authority": "authoritative",
                "source": f"git://{ctx.revision.git_commit}",
            },
            {
                "authority": "authoritative",
                "source": (
                    f"sysml://{ctx.revision.sysml_project_id}/"
                    f"{ctx.revision.sysml_commit_id}"
                ),
            },
            {
                "authority": "derived",
                "source": "de4sdv.semantic.method_evaluator",
                "contract_digest": self.contract.digest(),
            },
        ]
        return CanonicalEvaluation(
            evaluation_key=key,
            method_identity={
                "method_id": self.contract.method_id,
                "contract_id": self.contract.contract_id,
                "phase": self.contract.phase,
                "contract_digest": self.contract.digest(),
                "policy_bundle_id": self.contract.policy_bundle_id,
            },
            revision_identity={
                "git_commit": ctx.revision.git_commit,
                "sysml_project_id": ctx.revision.sysml_project_id,
                "sysml_commit_id": ctx.revision.sysml_commit_id,
                "scope": ctx.revision.scope,
            },
            scope_identity={
                "scope_id": ctx.scope.scope_id,
                "increment_id": ctx.scope.increment_id,
                "usage_ids": list(ctx.scope.usage_ids),
                "profiles": list(ctx.scope.profiles),
            },
            results=tuple(results),
            assessment_coverage=coverage,
            evaluation_state=state,
            conformance_verdict=verdict,
            assessed_ids=counts["assessed_ids"],
            unassessed_ids=counts["unassessed_ids"],
            failed_ids=counts["failed_ids"],
            indeterminate_ids=counts["indeterminate_ids"],
            errored_ids=counts["errored_ids"],
            not_applicable_ids=counts["not_applicable_ids"],
            readiness=readiness,
            diagnostics=tuple(ctx.diagnostics),
            provenance=tuple(provenance),
            units=tuple(combined),
            required_units=tuple(required_ids),
        )


def _combine_unit_result(
    spec: ObligationSpec, children: Sequence[EvaluationResult]
) -> EvaluationResult:
    """Combine per-subject children into one obligation-level result.

    Any unassessed child keeps the unit unassessed (null state/verdict); known
    child results stay individually visible in the reported children.
    """
    if not children:
        return EvaluationResult(
            unit_id=spec.obligation_id,
            coverage=COVERAGE_UNASSESSED,
            state=None,
            verdict=None,
            reason_codes=(NOT_ATTEMPTED,),
            diagnostics=("no subject results were produced",),
            claim_boundary=spec.claim_boundary,
        )
    unassessed = [c for c in children if c.coverage == COVERAGE_UNASSESSED]
    if unassessed:
        diagnostics = tuple(
            d for child in unassessed for d in child.diagnostics
        ) or ("a required child result was not assessed",)
        return EvaluationResult(
            unit_id=spec.obligation_id,
            coverage=COVERAGE_UNASSESSED,
            state=None,
            verdict=None,
            reason_codes=(NOT_ATTEMPTED,),
            diagnostics=diagnostics,
            claim_boundary=spec.claim_boundary,
        )
    if any(child.state == STATE_ERROR for child in children):
        child = next(c for c in children if c.state == STATE_ERROR)
        return EvaluationResult(
            unit_id=spec.obligation_id,
            coverage=COVERAGE_ASSESSED,
            state=STATE_ERROR,
            verdict=None,
            reason_codes=child.reason_codes,
            diagnostics=child.diagnostics,
            claim_boundary=spec.claim_boundary,
        )
    if any(child.state == STATE_INDETERMINATE for child in children):
        child = next(c for c in children if c.state == STATE_INDETERMINATE)
        return EvaluationResult(
            unit_id=spec.obligation_id,
            coverage=COVERAGE_ASSESSED,
            state=STATE_INDETERMINATE,
            verdict=None,
            reason_codes=child.reason_codes,
            diagnostics=child.diagnostics,
            missing=child.missing,
            claim_boundary=spec.claim_boundary,
        )
    if any(child.verdict == VERDICT_FAIL for child in children):
        failing = next(c for c in children if c.verdict == VERDICT_FAIL)
        return EvaluationResult(
            unit_id=spec.obligation_id,
            coverage=COVERAGE_ASSESSED,
            state=STATE_COMPLETE,
            verdict=VERDICT_FAIL,
            reason_codes=failing.reason_codes,
            diagnostics=failing.diagnostics,
            claim_boundary=spec.claim_boundary,
        )
    if all(child.verdict == VERDICT_NOT_APPLICABLE for child in children):
        return EvaluationResult(
            unit_id=spec.obligation_id,
            coverage=COVERAGE_ASSESSED,
            state=STATE_COMPLETE,
            verdict=VERDICT_NOT_APPLICABLE,
            reason_codes=(NOT_APPLICABLE_REASON,),
            diagnostics=children[0].diagnostics,
            claim_boundary=spec.claim_boundary,
        )
    return EvaluationResult(
        unit_id=spec.obligation_id,
        coverage=COVERAGE_ASSESSED,
        state=STATE_COMPLETE,
        verdict=VERDICT_PASS,
        reason_codes=(),
        claim_boundary=spec.claim_boundary,
    )


# ---------------------------------------------------------------------------
# Method discovery (candidate-independent phase_contract)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ApprovedMethodSelection:
    """The configured approved method/policy selection (outside candidate control)."""

    method_id: str
    contract_id: str
    policy_bundle_id: str
    source: str
    contracts: Mapping[str, MethodContract]

    def phase_contract(self, phase: str, candidate_context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Return the approved contract for ``phase``; never a conformance verdict.

        Method-only provenance: no candidate Git/API binding is included or
        fabricated. Obligations are never removed because of candidate state;
        optional candidate context only resolves applicability and never hides
        unresolved obligations (MC-35).
        """
        contract = self.contracts.get(phase)
        response: dict[str, Any] = {
            "query": "phase_contract",
            "method": {
                "method_id": self.method_id,
                "contract_id": self.contract_id,
                "policy_bundle_id": self.policy_bundle_id,
                "source": self.source,
                "provenance": [{"authority": "authoritative", "source": self.source}],
            },
            "phase": phase,
            "executable_contract_available": contract is not None,
        }
        if contract is None:
            response["reason_codes"] = [CONTRACT_UNAVAILABLE]
            response["obligations"] = []
            response["diagnostics"] = [
                f"no reviewed executable contract exists for phase {phase!r}"
            ]
            return response
        response["contract_digest"] = contract.digest()
        obligations: list[dict[str, Any]] = []
        for spec in contract.obligations:
            entry: dict[str, Any] = {
                "obligation_id": spec.obligation_id,
                "subject_selector": spec.subject_selector,
                "subject_type": spec.selector_kind,
                "applicability": spec.applicability,
                "predicate": spec.predicate,
                "target_filters": list(spec.target_filters),
                "cardinality": list(spec.cardinality),
                "minimum_population": spec.minimum_population,
                "permitted_empty": spec.permitted_empty,
                "required": spec.required,
                "evaluation_source": spec.evaluation_source,
                "attestation_policy_ref": spec.attestation_policy_ref,
                "claim_boundary": spec.claim_boundary,
                "depends_on": list(spec.depends_on),
            }
            if candidate_context is not None and spec.applicability_kind == APPLICABILITY_CANDIDATE_SCOPE:
                declared = candidate_context.get("pilot_scope_declared")
                if declared is True:
                    entry["applicability_resolution"] = "applicable"
                elif declared is False:
                    entry["applicability_resolution"] = "not_applicable"
                else:
                    entry["applicability_resolution"] = "unresolved"
                    entry["applicability_missing_inputs"] = list(
                        candidate_context.get("missing_inputs") or ()
                    )
            elif spec.applicability_kind == APPLICABILITY_UNCONDITIONAL:
                entry["applicability_resolution"] = "applicable"
            else:
                entry["applicability_resolution"] = "unresolved"
            obligations.append(entry)
        response["obligations"] = obligations
        return response


def verify_candidate_policy_closure(
    approved: MethodContract, candidate_obligations: Sequence[Mapping[str, str]]
) -> list[str]:
    """Detect candidate modifications of the policy-bearing contract closure.

    ``candidate_obligations`` are the candidate revision's model-resident
    obligation records (as decoded from the API elements). Any divergence from
    the approved contract is a migration blocker; the candidate never
    selects or redefines its own governing contract (MC-23).
    """

    def field(item: Mapping[str, str], *names: str) -> str:
        for name in names:
            value = item.get(name)
            if value is not None:
                return str(value)
        return ""

    mismatches: list[str] = []
    approved_ids = {o.obligation_id for o in approved.obligations}
    candidate_ids = {
        field(item, "obligation_id", "obligationId") for item in candidate_obligations
    }
    candidate_ids.discard("")
    missing = sorted(approved_ids - candidate_ids)
    extra = sorted(candidate_ids - approved_ids)
    if missing:
        mismatches.append(f"candidate closure is missing approved obligations: {missing}")
    if extra:
        mismatches.append(f"candidate closure declares unapproved obligations: {extra}")
    for spec in approved.obligations:
        candidate = next(
            (
                item
                for item in candidate_obligations
                if field(item, "obligation_id", "obligationId") == spec.obligation_id
            ),
            None,
        )
        if candidate is None:
            continue
        observed_predicate = field(candidate, "predicate")
        if observed_predicate and observed_predicate != spec.predicate:
            mismatches.append(
                f"{spec.obligation_id}: candidate predicate "
                f"{observed_predicate!r} differs from approved {spec.predicate!r}"
            )
        for field_names, approved_value in (
            (("cardinality_minimum", "cardinalityMinimum"), spec.cardinality[0]),
            (("cardinality_maximum", "cardinalityMaximum"), spec.cardinality[1]),
        ):
            observed = field(candidate, *field_names)
            if observed and observed != str(approved_value):
                mismatches.append(
                    f"{spec.obligation_id}: candidate {field_names[1]} {observed!r} "
                    f"differs from approved {approved_value!r}"
                )
        observed_required = field(candidate, "required")
        if observed_required and observed_required != str(spec.required).lower():
            mismatches.append(
                f"{spec.obligation_id}: candidate required flag differs from approved"
            )
        observed_policy = field(candidate, "attestation_policy_ref", "attestationPolicyRef")
        if observed_policy != spec.attestation_policy_ref:
            mismatches.append(
                f"{spec.obligation_id}: candidate attestation policy differs from approved"
            )
    return mismatches


# ---------------------------------------------------------------------------
# Manifest identity verification and the C-owned service facade
# ---------------------------------------------------------------------------

#: Evaluator build identity (part of any evaluation manifest; MC-11).
EVALUATOR_BUILD_ID = "de4sdv.method-evaluator/1"


class ManifestMismatchError(RuntimeError):
    """Loaded artifacts do not match the expected evaluation manifest (MC-11)."""

    def __init__(self, mismatches: Sequence[str]) -> None:
        self.mismatches = tuple(mismatches)
        super().__init__(
            "evaluation manifest mismatch; refusing the mismatched evaluation: "
            + "; ".join(mismatches)
        )


def verify_manifest_identity(
    expected: Mapping[str, Any], observed: Mapping[str, Any]
) -> None:
    """Refuse an evaluation whose bound identities differ from the expected ones.

    Compares Git revision, SysML project/commit, method contract digest,
    evaluator build, and governing policy identity (frozen baseline Section 9).
    An updated evaluator or contract yields a different evaluation identity
    even when the verdict is unchanged.
    """
    mismatches: list[str] = []
    for key in sorted(set(expected) | set(observed)):
        if expected.get(key) != observed.get(key):
            mismatches.append(
                f"{key}: expected {expected.get(key)!r}, observed {observed.get(key)!r}"
            )
    if mismatches:
        raise ManifestMismatchError(mismatches)


@dataclass
class MethodConformanceService:
    """Read-only facade over one approved method selection.

    ``increment_status``, ``method_gaps``, and ``next_obligation`` project one
    canonical evaluation per (phase, Git revision, scope) identity; they never
    recompute conflicting states. ``phase_contract`` has method-only
    provenance and works without any candidate.
    """

    selection: ApprovedMethodSelection
    _evaluations: dict[tuple[str, str, str], CanonicalEvaluation] = field(
        default_factory=dict, init=False, repr=False
    )
    evaluation_count: int = field(default=0, init=False)

    def phase_contract(
        self, phase: str, candidate_context: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.selection.phase_contract(phase, candidate_context)

    def evaluation(
        self,
        phase: str,
        context: EvaluationContext,
        *,
        requested_readiness: Sequence[ReadinessTarget] = (),
    ) -> CanonicalEvaluation | None:
        """Canonical evaluation for the phase, or None when no contract exists."""
        contract = self.selection.contracts.get(phase)
        if contract is None:
            return None
        key = (phase, context.revision.git_commit, context.scope.scope_id)
        if key not in self._evaluations:
            self.evaluation_count += 1
            if requested_readiness:
                evaluation = MethodEvaluator(contract).evaluate(
                    context, requested_readiness=requested_readiness
                )
                self._evaluations[key] = evaluation
                return evaluation
            self._evaluations[key] = MethodEvaluator(contract).evaluate(context)
        return self._evaluations[key]

    def _no_contract_payload(
        self,
        query: str,
        phase: str,
        requested_readiness: Sequence[ReadinessTarget],
    ) -> dict[str, Any]:
        response: dict[str, Any] = {
            "query": query,
            "phase": phase,
            "method": {
                "method_id": self.selection.method_id,
                "contract_id": self.selection.contract_id,
                "policy_bundle_id": self.selection.policy_bundle_id,
                "source": self.selection.source,
            },
            "assessment_coverage": COVERAGE_UNASSESSED,
            "evaluation_state": None,
            "conformance_verdict": None,
            "reason_codes": [CONTRACT_UNAVAILABLE],
            "diagnostics": [
                f"no reviewed executable contract exists for phase {phase!r}; "
                "required broader coverage remains unassessed"
            ],
        }
        if requested_readiness:
            response["readiness"] = [
                ReadinessBlock(
                    target=target,
                    readiness="BLOCKED",
                    reason_codes=(CONTRACT_UNAVAILABLE,),
                    diagnostics=(
                        "no executable contract exists for the requested phase",
                    ),
                ).as_dict()
                for target in requested_readiness
            ]
        return response

    def increment_status(
        self,
        phase: str,
        context: EvaluationContext | None = None,
        *,
        requested_readiness: Sequence[ReadinessTarget] = (),
    ) -> dict[str, Any]:
        if context is None:
            return self._no_contract_payload("increment_status", phase, requested_readiness)
        evaluation = self.evaluation(
            phase, context, requested_readiness=requested_readiness
        )
        if evaluation is None:
            return self._no_contract_payload("increment_status", phase, requested_readiness)
        return evaluation.increment_status()

    def method_gaps(
        self, phase: str, context: EvaluationContext | None = None
    ) -> dict[str, Any]:
        if context is None:
            return self._no_contract_payload("method_gaps", phase, ())
        evaluation = self.evaluation(phase, context)
        if evaluation is None:
            return self._no_contract_payload("method_gaps", phase, ())
        return evaluation.method_gaps()

    def next_obligation(
        self, phase: str, context: EvaluationContext | None = None
    ) -> dict[str, Any]:
        if context is None:
            return self._no_contract_payload("next_obligation", phase, ())
        evaluation = self.evaluation(phase, context)
        if evaluation is None:
            return self._no_contract_payload("next_obligation", phase, ())
        return evaluation.next_obligation()
