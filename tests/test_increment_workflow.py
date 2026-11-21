"""Lexical guards for the increment workflow, its method checks and INC-AEBS-010.

DE4SDV_IncrementWorkflow holds the increment workflow (one step per method
phase, in method order) and, inside the step definitions, MethodCheck metadata
usages about step parameters that encode the accepted method rules. These tests
lock that encoding. They are text checks, not a SysML parser; licensed SysML
validation stays the authority for syntax and semantics.

Rule 5 has two homes, the method document and the doc of SpecifyRequirements in
the kernel. The last tests keep the two in step, and keep the decision records
that ADR 0027 amends pointing at it.
"""

from __future__ import annotations

import re

from sysml_shapes import MODEL_ROOT, braced_body, strip_comments

WORKFLOW_FILE = MODEL_ROOT / "packages/methods/de4sdv/de4sdv_increment_workflow.sysml"
FRAMING_FILE = MODEL_ROOT / "packages/features/aebs/aebs_visualization_framing.sysml"
WORKFLOW_DOC = MODEL_ROOT.parent / "methodologies/sysmod-sysmlv2/increment-workflow.md"
METHOD_CONTEXT_FILE = MODEL_ROOT / "packages/methods/de4sdv/de4sdv_method_context.sysml"

PHASES = (
    "phase0_incrementFraming", "phase1_concernFraming", "phase2_operationalContext",
    "phase3_capabilityClassification", "phase4_needs", "phase5_requirements",
    "phase6_functionalArchitecture", "phase7_logicalArchitecture", "phase8_physicalRealization",
    "phase9_variabilityConfiguration", "phase10_vvEvidence", "phase11_baseline",
)
# One check per accepted rule clause, in the step whose output it is about.
CHECKS_BY_STEP = {
    "FrameIncrement": {
        "incrementHasIdentifier", "incrementHasCharter", "incrementHasProblemStatement",
        "incrementHasEngineeringQuestion", "incrementHasLifecycleDecision",
        "incrementHasAssumption", "incrementHasStakeholder", "incrementHasFramedConcern",
        "incrementHasScope", "incrementHasOutOfScopeItem", "incrementHasOwner",
        "incrementDeclaresApplicablePhases", "incrementDeclaresExpectedArtifacts",
        "incrementDeclaresExpectedReviewEvidence", "expectedArtifactsCoverIncrementContent",
    },
    "FrameConcerns": {"incrementHasNonBoundaryConcern", "concernHasStakeholder", "concernFramedByViewpoint"},
    "SpecifyOperationalContext": {
        "incrementHasOperationalContext", "operationalContextHoldsSystemOfInterest",
        "storyBindsSubjectToSystemOfInterest", "storyBindsActorsToContextParts",
    },
    "ClassifyCapabilities": {"characteristicIsFeatureDelta"},
    "ElaborateNeeds": {
        "needHasStatement", "needHasStakeholder", "needHasSource", "needHasRationale",
        "needHasValidationScenario", "needSubjectIsSystemOfInterest",
    },
    "SpecifyRequirements": {
        "requirementHasStatement", "requirementDerivesFromNeed", "requirementHasOneSubject",
        "requirementSubjectIsSystemOfInterest", "requirementHasVerificationMethod",
        "requirementStatesSuccessCriteria",
    },
    "DefineFunctionalArchitecture": {
        "functionalRequirementAllocatedToFunction", "incrementHasFunction", "requirementCarriedByArchitecture",
        "functionCarriesRequirement",
    },
    "DefineLogicalArchitecture": {"functionAllocatedToLogicalElement", "logicalElementCarriesFunction"},
    "DefinePhysicalRealization": {
        "logicalElementAllocatedToPhysicalElement", "physicalElementCarriesLogicalElement",
        "crossingHasSignalMapping", "signalMappingNamesSemanticSource",
    },
    "PlanVerificationAndEvidence": {
        "verificationCaseVerifiesRequirement", "requirementVerifiedByVerificationCase",
        "verificationCaseHasEvidenceRecordOrStatus",
    },
    "DefineVariabilityAndConfiguration": {
        "incrementHasConfiguredProduct", "configuredProductConfiguredByOneConfiguration",
    },
    "DecideBaseline": {
        "publishedViewFramesConcern", "publishedViewExposesContent",
        "incrementHasBaselineDecision", "baselineDecisionStatesDisposition", "openGapStatesDisposition",
        "applicablePhaseContentPublished", "concernAnsweredInItsDomain",
    },
}
#: The steps with no executable check. Every step has checks now: a step without one is a method decision
#: this test makes visible.
UNCHECKED_STEPS: set[str] = set()
ADVISORY = {
    "expectedArtifactsCoverIncrementContent",
    "needSubjectIsSystemOfInterest",
    "requirementSubjectIsSystemOfInterest",
    "requirementStatesSuccessCriteria",
    "requirementCarriedByArchitecture",
    "functionCarriesRequirement",
    "logicalElementCarriesFunction",
    "physicalElementCarriesLogicalElement",
    "crossingHasSignalMapping",
    "signalMappingNamesSemanticSource",
    "verificationCaseHasEvidenceRecordOrStatus",
    "applicablePhaseContentPublished",
    "concernAnsweredInItsDomain",
}
# Registry contract for the evaluation engine: every check identifier the model
# uses must be one of these. The engine fails closed on any other identifier.
CHECK_REGISTRY = {
    "incrementShortName", "charterReferencesIncrement", "problemStatementSubject",
    "ownedByIncrementPackage", "stakeholderMember", "framedByIncrementView", "charterOwner",
    "charterApplicablePhases", "charterExpectedArtifacts", "charterExpectedReviewEvidence",
    "requireConstraint", "sourceAttribute", "rationaleAttribute", "hasValidationScenario",
    "derivesRequirementFromNeed", "oneNativeSubject",
    "subjectIsSystemOfInterest", "charterExpectedArtifactsCoverContent",
    "oneVerificationMethodKind", "successCriteriaAttribute",
    "allocatedTo", "populationMember", "carriedByArchitecture", "receivesAllocation",
    "signalMappingRecorded", "semanticSourceNamed",
    "verifiesIncrementRequirement", "verifiedBy", "evidenceRecordOrStatus",
    "framedByViewpoint", "nonBoundaryConcernPresent", "contextSystemOfInterest", "storySubjectBound", "storyActorsBound",
    "featureDeltaOnly", "viewpointFramesConcern", "exposesModelContent", "phaseContentPublished",
    "configuredByOneConfiguration", "dispositionStated", "concernAnsweredInDomain",
}


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
    assert len(steps) == 12
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
    assert len(questions) == 12
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


def test_every_step_has_checks() -> None:
    steps = {definition for _, _, definition in _steps()}
    assert {definition for definition in steps if not _checks(definition)} == UNCHECKED_STEPS
    assert UNCHECKED_STEPS | set(CHECKS_BY_STEP) == steps


def test_every_check_identifier_is_in_the_registry() -> None:
    used = {fields["check"].strip('"') for _, _, definition in _steps()
            for fields in _checks(definition).values()}
    assert used and used <= CHECK_REGISTRY, used - CHECK_REGISTRY
    assert CHECK_REGISTRY <= used, CHECK_REGISTRY - used  # no stale registry entry


def test_structural_checks_block_and_the_named_trace_checks_are_advisory() -> None:
    advisory = {name for _, _, definition in _steps()
                for name, fields in _checks(definition).items()
                if fields.get("advisory") == "true"}
    assert advisory == ADVISORY


#: The architecture steps' parameters (direction, keyword, name, multiplicity, type): the trace profile
#: classes the allocation end pairs reach, the functional requirements the blocking phase-6 check reads.
ARCHITECTURE_PARAMETERS = {
    "DefineFunctionalArchitecture": [
        ("in", "requirement", "requirements", "[0..*]", "RequirementCandidate"),
        ("in", "requirement", "functionalRequirements", "[0..*]", "FunctionalRequirementCandidate"),
        ("out", "action", "functions", "[1..*]", "AllocatableFunction")],
    "DefineLogicalArchitecture": [
        ("in", "action", "functions", "[1..*]", "AllocatableFunction"),
        ("out", "part", "logicalElements", "[1..*]", "LogicalAllocationElement")],
    "DefinePhysicalRealization": [
        ("in", "part", "logicalElements", "[1..*]", "LogicalAllocationElement"),
        ("out", "part", "physicalElements", "[1..*]", "PhysicalAllocationElement"),
        ("out", "allocation", "signalMappings", "[0..*]", "SystemToSoftwareSignalMappingCandidate")],
}


#: The parameters of the steps of phases 1, 2, 3 and 11 (direction, keyword, name, multiplicity, type). An
#: untyped parameter counts the usages of its keyword; the phase-3 output is typed by the classification
#: base, so the check also sees a characteristic that is no feature candidate.
REMAINING_PARAMETERS = {
    "FrameConcerns": [
        ("in", "requirement", "problemStatement", "", "ProblemStatement"),
        ("out", "part", "stakeholders", "[1..*]", "Stakeholder"),
        ("out", "concern", "concerns", "[1..*]", "")],
    "SpecifyOperationalContext": [
        ("in", "requirement", "problemStatement", "", "ProblemStatement"),
        ("out", "part", "operationalContext", "", "SystemContext")],
    "ClassifyCapabilities": [
        ("in", "part", "operationalContext", "", "SystemContext"),
        ("out", "part", "characteristics", "[0..*]", "ProductLineCharacteristic")],
    "DecideBaseline": [
        ("in", "part", "charter", "", "IncrementCharter"),
        ("in", "concern", "concerns", "[0..*]", ""),
        ("out", "view", "publishedViews", "[1..*]", ""),
        ("out", "part", "baselineDecision", "", "IncrementBaselineDecision"),
        ("out", "part", "openGaps", "[0..*]", "IncrementGap")],
}


def test_remaining_steps_declare_the_parameters_their_checks_are_about() -> None:
    for definition, expected in REMAINING_PARAMETERS.items():
        found = re.findall(r"\b(in|out)\s+(\w+)\s+(\w+)(\[[^\]]*\])?\s*(?::\s*(\w+))?\s*;", _step_body(definition))
        assert found == expected, definition
    code = _code(WORKFLOW_FILE)
    assert code.count("private import DE4SDV_ProductLine::ProductLineCharacteristic;") == 1
    assert "ProductLineFeatureCandidate" not in code


def test_architecture_steps_type_their_parameters_by_the_trace_profile_classes() -> None:
    """Typed parameters select the increment's functions, logical and physical elements; a declared but
    unauthored phase 7 or 8 finds no subjects and blocks (lower bound 1), never passes vacuously."""
    for definition, expected in ARCHITECTURE_PARAMETERS.items():
        found = re.findall(r"\b(in|out)\s+(\w+)\s+(\w+)(\[[^\]]*\])\s*:\s*(\w+)\s*;", _step_body(definition))
        assert found == expected, definition
    code = _code(WORKFLOW_FILE)
    for name in ("AllocatableFunction", "LogicalAllocationElement", "PhysicalAllocationElement"):
        assert code.count(f"private import DE4SDV_TraceVocabulary::{name};") == 1, name


def test_method_check_is_a_light_metadata_definition() -> None:
    body = braced_body(_code(WORKFLOW_FILE), "metadata def MethodCheck")
    declared = re.findall(r"\battribute\s+(\w+)\s*:\s*(\w+)(?:\s+default\s+(\w+))?", body)
    assert declared == [("check", "String", ""), ("minimum", "Natural", "1"),
                        ("advisory", "Boolean", "false")]


def test_the_charter_declares_the_system_of_interest_by_reference() -> None:
    """IncrementCharter owns the optional systemOfInterest reference the subject checks read."""
    body = braced_body(_code(WORKFLOW_FILE), "part def IncrementCharter :> IncrementTraceObligations")
    assert re.search(r"\bref\s+part\s+systemOfInterest\s*\[0\.\.1\]", body)


def test_the_requirement_type_carries_the_success_criteria_the_advisory_check_reads() -> None:
    """successCriteriaAttribute reads this attribute through the requirement's type lineage."""
    body = braced_body(_code(METHOD_CONTEXT_FILE), "requirement def RequirementCandidate")
    declared = re.findall(r"\battribute\s+(\w+)\s*:\s*([\w:]+)\s*(\[[^\]]*\])?", body)
    assert declared == [("successCriteria", "ScalarValues::String", "[0..1]")]


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
    assert re.search(r"ref\s+part\s+:>>\s+systemOfInterest\s*=\s*"
                     r"DE4SDV_AEBSVisualizationFraming::system2VisualizationInstrument\s*;", body)
    artifacts = re.search(r"attribute\s+:>>\s+expectedArtifacts\s*=\s*\(([^)]*)\)\s*;", body).group(1)
    packages = set(re.findall(r'"([^"]+)"', artifacts))
    declared = {match for path in MODEL_ROOT.rglob("*.sysml")
                for match in re.findall(r"^package\s+(\w+)", _code(path), re.MULTILINE)}
    assert packages and packages <= declared, packages - declared
    evidence = re.search(r"attribute\s+:>>\s+expectedReviewEvidence\s*=\s*\(([^)]*)\)\s*;", body).group(1)
    assert all(item.strip() for item in re.findall(r'"([^"]*)"', evidence))


ADR_DIR = MODEL_ROOT.parent / "docs/architecture-decisions"
ADR_0027 = "0027-bind-varying-elements-in-the-feature-models.md"
# What rule 5 states in both homes, in words the two share once whitespace and comment stars are flattened.
RULE_5_SHARED = (
    "By the owner's decision of 2026-11-14 (rule-5 option A)",
    "the shared assets are one superset: an element is in every member product unless one link",
    "The element carries nothing",
    "FeatureBinding",
    "Bind the system of interest once; its requirements follow it.",
    "A requirement gets its own link only for what its subject does not bring",
    "An element that by itself needs an application and a middleware follows the adapter that the derivation "
    "rules derive for the pair",
    "This is the owner's decision of 2026-11-15",
    "names every premise of",
    "An element carries at most one link",
    "goes to the owner",
    "A requirement whose subject has no link, and that has none of its own, is core",
    "the dependency form governs",
    "Several of them name all their features",
)
# Sentences of the rule before 2026-11-15 that no home may keep.
RULE_5_RETIRED = (
    "When the links name more than one feature",
    "waits until the evaluator binds requirement variants",
    "binds only the variations of a feature model's projection owner",
)
# Each record that ADR 0027 amends carries one dated note that links it and states what changes.
AMENDED_RECORDS = {
    "0009-adopt-ode4hera-requirements-attributes.md": "the dependency form of rule 5 governs",
    "0021-make-model-elements-earn-their-place.md": "rule 5's dependency form governs",
    "0022-adopt-pleml-as-product-line-authority.md": "amends decisions 3 and 5",
}


def _flat(text: str) -> str:
    return " ".join(text.split())


#: The phase 8 rule as both homes state it: the method document's paragraph and the doc of DefinePhysicalRealization,
#: which the phase contract serves as the step's documentation (owner decision of 2026-11-19).
PHASE_8_SHARED = (
    "Phase 8 has two kinds of realization package.",
    "The software realization, a package whose name ends in PhysicalSoftwareRealization, holds the software, the "
    "platforms it runs on (operating systems, hypervisors, virtual machines, bench hosts) and its deployment.",
    "The E/E realization, a package whose name ends in PhysicalEERealization, holds the vehicle's "
    "electrical/electronic topology: ECUs and controllers as network nodes, buses and links, the frames on them, "
    "connectors and I/O.",
    "The physical/software realization is phase 8 with both kinds.",
    "An ECU or controller that software runs on is declared in the E/E realization; the software realization "
    "imports it and does not declare it again. An import lets the software realization refer to the ECU. It does not "
    "assign software to the ECU, and the method defines no relation for that yet.",
    "The checks of phase 8 read both kinds alike: they find physical elements by their type, in the packages the "
    "charter names and among the targets of the increment's own allocations, not by how a package's name ends. They "
    "do not check which kind holds an element, where an ECU is declared, or what a package imports.",
    "Phase 8 packages merged before this rule keep their names and their content.",
    "An increment with no E/E topology has only a software realization.",
    "No kind exists for mechanical elements until an increment has them inside its boundary",
)
#: Phrases neither home states again: the method document no longer says what the kernel means, an import assigns no
#: software to an ECU, and the scope of the checks and what merged packages keep are stated in full.
PHASE_8_RETIRED = (
    "Wherever this document or the kernel speaks",
    "imports it to deploy software on it",
    "by their type in the packages the charter names, not by",
    "rule keep their content",
)


STEP_8 = "action def DefinePhysicalRealization :> IncrementStep"


def _owned_docs(text: str, header: str) -> list[str]:
    """The doc comments the declaration opened by ``header`` owns itself, on the first level of its body, as the phase
    contract reads them (the Documentation the step definition owns), not the docs of its features or checks."""
    index = text.index("{", text.index(header)) + 1
    depth, statement, docs = 1, "", []
    while depth:
        if text.startswith("/*", index):
            end = text.index("*/", index)
            if depth == 1 and re.match(r"(?:(?:private|protected|public)\s+)?doc\b", statement.strip()):
                docs.append(text[index + 2:end])
            index, statement = end + 2, ""
        elif text.startswith("//", index):
            index = text.index("\n", index)
        elif text[index] in "\"'":
            index = text.index(text[index], index + 1) + 1
        else:
            character = text[index]
            if character in "{};":
                depth += {"{": 1, "}": -1}.get(character, 0)
                statement = ""
            else:
                statement += character
            index += 1
    return docs


def _phase_8_homes() -> tuple[str, str]:
    """The phase 8 paragraph of the method document (code marks dropped) and the doc that DefinePhysicalRealization
    owns itself, flattened."""
    document = WORKFLOW_DOC.read_text(encoding="utf-8")
    start = document.index("Phase 8 has two kinds of realization package.")
    paragraph = document[start:document.index("\n\n", start)]
    docs = _owned_docs(WORKFLOW_FILE.read_text(encoding="utf-8"), STEP_8)
    return _flat(paragraph.replace("`", "")), _flat(re.sub(r"^\s*\*", " ", " ".join(docs), flags=re.MULTILINE))


def test_phase_8_states_its_two_kinds_of_realization_in_both_homes() -> None:
    homes = _phase_8_homes()
    for home in homes:
        assert not [sentence for sentence in PHASE_8_SHARED if sentence not in home]
    for text in (*homes, _flat(WORKFLOW_DOC.read_text(encoding="utf-8"))):
        assert not [phrase for phrase in PHASE_8_RETIRED if phrase in text]
    assert "The kernel's DefinePhysicalRealization states the same rule." in homes[0]


def test_the_phase_8_home_in_the_kernel_is_the_steps_own_doc() -> None:
    """The phase contract serves the doc the step owns; a doc moved onto one of its features is not the step's."""
    own = (f"{STEP_8} {{\n    doc /* The rule. */\n"
           "    in part logicalElements[1..*] : LogicalAllocationElement { doc /* A feature's doc. */ }\n"
           "    metadata allocated : MethodCheck about logicalElements {\n      doc /* A check's doc. */\n"
           "      :>> check = \"allocatedTo\";\n    }\n  }\n")
    assert _owned_docs(own, STEP_8) == [" The rule. "]
    for feature in ("in part logicalElements[1..*] : LogicalAllocationElement",
                    "out part physicalElements[1..*] : PhysicalAllocationElement"):
        moved = f"{STEP_8} {{\n    attribute :>> phase = MethodPhase::phase8_physicalRealization;\n" \
                f"    {feature} {{ doc /* The rule. */ }}\n  }}\n"
        assert _owned_docs(moved, STEP_8) == [], feature


STEP_5 = "action def SpecifyRequirements :> IncrementStep"


def _rule_5_homes(kernel: str | None = None) -> tuple[str, str]:
    """Rule 5 in the method document and in the doc that SpecifyRequirements owns itself, flattened (``kernel``: the
    kernel file's text, read from disk when not given)."""
    document = WORKFLOW_DOC.read_text(encoding="utf-8")
    start = document.index("5. **Requirement.**")
    section = document[start:document.index("6. **Verification.**", start)]
    kernel = WORKFLOW_FILE.read_text(encoding="utf-8") if kernel is None else kernel
    docs = _owned_docs(kernel, STEP_5)
    return _flat(section), _flat(re.sub(r"^\s*\*", " ", " ".join(docs), flags=re.MULTILINE))


def _moved_onto(kernel: str, header: str, parameter: str) -> str:
    """The kernel text with the doc the step opened by ``header`` owns moved, unchanged, onto one of its parameters."""
    head = kernel.index(header)
    start = kernel.index("    doc /* ", head)
    end = kernel.index("*/", start) + 2
    doc = kernel[start:end]
    kernel = kernel[:start] + kernel[end + 1:]
    at = kernel.index(parameter, head)
    return kernel[:at] + parameter[:-1] + " {\n  " + doc + "\n    }" + kernel[at + len(parameter):]


def test_the_rule_5_home_in_the_kernel_is_the_steps_own_doc() -> None:
    """The phase contract serves the doc SpecifyRequirements owns; moved unchanged onto one of the step's parameters,
    the rule is no longer in the step's home."""
    kernel = WORKFLOW_FILE.read_text(encoding="utf-8")
    assert not [phrase for phrase in RULE_5_SHARED if phrase not in _rule_5_homes(kernel)[1]]
    for parameter in ("    in requirement needs[0..*] : StakeholderNeedCandidate;",
                      "    out requirement requirements[1..*] : RequirementCandidate;"):
        home = _rule_5_homes(_moved_onto(kernel, STEP_5, parameter))[1]
        assert not [phrase for phrase in RULE_5_SHARED if phrase in home], parameter


def _dated_note(record: str) -> str:
    lines = (ADR_DIR / record).read_text(encoding="utf-8").splitlines()
    starts = [index for index, line in enumerate(lines) if line.startswith("> Note (2026-11-15):")]
    assert len(starts) == 1, record
    note = []
    for line in lines[starts[0]:]:
        if not line.startswith(">") or not line[1:].strip():
            break
        note.append(line[1:])
    return _flat(" ".join(note))


def test_rule_5_states_the_same_binding_rule_in_both_homes() -> None:
    for home in _rule_5_homes():
        assert not [phrase for phrase in RULE_5_SHARED if phrase not in home]
        assert not [phrase for phrase in RULE_5_RETIRED if phrase in home]


def test_rule_5_keeps_the_dependency_form_until_the_evaluator_reads_the_links() -> None:
    section, _ = _rule_5_homes()
    assert ("Until both land and the existing links have moved, the dependency form governs, and no slice "
            "declares a link the evaluator refuses.") in section
    assert f"(../../docs/architecture-decisions/{ADR_0027})" in section


def test_the_records_that_adr_0027_amends_point_to_it() -> None:
    record = _flat((ADR_DIR / ADR_0027).read_text(encoding="utf-8"))
    assert ("The owner took decisions 1 to 4 and 7 on 2026-11-14, as rule-5 option A, and decision 5 on "
            "2026-11-15, as the form for a pair. Decisions 6 and 8 work out their consequences.") in record
    assert f"]({ADR_0027})" in (ADR_DIR / "README.md").read_text(encoding="utf-8")
    for amended, change in AMENDED_RECORDS.items():
        note = _dated_note(amended)
        assert f"[ADR 0027]({ADR_0027})" in note, amended
        assert change in note, amended


def test_adr_0027_is_accepted_with_the_fallback_of_decision_8() -> None:
    text = (ADR_DIR / ADR_0027).read_text(encoding="utf-8")
    assert text.split("## Status\n\n", 1)[1].splitlines()[0] == "Accepted"
    record = _flat(text)
    assert ("They were drafted after his choices, and on 2026-11-15 he accepted them with this record, decision 8 "
            "with the fallback for INC-DRIVING-002 that it states.") in record
    assert ("INC-DRIVING-002 binds directly in its phase 9 if the evaluator change and the move have merged by the "
            "time its phase 8 merges. Otherwise its phase 9 declares its links in rule 5's dependency form, and the "
            "move takes them along.") in record
    assert ("move into the feature-model document, and with them those of INC-DRIVING-002 if its phase 9 declared "
            "them in the dependency form.") in record
    assert "he decides on them with this record" not in record
