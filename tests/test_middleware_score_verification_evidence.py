"""INC-MW-011 phase 10, first slice: the verification cases of the S-CORE integration layer.

One case per requirement of the increment. Each case verifies its requirement with
the requirement's subject bound to the integration layer of the configured product
MW-CONFIG-002, collects by the method that the requirement states, and has not
started: no evidence record, claim or verdict exists, and every requirement keeps
the verification status NotStarted. The evidence record specializes the retained
record of the closed INC-MW-010 slice and adds the receipt digest; the closed slice
is unchanged.

These are lexical source guards; licensed Syside validates the model in CI, and the
Method Check evaluates the phase-10 checks. Comments and string literals are blanked
before code is matched.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "textual-notation-of-model"
MIDDLEWARE = MODEL / "packages" / "features" / "middleware"
SLICE = MIDDLEWARE / "middleware_score_verification_evidence.sysml"
NEEDS = MIDDLEWARE / "middleware_score_needs_requirements.sysml"
FRAMING = MIDDLEWARE / "middleware_score_framing.sysml"
CONFIGURATION = MIDDLEWARE / "middleware_score_variability_configuration.sysml"
CLOSED_SLICE = MIDDLEWARE / "middleware_verification_evidence.sysml"
PACKAGE = "DE4SDV_MiddlewareSCOREVerificationEvidence"

#: Case ID -> the requirement it verifies, in requirement order. The IDs take the next free numbers of
#: the VC-MW family after the grandfathered VC-MW-010-01 to VC-MW-010-06 (docs/naming/naming-conventions.md).
CASES = {
    "VC-MW-011": "reqDeliverReferenceVehicleSpeed",
    "VC-MW-012": "reqWithholdNonFiniteSpeedSample",
    "VC-MW-013": "reqIndicateStaleReferenceVehicleSpeed",
    "VC-MW-014": "reqDeliverSpeedSampleAtMostOnce",
    "VC-MW-015": "reqDeliverAEBSSignalsInSourceOrder",
    "VC-MW-016": "reqPreserveAEBSSignalProvenance",
    "VC-MW-017": "reqNoApplicationDataFromHMIGuest",
    "VC-MW-018": "reqNoEmergencyCommandOnMiddleware",
    "VC-MW-019": "reqTerminateAdapterOnException",
    "VC-MW-020": "reqDiscardFramesWhileHMIUnsubscribed",
    "VC-MW-021": "reqNoSpeedSampleToAEBVelocityInput",
}

_NOT_CODE = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:[^"\\\n]|\\.)*"', re.DOTALL)
_USAGE = re.compile(r"\bverification\s+<'(?P<id>[^']+)'>\s*(?P<name>\w+)\s*:\s*(?P<definition>\w+)\s*\{")
_REQUIREMENT = re.compile(r"\brequirement\s+<'(?P<id>REQ-MW-\d{3})'>\s*(?P<name>\w+)\s*:\s*\w+\s*\{")


def _blanked(text: str) -> str:
    """``text`` with the content of comments and string literals replaced by spaces, so that braces in
    them do not count and every position still points into ``text``."""
    def blank(match: re.Match[str]) -> str:
        found = match.group()
        if found.startswith('"'):
            return '"' + " " * (len(found) - 2) + '"'
        return re.sub(r"[^\n]", " ", found)
    return _NOT_CODE.sub(blank, text)


def _span(text: str, header: str) -> tuple[int, int]:
    """The span of the braced body after the one match of ``header`` in the code of ``text``."""
    code = _blanked(text)
    matches = list(re.finditer(header, code))
    assert len(matches) == 1, f"expected one {header!r}, found {len(matches)}"
    start = matches[0].end() - 1
    assert code[start] == "{", f"{header!r} does not end with an opening brace"
    depth = 0
    for end in range(start, len(code)):
        depth += {"{": 1, "}": -1}.get(code[end], 0)
        if depth == 0:
            return start, end + 1
    raise AssertionError(f"{header!r} has an unbalanced body")


def _code_body(text: str, header: str) -> str:
    """The body after ``header``, comments and strings blanked, whitespace collapsed."""
    start, end = _span(text, header)
    return " ".join(_blanked(text)[start:end].split())


def _raw_body(text: str, header: str) -> str:
    """The body after ``header`` as written, comments and strings included."""
    start, end = _span(text, header)
    return text[start:end]


def _requirements() -> dict[str, dict[str, str]]:
    """Requirement name -> its ID, verification method and verification status."""
    text = NEEDS.read_text(encoding="utf-8")
    found = {}
    for match in _REQUIREMENT.finditer(_blanked(text)):
        body = _raw_body(text, re.escape(match.group()))
        (method,) = re.findall(r'\battribute :>> verificationMethod = "(\w+)";', body)
        (status,) = re.findall(r"\battribute :>> verificationStatus = VVStatus::(\w+);", body)
        found[match["name"]] = {"id": match["id"], "method": method, "status": status}
    return found


def _usages() -> dict[str, tuple[str, str]]:
    """Case ID -> (usage name, definition name), in source order."""
    return {match["id"]: (match["name"], match["definition"])
            for match in _USAGE.finditer(_blanked(SLICE.read_text(encoding="utf-8")))}


def _definition(definition: str) -> str:
    return _code_body(SLICE.read_text(encoding="utf-8"), rf"\bverification\s+def\s+{definition}\s*\{{")


def test_each_requirement_of_the_increment_is_verified_by_one_case() -> None:
    """Eleven cases for the eleven requirements, one each, the IDs in requirement order."""
    requirements = _requirements()
    assert sorted(requirements) == sorted(CASES.values())
    assert [requirements[name]["id"] for name in CASES.values()] == [f"REQ-MW-{n:03d}" for n in range(10, 21)]
    usages = _usages()
    assert list(usages) == list(CASES)
    for case, requirement in CASES.items():
        body = _definition(usages[case][1])
        assert re.findall(r"\bverify\s+(\w+)", body) == [requirement], case
        assert f"verify {requirement} {{ subject integrationLayer = verifiedBench.integrationLayer; }}" in body, case
    verified = re.findall(r"\bverify\s+(\w+)", _blanked(SLICE.read_text(encoding="utf-8")))
    assert sorted(verified) == sorted(CASES.values()), "a requirement is verified twice, or a case verifies another"


def test_the_case_ids_are_unique_in_the_model() -> None:
    """Each case ID is the short name of one usage, and no other model file holds a VC-MW number from 011 on."""
    others = {}
    for path in sorted(MODEL.rglob("*.sysml")):
        if path == SLICE:
            continue
        numbers = [int(n) for n in re.findall(r"\bVC-MW-(\d{3})\b(?!-)", path.read_text(encoding="utf-8"))]
        if any(number >= 11 for number in numbers):
            others[path.relative_to(ROOT).as_posix()] = numbers
    assert others == {}
    text = SLICE.read_text(encoding="utf-8")
    for case in CASES:
        assert len(re.findall(rf"<'{case}'>", text)) == 1, case


def test_each_case_collects_by_the_method_its_requirement_states() -> None:
    """A test requirement gets a test and an inspect requirement an inspection; processing and evaluation
    are analysis. The usage names the methods of its actions."""
    requirements = _requirements()
    text = SLICE.read_text(encoding="utf-8")
    for case, requirement in CASES.items():
        name, definition = _usages()[case]
        method = requirements[requirement]["method"]
        assert method in {"test", "inspect"}, (requirement, method)
        body = _definition(definition)
        for action, expected in (("collectData", method), ("processData", "analyze"), ("evaluateData", "analyze")):
            action_body = _code_body(body, rf"\baction\s+{action}\s*\{{")
            assert re.findall(r"@VerificationMethod\{ kind = (\w+); \}", action_body) == [expected], (case, action)
        assert "subject verifiedBench : SCOREMiddlewareVerificationBench;" in body, case
        assert "out item retainedEvidence : ReceiptBoundMiddlewareEvidence;" in body, case
        usage = _code_body(text, rf"\bverification\s+<'{case}'>\s*{name}\s*:\s*{definition}\s*\{{")
        assert f"@VerificationMethod{{ kind = ({method}, analyze); }}" in usage, case
        assert "subject verifiedBench :> scoreMiddlewareVerificationBench;" in usage, case


def test_no_case_has_started() -> None:
    """Planning only: each usage doc starts with Not started and names its bench, the slice binds no
    evidence record and states no claim or verdict, and every requirement stays NotStarted."""
    assert {name: facts["status"] for name, facts in _requirements().items()} == {
        name: "NotStarted" for name in CASES.values()}
    text = SLICE.read_text(encoding="utf-8")
    for case in CASES:
        usage = _raw_body(text, rf"\bverification\s+<'{case}'>\s*\w+\s*:\s*\w+\s*\{{")
        (doc,) = re.findall(r"\bdoc\s*/\*(.*?)\*/", usage, re.DOTALL)
        assert " ".join(doc.split()).startswith("Not started. Bench: "), case
    code = _blanked(text)
    assert not re.search(r"VerdictKind::\w+", code), "the slice states a verdict"
    assert not re.search(r"\b(?:AssuranceClaim|AssuranceArgument|AssuranceCounterClaim)\b", code)
    assert not re.search(r"\bsatisfy\b", code)
    typed = re.findall(r"\b(?:part|item)\s+(\w+)\s*:\s*(?:ReceiptBoundMiddlewareEvidence|RetainedMiddlewareEvidence)\b",
                       code)
    assert typed == ["retainedEvidence"] * (2 * len(CASES)), "an evidence record outside the case parameters"


def test_the_evidence_record_adds_the_receipt_digest_to_the_closed_record() -> None:
    """The specialization carries the digest; the retained record of the closed INC-MW-010 slice is
    unchanged and has none."""
    record = _code_body(SLICE.read_text(encoding="utf-8"),
                        r"\bitem\s+def\s+ReceiptBoundMiddlewareEvidence\s*:>\s*RetainedMiddlewareEvidence\s*\{")
    assert re.findall(r"\battribute\s+(\w+)\s*:", record) == ["receiptSha256"]
    assert "attribute receiptSha256 : ScalarValues::String;" in record
    closed = _code_body(CLOSED_SLICE.read_text(encoding="utf-8"), r"\bitem\s+def\s+RetainedMiddlewareEvidence\s*\{")
    assert re.findall(r"\battribute\s+(\w+)\s*:", closed) == [
        "configurationIdentity", "executionEnvironmentIdentity", "contractIdentity", "rawObservationArtifact",
        "independentObserverIdentity", "disposition", "claimBoundary"]


def test_the_bench_refers_to_the_integration_layer_of_mw_config_002() -> None:
    """System 1 is MW-CONFIG-002, which the bench refers to; each requirement's subject binds its layer."""
    bench = _code_body(SLICE.read_text(encoding="utf-8"), r"\bpart\s+def\s+SCOREMiddlewareVerificationBench\s*\{")
    assert re.findall(r"\b(ref\s+)?part\s+(\w+)", bench) == [
        ("ref ", "system1ConfiguredProduct"), ("ref ", "integrationLayer")]
    assert ("ref part system1ConfiguredProduct :> "
            "DE4SDV_MiddlewareSCOREVariabilityConfiguration::configuredProduct;") in bench
    assert ("ref part integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer "
            "= system1ConfiguredProduct.integrationLayer;") in bench
    assert re.search(r"\bpart <'MW-CONFIG-002'> configuredProduct :", CONFIGURATION.read_text(encoding="utf-8"))


def test_the_charter_names_the_phase_10_package() -> None:
    (artifacts,) = re.findall(r"attribute :>> expectedArtifacts = \(([^)]*)\);", FRAMING.read_text(encoding="utf-8"))
    assert f'"{PACKAGE}"' in artifacts
    assert re.search(rf"\bpackage {PACKAGE}\s*\{{", _blanked(SLICE.read_text(encoding="utf-8")))
