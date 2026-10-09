"""Lexical guards for the increment workflow, its method checks and INC-AEBS-010.

DE4SDV_IncrementWorkflow holds the increment workflow (one step per method
phase, in method order) and, inside the step definitions, MethodCheck metadata
usages about step parameters that encode the accepted method rules. These tests
lock that encoding. They are text checks, not a SysML parser; licensed SysML
validation stays the authority for syntax and semantics.
"""

from __future__ import annotations

import gzip
import json
import re

from increment_model_fixtures import GENUINE_EXPORT
from sysml_shapes import MODEL_ROOT, braced_body, strip_comments

WORKFLOW_FILE = MODEL_ROOT / "packages/methods/de4sdv/de4sdv_increment_workflow.sysml"
FRAMING_FILE = MODEL_ROOT / "packages/features/aebs/aebs_visualization_framing.sysml"
WORKFLOW_DOC = MODEL_ROOT.parent / "methodologies/sysmod-sysmlv2/increment-workflow.md"

PHASES = (
    "phase0_incrementFraming", "phase1_concernFraming", "phase2_operationalContext",
    "phase3_capabilityClassification", "phase4_needs", "phase5_requirements",
    "phase6_functionalArchitecture", "phase7_logicalArchitecture", "phase8_physicalRealization",
    "phase9_variabilityConfiguration", "phase10_vvEvidence", "phase11_publication",
    "phase12_baselineNextSlice",
)
# One check per accepted rule clause, in the step whose output it is about.
CHECKS_BY_STEP = {
    "FrameIncrement": {
        "incrementHasIdentifier", "incrementHasCharter", "incrementHasProblemStatement",
        "incrementHasEngineeringQuestion", "incrementHasLifecycleDecision",
        "incrementHasAssumption", "incrementHasStakeholder", "incrementHasFramedConcern",
        "incrementHasScope", "incrementHasOutOfScopeItem", "incrementHasOwner",
        "incrementDeclaresApplicablePhases", "incrementDeclaresExpectedArtifacts",
        "incrementDeclaresExpectedReviewEvidence",
    },
    "ElaborateNeeds": {
        "needHasStatement", "needHasStakeholder", "needHasSource", "needHasRationale",
        "needHasValidationScenario",
    },
    "SpecifyRequirements": {
        "requirementDerivesFromNeed", "requirementHasOneSubject",
        "requirementHasVerificationMethod", "requirementSpecifiesFeatureOrCapability",
    },
    "PlanVerificationAndEvidence": {
        "verificationCaseVerifiesRequirement", "requirementVerifiedByVerificationCase",
        "verificationCaseVerifiesAcceptanceCriterion", "verificationCaseHasEvidenceRecordOrStatus",
    },
}
ADVISORY = {
    "requirementSpecifiesFeatureOrCapability",
    "verificationCaseVerifiesAcceptanceCriterion",
    "verificationCaseHasEvidenceRecordOrStatus",
}
# Registry contract for the evaluation engine: every check identifier the model
# uses must be one of these. The engine fails closed on any other identifier.
CHECK_REGISTRY = {
    "incrementShortName", "charterReferencesIncrement", "problemStatementSubject",
    "ownedByIncrementPackage", "stakeholderMember", "framedByIncrementView", "charterOwner",
    "charterApplicablePhases", "charterExpectedArtifacts", "charterExpectedReviewEvidence",
    "requireConstraint", "sourceAttribute", "rationaleAttribute", "hasValidationScenario",
    "framesStakeholderConcern", "derivesRequirementFromNeed", "oneNativeSubject",
    "oneVerificationMethodKind", "specifiesFeatureOrCommonCapability",
    "verifiesIncrementRequirement", "verifiedBy", "verifiesAcceptanceCriterion",
    "evidenceRecordOrStatus",
}
# Registry entries the workflow no longer declares: the engine keeps them only for
# the frozen genuine-export cut, whose workflow predates their removal. Needs never
# frame concerns; only viewpoints do.
FROZEN_CUT_ONLY_CHECKS = {"framesStakeholderConcern"}


def _code(path) -> str:
    return strip_comments(path.read_text(encoding="utf-8"))


def _steps() -> list[tuple[str, str, str]]:
    """(usage, multiplicity, definition) of the workflow steps in order."""
    body = braced_body(_code(WORKFLOW_FILE), "action def IncrementWorkflow")
    return re.findall(r"\bthen\s+action\s+(\w+)\s*(\[[^\]]*\])?\s*:\s*(\w+)\s*;", body)


def _step_body(definition: str) -> str:
    return braced_body(_code(WORKFLOW_FILE), f"action def {definition} :> IncrementStep")


def _checks(definition: str) -> dict[str, dict[str, str]]:
    checks = {}
    body = _step_body(definition)
    for name, target in re.findall(r"\bmetadata\s+(\w+)\s*:\s*MethodCheck\s+about\s+(\w+)\s*\{", body):
        check_body = braced_body(body, f"metadata {name} : MethodCheck about {target}")
        fields = dict(re.findall(r":>>\s*(\w+)\s*=\s*([^;]*);", check_body))
        checks[name] = {"about": target, **fields}
    return checks


def test_workflow_orders_one_step_per_phase_and_makes_later_steps_optional() -> None:
    steps = _steps()
    assert len(steps) == 13
    phases = []
    for usage, multiplicity, definition in steps:
        assert usage == definition[0].lower() + definition[1:], usage
        assert multiplicity == ("" if usage == "frameIncrement" else "[0..1]"), usage
        phase = re.search(r"attribute\s+:>>\s+phase\s*=\s*MethodPhase::(\w+)\s*;", _step_body(definition))
        phases.append(phase.group(1))
    assert phases == list(PHASES)
    body = braced_body(_code(WORKFLOW_FILE), "action def IncrementWorkflow")
    assert re.search(r"\bfirst\s+start\s*;", body) and re.search(r"\bthen\s+done\s*;", body)


def test_each_step_asks_its_phase_question_and_declares_artifacts() -> None:
    table = WORKFLOW_DOC.read_text(encoding="utf-8")
    questions = re.findall(r"^\| \d+\. [^|]+\| ([^|]+?) \|", table, re.MULTILINE)
    assert len(questions) == 13
    text = WORKFLOW_FILE.read_text(encoding="utf-8")
    for (_, _, definition), question in zip(_steps(), questions):
        start = text.index(f"action def {definition} :> IncrementStep")
        doc = re.search(r"doc\s*/\*(.*?)\*/", text[start:], re.DOTALL).group(1)
        assert " ".join(question.split()) in " ".join(doc.replace("*", " ").split()), definition
        assert re.search(r"\bout\s+\w+\s+\w+", _step_body(definition)), definition


def test_checks_encode_the_accepted_rules_about_step_parameters() -> None:
    steps = [definition for _, _, definition in _steps()]
    for definition in steps:
        checks = _checks(definition)
        assert set(checks) == CHECKS_BY_STEP.get(definition, set()), definition
        parameters = set(re.findall(r"\b(?:in|out)\s+\w+\s+(\w+)", _step_body(definition)))
        for name, fields in checks.items():
            assert fields["about"] in parameters, (definition, name)
            assert re.fullmatch(r'"\w+"', fields["check"]), (definition, name)


def test_every_check_identifier_is_in_the_registry() -> None:
    used = {fields["check"].strip('"') for _, _, definition in _steps()
            for fields in _checks(definition).values()}
    assert used and used <= CHECK_REGISTRY, used - CHECK_REGISTRY
    current = CHECK_REGISTRY - FROZEN_CUT_ONLY_CHECKS
    assert current <= used, current - used  # no stale registry entry
    assert not used & FROZEN_CUT_ONLY_CHECKS, used & FROZEN_CUT_ONLY_CHECKS


def test_checks_kept_for_the_frozen_cut_expire_with_it() -> None:
    """A re-cut that no longer declares such a check fails here: then remove it from
    FROZEN_CUT_ONLY_CHECKS, CHECK_REGISTRY and the engine."""
    cut = json.loads(gzip.decompress(GENUINE_EXPORT.read_bytes()))
    literals = {e.get("value") for e in cut["elements"] if e.get("@type") == "LiteralString"}
    assert FROZEN_CUT_ONLY_CHECKS <= literals, FROZEN_CUT_ONLY_CHECKS - literals


def test_structural_checks_block_and_the_named_trace_checks_are_advisory() -> None:
    advisory = {name for _, _, definition in _steps()
                for name, fields in _checks(definition).items()
                if fields.get("advisory") == "true"}
    assert advisory == ADVISORY


def test_method_check_is_a_light_metadata_definition() -> None:
    body = braced_body(_code(WORKFLOW_FILE), "metadata def MethodCheck")
    declared = re.findall(r"\battribute\s+(\w+)\s*:\s*(\w+)(?:\s+default\s+(\w+))?", body)
    assert declared == [("check", "String", ""), ("minimum", "Natural", "1"),
                        ("advisory", "Boolean", "false")]


def test_workflow_is_generic_and_semantically_named() -> None:
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', _code(WORKFLOW_FILE))
    assert not re.search(r"\b(?:AEBS|aebs|Visualization|incAEBS\w*|Middleware|middleware)", code)
    names = re.findall(r"\b(?:\w+\s+def|metadata|then\s+action)\s+(\w+)", code)
    assert names
    for name in names:
        # Phases never name model elements; pilot obligation scans read
        # ItemUsages named obligation*, so no element uses that prefix.
        assert not re.match(r"(?:p|phase)\d", name), name
        assert not name.startswith("obligation"), name


def test_inc_aebs_010_is_declared_with_identifier_and_charter() -> None:
    code = _code(FRAMING_FILE)
    assert re.search(r"\bpart\s+<'INC-AEBS-010'>\s+incAEBS010\s*:\s*VisualizationIncrement\s*\{", code)
    assert "private import DE4SDV_IncrementWorkflow::IncrementCharter;" in code
    body = braced_body(code, "part visualizationTraceObligations : IncrementCharter")
    phases = re.search(r"attribute\s+:>>\s+applicablePhases\s*=\s*\(([^)]*)\)\s*;", body).group(1)
    assert [p.strip().removeprefix("MethodPhase::") for p in phases.split(",")] == list(PHASES[:11])
    assert re.search(r'attribute\s+:>>\s+owner\s*=\s*"[^"]+"\s*;', body)
    artifacts = re.search(r"attribute\s+:>>\s+expectedArtifacts\s*=\s*\(([^)]*)\)\s*;", body).group(1)
    packages = set(re.findall(r'"([^"]+)"', artifacts))
    declared = {match for path in MODEL_ROOT.rglob("*.sysml")
                for match in re.findall(r"^package\s+(\w+)", _code(path), re.MULTILINE)}
    assert packages and packages <= declared, packages - declared
    evidence = re.search(r"attribute\s+:>>\s+expectedReviewEvidence\s*=\s*\(([^)]*)\)\s*;", body).group(1)
    assert all(item.strip() for item in re.findall(r'"([^"]*)"', evidence))
