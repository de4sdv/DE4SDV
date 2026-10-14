"""What to author: remedies built from the typed parameter a check is about.

A workflow step declares typed parameters, and each method check is about one
of them. These tests check, over synthetic export-shaped models, that what an
answer tells an agent to author is built from that parameter in the bound
view: its SysML keyword, its type's qualified name computed from ownership,
the ``private import`` of the type's package, the types the check's own type
test admits, the order in which elements must be declared, and only SysML an
author can write. The oracles are the builders' own construction (which
package each definition was put in, which name it got) and the KerML
qualified-name resolution of :mod:`de4sdv.sysml_api.qualified_names`, never
the remedy code. The genuine-export cut is covered in
``test_remedies_on_the_genuine_export.py``.
"""

from __future__ import annotations

from typing import Any

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from de4sdv.sysml_api.qualified_names import QualifiedNameIndex
from increment_model_fixtures import (
    INFINITY,
    WorkflowCheck,
    WorkflowParameter,
    WorkflowStep,
    increment_scenario,
    increment_workflow,
)
from test_revision_index import _traversal

REVISION = me.RevisionIdentity("b" * 40, "project", "commit", "full-model")
P0, P4, P5, P10 = ("phase0_incrementFraming", "phase4_needs", "phase5_requirements", "phase10_vvEvidence")
P, C = WorkflowParameter, WorkflowCheck


def _view(scenario) -> ModelView:
    builder = scenario.builder
    return ModelView(builder.elements, _traversal(builder), sources=builder.sources)


def _evaluate(scenario, increment_id: str | None = None):
    return evaluate_increment(_view(scenario), increment_id or scenario.increment_id, revision=REVISION)


def _needs_workflow(scenario) -> None:
    """A workflow whose needs step checks the statement of each need."""
    increment_workflow(scenario.builder, [
        WorkflowStep("frameIncrement", P0, (P("increment", "EngineeringIncrement"),)),
        WorkflowStep("elaborateNeeds", P4, (P("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),), (
            C("needHasStatement", "requireConstraint", "needs"),)),
    ], charter=scenario.charter)


def _printed(value: Any) -> list[tuple[str, str]]:
    """Every (element_id, qualified_name) pair an answer prints."""
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        if value.get("element_id") and value.get("qualified_name"):
            found.append((value["element_id"], value["qualified_name"]))
        for item in value.values():
            found.extend(_printed(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_printed(item))
    return found


# -- one name printer ------------------------------------------------------------


def test_every_name_the_method_answers_print_resolves_to_the_element_it_names() -> None:
    """The answers print KerML qualified names computed from ownership: a name that is not a basic
    name is quoted, and every printed name resolves, exactly, to the element it is printed for."""
    scenario = increment_scenario()
    _needs_workflow(scenario)
    builder = scenario.builder
    builder.remove(builder.feature_of(scenario.needs[1], "statement"))
    scenario.needs[1]["declaredName"] = "need one"  # not a basic name
    evaluation = _evaluate(scenario)
    answers = [evaluation.status(), evaluation.gaps(), evaluation.next_obligation(), evaluation.phase_contract()]
    (gap,) = evaluation.gaps()["blocking"]
    assert [s["qualified_name"] for s in gap["subjects"]] == ["DE4SDV_FixtureNeedsRequirements::'need one'"]
    names = QualifiedNameIndex(builder.elements)
    printed = [pair for answer in answers for pair in _printed(answer)]
    assert len(printed) >= 5
    for element_id, name in printed:
        assert [e["@id"] for e in names.resolve(name)] == [element_id], name
