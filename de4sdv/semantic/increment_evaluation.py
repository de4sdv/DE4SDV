"""One canonical method evaluation per increment, and its projections.

The agent loop is ``next`` -> the agent authors -> ``gaps``: the agent
authors, the deterministic evaluation judges. For one increment and one
model revision this module runs the method gates read from the model through
the existing evaluator once and projects that single canonical evaluation as

- ``status``: per phase, the aggregate verdict and the phase-exit readiness;
- ``gaps``: unmet blocking gates (violations, input problems, method-side
  blockers) plus advisory notes;
- ``next``: the first actionable blocking gate in workflow order (step
  order, then check order), with what to author and where;
- ``phase_contract``: the gates of a phase with the increment's
  applicability, no verdict.

All projections carry the same evaluation key. A model revision without
gates is UNASSESSED with ``CONTRACT_UNAVAILABLE``; invalid gates are an
evaluation ERROR with ``INVALID_CONTRACT`` (frozen baseline Section 8).

Every answer states what it covers. ``phase_contract`` lists every workflow
step with what it declares, with or without checks; ``status`` lists each
phase the charter declares whose step has no checks as "no executable checks
at this revision" (UNASSESSED, its exit BLOCKED: a phase without an
executable contract never disappears); the evaluation answers carry
``coverage``. An increment the evaluated revision does not declare carries
the answer-level reason ``INCREMENT_NOT_DECLARED`` with a message naming the
revision. None of this changes the contract, the evaluation or its key.
Results describe model content only; no acceptance, compliance or
certification claim follows from them.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from . import method_evaluator as me
from .increment_workflow import (
    OWN_PACKAGE_SELECTOR,
    PHASE_ORDER,
    UNBOUNDED,
    WORKFLOW_SELECTORS,
    IncrementMethod,
    read_increment_method,
)
from .increment_scope import IDENTITY_PROBLEM, PROBLEM_UNAVAILABLE, IncrementScope, ModelView, resolve_increment
from .method_checks import IncrementEvaluationContext, remedy
from .relation_checks import METHOD_SIDE_PREFIXES

CLAIM_BOUNDARY = (
    "model-content gates of the method declared in the evaluated revision; no acceptance, "
    "compliance, certification or evidence-adequacy claim"
)
KIND_VIOLATION = "violation"
KIND_INPUT = "input-problem"
KIND_METHOD_SIDE = "method-side"
#: Coverage of a workflow step or phase: whether executable checks judge what it declares.
EXECUTABLE_CHECKS = "executable checks at this revision"
NO_EXECUTABLE_CHECKS = "no executable checks at this revision"
COVERAGE_NOTE = ("the verdicts, gaps and next cover only the phases with executable checks at this revision; "
                 "a declared phase without executable checks is reported, never evaluated")
#: Answer-level reason, not a reason of the result algebra: no increment usage carries the requested
#: identifier at the evaluated revision. Content on another branch or commit is invisible to it.
INCREMENT_NOT_DECLARED = "INCREMENT_NOT_DECLARED"
NEXT_REASON = "the first open blocking check in workflow order (step order, then check order)"
NONE_OPEN_REASON = "every required gate passes or is not applicable"
#: What the bounds of a phase_contract gate count (a claim of "at least one ..." reads on one of them).
CONTRACT_LEGEND = {
    "population": "[lower, upper] number of subjects: the elements conforming to the step parameter the "
                  "check is about, bounded by that parameter's multiplicity; * is unbounded",
    "cardinality": "[lower, upper] number of distinct targets each subject must reach through the check; "
                   "* is unbounded",
    "steps": "every workflow step in method order, with what it declares; a step whose coverage is "
             "'no executable checks at this revision' is never evaluated",
}


@dataclass
class IncrementEvaluation:
    """The canonical evaluation of one increment at one revision."""

    increment_id: str
    revision: me.RevisionIdentity
    increment_method: IncrementMethod
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
            "method": dict(self.increment_method.method_identity),
            "reason": self.increment_method.reason,
            "problems": list(self.increment_method.problems),
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
            "coverage": self._coverage(),
            "claim_boundary": CLAIM_BOUNDARY,
        }

    def _coverage(self) -> dict[str, Any]:
        """Which phases the answer's verdicts cover, and which declared phases no check judges."""
        checked = list(self.increment_method.phases)
        declared = self.scope.declared_phases
        unchecked = None if declared is None else list(dict.fromkeys(
            step["phase"] for step in self.increment_method.steps
            if not step["checks"] and step["phase"] in declared and step["phase"] not in checked))
        note = COVERAGE_NOTE if declared is not None else (
            COVERAGE_NOTE + "; the increment's declared phases are unresolved")
        return {"phases_with_executable_checks": checked,
                "declared_phases_without_executable_checks": unchecked, "note": note}

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
        block["scope"] = {
            "packages": [self.view.index.qualified_name(package) for package in scope.scope_packages],
            "elements": len(scope.scope_elements),
        }
        block.update(_declaration_reason(scope, self.revision))
        return block

    def _method_block(self) -> dict[str, Any]:
        block = dict(self.increment_method.method_identity)
        block["executable_contract_available"] = self.increment_method.available
        if self.increment_method.problems:
            block["problems"] = list(self.increment_method.problems)
        return block

    def _unavailable(self, query: str) -> dict[str, Any]:
        response = self._header(query)
        invalid = bool(self.increment_method.problems)
        response.update(
            executable_contract_available=False,
            assessment_coverage=me.COVERAGE_ASSESSED if invalid else me.COVERAGE_UNASSESSED,
            evaluation_state=me.STATE_ERROR if invalid else None,
            conformance_verdict=None,
            reason_codes=[me.INVALID_CONTRACT if invalid else me.CONTRACT_UNAVAILABLE],
            diagnostics=[self.increment_method.reason],
        )
        return response

    # -- shared structure -------------------------------------------------------

    def _contract(self) -> me.MethodContract:
        assert self.increment_method.contract is not None
        return self.increment_method.contract

    def _phases(self, phase: str | None) -> list[str]:
        """The phases with executable checks (or the requested one among them)."""
        return self._selected(list(self.increment_method.phases), phase)

    def _status_phases(self, phase: str | None) -> list[str]:
        """The phases a status reports, in workflow order: those with executable checks, and
        those the charter declares whose steps have none (reported, never evaluated)."""
        checked = set(self.increment_method.phases)
        declared = set(self.scope.declared_phases or ())
        ordered = dict.fromkeys([*(step["phase"] for step in self.increment_method.steps),
                                 *self.increment_method.phases])
        return self._selected([p for p in ordered if p in checked or p in declared], phase)

    @staticmethod
    def _selected(phases: list[str], phase: str | None) -> list[str]:
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
            missing = f"{phase} has {NO_EXECUTABLE_CHECKS}" if not ids else f"no blocking gate is declared for {phase}"
            return me.ReadinessBlock(
                target=target, readiness="BLOCKED", reason_codes=(me.CONTRACT_UNAVAILABLE,),
                diagnostics=(f"{missing}; an empty required inventory cannot authorize a phase exit",),
            )
        return me.subset_readiness(self.canonical, ids, target)

    def _kind(self, unit: me.EvaluationResult) -> str | None:
        """Gap kind of one gate unit (None when the gate passes or is not applicable)."""
        if unit.verdict in {me.VERDICT_PASS, me.VERDICT_NOT_APPLICABLE}:
            return None
        if unit.verdict == me.VERDICT_FAIL:
            return KIND_VIOLATION
        # An authorable child (a failure, or an input problem that is not method
        # side) makes the gate actionable even next to method-side children.
        children = self._open_children(unit.unit_id)
        if any(child.verdict == me.VERDICT_FAIL for child in children):
            return KIND_VIOLATION
        if any(not _method_side(child) for child in children) or not (children or _method_side(unit)):
            return KIND_INPUT
        return KIND_METHOD_SIDE

    def _open_children(self, gate_id: str) -> list[me.EvaluationResult]:
        return [c for c in self._children(gate_id) if c.verdict not in {me.VERDICT_PASS, me.VERDICT_NOT_APPLICABLE}]

    def _entry(self, gate: me.ObligationSpec, kind: str) -> dict[str, Any]:
        unit = self._unit(gate.obligation_id)
        entry: dict[str, Any] = {
            "gate": gate.obligation_id,
            "phase": gate.phase,
            "predicate": gate.predicate,
            "required": gate.required,
            "kind": kind,
            "assessment_coverage": unit.coverage,
            "evaluation_state": unit.state,
            "conformance_verdict": unit.verdict,
            "reason_codes": list(unit.reason_codes),
            "claim_boundary": gate.claim_boundary,
        }
        children = self._open_children(gate.obligation_id)
        method_side = [c for c in children if kind != KIND_METHOD_SIDE and c.verdict != me.VERDICT_FAIL
                       and _method_side(c)]
        subjects = [self._subject(c) for c in children if c not in method_side]
        if method_side:
            entry["method_side_subjects"] = [self._subject(c) for c in method_side]
        if not subjects:
            entry["diagnostics"] = list(unit.diagnostics)
            entry["missing"] = list(unit.missing)
        entry["subjects"] = subjects
        if kind in {KIND_VIOLATION, KIND_INPUT}:
            first = next((c.subject_id for c in children if c not in method_side), None)
            if me.POPULATION_POLICY_VIOLATION in unit.reason_codes:
                entry["what_to_author"] = self._population_remedy(gate, unit)
            elif me.SCOPE_RESOLUTION_ERROR in unit.reason_codes:  # an ambiguous increment identity
                entry["what_to_author"] = (f"keep one part usage with the declared short name {self.increment_id}"
                                           f" ({'; '.join(unit.diagnostics)})")
            else:
                entry["what_to_author"] = remedy(gate.predicate, self.view, _element_subject(first, self.view))
            entry["where"] = self._where(subjects)
        return entry

    def _population_remedy(self, gate: me.ObligationSpec, unit: me.EvaluationResult) -> str:
        """What to author when the number of subjects is outside the population bounds."""
        label = self.increment_method.labels.get(gate.obligation_id, {})
        subject_type = str(label.get("subject_type") or "subject").rsplit("::", 1)[-1]
        lower, upper = gate.minimum_population, gate.maximum_population
        if upper is None:
            bounds = f"at least {lower}"
        elif lower == upper:
            bounds = f"exactly {lower}"
        else:
            bounds = f"between {lower} and {upper}"
        observed = unit.diagnostics[0] if unit.diagnostics else ""
        where = ("package" if gate.selector_kind == OWN_PACKAGE_SELECTOR
                 else "packages named in the charter's expectedArtifacts")
        return f"keep {bounds} {subject_type} in the increment's {where} ({observed})"

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
        phases = self._status_phases(phase)
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
            if phase and not selected:
                response["diagnostics"] = [f"{phase} has {NO_EXECUTABLE_CHECKS}"]
            else:
                response["diagnostics"] = [f"no blocking gate is declared for {phase}" if phase
                                           else "the method declares no blocking gate"]
        return self._presented(response)

    def _phase_status(self, phase: str) -> dict[str, Any]:
        assert self.canonical is not None
        gates = self._gates(phase)
        ids = [g.obligation_id for g in gates]
        coverage, state, verdict = self._aggregate(ids)
        readiness = self._phase_exit(phase, ids)
        if not gates:
            return self._unchecked_phase_status(phase, coverage, state, verdict, readiness)
        blocking, advisory = [], []
        for gate in gates:
            kind = self._kind(self._unit(gate.obligation_id))
            if kind is None:
                continue
            (blocking if gate.required else advisory).append({"gate": gate.obligation_id, "kind": kind})
        return {
            "phase": phase,
            "applicability": self._applicability(gates, phase),
            "executable_checks": len(gates),
            "coverage": EXECUTABLE_CHECKS,
            "assessment_coverage": coverage,
            "evaluation_state": state,
            "conformance_verdict": verdict,
            "phase_exit": readiness.readiness,
            "readiness": readiness.as_dict(),
            "gates": {g.obligation_id: _state_label(self._unit(g.obligation_id)) for g in gates},
            "blocking": blocking,
            "advisory_open": advisory,
        }

    def _unchecked_phase_status(self, phase: str, coverage: str, state: str | None, verdict: str | None,
                                readiness: me.ReadinessBlock) -> dict[str, Any]:
        """A declared phase whose steps have no executable checks: reported with what its steps
        declare, never evaluated (UNASSESSED, and its exit stays BLOCKED)."""
        steps = [step for step in self.increment_method.steps if step["phase"] == phase]
        return {
            "phase": phase,
            "applicability": "declared",
            "executable_checks": 0,
            "coverage": NO_EXECUTABLE_CHECKS,
            "step": ", ".join(step["step"] for step in steps),
            "outputs": copy.deepcopy([output for step in steps for output in step["outputs"]]),
            "assessment_coverage": coverage,
            "evaluation_state": state,
            "conformance_verdict": verdict,
            "phase_exit": readiness.readiness,
            "readiness": readiness.as_dict(),
            "gates": {},
            "blocking": [],
            "advisory_open": [],
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
        """The first actionable blocking check, in workflow order (step order, then check order)."""
        if self.canonical is None:
            response = self._unavailable("next_obligation")
            response.update(next=None, reason=self.increment_method.reason, stage_queue=[], method_side_blockers=[])
            response.update(_next_reason(self.scope, self.revision))
            return response
        response = self._header("next_obligation")
        order = {g.obligation_id: i for i, g in enumerate(self._contract().obligations)}
        actionable: list[tuple[int, me.ObligationSpec, str]] = []
        method_side: list[dict[str, Any]] = []
        for p in self._phases(phase):
            for gate in self._gates(p):
                if not gate.required:
                    continue
                kind = self._kind(self._unit(gate.obligation_id))
                if kind in {KIND_VIOLATION, KIND_INPUT}:
                    actionable.append((order[gate.obligation_id], gate, kind))
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
        reason = NEXT_REASON
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
            }
            if entry.get("method_side_subjects"):
                step["method_side_subjects"] = entry["method_side_subjects"]
            if not step["subjects"]:
                step["diagnostics"] = entry.get("diagnostics", [])
        elif method_side:
            reason = ("no gate the agent can author is open; the remaining blockers need a method or "
                      "kernel change")
        elif phase is not None and not self._phases(phase):
            reason = f"{phase} has {NO_EXECUTABLE_CHECKS}"
        else:
            # 0 open gates says nothing about a declared phase that no check judges: name those phases.
            unchecked = [p for p in self._coverage()["declared_phases_without_executable_checks"] or ()
                         if phase is None or p == phase]
            reason = NONE_OPEN_REASON + (
                f"; {NO_EXECUTABLE_CHECKS} judge the declared phase{'s' if len(unchecked) > 1 else ''} "
                f"{', '.join(unchecked)}" if unchecked else "")
        response.update(next=step, reason=reason, stage_queue=queue, method_side_blockers=method_side)
        response.update(_next_reason(self.scope, self.revision))
        return self._presented(response)

    def phase_contract(self, phase: str | None = None) -> dict[str, Any]:
        """The gates of the method (or one phase) with this increment's applicability."""
        return phase_contract_response(self.increment_method, self.view, self.revision, phase=phase, scope=self.scope)


def phase_contract_response(
    increment_method: IncrementMethod,
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
    method = dict(increment_method.method_identity)
    method["executable_contract_available"] = increment_method.available
    if increment_method.problems:
        method["problems"] = list(increment_method.problems)
    response: dict[str, Any] = {
        "query": "phase_contract",
        "method": method,
        "method_provenance": [{"authority": "authoritative", "source": f"git://{revision.git_commit}"}],
        "phase": phase,
        "legend": dict(CONTRACT_LEGEND),
    }
    if scope is not None:
        response["increment"] = {
            "id": scope.increment_id,
            "resolved": scope.usage_id is not None,
            "declared_phases": list(scope.declared_phases) if scope.declared_phases is not None else None,
            **_declaration_reason(scope, revision),
        }
    # Every step of the workflow, with or without checks: a step without checks has no gate,
    # so only its record says what the method requires there.
    steps = [_step_record(step, scope) for step in increment_method.steps if phase is None or step["phase"] == phase]
    response["steps"] = steps
    response["phases_without_executable_checks"] = list(dict.fromkeys(
        step["phase"] for step in steps if not step["checks"]))
    if increment_method.contract is None:
        response.update(executable_contract_available=False, phases=[], gates=[],
                        reason_codes=[me.INVALID_CONTRACT if increment_method.problems else me.CONTRACT_UNAVAILABLE],
                        diagnostics=[increment_method.reason])
        return response
    phases = [p for p in increment_method.phases if phase is None or p == phase]
    gates = [_gate_record(gate, view, scope, increment_method) for p in phases
             for gate in increment_method.contract.obligations if gate.phase == p]
    response.update(executable_contract_available=bool(gates), phases=phases, gates=gates,
                    contract_digest=increment_method.contract.digest())
    if not gates:
        response["reason_codes"] = [me.CONTRACT_UNAVAILABLE]
        response["diagnostics"] = [f"{phase} has {NO_EXECUTABLE_CHECKS}" + (
            "; steps lists what its step declares" if steps else "")]
    return response


def _step_record(step: Mapping[str, Any], scope: IncrementScope | None) -> dict[str, Any]:
    """One workflow step as answered: what it declares, how many checks judge it, whether it applies."""
    record = copy.deepcopy(dict(step))
    record["executable_checks"] = len(step["checks"])
    record["coverage"] = EXECUTABLE_CHECKS if step["checks"] else NO_EXECUTABLE_CHECKS
    if scope is None:
        return record
    if not step["optional"]:
        record["applicability_resolution"] = "applicable"
    elif scope.declared_phases is None:
        record["applicability_resolution"] = "unresolved"
    else:
        declared = step["phase"] in scope.declared_phases
        record["applicability_resolution"] = "applicable" if declared else "not_applicable"
    return record


def _gate_record(gate: me.ObligationSpec, view: ModelView, scope: IncrementScope | None,
                 increment_method: IncrementMethod) -> dict[str, Any]:
    record: dict[str, Any] = {
        "obligation_id": gate.obligation_id,
        "phase": gate.phase,
        "subject_selector": gate.subject_selector,
        "predicate": gate.predicate,
        "population": [gate.minimum_population, "*" if gate.maximum_population is None else gate.maximum_population],
        "cardinality": [gate.cardinality[0], "*" if gate.cardinality[1] >= UNBOUNDED else gate.cardinality[1]],
        "minimum_population": gate.minimum_population,
        "permitted_empty": gate.permitted_empty,
        "required": gate.required,
        "applicability": gate.applicability,
        "claim_boundary": gate.claim_boundary,
    }
    record.update(increment_method.labels.get(gate.obligation_id, {}))
    if scope is None:
        return record
    record["what_satisfies"] = remedy(gate.predicate, view)
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
    method: IncrementMethod | None = None,
) -> IncrementEvaluation:
    """Evaluate one increment against the workflow its charter declares (or ``method``)."""
    scope = resolve_increment(view, increment_id)
    increment_method = method if method is not None else read_increment_method(
        view, scope, revision_label=revision.git_commit)
    canonical = None
    if increment_method.contract is not None:
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
        evaluator = me.MethodEvaluator(increment_method.contract, predicates=increment_method.predicates,
                                       selectors=WORKFLOW_SELECTORS)
        canonical = evaluator.evaluate(ctx)
    return IncrementEvaluation(
        increment_id=scope.increment_id, revision=revision, increment_method=increment_method, scope=scope,
        view=view, canonical=canonical,
    )


def _not_declared(scope: IncrementScope) -> bool:
    """No increment usage carries the identifier at this revision: neither an ambiguous identity
    (an invalid problem) nor an unbound kernel lineage (a method-side marker)."""
    if scope.usage_id is not None:
        return False
    kind, detail = scope.problems.get(IDENTITY_PROBLEM, ("", ""))
    return kind == PROBLEM_UNAVAILABLE and not str(detail).startswith(METHOD_SIDE_PREFIXES)


def _declaration_reason(scope: IncrementScope, revision: me.RevisionIdentity) -> dict[str, str]:
    """``reason_code`` and ``message`` of an increment the evaluated revision does not declare (else nothing)."""
    if not _not_declared(scope):
        return {}
    message = (f"{scope.increment_id} isn't declared at revision {revision.git_commit or '(none)'} "
               f"({revision.scope}): no increment usage there carries it as its declared short name. Work on a "
               "branch or another commit is not part of this evaluation; the PR Method Check evaluates the "
               "head of a pull request.")
    return {"reason_code": INCREMENT_NOT_DECLARED, "message": message}


def _next_reason(scope: IncrementScope, revision: me.RevisionIdentity) -> dict[str, str]:
    """For an increment the revision does not declare, ``next``'s reason is that fact (with its code)."""
    reason = _declaration_reason(scope, revision)
    return {"reason_code": reason["reason_code"], "reason": reason["message"]} if reason else {}


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
