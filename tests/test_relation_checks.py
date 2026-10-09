"""Relation checks: a relation name maps to an implementation over the model.

A method check names the relation it checks (for example
``derivesRequirementFromNeed``). Its check decides it for one subject from
the model alone: no selector, filter, cardinality or phase text is involved,
so the checks hold for any representation of the method that names
relations. The synthetic increment carries complete content; each test
changes one relation.
"""

from __future__ import annotations

import inspect

import pytest

from de4sdv.semantic.increment_scope import ModelView
from de4sdv.semantic.model_authority_runtime import model_facade
from de4sdv.semantic.relation_checks import RelationResult, check_relation, relation_checks
from increment_model_fixtures import increment_scenario, ref
from test_revision_index import _traversal


def _check(scenario, relation: str, subject: dict) -> RelationResult:
    builder = scenario.builder
    view = ModelView(builder.elements, _traversal(builder), sources=builder.sources)
    return check_relation(view, relation, subject["@id"])


def _named(scenario, name: str) -> dict:
    (element,) = [e for e in scenario.builder.elements if e.get("declaredName") == name]
    return element


def _checks(scenario):
    builder = scenario.builder
    return relation_checks(ModelView(builder.elements, _traversal(builder), sources=builder.sources))


def test_every_contract_relation_and_native_relation_has_a_check_taking_the_view_and_one_subject() -> None:
    checks = _checks(increment_scenario())
    assert set(checks) == set(model_facade().relationships) | {"frame", "stakeholder", "subject", "verify"}
    for name, check in checks.items():
        assert list(inspect.signature(check).parameters) == ["view", "subject_id"], name


def test_a_derivation_relation_reaches_the_need_through_its_connection() -> None:
    scenario = increment_scenario()
    result = _check(scenario, "derivesRequirementFromNeed", scenario.requirements[0])
    assert result.problem == ""
    assert result.targets == [scenario.needs[0]["@id"]]
    assert len(result.witnesses) == 1


def test_plain_dependencies_are_near_misses_never_witnesses() -> None:
    scenario = increment_scenario()
    builder = scenario.builder
    requirement, need = scenario.requirements[0], scenario.needs[0]
    builder.remove(_named(scenario, "requirement0DerivedFromNeed0"))
    dependency = builder.new("Dependency", client=[ref(requirement)], supplier=[ref(need)])
    builder.own(scenario.needs_package, dependency)
    result = _check(scenario, "derivesRequirementFromNeed", requirement)
    assert result.problem == "" and result.hops == ()
    assert result.absent.endswith("has no derivesRequirementFromNeed target")
    assert result.near_misses == (
        "1 plain dependency derivation(s) to needs do not count; only a DerivesFromNeed connection does",)


def test_a_connection_carried_relation_reads_export_shaped_connections() -> None:
    scenario = increment_scenario()
    result = _check(scenario, "hasValidationScenario", scenario.needs[0])
    assert result.problem == ""
    assert result.targets == [_named(scenario, "scenario0")["@id"]]
    assert result.witnesses == [_named(scenario, "need0ValidationPlanning")["@id"]]


def test_a_need_without_a_planning_connection_reaches_no_scenario() -> None:
    scenario = increment_scenario()
    scenario.builder.remove(_named(scenario, "need0ValidationPlanning"))
    result = _check(scenario, "hasValidationScenario", scenario.needs[0])
    assert result.problem == "" and result.hops == ()
    assert result.absent.endswith(
        "need0 has no ValidationPlanningAssociation connection to a ValidationPlanningScenario")


@pytest.mark.parametrize("relation", ["hasStakeholder", "usesVerificationMethod", "specifiesFeature"])
def test_a_relation_without_a_sysml_mapping_is_method_side_never_missing(relation: str) -> None:
    scenario = increment_scenario()
    result = _check(scenario, relation, scenario.requirements[0])
    assert result.method_side and result.problem == f"governed-relation:{relation}"
    assert result.hops == () and result.absent == ""


def test_an_external_relation_is_method_side() -> None:
    scenario = increment_scenario()
    result = _check(scenario, "hasEvidence", scenario.cases[0])
    assert result.method_side and result.problem == "external-relation:hasEvidence"


def test_unreadable_witnesses_are_a_model_problem_not_a_gap(monkeypatch) -> None:
    from de4sdv.semantic.relationship_successor import SuccessorTraversal

    def unreadable(self, predicate, source, elements):
        self.unavailable(predicate, "native connection endpoint is absent")
        return []

    monkeypatch.setattr(SuccessorTraversal, "traverse", unreadable)
    scenario = increment_scenario()
    result = _check(scenario, "derivesRequirementFromNeed", scenario.requirements[0])
    assert result.problem == "model-witness:derivesRequirementFromNeed" and not result.method_side
    assert result.reason == "native connection endpoint is absent"


def test_native_relations_read_their_memberships() -> None:
    scenario = increment_scenario()
    need, requirement, case = scenario.needs[0], scenario.requirements[0], scenario.cases[0]
    assert _check(scenario, "frame", need).targets == [scenario.concern["@id"]]
    assert len(_check(scenario, "stakeholder", need).targets) == 1
    assert len(_check(scenario, "subject", requirement).targets) == 1
    # The case verifies through the objective of its definition (inherited).
    assert _check(scenario, "verify", case).targets == [r["@id"] for r in scenario.requirements]


def test_native_relations_state_what_is_absent() -> None:
    scenario = increment_scenario()
    builder = scenario.builder
    bare = builder.usage("RequirementUsage", "bareRequirement", scenario.needs_package)
    for relation, absent in (("frame", "frames no concern"), ("stakeholder", "declares no stakeholder"),
                             ("subject", "declares no subject")):
        result = _check(scenario, relation, bare)
        assert result.hops == () and result.absent.endswith(absent), relation


def test_only_connection_ends_in_the_range_lineage_are_targets() -> None:
    scenario = increment_scenario()
    builder = scenario.builder
    association = _named(scenario, "FixtureValidationAssociation")
    stray = builder.usage("PartUsage", "notAScenario", scenario.needs_package)
    builder.remove(_named(scenario, "need1ValidationPlanning"))
    builder.connection("need1StrayPlanning", scenario.needs_package, association,
                       [("source", scenario.needs[1]), ("target", stray)])
    result = _check(scenario, "hasValidationScenario", scenario.needs[1])
    assert result.problem == "" and result.hops == ()
