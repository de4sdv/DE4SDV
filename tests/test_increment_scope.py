"""Increment resolution: identifier grammar, model identity, charter and scope.

An increment is identified only by its registered identifier carried as the
declared short name of a part usage in the EngineeringIncrement lineage
(validated kernel identity, never a name). Its charter declaration is the
IncrementTraceObligations-lineage usage whose ``increment`` value references
it. Its scope is the packages the charter declares in ``expectedArtifacts``,
with the packages nested in them.
"""

from __future__ import annotations

import pytest

from de4sdv.semantic.increment_scope import (
    IncrementIdentifierError,
    ModelView,
    parse_increment_id,
    resolve_increment,
)
from increment_model_fixtures import ModelBuilder, increment_scenario
from test_revision_index import _traversal


def _view(scenario) -> ModelView:
    builder = scenario.builder
    return ModelView(builder.elements, _traversal(builder), sources=builder.sources)


@pytest.mark.parametrize("text", ["INC-AEBS-010", "INC-AEBS-009D", "INC-MW-010-02", "INC-FIXTURE-001"])
def test_registered_identifier_grammar_is_accepted(text: str) -> None:
    assert parse_increment_id(text) == text


@pytest.mark.parametrize(
    "text", ["inc-aebs-010", "AEBS-010", "INC-AEBS", "INC--010", " INC-AEBS-010", "INC-AEBS-010 ",
             "REQ-AEBS-010", "INC-aebs-010", ""],
)
def test_malformed_identifier_is_refused_with_the_grammar(text: str) -> None:
    with pytest.raises(IncrementIdentifierError, match=r"INC-<SUBJECT>-<SEQ>"):
        parse_increment_id(text)


def test_complete_increment_resolves_identity_charter_and_scope() -> None:
    scenario = increment_scenario()
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert scope.usage_id == scenario.usage["@id"]
    assert scope.candidates == (scenario.usage["@id"],)
    assert scope.definition_ids == (scenario.definition["@id"],)
    assert scope.package_id == scenario.framing["@id"]
    assert scope.charters == (scenario.charter["@id"],)
    assert scope.declared_phases == (
        "phase0_incrementFraming", "phase4_needs", "phase5_requirements", "phase10_vvEvidence")
    assert scope.scope_packages == (
        scenario.framing["@id"], scenario.needs_package["@id"], scenario.evidence_package["@id"])
    for element in (scenario.usage, scenario.charter, *scenario.needs, *scenario.requirements, *scenario.cases):
        assert element["@id"] in scope.scope_elements


def test_scope_is_the_packages_the_charter_declares() -> None:
    scenario = increment_scenario()
    b = scenario.builder
    extra = b.package("DE4SDV_FixtureExtraEvidence")
    b.references(extra, scenario.usage)  # referencing the increment does not put a package in scope
    stray_def = b.definition("VerificationCaseDefinition", "StrayVerification", extra)
    stray = b.usage("VerificationCaseUsage", "strayVerification", extra, [stray_def])
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert extra["@id"] not in scope.scope_packages and stray["@id"] not in scope.scope_elements
    declared = b.feature_of(scenario.charter, "expectedArtifacts")
    b.remove(declared)
    b.attribute(scenario.charter, "expectedArtifacts",
                ["DE4SDV_FixtureFraming", "DE4SDV_FixtureExtraEvidence"])
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert scope.scope_packages == (scenario.framing["@id"], extra["@id"])
    assert stray["@id"] in scope.scope_elements
    assert scenario.needs[0]["@id"] not in scope.scope_elements


def test_scope_reaches_nested_packages_but_not_features() -> None:
    scenario = increment_scenario()
    b = scenario.builder
    nested = b.package("NestedRequirements", owner=scenario.needs_package)
    deep = b.usage("RequirementUsage", "deepRequirement", nested, [b.kernel["Requirement"]])
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert deep["@id"] in scope.scope_elements
    shadows = [e["@id"] for e in b.elements if e["@type"] == "ConcernUsage" and e["@id"] != scenario.concern["@id"]]
    assert shadows and not set(shadows) & set(scope.scope_elements)  # framed-concern shadows of needs


def test_a_declared_artifact_without_a_package_is_reported() -> None:
    scenario = increment_scenario()
    b = scenario.builder
    b.remove(b.feature_of(scenario.charter, "expectedArtifacts"))
    b.attribute(scenario.charter, "expectedArtifacts", ["DE4SDV_FixtureFraming", "DE4SDV_FixtureMissing"])
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert scope.scope_packages == (scenario.framing["@id"],)
    assert any("DE4SDV_FixtureMissing" in d for d in scope.diagnostics)


def test_short_name_outside_the_increment_lineage_is_not_the_increment() -> None:
    builder = ModelBuilder(label="impostor")
    package = builder.package("ImpostorPackage")
    builder.kernel_definition("EngineeringIncrement")
    other = builder.definition("PartDefinition", "NotAnIncrement", package)
    impostor = builder.usage("PartUsage", "impostor", package, [other], short="INC-FIXTURE-001")
    scope = resolve_increment(ModelView(builder.elements, _traversal(builder)), "INC-FIXTURE-001")
    assert scope.usage_id is None
    assert scope.candidates == ()
    assert scope.rejected_candidates == (impostor["@id"],)
    assert any("EngineeringIncrement lineage" in d for d in scope.diagnostics)


def test_unknown_identifier_resolves_to_no_increment() -> None:
    scenario = increment_scenario()
    scope = resolve_increment(_view(scenario), "INC-FIXTURE-002")
    assert scope.usage_id is None and scope.candidates == ()
    assert scope.scope_packages == () and scope.scope_elements == ()
    assert scope.declared_phases is None


def test_two_increments_with_one_identifier_are_ambiguous() -> None:
    scenario = increment_scenario()
    builder = scenario.builder
    builder.usage("PartUsage", "duplicateIncrement", scenario.framing, [scenario.definition],
                  short=scenario.increment_id)
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert scope.usage_id is None
    assert len(scope.candidates) == 2
    assert any("ambiguous" in d for d in scope.diagnostics)


def test_charter_count_other_than_one_leaves_phases_and_scope_unresolved() -> None:
    scenario = increment_scenario()
    scenario.builder.remove(scenario.charter)
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert scope.charters == ()
    assert scope.declared_phases is None
    assert scope.scope_packages == ()
