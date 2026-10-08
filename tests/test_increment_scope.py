"""Increment resolution: identifier grammar, model identity and populations.

An increment is identified only by its registered identifier carried as the
declared short name of a part usage in the EngineeringIncrement lineage
(validated kernel identity, never a name). Its charter declaration is the
IncrementTraceObligations-lineage usage whose ``increment`` value references
it; its populations are read from native relationships.
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


def test_complete_increment_resolves_identity_charter_and_populations() -> None:
    scenario = increment_scenario()
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert scope.usage_id == scenario.usage["@id"]
    assert scope.candidates == (scenario.usage["@id"],)
    assert scope.definition_ids == (scenario.definition["@id"],)
    assert scope.package_id == scenario.framing["@id"]
    assert scope.charters == (scenario.charter["@id"],)
    assert scope.declared_phases == (
        "phase0_incrementFraming", "phase4_needs", "phase5_requirements", "phase10_vvEvidence")
    assert scope.populations["incrementNeeds"] == tuple(n["@id"] for n in scenario.needs)
    assert scope.populations["incrementRequirements"] == tuple(r["@id"] for r in scenario.requirements)
    assert scope.populations["incrementVerificationCases"] == tuple(c["@id"] for c in scenario.cases)
    assert scope.populations["increment"] == (scenario.usage["@id"],)
    assert scope.populations["incrementIdentifier"] == (scenario.increment_id,)
    assert scope.verification_packages == (scenario.framing["@id"], scenario.evidence_package["@id"])


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
    assert scope.populations["increment"] == ()
    assert scope.populations["incrementIdentifier"] == ("INC-FIXTURE-002",)
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


def test_charter_count_other_than_one_leaves_phases_unresolved() -> None:
    scenario = increment_scenario()
    scenario.builder.remove(scenario.charter)
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert scope.charters == ()
    assert scope.declared_phases is None


def test_requirement_population_excludes_evidence_contracts_and_foreign_subjects() -> None:
    scenario = increment_scenario()
    b = scenario.builder
    evidence_root = scenario.vocabulary["EvidenceContract"]
    evidence_def = b.definition("RequirementDefinition", "FixtureEvidenceContract", scenario.needs_package,
                                [evidence_root])
    contract_usage = b.usage("RequirementUsage", "fixtureEvidence", scenario.needs_package, [evidence_def])
    b.subject(contract_usage, scenario.definition, name="increment")
    foreign_def = b.definition("PartDefinition", "ForeignSubject", scenario.needs_package)
    foreign = b.usage("RequirementUsage", "foreignRequirement", scenario.needs_package,
                      [b.kernel["Requirement"]])
    b.subject(foreign, foreign_def, name="other")
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert contract_usage["@id"] not in scope.populations["incrementRequirements"]
    assert foreign["@id"] not in scope.populations["incrementRequirements"]
    assert scope.populations["incrementRequirements"] == tuple(r["@id"] for r in scenario.requirements)


def test_verification_cases_come_only_from_the_increment_and_referencing_packages() -> None:
    scenario = increment_scenario()
    b = scenario.builder
    unrelated = b.package("DE4SDV_UnrelatedEvidence")
    stray_def = b.definition("VerificationCaseDefinition", "StrayVerification", unrelated)
    stray = b.usage("VerificationCaseUsage", "strayVerification", unrelated, [stray_def])
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert stray["@id"] not in scope.populations["incrementVerificationCases"]
