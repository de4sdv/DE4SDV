"""Lexical guards for the generic method gates and the increment declaration.

The gates live in DE4SDV_MethodGates as typed MethodGate usages, one gate per
rule clause. These tests lock the encoding (fields, phases, blocking versus
advisory, empty-population policy, prerequisites) and the INC-AEBS-010
declaration shape. They are text checks, not a SysML parser; licensed SysML
validation stays the authority for syntax and semantics.
"""

from __future__ import annotations

import re

from sysml_shapes import MODEL_ROOT, braced_body, strip_comments

METHODS = MODEL_ROOT / "packages/methods/de4sdv"
GATES_FILE = METHODS / "de4sdv_method_gates.sysml"
FRAMING_FILE = MODEL_ROOT / "packages/features/aebs/aebs_visualization_framing.sysml"

CONTRACT_FIELDS = (
    "obligationId", "phase", "subjectSelector", "applicability", "minimumPopulation",
    "permittedEmpty", "predicate", "targetFilter", "cardinalityMinimum",
    "cardinalityMaximum", "required", "evaluationSource", "attestationPolicyRef",
    "claimBoundary",
)
GATES_BY_PHASE = {
    "phase0_incrementFraming": {
        "incrementHasIdentifier", "incrementHasCharter", "incrementHasProblemStatement",
        "incrementHasEngineeringQuestion", "incrementHasLifecycleDecision",
        "incrementHasAssumption", "incrementHasStakeholder", "incrementHasFramedConcern",
        "incrementHasScope", "incrementHasOutOfScopeItem", "incrementHasOwner",
        "incrementDeclaresApplicablePhases", "incrementDeclaresExpectedArtifacts",
        "incrementDeclaresExpectedReviewEvidence",
    },
    "phase4_needs": {
        "needHasStatement", "needHasStakeholder", "needHasSource", "needHasRationale",
        "needHasValidationScenario", "needFramesConcern",
    },
    "phase5_requirements": {
        "requirementDerivesFromNeed", "requirementHasOneSubject",
        "requirementHasVerificationMethod", "requirementSpecifiesFeatureOrCapability",
    },
    "phase10_vvEvidence": {
        "verificationCaseVerifiesRequirement", "requirementVerifiedByVerificationCase",
        "verificationCaseVerifiesAcceptanceCriterion", "verificationCaseHasEvidenceRecordOrStatus",
    },
}
ADVISORY = {
    "requirementSpecifiesFeatureOrCapability",
    "verificationCaseVerifiesAcceptanceCriterion",
    "verificationCaseHasEvidenceRecordOrStatus",
}
SELECTORS = {"incrementIdentifier", "increment", "incrementNeeds", "incrementRequirements",
             "incrementVerificationCases"}


def _code(path) -> str:
    return strip_comments(path.read_text(encoding="utf-8"))


def _gates() -> dict[str, dict[str, str]]:
    code = _code(GATES_FILE)
    gates = {}
    for name in re.findall(r"\bitem\s+(\w+)\s*:\s*MethodGate\s*\{", code):
        body = braced_body(code, f"item {name} : MethodGate")
        fields = dict(re.findall(r"attribute\s+:>>\s+(\w+)\s*=\s*([^;]*);", body))
        prerequisites = re.findall(r"ref\s+item\s+:>>\s+prerequisites\s*=\s*([^;]*);", body)
        fields["prerequisites"] = prerequisites[0] if prerequisites else ""
        gates[name] = fields
    return gates


def test_gate_vocabulary_specializes_the_obligation_without_restating_it() -> None:
    code = _code(GATES_FILE)
    body = braced_body(code, "item def MethodGate :> MethodContractObligation")
    declared = set(re.findall(r"(?:ref\s+item|attribute)\s+(\w+)\s*:", body))
    assert declared == {"prerequisites", "permittedEmptyDisposition"}
    assert re.search(r"ref\s+item\s+prerequisites\s*:\s*MethodContractObligation\[0\.\.\*\]", body)
    disposition = braced_body(code, "enum def PermittedEmptyDisposition")
    assert set(re.findall(r"^\s*(\w+)\s*\{", disposition, re.MULTILINE)) == {
        "noEligibleSubjects", "explicitDisposition"}
    charter = braced_body(code, "part def IncrementCharter :> IncrementTraceObligations")
    assert set(re.findall(r"attribute\s+(\w+)\s*:", charter)) == {
        "owner", "expectedArtifacts", "expectedReviewEvidence"}


def test_one_gate_per_rule_clause_in_each_phase() -> None:
    gates = _gates()
    by_phase: dict[str, set[str]] = {}
    for name, fields in gates.items():
        literal = fields["phase"].removeprefix("MethodPhase::")
        by_phase.setdefault(literal, set()).add(name)
    assert by_phase == GATES_BY_PHASE


def test_every_gate_binds_the_full_contract_with_its_own_name() -> None:
    for name, fields in _gates().items():
        missing = [field for field in CONTRACT_FIELDS if field not in fields]
        assert not missing, (name, missing)
        assert fields["obligationId"] == f'"{name}"', name
        assert fields["subjectSelector"].strip('"') in SELECTORS, name
        assert fields["predicate"].strip('"'), name
        assert fields["claimBoundary"].strip('"'), name
        assert fields["evaluationSource"] == "EvaluationSourceKind::pinnedModelRecord", name
        assert fields["attestationPolicyRef"] == '""', name
        # An unbounded maximum is the infinity literal, never a numeric sentinel.
        assert fields["cardinalityMaximum"] in {"1", "*"}, name
        assert fields["cardinalityMinimum"] == "1", name


def test_structural_gates_block_and_named_trace_checks_are_advisory() -> None:
    gates = _gates()
    assert {name for name, fields in gates.items() if fields["required"] == "false"} == ADVISORY
    assert all(fields["required"] in {"true", "false"} for fields in gates.values())


def test_empty_population_policy_is_explicit() -> None:
    for name, fields in _gates().items():
        permitted = fields["permittedEmpty"] == "true"
        disposition = fields.get("permittedEmptyDisposition")
        if permitted:
            assert fields["minimumPopulation"] == "0", name
            assert disposition == "PermittedEmptyDisposition::noEligibleSubjects", name
        else:
            assert fields["minimumPopulation"] == "1", name
            assert disposition is None, name
    assert _gates()["requirementVerifiedByVerificationCase"]["permittedEmpty"] == "true"
    for name in GATES_BY_PHASE["phase4_needs"]:
        assert _gates()[name]["permittedEmpty"] == "false", name


def test_prerequisites_reference_declared_gates_without_cycles() -> None:
    gates = _gates()
    edges = {}
    for name, fields in gates.items():
        targets = [t.strip() for t in fields["prerequisites"].strip("()").split(",") if t.strip()]
        assert all(target in gates for target in targets), (name, targets)
        edges[name] = targets
    assert edges["incrementHasIdentifier"] == []
    for name in set(gates) - GATES_BY_PHASE["phase0_incrementFraming"]:
        assert edges[name] == ["incrementDeclaresApplicablePhases"], name

    def reaches(start: str, goal: str, seen: frozenset = frozenset()) -> bool:
        return any(nxt == goal or (nxt not in seen and reaches(nxt, goal, seen | {nxt}))
                   for nxt in edges[start])

    assert not [name for name in gates if reaches(name, name)]


def test_gates_are_generic_and_semantically_named() -> None:
    code = _code(GATES_FILE)
    code_without_strings = re.sub(r'"(?:[^"\\]|\\.)*"', '""', code)
    assert not re.search(r"\b(?:AEBS|aebs|Visualization|incAEBS\w*|Middleware|middleware)", code_without_strings)
    for name in _gates():
        # Phases never name model elements; pilot obligation scans read
        # ItemUsages named obligation*, so gates never use that prefix.
        assert not re.match(r"(?:p|phase)\d", name), name
        assert not name.startswith("obligation"), name


def test_each_gate_encodes_exactly_one_accepted_rule() -> None:
    code = _code(GATES_FILE)
    annotated: dict[str, list[str]] = {}
    rules = dict(re.findall(r"\bcomment\s+(\w+)\s+about\s+([^;{}]*?)(?=\n\s*\n|\Z)", code))
    assert set(rules) == {
        "blockingPrinciple", "incrementRule", "needsRule", "needFramingRule",
        "requirementDerivationRule", "requirementRule", "verificationRule", "advisoryTraceRule"}
    assert rules["blockingPrinciple"].strip() == "MethodGate"
    for rule, targets in rules.items():
        for target in (name.strip() for name in targets.split(",")):
            annotated.setdefault(target, []).append(rule)
    for name in _gates():
        assert len(annotated.get(name, [])) == 1, (name, annotated.get(name))
    assert set(annotated) - {"MethodGate"} == set(_gates())
    advisory_rule = {t.strip() for t in rules["advisoryTraceRule"].split(",")}
    assert advisory_rule == ADVISORY


def test_inc_aebs_010_is_declared_with_identifier_and_charter() -> None:
    code = _code(FRAMING_FILE)
    assert re.search(r"\bpart\s+<'INC-AEBS-010'>\s+incAEBS010\s*:\s*VisualizationIncrement\s*\{", code)
    body = braced_body(code, "part visualizationTraceObligations : IncrementCharter")
    phases = re.search(r"attribute\s+:>>\s+applicablePhases\s*=\s*\(([^)]*)\)\s*;", body).group(1)
    assert [p.strip().removeprefix("MethodPhase::") for p in phases.split(",")] == [
        "phase0_incrementFraming", "phase1_concernFraming", "phase2_operationalContext",
        "phase3_capabilityClassification", "phase4_needs", "phase5_requirements",
        "phase6_functionalArchitecture", "phase7_logicalArchitecture",
        "phase8_physicalRealization", "phase9_variabilityConfiguration", "phase10_vvEvidence"]
    assert re.search(r'attribute\s+:>>\s+owner\s*=\s*"[^"]+"\s*;', body)
    artifacts = re.search(r"attribute\s+:>>\s+expectedArtifacts\s*=\s*\(([^)]*)\)\s*;", body).group(1)
    packages = set(re.findall(r'"([^"]+)"', artifacts))
    declared = {match for path in MODEL_ROOT.rglob("*.sysml")
                for match in re.findall(r"^package\s+(\w+)", _code(path), re.MULTILINE)}
    assert packages and packages <= declared, packages - declared
    evidence = re.search(r"attribute\s+:>>\s+expectedReviewEvidence\s*=\s*\(([^)]*)\)\s*;", body).group(1)
    assert all(item.strip() for item in re.findall(r'"([^"]*)"', evidence))
