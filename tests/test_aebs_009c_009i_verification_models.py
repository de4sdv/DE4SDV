"""Increment-specific content pins for the AEBS 009C-009I verification models.

Structural shape (objectives, pipeline, usage/def wiring, product-claim
resistance, verdict vocabulary) is asserted once, capability-agnostically,
in ``tests/test_verification_model_invariants.py`` — every discovered
verification model is covered there automatically.

Only increment-specific *content* is pinned here: the exact evidence
contracts and dependency pairings that make each increment mean what it
means. A new capability adds its own content pins only where its semantics
are genuinely unique.
"""

import re
from pathlib import Path

from sysml_shapes import braced_body, load_model, strip_comments

ROOT = Path(__file__).parents[1]
MODEL_DIR = ROOT / "textual-notation-of-model/packages/features/aebs"
MODELS = {
    "009C": MODEL_DIR / "aebs_partial_intervention_verification.sysml",
    "009D": MODEL_DIR / "aebs_override_verification.sysml",
    "009E": MODEL_DIR / "aebs_non_activation_verification.sysml",
    "009F": MODEL_DIR / "aebs_degraded_input_verification.sysml",
    "009G": MODEL_DIR / "aebs_pedestrian_verification.sysml",
    "009H": MODEL_DIR / "aebs_bicycle_verification.sysml",
    "009I": MODEL_DIR / "aebs_regulatory_criterion_verification.sysml",
}


def _source(increment: str) -> tuple[str, str]:
    """(raw, comment-stripped) source for one increment's verification model."""
    return load_model(MODELS[increment])


def test_009i_target_cases_verify_only_their_applicable_criterion_contract():
    code = _source("009I")[1]
    pedestrian = braced_body(
        code, "verification def PedestrianCriterionVerification009I"
    )
    bicycle = braced_body(code, "verification def BicycleCriterionVerification009I")
    assert "verify evidenceContract009IPedestrianApplicableCriterion;" in pedestrian
    assert "verify evidenceContract009IBicycleApplicableCriterion;" not in pedestrian
    assert "verify evidenceContract009IBicycleApplicableCriterion;" in bicycle
    assert "verify evidenceContract009IPedestrianApplicableCriterion;" not in bicycle


def test_009c_maps_all_five_scenario_outcomes_to_native_verdicts():
    code = _source("009C")[1]
    for outcome in (
        "passObservedChain",
        "failScenario",
        "inconclusivePrecondition",
        "inconclusiveInstrumentation",
        "aborted",
    ):
        assert outcome in code
    assert "Map009COutcomeToVerdict" in code


def test_split_candidate_relevance_dependencies_match_atomic_meanings():
    e = _source("009E")[1]
    f = _source("009F")[1]
    g = _source("009G")[1]
    h = _source("009H")[1]
    i = _source("009I")[1]

    assert re.search(r"from\s+evidenceContract009EWarningSilenceWindow\s+to\s+reqResistFalseReaction\s*;", e)
    assert re.search(r"from\s+evidenceContract009EBrakingSilenceWindow\s+to\s+reqResistFalseBrakingCommand\s*;", e)
    assert re.search(r"from\s+evidenceContract009FStateOwnership\s+to\s+reqHandleDegradedUnavailableInputs\s*;", f)
    assert re.search(r"from\s+evidenceContract009FStatusIndication\s+to\s+reqIndicateDegradedUnavailableStatus\s*;", f)

    assert re.search(r"from\s+\w+\s+to\s+reqPedestrianTargetResponse\s*;", g)
    assert re.search(r"from\s+\w+\s+to\s+reqPedestrianTargetControlledResponse\s*;", g)
    assert "reqBicycleTarget" not in g
    assert re.search(r"from\s+\w+\s+to\s+reqBicycleTargetResponse\s*;", h)
    assert re.search(r"from\s+\w+\s+to\s+reqBicycleTargetControlledResponse\s*;", h)
    assert "reqPedestrianTarget" not in h

    assert re.search(r"from\s+evidenceContract009IPedestrianApplicableCriterion\s+to\s+reqPedestrianTargetResponse\s*;", i)
    assert re.search(r"from\s+evidenceContract009IPedestrianApplicableCriterion\s+to\s+reqPedestrianTargetControlledResponse\s*;", i)
    assert re.search(r"from\s+evidenceContract009IBicycleApplicableCriterion\s+to\s+reqBicycleTargetResponse\s*;", i)
    assert re.search(r"from\s+evidenceContract009IBicycleApplicableCriterion\s+to\s+reqBicycleTargetControlledResponse\s*;", i)


def test_009i_models_source_criterion_measurement_and_provenance_as_fail_closed_contracts():
    code = _source("009I")[1]
    for target in (
        "evidenceContract009ISourceIdentity",
        "evidenceContract009IPedestrianApplicableCriterion",
        "evidenceContract009IBicycleApplicableCriterion",
        "evidenceContract009IMeasurementTrace",
        "evidenceContract009IProvenance",
        "evidenceContract009IConfigurationBoundedVerdict",
    ):
        assert f"verify {target};" in code
    source = _source("009I")[0]
    assert "source identity gap" not in source.lower()
    assert "E/ECE/TRANS/505/Rev.3/Add.151/Rev.2" in source
    assert "dc9cc84498dcae8f0888067ad3967fb5a346e814bc2f19128987a654c8a193de" in source
    assert "aebs-regulatory-source.yaml" in source
    assert "aebs-regulatory-criteria.yaml" in source
    assert "scripts/aebs_regulatory_criteria.py" in source
    assert "applicability" in source.lower()
    assert "compliance" in source.lower()
    assert "withheld" in source.lower()
    assert "@VerificationMethod{ kind = inspect; }" in strip_comments(source)


def test_override_matrix_spans_all_six_override_verifications():
    code = _source("009D")[1]
    for usage in (
        "overrideFalseControlVerification009D",
        "overrideTrueVerification009D",
        "overrideStaleVerification009D",
        "overrideMissingVerification009D",
        "overrideMalformedVerification009D",
        "overrideFutureStampedVerification009D",
    ):
        assert usage in code
