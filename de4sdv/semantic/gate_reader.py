"""Read the method gates of one model revision into a method contract.

Method gates are MethodContractObligation-lineage usages (ingestion-validated
kernel identity, ADR 0011) whose subject selector is a typed increment
selector. Their attributes decode into one contract spanning the gate phases:
phase literals, selector, applicability, population policy, predicate and
filter text, cardinality, blocking flag, evaluation source, claim boundary,
and the gate prerequisites. The contract is validated against the gate
predicate and selector registries before any evaluation; a problem in any
gate makes the method invalid rather than silently dropping the gate.

Other model obligations (for example the phase-10 obligations of a declared
pilot scope) are not increment gates; they are listed, not evaluated here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from de4sdv.sysml_api.errors import IdentityNotFoundError

from . import method_evaluator as me
from .gate_predicates import GATE_PREDICATES, GATE_SELECTORS
from .increment_scope import INCREMENT_SELECTORS, ModelView
from .method_trace_adapter import CANONICAL_PHASE_LITERALS

#: Upper cardinality bound for an unbounded (``*``) gate maximum.
UNBOUNDED = 1_000_000
METHOD_ID = "de4sdv.method-gates"
OBLIGATION_CLASS = "MethodContractObligation"
PHASE_ORDER = {literal: number for number, literal in CANONICAL_PHASE_LITERALS.items()}

_APPLICABILITY = {
    "unconditional": me.APPLICABILITY_UNCONDITIONAL,
    "increment declares the gate phase": me.APPLICABILITY_DECLARED_PHASE,
}
_EVALUATION_SOURCES = {
    "pinnedModelRecord": me.EVALUATION_SOURCE_MODEL,
    "pinnedRepositoryArtifact": me.EVALUATION_SOURCE_REPOSITORY,
    "liveDeliveryAdapter": me.EVALUATION_SOURCE_LIVE,
}
_DISPOSITIONS = {
    "noEligibleSubjects": me.NO_ELIGIBLE_SUBJECTS,
    "explicitDisposition": me.EXPLICIT_DISPOSITION,
}


@dataclass(frozen=True)
class GateSet:
    """The method gates of one revision and the contract they form."""

    method_identity: Mapping[str, Any]
    contract: me.MethodContract | None
    phases: tuple[str, ...] = ()
    gate_elements: Mapping[str, str] = field(default_factory=dict)
    other_obligations: tuple[str, ...] = ()
    problems: tuple[str, ...] = ()
    reason: str = ""

    @property
    def available(self) -> bool:
        return self.contract is not None


class _Undecodable(ValueError):
    pass


def read_method_gates(view: ModelView, *, revision_label: str) -> GateSet:
    """Decode the gates of ``view`` (a model revision) into one contract."""
    identity = {"method_id": METHOD_ID, "method_revision": revision_label}
    index = view.index
    try:
        view.kernel_element(OBLIGATION_CLASS)
        candidates = [
            element for element in index.elements_of_type("ItemUsage")
            if view.in_lineage(element, OBLIGATION_CLASS)
        ]
    except IdentityNotFoundError as error:
        return GateSet(method_identity=identity, contract=None,
                       reason=f"method gates cannot be read: kernel-binding:{OBLIGATION_CLASS}: {error}")
    try:
        phase_root = view.kernel_element("MethodPhase")
    except IdentityNotFoundError:
        phase_root = None
    try:
        source_root = view.kernel_element("EvaluationSourceKind")
    except IdentityNotFoundError:
        source_root = None

    gates: list[me.ObligationSpec] = []
    elements: dict[str, str] = {}
    others: list[str] = []
    problems: list[str] = []
    prerequisite_refs: dict[str, list[str]] = {}
    by_element: dict[str, str] = {}
    for element in candidates:
        label = index.qualified_name(element) or element
        try:
            fields = _decode_fields(view, element, phase_root, source_root)
        except _Undecodable as error:
            problems.append(f"{label}: {error}")
            continue
        selector = fields["subjectSelector"]
        if selector not in INCREMENT_SELECTORS:
            others.append(fields["obligationId"])
            continue
        applicability = _APPLICABILITY.get(fields["applicability"])
        if applicability is None:
            problems.append(f"{fields['obligationId']}: unsupported applicability {fields['applicability']!r}")
            continue
        maximum = fields["cardinalityMaximum"]
        gate = me.ObligationSpec(
            obligation_id=fields["obligationId"],
            phase=fields["phase"],
            subject_selector=selector,
            selector_kind=selector,
            applicability=fields["applicability"],
            applicability_kind=applicability,
            minimum_population=fields["minimumPopulation"],
            permitted_empty=fields["permittedEmpty"],
            permitted_empty_disposition=fields.get("permittedEmptyDisposition"),
            predicate=fields["predicate"],
            target_filters=(fields["targetFilter"],) if fields["targetFilter"] else (),
            cardinality=(fields["cardinalityMinimum"], UNBOUNDED if maximum is None else maximum),
            required=fields["required"],
            evaluation_source=fields["evaluationSource"],
            attestation_policy_ref=fields["attestationPolicyRef"],
            claim_boundary=fields["claimBoundary"],
        )
        if gate.obligation_id in elements:
            problems.append(f"duplicate gate identifier {gate.obligation_id!r}")
            continue
        gates.append(gate)
        elements[gate.obligation_id] = element
        by_element[element] = gate.obligation_id
        prerequisite_refs[gate.obligation_id] = [
            leaf.value for leaf in index.feature_values(element, "prerequisites") if leaf.kind == "reference"
        ]

    resolved: list[me.ObligationSpec] = []
    for gate in gates:
        prerequisites = []
        for reference in prerequisite_refs[gate.obligation_id]:
            if reference not in by_element:
                problems.append(f"{gate.obligation_id}: prerequisite {index.qualified_name(reference) or reference} "
                                "is not a method gate")
                continue
            prerequisites.append(by_element[reference])
        resolved.append(_with_prerequisites(gate, prerequisites))
    if not resolved and not problems:
        return GateSet(method_identity=identity, contract=None, other_obligations=tuple(sorted(others)),
                       reason="the model revision declares no method gates")
    phases = tuple(sorted({gate.phase for gate in resolved}, key=lambda p: PHASE_ORDER.get(p, 99)))
    contract = me.MethodContract(
        method_id=METHOD_ID,
        contract_id=f"{METHOD_ID}@{revision_label}",
        phase=",".join(phases),
        obligations=tuple(_ordered(resolved)),
    )
    try:
        me.validate_contract(contract, predicates=GATE_PREDICATES, selectors=GATE_SELECTORS)
    except me.ContractValidationError as error:
        problems.extend(error.violations)
    if problems:
        return GateSet(method_identity=identity, contract=None, phases=phases, gate_elements=elements,
                       other_obligations=tuple(sorted(others)), problems=tuple(problems),
                       reason="the method gates are invalid")
    return GateSet(
        method_identity={**identity, "contract_id": contract.contract_id,
                         "contract_digest": contract.digest()},
        contract=contract,
        phases=phases,
        gate_elements=elements,
        other_obligations=tuple(sorted(others)),
    )


def _with_prerequisites(gate: me.ObligationSpec, prerequisites: list[str]) -> me.ObligationSpec:
    from dataclasses import replace

    return replace(gate, depends_on=tuple(sorted(set(prerequisites))))


def _ordered(gates: list[me.ObligationSpec]) -> list[me.ObligationSpec]:
    """Phase order, then prerequisite depth, then identifier (corpus-independent)."""
    by_id = {gate.obligation_id: gate for gate in gates}
    depth: dict[str, int] = {}

    def depth_of(gate_id: str, trail: frozenset[str] = frozenset()) -> int:
        if gate_id in depth:
            return depth[gate_id]
        if gate_id in trail or gate_id not in by_id:
            return 0
        value = 1 + max((depth_of(d, trail | {gate_id}) for d in by_id[gate_id].depends_on), default=-1)
        depth[gate_id] = value
        return value

    return sorted(gates, key=lambda g: (PHASE_ORDER.get(g.phase, 99), depth_of(g.obligation_id), g.obligation_id))


def _single(view: ModelView, element: str, name: str) -> Any:
    leaves = view.index.feature_values(element, name)
    if len(leaves) != 1:
        raise _Undecodable(f"{name} carries {len(leaves)} values; exactly one is required")
    return leaves[0]


def _text(view: ModelView, element: str, name: str) -> str:
    leaf = _single(view, element, name)
    if leaf.kind != "string":
        raise _Undecodable(f"{name} is not a String value")
    return str(leaf.value or "")


def _natural(view: ModelView, element: str, name: str, *, unbounded: bool = False) -> int | None:
    leaf = _single(view, element, name)
    if unbounded and leaf.kind == "infinity":
        return None
    if leaf.kind != "integer" or isinstance(leaf.value, bool) or int(leaf.value) < 0:
        raise _Undecodable(f"{name} is not a Natural value")
    return int(leaf.value)


def _boolean(view: ModelView, element: str, name: str) -> bool:
    leaf = _single(view, element, name)
    if leaf.kind != "boolean":
        raise _Undecodable(f"{name} is not a Boolean value")
    return bool(leaf.value)


def _literal(view: ModelView, element: str, name: str, root: str | None) -> str:
    leaf = _single(view, element, name)
    if leaf.kind != "reference" or (root is not None and view.index.owner_of(leaf.value) != root):
        raise _Undecodable(f"{name} is not a literal of its enumeration")
    return view.index.name_of(leaf.value)


def _decode_fields(view: ModelView, element: str, phase_root: str | None,
                   source_root: str | None) -> dict[str, Any]:
    if phase_root is None:
        raise _Undecodable("MethodPhase has no validated kernel binding")
    phase = _literal(view, element, "phase", phase_root)
    if phase not in PHASE_ORDER:
        raise _Undecodable(f"phase {phase!r} is not a MethodPhase literal")
    source = _literal(view, element, "evaluationSource", source_root)
    if source not in _EVALUATION_SOURCES:
        raise _Undecodable(f"evaluationSource {source!r} is not an EvaluationSourceKind literal")
    fields: dict[str, Any] = {
        "obligationId": _text(view, element, "obligationId"),
        "phase": phase,
        "subjectSelector": _text(view, element, "subjectSelector"),
        "applicability": _text(view, element, "applicability"),
        "minimumPopulation": _natural(view, element, "minimumPopulation"),
        "permittedEmpty": _boolean(view, element, "permittedEmpty"),
        "predicate": _text(view, element, "predicate"),
        "targetFilter": _text(view, element, "targetFilter"),
        "cardinalityMinimum": _natural(view, element, "cardinalityMinimum"),
        "cardinalityMaximum": _natural(view, element, "cardinalityMaximum", unbounded=True),
        "required": _boolean(view, element, "required"),
        "evaluationSource": _EVALUATION_SOURCES[source],
        "attestationPolicyRef": _text(view, element, "attestationPolicyRef"),
        "claimBoundary": _text(view, element, "claimBoundary"),
    }
    if not fields["obligationId"]:
        raise _Undecodable("obligationId is empty")
    if view.index.feature_values(element, "permittedEmptyDisposition"):
        disposition = _literal(view, element, "permittedEmptyDisposition", None)
        if disposition not in _DISPOSITIONS:
            raise _Undecodable(f"permittedEmptyDisposition {disposition!r} is not a disposition literal")
        fields["permittedEmptyDisposition"] = _DISPOSITIONS[disposition]
    return fields
