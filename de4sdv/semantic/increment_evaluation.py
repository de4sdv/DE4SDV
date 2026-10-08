"""One canonical method evaluation per increment, and its projections.

The agent loop is ``next`` -> the agent authors -> ``gaps``: the agent
authors, the deterministic evaluation judges. For one increment and one
model revision this module runs the method gates read from the model through
the existing evaluator once and projects that single canonical evaluation as

- ``status``: per phase, the aggregate verdict and the phase-exit readiness;
- ``gaps``: unmet blocking gates (violations, input problems, method-side
  blockers, unattempted gates and what blocks them) plus advisory notes;
- ``next``: the first actionable blocking gate, ranked by gate prerequisites
  (depth in the prerequisite graph, then phase, then gate order), with what
  to author and where;
- ``phase_contract``: the gates of a phase with the increment's
  applicability, no verdict.

All projections carry the same evaluation key. A model revision without
gates is UNASSESSED with ``CONTRACT_UNAVAILABLE``; invalid gates are an
evaluation ERROR with ``INVALID_CONTRACT`` (frozen baseline Section 8).
Results describe model content only; no acceptance, compliance or
certification claim follows from them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from . import method_evaluator as me
from .gate_reader import PHASE_ORDER, UNBOUNDED, GateSet, read_method_gates
from .increment_scope import IncrementScope, ModelView, resolve_increment
from .method_checks import IncrementEvaluationContext
from .relation_checks import METHOD_SIDE_PREFIXES

CLAIM_BOUNDARY = (
    "model-content gates of the method declared in the evaluated revision; no acceptance, "
    "compliance, certification or evidence-adequacy claim"
)
KIND_VIOLATION = "violation"
KIND_INPUT = "input-problem"
KIND_METHOD_SIDE = "method-side"
KIND_NOT_ATTEMPTED = "not-attempted"


@dataclass
class IncrementEvaluation:
    """The canonical evaluation of one increment at one revision."""

    increment_id: str
    revision: me.RevisionIdentity
    gate_set: GateSet
    scope: IncrementScope
    view: ModelView
    canonical: me.CanonicalEvaluation | None

    # -- identity -------------------------------------------------------------

    @property
    def evaluation_key(self) -> str:
        if self.canonical is not None:
            return self.canonical.evaluation_key
        payload = {
            "increment_id": self.increment_id,
            "revision": _revision(self.revision),
            "method": dict(self.gate_set.method_identity),
            "reason": self.gate_set.reason,
            "problems": list(self.gate_set.problems),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def _header(self, query: str) -> dict[str, Any]:
        return {
            "query": query,
            "evaluation_key": self.evaluation_key,
            "increment": self._increment_block(),
            "method": self._method_block(),
            "revision": _revision(self.revision),
            "claim_boundary": CLAIM_BOUNDARY,
        }

    def _increment_block(self) -> dict[str, Any]:
        scope = self.scope
        block: dict[str, Any] = {
            "id": scope.increment_id,
            "resolved": scope.usage_id is not None,
            "declared_phases": list(scope.declared_phases) if scope.declared_phases is not None else None,
            "diagnostics": list(scope.diagnostics),
        }
        if scope.usage_id:
            block["usage"] = self.view.describe(scope.usage_id)
        if scope.package_id:
            block["package"] = self.view.describe(scope.package_id)
        if len(scope.charters) == 1:
            block["charter"] = self.view.describe(scope.charters[0])
        block["populations"] = {
            selector: len(members) for selector, members in scope.populations.items()
        }
        return block

    def _method_block(self) -> dict[str, Any]:
        block = dict(self.gate_set.method_identity)
        block["executable_contract_available"] = self.gate_set.available
        if self.gate_set.problems:
            block["problems"] = list(self.gate_set.problems)
        if self.gate_set.other_obligations:
            block["other_model_obligations"] = list(self.gate_set.other_obligations)
        return block

    def _unavailable(self, query: str) -> dict[str, Any]:
        response = self._header(query)
        invalid = bool(self.gate_set.problems)
        response.update(
            executable_contract_available=False,
            assessment_coverage=me.COVERAGE_ASSESSED if invalid else me.COVERAGE_UNASSESSED,
            evaluation_state=me.STATE_ERROR if invalid else None,
            conformance_verdict=None,
            reason_codes=[me.INVALID_CONTRACT if invalid else me.CONTRACT_UNAVAILABLE],
            diagnostics=[self.gate_set.reason],
        )
        return response

    # -- shared structure -------------------------------------------------------

    def _contract(self) -> me.MethodContract:
        assert self.gate_set.contract is not None
        return self.gate_set.contract

    def _phases(self, phase: str | None) -> list[str]:
        phases = list(self.gate_set.phases)
        if phase is None:
            return phases
        if phase not in PHASE_ORDER:
            raise ValueError(f"{phase!r} is not a MethodPhase literal")
        return [p for p in phases if p == phase]

    def _gates(self, phase: str | None = None) -> list[me.ObligationSpec]:
        return [g for g in self._contract().obligations if phase is None or g.phase == phase]

    def _unit(self, gate_id: str) -> me.EvaluationResult:
        assert self.canonical is not None
        return next(u for u in self.canonical.units if u.unit_id == gate_id)

    def _children(self, gate_id: str) -> list[me.EvaluationResult]:
        assert self.canonical is not None
        return [r for r in self.canonical.results if r.unit_id == gate_id]

    def _required(self, ids: Sequence[str]) -> list[str]:
        assert self.canonical is not None
        required = set(self.canonical.required_units)
        return [unit_id for unit_id in ids if unit_id in required]

    def _aggregate(self, ids: Sequence[str]) -> tuple[str, str | None, str | None]:
        """Aggregate of the given gates; an empty required inventory is UNASSESSED."""
        assert self.canonical is not None
        if not self._required(ids):
            return me.COVERAGE_UNASSESSED, None, None
        return me.subset_aggregate(self._contract(), self.canonical, ids)

    def _phase_exit(self, phase: str, ids: Sequence[str]) -> me.ReadinessBlock:
        """Phase-exit readiness; an empty required inventory never opens an exit."""
        assert self.canonical is not None
        target = me.ReadinessTarget("PHASE_EXIT", f"{self.increment_id}/{phase}")
        if not self._required(ids):
            return me.ReadinessBlock(
                target=target, readiness="BLOCKED", reason_codes=(me.CONTRACT_UNAVAILABLE,),
                diagnostics=(f"no blocking gate is declared for {phase}; an empty required "
                             "inventory cannot authorize a phase exit",),
            )
        return me.subset_readiness(self.canonical, ids, target)

    def _depths(self) -> dict[str, int]:
        gates = {g.obligation_id: g for g in self._contract().obligations}
        depth: dict[str, int] = {}

        def of(gate_id: str) -> int:
            if gate_id not in depth:
                depth[gate_id] = 0
                depth[gate_id] = 1 + max((of(d) for d in gates[gate_id].depends_on if d in gates), default=-1)
            return depth[gate_id]

        for gate_id in gates:
            of(gate_id)
        return depth

    def _kind(self, unit: me.EvaluationResult) -> str | None:
        """Gap kind of one gate unit (None when the gate passes or is not applicable)."""
        if unit.coverage == me.COVERAGE_UNASSESSED:
            return KIND_NOT_ATTEMPTED
        if unit.verdict in {me.VERDICT_PASS, me.VERDICT_NOT_APPLICABLE}:
            return None
        if unit.verdict == me.VERDICT_FAIL:
            return KIND_VIOLATION
        children = [c for c in self._children(unit.unit_id) if c.state in {me.STATE_INDETERMINATE, me.STATE_ERROR}]
        if children and all(_method_side(child) for child in children):
            return KIND_METHOD_SIDE
        if not children and _method_side(unit):
            return KIND_METHOD_SIDE
        return KIND_INPUT

    def _entry(self, gate: me.ObligationSpec, kind: str) -> dict[str, Any]:
        unit = self._unit(gate.obligation_id)
        entry: dict[str, Any] = {
            "gate": gate.obligation_id,
            "phase": gate.phase,
            "predicate": gate.predicate,
            "target_filters": list(gate.target_filters),
            "required": gate.required,
            "kind": kind,
            "assessment_coverage": unit.coverage,
            "evaluation_state": unit.state,
            "conformance_verdict": unit.verdict,
            "reason_codes": list(unit.reason_codes),
            "claim_boundary": gate.claim_boundary,
        }
        if kind == KIND_NOT_ATTEMPTED:
            entry["blocked_by"] = [
                d for d in gate.depends_on
                if self._unit(d).verdict not in {me.VERDICT_PASS, me.VERDICT_NOT_APPLICABLE}
            ]
            entry["diagnostics"] = list(unit.diagnostics)
            return entry
        subjects = []
        for child in self._children(gate.obligation_id):
            if child.verdict in {me.VERDICT_PASS, me.VERDICT_NOT_APPLICABLE}:
                continue
            subjects.append(self._subject(child))
        if not subjects:
            entry["diagnostics"] = list(unit.diagnostics)
            entry["missing"] = list(unit.missing)
        entry["subjects"] = subjects
        if kind in {KIND_VIOLATION, KIND_INPUT}:
            first = next((c.subject_id for c in self._children(gate.obligation_id)
                          if c.verdict == me.VERDICT_FAIL or c.state in {me.STATE_INDETERMINATE, me.STATE_ERROR}),
                         None)
            entry["what_to_author"] = self.gate_set.remedy(gate, increment=self.scope, view=self.view,
                                             subject_id=_element_subject(first, self.view))
            entry["where"] = self._where(subjects)
        return entry

    def _subject(self, child: me.EvaluationResult) -> dict[str, Any]:
        subject_id = child.subject_id
        record: dict[str, Any] = (
            self.view.describe(subject_id) if subject_id in self.view.index.by_id
            else {"element_id": None, "name": str(subject_id or "")}
        )
        record.update(
            evaluation_state=child.state,
            conformance_verdict=child.verdict,
            reason_codes=list(child.reason_codes),
            diagnostics=list(child.diagnostics),
        )
        if child.missing:
            record["missing"] = list(child.missing)
        if child.targets:
            record["targets"] = list(child.targets)
        return record

    def _where(self, subjects: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        package = self.view.describe(self.scope.package_id) if self.scope.package_id else None
        modules = sorted({
            self.view.index.qualified_name(top)
            for s in subjects
            if s.get("element_id") and (top := self.view.top_package(s["element_id"]))
        })
        where: dict[str, Any] = {"increment_package": package}
        if modules:
            where["packages"] = modules
        return where

    def _presented(self, response: dict[str, Any]) -> dict[str, Any]:
        """Attach input-dependent presentation data outside the canonical payload."""
        if not self.view.sources:
            return response
        referenced = set(_element_ids(response))
        sources = {i: self.view.source_of(i) for i in sorted(referenced) if self.view.source_of(i)}
        if sources:
            response["presentation"] = {
                "element_sources": sources,
                "note": "serializer-recorded source files of the evaluated export; presentation "
                        "data outside the canonical payload",
            }
        return response

    # -- projections -----------------------------------------------------------

    def status(self, phase: str | None = None) -> dict[str, Any]:
        """Per-phase aggregate and phase-exit readiness."""
        if self.canonical is None:
            return self._unavailable("increment_status")
        response = self._header("increment_status")
        phases = self._phases(phase)
        selected = [g.obligation_id for p in phases for g in self._gates(p)]
        coverage, state, verdict = self._aggregate(selected)
        response.update(
            executable_contract_available=True,
            assessment_coverage=coverage,
            evaluation_state=state,
            conformance_verdict=verdict,
            phases=[self._phase_status(p) for p in phases],
            provenance=[dict(item) for item in self.canonical.provenance],
        )
        if not self._required(selected):
            response["reason_codes"] = [me.CONTRACT_UNAVAILABLE]
            response["diagnostics"] = [
                f"no blocking gate is declared for {phase}" if phase
                else "the method declares no blocking gate"
            ]
        return self._presented(response)

    def _phase_status(self, phase: str) -> dict[str, Any]:
        assert self.canonical is not None
        gates = self._gates(phase)
        ids = [g.obligation_id for g in gates]
        coverage, state, verdict = self._aggregate(ids)
        readiness = self._phase_exit(phase, ids)
        blocking, advisory = [], []
        for gate in gates:
            kind = self._kind(self._unit(gate.obligation_id))
            if kind is None:
                continue
            (blocking if gate.required else advisory).append({"gate": gate.obligation_id, "kind": kind})
        return {
            "phase": phase,
            "applicability": self._applicability(gates, phase),
            "assessment_coverage": coverage,
            "evaluation_state": state,
            "conformance_verdict": verdict,
            "phase_exit": readiness.readiness,
            "readiness": readiness.as_dict(),
            "gates": {g.obligation_id: _state_label(self._unit(g.obligation_id)) for g in gates},
            "blocking": blocking,
            "advisory_open": advisory,
        }

    def _applicability(self, gates: Sequence[me.ObligationSpec], phase: str) -> str:
        if all(g.applicability_kind == me.APPLICABILITY_UNCONDITIONAL for g in gates):
            return "unconditional"
        declared = self.scope.declared_phases
        if declared is None:
            return "unresolved"
        return "declared" if phase in declared else "not declared"

    def gaps(self, phase: str | None = None) -> dict[str, Any]:
        """Unmet blocking gates and advisory notes."""
        if self.canonical is None:
            response = self._unavailable("method_gaps")
            response.update(blocking=[], advisory=[])
            return response
        response = self._header("method_gaps")
        blocking, advisory = [], []
        for p in self._phases(phase):
            for gate in self._gates(p):
                kind = self._kind(self._unit(gate.obligation_id))
                if kind is None:
                    continue
                (blocking if gate.required else advisory).append(self._entry(gate, kind))
        counts: dict[str, int] = {}
        for entry in blocking:
            counts[entry["kind"]] = counts.get(entry["kind"], 0) + 1
        response.update(blocking=blocking, advisory=advisory, counts=counts)
        return self._presented(response)

    def next_obligation(self, phase: str | None = None) -> dict[str, Any]:
        """The first actionable blocking gate, ranked by gate prerequisites."""
        if self.canonical is None:
            response = self._unavailable("next_obligation")
            response.update(next=None, reason=self.gate_set.reason, stage_queue=[], method_side_blockers=[])
            return response
        response = self._header("next_obligation")
        depths = self._depths()
        order = {g.obligation_id: i for i, g in enumerate(self._contract().obligations)}
        actionable: list[tuple[tuple[int, int, int], me.ObligationSpec, str]] = []
        method_side: list[dict[str, Any]] = []
        for p in self._phases(phase):
            for gate in self._gates(p):
                if not gate.required:
                    continue
                kind = self._kind(self._unit(gate.obligation_id))
                if kind in {KIND_VIOLATION, KIND_INPUT}:
                    rank = (depths[gate.obligation_id], PHASE_ORDER.get(gate.phase, 99), order[gate.obligation_id])
                    actionable.append((rank, gate, kind))
                elif kind == KIND_METHOD_SIDE:
                    unit = self._unit(gate.obligation_id)
                    missing = sorted({m for c in self._children(gate.obligation_id) for m in c.missing}
                                     | set(unit.missing))
                    method_side.append({"gate": gate.obligation_id, "phase": gate.phase, "missing": missing})
        actionable.sort(key=lambda item: item[0])
        queue: list[dict[str, Any]] = []
        for _rank, gate, _kind in actionable:
            if not queue or queue[-1]["phase"] != gate.phase:
                if any(entry["phase"] == gate.phase for entry in queue):
                    next(entry for entry in queue if entry["phase"] == gate.phase)["gates"].append(gate.obligation_id)
                    continue
                queue.append({"phase": gate.phase, "gates": []})
            queue[-1]["gates"].append(gate.obligation_id)
        for entry in queue:
            entry["phase_exit"] = self._phase_exit(
                entry["phase"], [g.obligation_id for g in self._gates(entry["phase"])]
            ).readiness
        step = None
        reason = ""
        if actionable:
            _rank, gate, kind = actionable[0]
            entry = self._entry(gate, kind)
            step = {
                "stage": gate.phase,
                "gate": gate.obligation_id,
                "kind": kind,
                "predicate": gate.predicate,
                "claim_boundary": gate.claim_boundary,
                "what_to_author": entry.get("what_to_author", ""),
                "where": entry.get("where", {}),
                "subjects": entry.get("subjects", []),
                "prerequisites": list(gate.depends_on),
            }
        elif method_side:
            reason = ("no gate the agent can author is open; the remaining blockers need a method or "
                      "kernel change")
        elif phase is not None and not self._phases(phase):
            reason = f"no gate is declared for {phase}"
        else:
            reason = "every required gate passes or is not applicable"
        response.update(next=step, reason=reason, stage_queue=queue, method_side_blockers=method_side)
        return self._presented(response)

    def phase_contract(self, phase: str | None = None) -> dict[str, Any]:
        """The gates of the method (or one phase) with this increment's applicability."""
        return phase_contract_response(self.gate_set, self.view, self.revision, phase=phase, scope=self.scope)


def phase_contract_response(
    gate_set: GateSet,
    view: ModelView,
    revision: me.RevisionIdentity,
    *,
    phase: str | None = None,
    scope: IncrementScope | None = None,
) -> dict[str, Any]:
    """Candidate-independent discovery of the method gates; never a verdict.

    With an increment scope, each gate also carries the increment's
    applicability resolution; without one, the gates are listed as declared.
    """
    if phase is not None and phase not in PHASE_ORDER:
        raise ValueError(f"{phase!r} is not a MethodPhase literal")
    method = dict(gate_set.method_identity)
    method["executable_contract_available"] = gate_set.available
    if gate_set.problems:
        method["problems"] = list(gate_set.problems)
    if gate_set.other_obligations:
        method["other_model_obligations"] = list(gate_set.other_obligations)
    response: dict[str, Any] = {
        "query": "phase_contract",
        "method": method,
        "method_provenance": [{"authority": "authoritative", "source": f"git://{revision.git_commit}"}],
        "phase": phase,
    }
    if scope is not None:
        response["increment"] = {
            "id": scope.increment_id,
            "resolved": scope.usage_id is not None,
            "declared_phases": list(scope.declared_phases) if scope.declared_phases is not None else None,
        }
    if gate_set.contract is None:
        response.update(executable_contract_available=False, phases=[], gates=[],
                        reason_codes=[me.INVALID_CONTRACT if gate_set.problems else me.CONTRACT_UNAVAILABLE],
                        diagnostics=[gate_set.reason])
        return response
    contract = me.decode_contract_filters(gate_set.contract, gate_set.predicates)
    phases = [p for p in gate_set.phases if phase is None or p == phase]
    gates = [_gate_record(gate, view, scope, gate_set) for p in phases
             for gate in contract.obligations if gate.phase == p]
    response.update(executable_contract_available=bool(gates), phases=phases, gates=gates,
                    contract_digest=gate_set.contract.digest())
    if not gates:
        response["reason_codes"] = [me.CONTRACT_UNAVAILABLE]
        response["diagnostics"] = [f"no gate is declared for {phase}"]
    return response


def _gate_record(gate: me.ObligationSpec, view: ModelView, scope: IncrementScope | None,
                 gate_set: GateSet) -> dict[str, Any]:
    record: dict[str, Any] = {
        "obligation_id": gate.obligation_id,
        "phase": gate.phase,
        "subject_selector": gate.subject_selector,
        "predicate": gate.predicate,
        "target_filters": list(gate.target_filters),
        "typed_filters": [
            {"kind": f.kind, "argument": f.argument, "values": list(f.values)} for f in gate.filters
        ],
        "cardinality": [gate.cardinality[0], "*" if gate.cardinality[1] >= UNBOUNDED else gate.cardinality[1]],
        "minimum_population": gate.minimum_population,
        "permitted_empty": gate.permitted_empty,
        "required": gate.required,
        "applicability": gate.applicability,
        "prerequisites": list(gate.depends_on),
        "claim_boundary": gate.claim_boundary,
    }
    record.update(gate_set.labels.get(gate.obligation_id, {}))
    if scope is None:
        return record
    record["what_satisfies"] = gate_set.remedy(gate, increment=scope, view=view)
    if gate.applicability_kind == me.APPLICABILITY_UNCONDITIONAL:
        record["applicability_resolution"] = "applicable"
    elif scope.declared_phases is None:
        record["applicability_resolution"] = "unresolved"
        record["applicability_missing_inputs"] = ["charter declaration applicablePhases"]
    else:
        record["applicability_resolution"] = "applicable" if gate.phase in scope.declared_phases else "not_applicable"
    return record


def evaluate_increment(
    view: ModelView,
    increment_id: str,
    *,
    revision: me.RevisionIdentity,
    gates: GateSet | None = None,
) -> IncrementEvaluation:
    """Evaluate one increment against the method gates of ``view`` (or ``gates``)."""
    gate_set = gates if gates is not None else read_method_gates(view, revision_label=revision.git_commit)
    scope = resolve_increment(view, increment_id)
    canonical = None
    if gate_set.contract is not None:
        ctx = IncrementEvaluationContext(
            revision=revision,
            elements=(),
            scope=me.DeclaredEvaluationScope(
                scope_id=scope.increment_id,
                increment_id=scope.increment_id,
                usage_ids=(scope.usage_id,) if scope.usage_id else (),
                contribution_ids=frozenset(),
                profiles=(),
                scope_element_id=scope.usage_id,
            ),
            declared_phases=frozenset(scope.declared_phases) if scope.declared_phases is not None else None,
            candidate_missing_inputs=("charter declaration applicablePhases",),
            diagnostics=tuple(scope.diagnostics),
            model=view,
            increment=scope,
        )
        evaluator = me.MethodEvaluator(gate_set.contract, predicates=gate_set.predicates,
                                       selectors=gate_set.selectors)
        canonical = evaluator.evaluate(ctx)
    return IncrementEvaluation(
        increment_id=scope.increment_id, revision=revision, gate_set=gate_set, scope=scope,
        view=view, canonical=canonical,
    )


def _revision(revision: me.RevisionIdentity) -> dict[str, str]:
    return {
        "git_commit": revision.git_commit,
        "sysml_project_id": revision.sysml_project_id,
        "sysml_commit_id": revision.sysml_commit_id,
        "scope": revision.scope,
    }


def _method_side(result: me.EvaluationResult) -> bool:
    return any(str(item).startswith(METHOD_SIDE_PREFIXES) for item in result.missing)


def _state_label(unit: me.EvaluationResult) -> str:
    return unit.verdict or unit.state or unit.coverage


def _element_ids(value: Any) -> list[str]:
    """Every ``element_id`` value inside a response."""
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "element_id" and isinstance(item, str) and item:
                found.append(item)
            else:
                found.extend(_element_ids(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(_element_ids(item))
    return found


def _element_subject(subject_id: str | None, view: ModelView) -> str | None:
    return subject_id if subject_id and subject_id in view.index.by_id else None
