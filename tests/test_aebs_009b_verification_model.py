from pathlib import Path
import re


MODEL = (
    Path(__file__).parents[1]
    / "textual-notation-of-model/packages/features/aebs/aebs_009b_nominal_evidence.sysml"
)
PRODUCT_CLAIM_RELATIONSHIP = re.compile(
    r"\b(?:verify|satisfy)\b[^;]*\b(?:reqProvideCollisionWarning|"
    r"reqCommandEmergencyBraking|reqAllowDriverOverride)\b[^;]*;"
)


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


def test_009b_uses_native_verification_semantics_for_evidence_contracts():
    code = _without_comments(MODEL.read_text(encoding="utf-8"))

    assert "verification def NominalMovingVehicleTargetVerification009B" in code
    assert "verification nominalMovingVehicleTargetVerification009B" in code
    assert "perform nominalMovingVehicleTargetVerification009B;" in code

    verify_targets = re.findall(r"\bverify\s+(\w+)\s*;", code)
    assert verify_targets == [
        "evidenceContract009BWarningLead",
        "evidenceContract009BFreshOverrideClear",
        "evidenceContract009BNominalBrakingPath",
        "evidenceContract009BVerifiedStopRelease",
        "evidenceContract009BIndependentNoncollision",
    ]


def test_009b_keeps_product_candidates_separate_from_verification_targets():
    code = _without_comments(MODEL.read_text(encoding="utf-8"))

    assert "private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;" in code
    assert not PRODUCT_CLAIM_RELATIONSHIP.search(code)
    assert "REQ-AEBS-009B-" not in code


def test_product_claim_detector_is_comment_insensitive_and_covers_satisfy():
    mutations = (
        "verify reqProvideCollisionWarning;",
        "verify /* bypass */ reqCommandEmergencyBraking;",
        "satisfy reqAllowDriverOverride;",
        "satisfy /* bypass */ reqProvideCollisionWarning;",
    )

    for mutation in mutations:
        assert PRODUCT_CLAIM_RELATIONSHIP.search(_without_comments(mutation))


def test_009b_records_simulation_execution_as_test_and_analysis_methods():
    code = _without_comments(MODEL.read_text(encoding="utf-8"))

    verification_usage = _braced_body(
        code, "verification nominalMovingVehicleTargetVerification009B"
    )
    collect_data = _braced_body(code, "action collectData")
    process_data = _braced_body(code, "action processData")
    evaluate_data = _braced_body(code, "action evaluateData")

    assert "@VerificationMethod{ kind = (test, analyze); }" in verification_usage
    assert "@VerificationMethod{ kind = test; }" in collect_data
    assert "@VerificationMethod{ kind = analyze; }" in process_data
    assert "@VerificationMethod{ kind = analyze; }" in evaluate_data
    assert "return verdict : VerdictKind = evaluateData.verdict;" in code
