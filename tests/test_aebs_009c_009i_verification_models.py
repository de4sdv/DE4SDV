import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
MODEL_DIR = ROOT / "textual-notation-of-model/packages/features/aebs"
MODELS = {
    increment: MODEL_DIR / f"aebs_{increment.lower()}_verification.sysml"
    for increment in ("009C", "009D", "009E", "009F", "009G", "009H", "009I")
}
EXPECTED_USAGES = {
    "009C": {"nativeInterventionToMRMVerification009C"},
    "009D": {
        "overrideFalseControlVerification009D",
        "overrideTrueVerification009D",
        "overrideStaleVerification009D",
        "overrideMissingVerification009D",
        "overrideMalformedVerification009D",
        "overrideFutureStampedVerification009D",
    },
    "009E": {
        "clearPathNonActivationVerification009E",
        "adjacentObjectNonActivationVerification009E",
        "falseReactionControlVerification009E",
    },
    "009F": {
        "staleInputVerification009F",
        "missingInputVerification009F",
        "malformedInputVerification009F",
        "inconsistentInputVerification009F",
        "unavailableInputVerification009F",
    },
    "009G": {"pedestrianTargetVerification009G"},
    "009H": {"bicycleTargetVerification009H"},
    "009I": {"configurationBoundedCriterionVerification009I"},
}
PRODUCT_TARGET = re.compile(r"\b(?:verify|satisfy)\s+(?:/\*.*?\*/\s*)?req\w+\s*;", re.DOTALL)


def _without_comments(source: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.DOTALL)


def _braced_body(source: str, declaration: str) -> str:
    start = source.index(declaration)
    opening = source.index("{", start + len(declaration))
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError(f"unclosed declaration: {declaration}")


def test_each_increment_has_native_case_one_objective_and_explicit_data_pipeline():
    for increment, path in MODELS.items():
        code = _without_comments(path.read_text(encoding="utf-8"))
        definitions = re.findall(r"verification def (\w+)", code)
        assert len(definitions) == 1, increment
        body = _braced_body(code, f"verification def {definitions[0]}")
        assert len(re.findall(r"\bobjective\b", body)) == 1, increment
        assert "action collectData" in body
        assert "action processData" in body
        assert "action evaluateData" in body
        assert "return verdict : VerdictKind = evaluateData.verdict;" in body
        assert re.search(r"\bsubject\s+verifiedBench\s*:\s*\w+Bench\w*;", body)
        assert "perform " in code


def test_only_system2_evidence_contracts_are_verification_targets():
    for increment, path in MODELS.items():
        source = path.read_text(encoding="utf-8")
        code = _without_comments(source)
        targets = re.findall(r"\bverify\s+(\w+)\s*;", code)
        assert targets, increment
        assert all(target.startswith("evidenceContract") for target in targets), increment
        assert not PRODUCT_TARGET.search(source), increment
        assert not re.search(r"\bsatisfy\b", code), increment


def test_product_claim_detector_resists_comment_insertion():
    mutations = (
        "verify reqAllowDriverOverride;",
        "verify /* split */ reqResistFalseReaction;",
        "satisfy reqHandleDegradedUnavailableInputs;",
        "satisfy /* split */ reqPedestrianTargetResponse;",
    )
    for mutation in mutations:
        assert PRODUCT_TARGET.search(mutation)
        assert re.search(r"\b(?:verify|satisfy)\s+req\w+\s*;", _without_comments(mutation))


def test_matrix_scenarios_keep_separate_configured_usages_and_verdicts():
    for increment, expected in EXPECTED_USAGES.items():
        code = _without_comments(MODELS[increment].read_text(encoding="utf-8"))
        actual = set(re.findall(r"\bverification\s+(\w+)\s*:\s*\w+\s*\{", code))
        assert actual == expected, increment
        for usage in expected:
            body = _braced_body(code, f"verification {usage}")
            assert "subject verifiedBench :>" in body
            assert "@VerificationMethod{" in body


def test_009c_maps_all_five_scenario_outcomes_to_native_verdicts():
    code = _without_comments(MODELS["009C"].read_text(encoding="utf-8"))
    for outcome in (
        "passObservedChain",
        "failScenario",
        "inconclusivePrecondition",
        "inconclusiveInstrumentation",
        "aborted",
    ):
        assert outcome in code
    for verdict in ("pass", "fail", "inconclusive", "error"):
        assert f"VerdictKind::{verdict}" in code
    assert "Map009COutcomeToVerdict" in code


def test_target_relevance_dependencies_match_target_specific_candidates_only():
    g = _without_comments(MODELS["009G"].read_text(encoding="utf-8"))
    h = _without_comments(MODELS["009H"].read_text(encoding="utf-8"))
    assert re.search(r"dependency\s+\w+\s+from\s+\w+\s+to\s+reqPedestrianTargetResponse\s*;", g)
    assert "reqBicycleTargetResponse" not in g
    assert re.search(r"dependency\s+\w+\s+from\s+\w+\s+to\s+reqBicycleTargetResponse\s*;", h)
    assert "reqPedestrianTargetResponse" not in h


def test_009i_models_source_criterion_measurement_and_provenance_as_fail_closed_contracts():
    code = _without_comments(MODELS["009I"].read_text(encoding="utf-8"))
    for target in (
        "evidenceContract009ISourceIdentity",
        "evidenceContract009IApplicableCriterion",
        "evidenceContract009IMeasurementTrace",
        "evidenceContract009IProvenance",
        "evidenceContract009IConfigurationBoundedVerdict",
    ):
        assert f"verify {target};" in code
    source = MODELS["009I"].read_text(encoding="utf-8")
    assert "controlled source identity" in source.lower()
    assert "source identity gap" not in source.lower()
    assert "applicability" in source.lower()
    assert "@VerificationMethod{ kind = inspect; }" in code
