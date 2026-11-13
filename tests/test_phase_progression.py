"""Phase progression over the live workflow: structure, vacuity and the walk.

The workflow comes from the checkout's live ``de4sdv_increment_workflow.sysml``
(``test_method_answer_coverage._workflow_steps``); the frozen genuine cut
predates the Phase 1 gate and must not be used here. The content is synthetic
export-shaped framing, not a copy of a production model.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_discovery import DeclaredIncrement
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from increment_model_fixtures import (
    INFINITY,
    PHASE_LITERALS,
    ModelBuilder,
    WorkflowCheck,
    WorkflowParameter,
    WorkflowStep,
    increment_scenario,
    increment_workflow,
    ref,
)
from model_contract_fixtures import model_contract
from scripts import method_check
from test_method_answer_coverage import _workflow_steps
from test_revision_index import _traversal

P0 = "phase0_incrementFraming"
P1 = "phase1_concernFraming"
P3 = "phase3_capabilityClassification"
P4 = "phase4_needs"
P5 = "phase5_requirements"
P10 = "phase10_vvEvidence"
P11 = "phase11_baseline"
META = {"part": "PartUsage", "requirement": "RequirementUsage", "concern": "ConcernUsage",
        "action": "ActionUsage", "view": "ViewUsage", "verification": "VerificationCaseUsage",
        "allocation": "AllocationUsage"}
REVISION = me.RevisionIdentity("b" * 40, "project", "commit", "full-model")


def _mapped(name: str) -> bool:
    try:
        model_contract().mapping(name)
        return True
    except KeyError:
        return False


def _typed_factory(builder: ModelBuilder, framing: dict, roots: dict, aliases: dict | None = None):
    """Live parameter type name -> the definition that types it in this export.

    A kernel-mapped class uses its validated kernel definition; an alias reuses
    the definition the existing fixture already types its content with; an
    unmapped one gets one local definition that both the workflow parameter and
    the content usage are typed by, so the selector and population agree.
    """
    definitions: dict[str, dict] = dict(aliases or {})

    def typed(name: str | None):
        if name is None:
            return None
        if name in definitions:
            return definitions[name]
        if name in roots:
            return roots[name]
        if name == "IncrementCharter":
            obligations = roots["IncrementTraceObligations"]
            charter = builder.definition("PartDefinition", "IncrementCharter", framing, [obligations])
            for feature_name, bounds in (("owner", ()), ("expectedArtifacts", (1, INFINITY)),
                                         ("expectedReviewEvidence", (1, INFINITY))):
                feature = builder.new("AttributeUsage", name=feature_name, source=builder.sources[charter["@id"]])
                builder.own(charter, feature, kind="FeatureMembership", member_name=feature_name)
                if bounds:
                    builder.multiplicity(feature, *bounds)
        elif _mapped(name):
            charter = builder.kernel_definition(name)
        else:
            charter = builder.definition("PartDefinition", name, framing)
        definitions[name] = charter
        return charter

    return typed


def _install_live_workflow(builder: ModelBuilder, charter: dict, typed) -> None:
    steps = _workflow_steps()
    increment_workflow(builder, [
        WorkflowStep(step.usage, step.phase, tuple(
            WorkflowParameter(p.name, typed(p.type), META[p.keyword], p.direction,
                              (p.multiplicity[0], INFINITY if p.multiplicity[1] == "*" else p.multiplicity[1]))
            for p in step.parameters), tuple(
            WorkflowCheck(c.name, c.check, c.about, advisory=True if c.advisory else None, doc=c.claim)
            for c in step.checks))
        for step in steps], charter=charter)


def _obligation_features(builder: ModelBuilder, roots: dict) -> dict:
    obligations = roots["IncrementTraceObligations"]
    if "increment" not in builder.members(obligations):
        for feature_name, kind, typed_by, bounds in (
                ("increment", "PartUsage", roots["EngineeringIncrement"], ()),
                ("applicablePhases", "AttributeUsage", builder.kernel_definition("MethodPhase"), (0, INFINITY)),
                ("owner", "AttributeUsage", None, ()),
                ("expectedArtifacts", "AttributeUsage", None, (1, INFINITY)),
                ("expectedReviewEvidence", "AttributeUsage", None, (1, INFINITY)),
                ("systemOfInterest", "PartUsage", None, (0, 1))):
            feature = builder.new(kind, name=feature_name, source=builder.sources[obligations["@id"]])
            builder.own(obligations, feature, kind="FeatureMembership", member_name=feature_name)
            if typed_by is not None:
                builder.typed(feature, typed_by)
            if bounds:
                builder.multiplicity(feature, *bounds)
    return obligations


def framing_only(applicable_phases=PHASE_LITERALS):
    """An increment with complete Phase 0 content and a boundary concern only."""
    b = ModelBuilder(label="progression-framing")
    phases = b.enumeration("MethodPhase", PHASE_LITERALS)
    roots = {name: b.kernel_definition(name) for name in (
        "EngineeringIncrement", "IncrementTraceObligations", "ProblemStatement",
        "IncrementEngineeringQuestion", "IncrementLifecycleDecision", "Stakeholder")}
    obligations = _obligation_features(b, roots)
    framing = b.package("DE4SDV_ProgressionFraming")
    typed = _typed_factory(b, framing, roots)
    definition = b.definition("PartDefinition", "ProgressionIncrement", framing, [roots["EngineeringIncrement"]])
    usage = b.usage("PartUsage", "incProgression", framing, [definition], short="INC-PROGRESSION-001")
    role = b.definition("PartDefinition", "ProgressionEngineer", framing, [roots["Stakeholder"]])
    problem = b.usage("RequirementUsage", "progressionProblemStatement", framing, [roots["ProblemStatement"]])
    b.subject(problem, definition, name="increment")
    b.stakeholder(problem, "engineer", role)
    b.usage("PartUsage", "progressionQuestion", framing, [roots["IncrementEngineeringQuestion"]])
    b.usage("PartUsage", "progressionDecision", framing, [roots["IncrementLifecycleDecision"]])
    boundary = b.kernel_definition("IncrementBoundaryConcern")
    concern = b.usage("ConcernUsage", "progressionBoundary", framing, [boundary])
    b.stakeholder(concern, "engineer", role)
    view = b.usage("ViewUsage", "progressionView", framing)
    viewpoint = b.usage("ViewpointUsage", "selectedViewpoint", view, membership="FeatureMembership")
    b.frame(viewpoint, concern)
    # ``expose DE4SDV_ProgressionFraming::*;``: a framing view shows the framing,
    # as the closed-loop driving framing view does.
    b.relationship("NamespaceExpose", view, importedNamespace=ref(framing))
    for name in ("IncrementScope", "OutOfScopeItem", "IncrementAssumption"):
        typed(name)
    b.usage("PartUsage", "progressionScope", framing, [typed("IncrementScope")])
    b.usage("PartUsage", "progressionOutOfScope", framing, [typed("OutOfScopeItem")])
    b.usage("PartUsage", "progressionAssumption", framing, [typed("IncrementAssumption")])
    charter = b.usage("PartUsage", "progressionCharter", framing, [typed("IncrementCharter")])
    b.attribute(charter, "applicablePhases", [phases[p] for p in applicable_phases])
    b.attribute(charter, "increment", usage, kind="PartUsage")
    b.attribute(charter, "owner", "progression test")
    b.attribute(charter, "expectedArtifacts", ["DE4SDV_ProgressionFraming"])
    b.attribute(charter, "expectedReviewEvidence", ["progress test evidence"])
    _install_live_workflow(b, charter, typed)
    assert obligations["@id"]
    return b


def with_later_slices(applicable_phases=(P0, P4, P5, P10)):
    """The existing increment fixture with complete Phase 0 and the live workflow."""
    scenario = increment_scenario(applicable_phases=applicable_phases, name="Progression")
    b = scenario.builder
    framing = scenario.framing
    roots = scenario.vocabulary
    definitions = {element.get("declaredName"): element for element in b.elements if element.get("declaredName")}
    typed = _typed_factory(b, framing, roots, {
        "IncrementCharter": definitions["ProgressionCharter"],
        "StakeholderNeedCandidate": definitions["ProgressionNeed"],
        "RequirementCandidate": definitions["ProgressionRequirement"],
        "IncrementAssumption": roots["Assumption"],
    })
    b.usage("PartUsage", "progressionScopeWalk", framing, [typed("IncrementScope")])
    b.usage("PartUsage", "progressionOutOfScopeWalk", framing, [typed("OutOfScopeItem")])
    _install_live_workflow(b, scenario.charter, typed)
    return scenario


def evaluate(builder: ModelBuilder):
    return evaluate_increment(ModelView(builder.elements, _traversal(builder), sources=builder.sources),
                              "INC-PROGRESSION-001" if builder.label == "progression-framing"
                              else "INC-FIXTURE-001", revision=REVISION)


def phase(evaluation, name: str) -> dict:
    (block,) = [item for item in evaluation.status()["phases"] if item["phase"] == name]
    return block


def test_framing_only_opens_only_vacuous_phase_3():
    """Phase 0 content alone opens no later phase but the vacuous phase 3. The
    publication phase that opened on a framing view alone is retired: its view
    checks are part of the baseline phase, which also needs a baseline decision."""
    evaluation = evaluate(framing_only())
    assert phase(evaluation, P0)["phase_exit"] == "READY"
    for name in (P1, "phase2_operationalContext", P4, P5, "phase6_functionalArchitecture",
                 "phase7_logicalArchitecture", "phase8_physicalRealization",
                 "phase9_variabilityConfiguration", P10, P11):
        assert phase(evaluation, name)["phase_exit"] == "BLOCKED", name
    vacuous = phase(evaluation, P3)
    assert vacuous["phase_exit"] == "READY" and vacuous["vacuous"] is True and vacuous["evaluated"] == 0
    assert vacuous["conformance_verdict"] == "NOT_APPLICABLE"
    baseline = phase(evaluation, P11)
    assert baseline["gates"]["publishedViewFramesConcern"] == "PASS"
    assert baseline["gates"]["publishedViewExposesContent"] == "PASS"
    assert baseline["gates"]["incrementHasBaselineDecision"] == "FAIL"
    assert [p["phase"] for p in evaluation.status()["phases"]][-1] == P11
    step = evaluation.next_obligation()["next"]
    assert (step["stage"], step["gate"]) == (P1, "incrementHasNonBoundaryConcern")
    # Phase 3 comes after the next obligation, so the advisory list is empty.
    assert evaluation.next_obligation()["vacuous_phases"] == []


def test_a_vacuous_phase_before_the_next_obligation_is_advised_not_blocking():
    evaluation = evaluate(framing_only(applicable_phases=(P0, P3, P4, P5, P10)))
    step = evaluation.next_obligation()["next"]
    assert (step["stage"], step["gate"]) == (P4, "needHasStatement")
    assert evaluation.next_obligation()["vacuous_phases"] == [
        {"phase": P3, "prompt": "confirm the increment adds no feature-model delta"}]


def test_vacuous_phases_keep_to_the_phase_a_next_obligation_asks_about():
    """A phase-scoped answer lists only the vacuous phases in that scope, like
    its ``stage_queue``; the unscoped answer is unchanged."""
    evaluation = evaluate(framing_only(applicable_phases=(P0, P3, P4, P5, P10)))
    prompt = {"phase": P3, "prompt": "confirm the increment adds no feature-model delta"}
    assert evaluation.next_obligation()["vacuous_phases"] == [prompt]
    framing = evaluation.next_obligation(P0)
    assert framing["next"] is None and framing["stage_queue"] == []
    assert framing["vacuous_phases"] == []
    evidence = evaluation.next_obligation(P10)
    assert evidence["next"]["stage"] == P10
    assert [entry["phase"] for entry in evidence["stage_queue"]] == [P10]
    assert evidence["vacuous_phases"] == []
    classification = evaluation.next_obligation(P3)
    assert classification["next"] is None
    assert classification["vacuous_phases"] == [prompt]


def test_the_walk_reaches_the_first_phase_whose_content_is_missing():
    complete = evaluate(with_later_slices().builder)
    assert complete.next_obligation()["next"] is None
    assert complete.next_obligation()["vacuous_phases"] == []
    for name in (P4, P5, P10):
        assert phase(complete, name)["phase_exit"] == "READY", name

    no_evidence = with_later_slices()
    no_evidence.builder.remove(*no_evidence.cases)
    missing_evidence = evaluate(no_evidence.builder)
    assert missing_evidence.next_obligation()["next"]["stage"] == P10

    no_requirements = with_later_slices()
    no_requirements.builder.remove(*no_requirements.requirements, *no_requirements.cases)
    missing_requirements = evaluate(no_requirements.builder)
    assert missing_requirements.next_obligation()["next"]["stage"] == P5

    no_needs = with_later_slices()
    no_needs.builder.remove(*no_needs.needs, *no_needs.requirements, *no_needs.cases)
    missing_needs = evaluate(no_needs.builder)
    assert missing_needs.next_obligation()["next"]["stage"] == P4


#: The summary line that names a vacuous phase the walk passed before ``next`` (or before "none").
PASSED_EMPTY = "**Passed with nothing to evaluate:**"
P3_PROMPT = {"phase": P3, "prompt": "confirm the increment adds no feature-model delta"}


def _summary_entry(step, vacuous_phases):
    """One evaluated increment as the Method Check summary renders it."""
    status = {"phase": P3, "applicability": "declared", "vacuous": True, "evaluated": 0}
    return {
        "id": "INC-X", "outcome": "evaluated", "usage": {"qualified_name": "P::inc"}, "charters": [],
        "next": step, "next_reason": "" if step else "every required gate passes or is not applicable",
        "counts": {}, "diagnostics": [],
        "phase_exits": {P3: "READY", P4: "BLOCKED" if step else "READY"},
        "phase_checks": {P3: {"pass": 0, "total": 1, "not_applicable": 1}, P4: {"pass": 0, "total": 6}},
        "evaluation": {"status": {"phases": [status]}, "gaps": {"blocking": [], "advisory": []},
                       "next": {"method_side_blockers": [], "vacuous_phases": vacuous_phases}},
    }


def _summary_lines(entry) -> list[str]:
    result = {"revision": "a" * 40, "export": {}, "increments": [entry], "notes": [], "errors": []}
    return method_check.render_summary(result).splitlines()


def test_the_summary_names_a_vacuous_phase_the_walk_passed_before_next():
    """Phase 3 passes with nothing to evaluate and the next gate is in phase 4: the summary says so
    under **Next**, with the review prompt, instead of jumping to phase 4 silently."""
    step = {"stage": P4, "gate": "needHasStatement", "kind": "violation"}
    lines = _summary_lines(_summary_entry(step, [P3_PROMPT]))
    at = lines.index("**Next:** `needHasStatement` in phase4_needs (violation)")
    passed = [line for line in lines if line.startswith(PASSED_EMPTY)]
    assert passed == [f"{PASSED_EMPTY} {P3} (confirm the increment adds no feature-model delta). "
                      "Review answers this; no gate does."]
    assert at < lines.index(passed[0]) < next(i for i, line in enumerate(lines) if line.startswith("**Blocking gaps"))
    assert lines[lines.index(passed[0]) - 1] == "", "a paragraph of its own, not a continuation of the list above"


def test_the_summary_names_a_vacuous_phase_when_nothing_is_next():
    lines = _summary_lines(_summary_entry(None, [P3_PROMPT]))
    at = next(i for i, line in enumerate(lines) if line.startswith("**Next:** none."))
    assert lines[at + 2] == (f"{PASSED_EMPTY} {P3} (confirm the increment adds no feature-model delta). "
                             "Review answers this; no gate does.")


def test_the_summary_adds_nothing_without_a_vacuous_phase_before_next():
    step = {"stage": P4, "gate": "needHasStatement", "kind": "violation"}
    for vacuous in ([], None):
        entry = _summary_entry(step, vacuous)
        if vacuous is None:
            del entry["evaluation"]["next"]["vacuous_phases"]
        assert not [line for line in _summary_lines(entry) if line.startswith(PASSED_EMPTY)]


def test_the_method_check_summary_reads_the_vacuous_phases_of_a_real_evaluation(tmp_path):
    """End to end over the Method Check's own entry builder: the real next_obligation answer of a
    framing-only increment whose charter declares phase 3 reaches the summary line."""
    evaluation = evaluate(framing_only(applicable_phases=(P0, P3, P4, P5, P10)))
    report = {"status": evaluation.status(), "gaps": evaluation.gaps(), "next": evaluation.next_obligation()}
    assert report["next"]["vacuous_phases"] == [P3_PROMPT]

    def runner(argv):
        argv = list(argv)
        Path(argv[argv.index("--output") + 1]).write_text(json.dumps(report))
        return method_check.RunnerResult(0, "", "")

    increment = DeclaredIncrement(increment_id=evaluation.increment_id, usage={"qualified_name": "P::inc"},
                                  charters=())
    entry, problems = method_check._evaluate(increment, tmp_path / "export.json", tmp_path, runner)
    assert problems == [] and entry["outcome"] == "evaluated"
    lines = _summary_lines(entry)
    assert f"**Next:** `needHasStatement` in {P4} (violation)" in lines
    assert (f"{PASSED_EMPTY} {P3} (confirm the increment adds no feature-model delta). "
            "Review answers this; no gate does.") in lines


@pytest.mark.parametrize("evaluated,shown", [
    (None, "(vacuous, nothing to evaluate)"),
    (0, "(vacuous, nothing to evaluate)"),
    (1, "(vacuous, 1 advisory check evaluated)"),
    (2, "(vacuous, 2 advisory checks evaluated)"),
])
def test_the_summary_marks_a_vacuous_phase_without_changing_readiness(evaluated, shown):
    status = {"phase": P3, "applicability": "declared", "vacuous": True}
    if evaluated is not None:
        status["evaluated"] = evaluated
    entry = {
        "id": "INC-X", "outcome": "evaluated", "usage": {"qualified_name": "P::inc"}, "charters": [],
        "next": None, "next_reason": "", "counts": {}, "diagnostics": [],
        "phase_exits": {P3: "READY"},
        "phase_checks": {P3: {"pass": 0, "total": 1, "not_applicable": 1}},
        "evaluation": {"status": {"phases": [status]},
                       "gaps": {"blocking": [], "advisory": []}, "next": {"method_side_blockers": []}},
    }
    result = {"revision": "a" * 40, "export": {}, "increments": [entry], "notes": [], "errors": []}
    text = method_check.render_summary(result)
    assert f"{P3} READY {shown}" in text
    assert entry["phase_exits"][P3] == "READY"
