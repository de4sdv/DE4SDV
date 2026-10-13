"""The method answers state what they cover: every workflow step, and only declared content.

The oracle is the checkout's workflow file, read lexically here (like
``test_increment_workflow.py``): its steps, their phases and parameters, and
the checks with their claims. A synthetic export declares exactly that
workflow through the fixture builder, and the answers computed over it must
report every step the file declares, say which phases no executable check
judges, and give each check the population its parameter allows. The code
under test reads the export, never the file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pytest

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from increment_model_fixtures import (
    INFINITY,
    PHASE_LITERALS,
    WorkflowCheck,
    WorkflowParameter,
    WorkflowStep,
    increment_scenario,
    increment_workflow,
)
from sysml_shapes import MODEL_ROOT, braced_body, strip_comments
from test_revision_index import _traversal

WORKFLOW_FILE = MODEL_ROOT / "packages/methods/de4sdv/de4sdv_increment_workflow.sysml"
REVISION = me.RevisionIdentity("c" * 40, "project", "commit", "full-model")
NO_CHECKS = "no executable checks at this revision"
#: SysML v2 textual keyword of a step parameter -> the usage metaclass the serializer records.
METACLASS = {"part": "PartUsage", "requirement": "RequirementUsage", "concern": "ConcernUsage",
             "action": "ActionUsage", "view": "ViewUsage", "verification": "VerificationCaseUsage"}
#: The phases INC-AEBS-010's charter declares: 0 to 10, so phases 11 and 12 stay undeclared.
DECLARED = PHASE_LITERALS[:11]


def _metaclass(keyword: str) -> str:
    """The usage metaclass of a parameter keyword; a keyword this test does not know stops it clearly."""
    if keyword not in METACLASS:
        pytest.fail(f"the workflow file declares a step parameter with the keyword {keyword!r}; map it to its "
                    "usage metaclass in METACLASS")
    return METACLASS[keyword]


@dataclass(frozen=True)
class Parameter:
    direction: str
    keyword: str
    name: str
    multiplicity: list
    type: str | None


@dataclass(frozen=True)
class Check:
    name: str
    check: str
    about: str
    advisory: bool
    claim: str


@dataclass(frozen=True)
class Step:
    usage: str
    definition: str
    phase: str
    parameters: tuple[Parameter, ...]
    checks: tuple[Check, ...]

    @property
    def outputs(self) -> list[Parameter]:
        return [p for p in self.parameters if p.direction != "in"]


def _multiplicity(text: str) -> list:
    """``[1..*]`` -> [1, "*"]; no multiplicity declared -> exactly one."""
    if not text:
        return [1, 1]
    bounds = [b.strip() for b in text.strip("[]").split("..")]
    values = [0 if (len(bounds) == 1 and b == "*") else ("*" if b == "*" else int(b)) for b in bounds]
    return [values[0], values[-1] if bounds[-1] != "*" else "*"]


def _claim(raw: str, start: int, declaration: str) -> str:
    """The doc text of a check, read from the raw file (comments kept), whitespace and ``*`` folded."""
    at = raw.index(declaration, start)
    body = re.search(r"doc\s*/\*(.*?)\*/", raw[at:], re.DOTALL).group(1)
    return " ".join(line.strip().lstrip("*").strip() for line in body.splitlines()).strip()


def _workflow_steps() -> list[Step]:
    """The steps the workflow file declares, in method order, with their parameters and checks."""
    raw = WORKFLOW_FILE.read_text(encoding="utf-8")
    code = strip_comments(raw)
    flow = braced_body(code, "action def IncrementWorkflow")
    steps = []
    for usage, _bounds, definition in re.findall(r"\bthen\s+action\s+(\w+)\s*(\[[^\]]*\])?\s*:\s*(\w+)\s*;", flow):
        declaration = f"action def {definition} :> IncrementStep"
        body = braced_body(code, declaration)
        phase = re.search(r"attribute\s+:>>\s+phase\s*=\s*MethodPhase::(\w+)\s*;", body).group(1)
        parameters = tuple(
            Parameter(direction, keyword, name, _multiplicity(bounds), type_ or None)
            for direction, keyword, name, bounds, type_ in re.findall(
                r"\b(in|out|inout)\s+(\w+)\s+(\w+)\s*(\[[^\]]*\])?\s*(?::\s*(\w+))?\s*;", body))
        start = raw.index(declaration)
        checks = []
        for name, about in re.findall(r"\bmetadata\s+(\w+)\s*:\s*MethodCheck\s+about\s+(\w+)\s*\{", body):
            fields = dict(re.findall(r":>>\s*(\w+)\s*=\s*([^;]*);",
                                     braced_body(body, f"metadata {name} : MethodCheck about {about}")))
            checks.append(Check(name, fields["check"].strip('"'), about, fields.get("advisory") == "true",
                                _claim(raw, start, f"metadata {name} : MethodCheck about {about}")))
        steps.append(Step(usage, definition, phase, parameters, tuple(checks)))
    return steps


def _scenario(steps: list[Step], applicable_phases=DECLARED):
    """A synthetic increment whose charter declares exactly the file's workflow."""
    scenario = increment_scenario(applicable_phases=applicable_phases)
    builder = scenario.builder
    types = builder.package("DE4SDV_WorkflowFileTypes")
    definitions: dict[str, dict] = {}

    def typed(name: str | None):
        if name is None:
            return None
        if name not in definitions:
            definitions[name] = builder.definition("PartDefinition", name, types)
        return definitions[name]

    increment_workflow(builder, [
        WorkflowStep(step.usage, step.phase, tuple(
            WorkflowParameter(p.name, typed(p.type), kind=_metaclass(p.keyword), direction=p.direction,
                              bounds=(p.multiplicity[0], INFINITY if p.multiplicity[1] == "*" else p.multiplicity[1]))
            for p in step.parameters), tuple(
            WorkflowCheck(c.name, c.check, c.about, advisory=True if c.advisory else None, doc=c.claim)
            for c in step.checks))
        for step in steps], charter=scenario.charter)
    return scenario


def _evaluate(scenario):
    builder = scenario.builder
    view = ModelView(builder.elements, _traversal(builder), sources=builder.sources)
    return evaluate_increment(view, scenario.increment_id, revision=REVISION)


def test_the_oracle_finds_one_step_per_phase() -> None:
    """The lexical oracle reads the 13 steps (whether or not a phase has checks yet)."""
    steps = _workflow_steps()
    assert [step.phase for step in steps] == list(PHASE_LITERALS)
    assert any(step.checks for step in steps)


def test_phase_contract_lists_every_step_the_file_declares_with_its_outputs() -> None:
    steps = _workflow_steps()
    contract = _evaluate(_scenario(steps)).phase_contract()
    listed = contract["steps"]
    assert [(s["step"], s["phase"]) for s in listed] == [(step.usage, step.phase) for step in steps]
    for record, step in zip(listed, steps):
        assert [(o["parameter"], o["multiplicity"]) for o in record["outputs"]] == [
            (p.name, p.multiplicity) for p in step.outputs], step.usage
        assert [o["sysml_type"] for o in record["outputs"]] == [_metaclass(p.keyword) for p in step.outputs]
        assert [(o["type"] or "").rsplit("::", 1)[-1] or None for o in record["outputs"]] == [
            p.type for p in step.outputs], step.usage
        assert record["checks"] == [check.name for check in step.checks], step.usage
        assert record["executable_checks"] == len(step.checks), step.usage
        assert (record["coverage"] == NO_CHECKS) == (not step.checks), step.usage
        expected = "applicable" if step.phase in DECLARED else "not_applicable"
        assert record["applicability_resolution"] == expected, step.usage
    assert contract["phases_without_executable_checks"] == [step.phase for step in steps if not step.checks]
    assert contract["phases"] == [step.phase for step in steps if step.checks]


def test_status_reports_every_declared_phase_and_says_which_no_check_judges() -> None:
    steps = _workflow_steps()
    evaluation = _evaluate(_scenario(steps))
    status = evaluation.status()
    assert [block["phase"] for block in status["phases"]] == [
        step.phase for step in steps if step.checks or step.phase in DECLARED]
    blocks = {block["phase"]: block for block in status["phases"]}
    unchecked = [step.phase for step in steps if not step.checks and step.phase in DECLARED]  # 1-3, 6-9 today
    for step in steps:
        block = blocks.get(step.phase)
        if step.checks:
            assert block["executable_checks"] == len(step.checks), step.phase
            assert block["coverage"] != NO_CHECKS
        elif step.phase in DECLARED:
            assert (block["coverage"], block["executable_checks"], block["applicability"]) == (
                NO_CHECKS, 0, "declared"), step.phase
            # Frozen result algebra (MC-34): no executable contract is UNASSESSED, and its exit stays BLOCKED.
            assert (block["assessment_coverage"], block["evaluation_state"], block["conformance_verdict"]) == (
                me.COVERAGE_UNASSESSED, None, None)
            assert (block["phase_exit"], block["readiness"]["reason_codes"]) == ("BLOCKED", [me.CONTRACT_UNAVAILABLE])
            assert block["step"] == step.usage
            assert [o["parameter"] for o in block["outputs"]] == [p.name for p in step.outputs], step.phase
            assert (block["gates"], block["blocking"], block["advisory_open"]) == ({}, [], [])
        else:
            assert block is None, step.phase  # an undeclared phase without checks does not apply
    coverage = status["coverage"]
    assert coverage["declared_phases_without_executable_checks"] == unchecked
    assert coverage["phases_with_executable_checks"] == [step.phase for step in steps if step.checks]
    for phase in unchecked[:1]:  # once every declared phase has checks, the frozen-cut tests still cover this
        assert [b["phase"] for b in evaluation.status(phase=phase)["phases"]] == [phase]
    last = steps[-1]  # declared by no charter here: listed only when checks judge it
    assert [b["phase"] for b in evaluation.status(phase=last.phase)["phases"]] == ([last.phase] if last.checks else [])
    for answer in (evaluation.gaps(), evaluation.next_obligation()):
        assert answer["coverage"] == coverage


def test_each_check_states_the_population_its_parameter_allows() -> None:
    """``population`` is the multiplicity of the parameter a check is about: how many subjects."""
    steps = _workflow_steps()
    contract = _evaluate(_scenario(steps)).phase_contract()
    gates = {gate["obligation_id"]: gate for gate in contract["gates"]}
    expected = {check.name: next(p.multiplicity for p in step.parameters if p.name == check.about)
                for step in steps for check in step.checks}
    assert {name: gate["population"] for name, gate in gates.items()} == expected


def test_population_and_cardinality_agree_with_the_claim_of_each_check() -> None:
    """A claim of "at least one" has an unbounded population (subjects) or cardinality (targets per
    subject); a claim of "exactly one" has [1, 1] in one of them. The claims come from the file."""
    steps = _workflow_steps()
    contract = _evaluate(_scenario(steps)).phase_contract()
    gates = {gate["obligation_id"]: gate for gate in contract["gates"]}
    claims = {check.name: check.claim.lower() for step in steps for check in step.checks}
    at_least = [name for name, claim in claims.items() if "at least one" in claim]
    exactly = [name for name, claim in claims.items() if "exactly one" in claim]
    assert at_least and exactly
    for name in at_least:
        assert "*" in (gates[name]["population"][1], gates[name]["cardinality"][1]), (name, claims[name])
    for name in exactly:
        assert [1, 1] in (gates[name]["population"], gates[name]["cardinality"]), (name, claims[name])
