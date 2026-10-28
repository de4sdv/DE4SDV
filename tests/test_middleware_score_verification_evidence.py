"""INC-MW-011 phase 10, first slice: the verification cases of the S-CORE integration layer.

One case per requirement of the increment. Each case verifies its requirement with
the requirement's subject bound to the integration layer of the configured product
MW-CONFIG-002, collects by the method that the requirement states, and has not
started: no evidence record, claim or verdict exists, and every requirement keeps
the verification status NotStarted. The evidence record specializes the retained
record of the closed INC-MW-010 slice and adds the receipt digest, the model revision
and the two S-CORE commits of ASM-MW-021; the closed slice is unchanged. GAP-MW-044
keeps the System 2 test environment open and ends on the verification system.
VC-MW-017 inspects the ROS 2 (DDS) and network configuration of the host that the
criteria of REQ-MW-016 name; VC-MW-018 needs only its HMI-path configurations.

These are lexical source guards; licensed Syside validates the model in CI, and the
Method Check evaluates the phase-10 checks. Comments and string literals are blanked
before code is matched.
"""

from __future__ import annotations

import re
from pathlib import Path

from sysml_shapes import SHORT_NAME

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "textual-notation-of-model"
MIDDLEWARE = MODEL / "packages" / "features" / "middleware"
SLICE = MIDDLEWARE / "middleware_score_verification_evidence.sysml"
NEEDS = MIDDLEWARE / "middleware_score_needs_requirements.sysml"
FRAMING = MIDDLEWARE / "middleware_score_framing.sysml"
CONFIGURATION = MIDDLEWARE / "middleware_score_variability_configuration.sysml"
CLOSED_SLICE = MIDDLEWARE / "middleware_verification_evidence.sysml"
PACKAGE = "DE4SDV_MiddlewareSCOREVerificationEvidence"

#: Case ID -> the kinds a case adds to its requirement's method when it collects. VC-MW-017 adds a runtime
#: reachability probe (test) to the inspection of REQ-MW-016 (owner decision of 2026-10-28, real isolation).
SUPPORTING_KINDS = {"VC-MW-017": ("test",)}

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


def _evidence_records(code: str) -> list[str]:
    """The names of the part and item declarations typed by an evidence record, short-named or not."""
    return re.findall(rf"\b(?:part|item)\s+{SHORT_NAME}(\w+)\s*:\s*(?:ReceiptBoundMiddlewareEvidence|"
                      r"RetainedMiddlewareEvidence)\b", code)


def _bench_parts(text: str) -> list[tuple[str, str]]:
    """(``ref `` or empty, name) of each part of the bench definition in ``text``, short-named or not."""
    bench = _code_body(text, r"\bpart\s+def\s+SCOREMiddlewareVerificationBench\s*\{")
    return re.findall(rf"\b(ref\s+)?part\s+{SHORT_NAME}(\w+)", bench)


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


def _kinds(annotation_body: str) -> list[tuple[str, ...]]:
    """The kinds of each ``@VerificationMethod`` annotation in ``annotation_body``, one tuple per annotation."""
    found = re.findall(r"@VerificationMethod\{ kind = (\w+|\([\w, ]+\)); \}", annotation_body)
    return [tuple(kind.strip("()").split(", ")) for kind in found]


def test_each_case_collects_by_the_method_its_requirement_states() -> None:
    """A test requirement gets a test and an inspect requirement an inspection; processing and evaluation
    are analysis. A case collects by its requirement's method first and adds only the kinds that
    SUPPORTING_KINDS states. The usage names the methods of its actions."""
    requirements = _requirements()
    text = SLICE.read_text(encoding="utf-8")
    assert set(SUPPORTING_KINDS) <= set(CASES)
    for case, requirement in CASES.items():
        name, definition = _usages()[case]
        method = requirements[requirement]["method"]
        assert method in {"test", "inspect"}, (requirement, method)
        collected = (method, *SUPPORTING_KINDS.get(case, ()))
        body = _definition(definition)
        for action, expected in (("collectData", collected), ("processData", ("analyze",)),
                                 ("evaluateData", ("analyze",))):
            action_body = _code_body(body, rf"\baction\s+{action}\s*\{{")
            assert _kinds(action_body) == [expected], (case, action, _kinds(action_body))
        assert "subject verifiedBench : SCOREMiddlewareVerificationBench;" in body, case
        assert "out item retainedEvidence : ReceiptBoundMiddlewareEvidence;" in body, case
        usage = _code_body(text, rf"\bverification\s+<'{case}'>\s*{name}\s*:\s*{definition}\s*\{{")
        assert _kinds(usage) == [(*collected, "analyze")], (case, _kinds(usage))
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
    assert _evidence_records(code) == ["retainedEvidence"] * (2 * len(CASES)), (
        "an evidence record outside the case parameters")


def test_the_evidence_record_adds_the_run_identity_to_the_closed_record() -> None:
    """The specialization carries the receipt digest, the model revision and the two S-CORE commits of
    ASM-MW-021; the retained record of the closed INC-MW-010 slice is unchanged and has none of them."""
    record = _code_body(SLICE.read_text(encoding="utf-8"),
                        r"\bitem\s+def\s+ReceiptBoundMiddlewareEvidence\s*:>\s*RetainedMiddlewareEvidence\s*\{")
    identity = ["receiptSha256", "modelRevision", "scoreReferenceIntegrationCommit", "scoreSOMEIPGatewayCommit"]
    assert re.findall(r"\battribute\s+(\w+)\s*:", record) == identity
    for name in identity:
        assert f"attribute {name} : ScalarValues::String;" in record, name
    closed = _code_body(CLOSED_SLICE.read_text(encoding="utf-8"), r"\bitem\s+def\s+RetainedMiddlewareEvidence\s*\{")
    assert re.findall(r"\battribute\s+(\w+)\s*:", closed) == [
        "configurationIdentity", "executionEnvironmentIdentity", "contractIdentity", "rawObservationArtifact",
        "independentObserverIdentity", "disposition", "claimBoundary"]


def test_the_bench_refers_to_the_integration_layer_of_mw_config_002() -> None:
    """System 1 is MW-CONFIG-002, which the bench refers to; each requirement's subject binds its layer."""
    text = SLICE.read_text(encoding="utf-8")
    assert _bench_parts(text) == [("ref ", "system1ConfiguredProduct"), ("ref ", "integrationLayer")]
    bench = _code_body(text, r"\bpart\s+def\s+SCOREMiddlewareVerificationBench\s*\{")
    assert ("ref part system1ConfiguredProduct :> "
            "DE4SDV_MiddlewareSCOREVariabilityConfiguration::configuredProduct;") in bench
    assert ("ref part integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer "
            "= system1ConfiguredProduct.integrationLayer;") in bench
    assert re.search(r"\bpart <'MW-CONFIG-002'> configuredProduct :", CONFIGURATION.read_text(encoding="utf-8"))


def test_the_charter_names_the_phase_10_package() -> None:
    (artifacts,) = re.findall(r"attribute :>> expectedArtifacts = \(([^)]*)\);", FRAMING.read_text(encoding="utf-8"))
    assert f'"{PACKAGE}"' in artifacts
    assert re.search(rf"\bpackage {PACKAGE}\s*\{{", _blanked(SLICE.read_text(encoding="utf-8")))


def test_the_record_and_bench_guards_read_short_named_declarations() -> None:
    """A short name hides neither an evidence record from the not-started guard nor a part from the bench
    guard (negative cases of those two guards)."""
    text = SLICE.read_text(encoding="utf-8")
    anchor = "  part scoreMiddlewareVerificationBench : SCOREMiddlewareVerificationBench;"
    record = "  part <'EVID-SYN-001'> speedRunEvidence : ReceiptBoundMiddlewareEvidence { }\n"
    with_record = text.replace(anchor, record + anchor, 1)
    assert with_record != text
    assert "speedRunEvidence" in _evidence_records(_blanked(with_record))
    assert _evidence_records(_blanked(with_record)) != ["retainedEvidence"] * (2 * len(CASES))
    first_part = "    ref part system1ConfiguredProduct"
    with_part = text.replace(first_part, "    part <'SYS2-SYN-001'> testEnvironment : Environment;\n" + first_part, 1)
    assert with_part != text
    assert _bench_parts(with_part) == [
        ("", "testEnvironment"), ("ref ", "system1ConfiguredProduct"), ("ref ", "integrationLayer")]


def test_the_source_order_case_needs_all_four_stages() -> None:
    """REQ-MW-014 names an AEBS event through four stages; without all four, VC-MW-015 is inconclusive."""
    body = _raw_body(SLICE.read_text(encoding="utf-8"), r"\bverification\s+def\s+AEBSSignalSourceOrderVerification\s*\{")
    (comment,) = re.findall(r"\bdoc\s*/\*(.*?)\*/", body, re.DOTALL)
    doc = " ".join(re.sub(r"^\s*\*\s?", "", line) for line in comment.splitlines())
    doc = " ".join(doc.split())
    assert "all four stages, MONITORING, WARNING, INTERVENTION and RELEASED" in doc
    assert "In that case, the outcome is inconclusiveMissingEvidence." in doc


def test_the_at_most_once_case_bounds_messages_after_the_stop() -> None:
    """REQ-MW-013: the pairing check covers the second clause; a bounded in-flight allowance covers the first."""
    body = _raw_body(SLICE.read_text(encoding="utf-8"),
                     r"\bverification\s+def\s+AtMostOnceSpeedSampleDeliveryVerification\s*\{")
    (comment,) = re.findall(r"\bdoc\s*/\*(.*?)\*/", body, re.DOTALL)
    doc = " ".join(" ".join(re.sub(r"^\s*\*\s?", "", line) for line in comment.splitlines()).split())
    for statement in ("It checks both clauses of the success criteria and adds no criterion.",
                      "The run declares an in-flight bound before it starts.",
                      "It pairs with a distinct sample that is not yet delivered.",
                      "It also arrives within the in-flight bound after the publish of that sample.",
                      "Any other message in that time fails the first clause."):
        assert statement in doc, statement


def test_the_environment_gap_ends_on_the_verification_system() -> None:
    """GAP-MW-044 leaves the System 2 performer of the cases without an identity."""
    code = " ".join(_blanked(SLICE.read_text(encoding="utf-8")).split())
    assert "part <'GAP-MW-044'> gapSCOREVerificationEnvironmentOpen : IncrementGap {" in code
    assert ("dependency environmentGapOnVerificationSystem from gapSCOREVerificationEnvironmentOpen "
            "to scoreMiddlewareVerificationSystem;") in code


def _flat_doc(body: str) -> str:
    """The first doc comment of ``body``, comment line prefixes removed and whitespace collapsed."""
    comment = re.findall(r"\bdoc\s*/\*(.*?)\*/", body, re.DOTALL)[0]
    return " ".join(" ".join(re.sub(r"^\s*\*\s?", "", line) for line in comment.splitlines()).split())


def _usage_doc(case: str) -> str:
    """The flattened doc of the usage of ``case``."""
    header = rf"\bverification\s+<'{case}'>\s*\w+\s*:\s*\w+\s*\{{"
    return _flat_doc(_raw_body(SLICE.read_text(encoding="utf-8"), header))


def test_the_isolation_case_inspects_the_host_and_probes_the_dds_ports_from_each_guest_domain() -> None:
    """REQ-MW-016 asks for DDS ports that no guest domain reaches: VC-MW-017 inspects the configuration that does
    it and probes the ports at run time, with a control on someipd (owner decision of 2026-10-28)."""
    definition = _flat_doc(_raw_body(SLICE.read_text(encoding="utf-8"),
                                     r"\bverification\s+def\s+NoApplicationDataFromHMIGuestVerification\s*\{"))
    for statement in ("Inspection of REQ-MW-016, with a runtime probe for its second finding.",
                      "the configuration of each element of the layer.",
                      "These elements are the S-CORE services, the adapter, gatewayd, someipd, the health proxy node "
                      "and the SOME/IP receiver.",
                      "the ROS 2 environment of each ROS 2 process on the Linux host, with the DDS configuration that "
                      "it names, and the host configuration that makes the DDS ports unreachable from the guest "
                      "domains, such as its firewall rules.",
                      "For the ROS 2 processes outside the layer, it records whether ASM-MW-031 holds on the member.",
                      "While the layer runs, collectData also runs a reachability probe from each guest domain of the "
                      "layer against the DDS ports of the Linux host. The probe must find these ports unreachable.",
                      "As a control, it must reach the SOME/IP ports of someipd from the guest domain that someipd "
                      "serves.",
                      "If ASM-MW-031 does not hold, the case does not show the criteria met. If the control fails, the "
                      "probe shows nothing about the DDS ports. In both cases, the outcome is "
                      "inconclusiveMissingEvidence."):
        assert statement in definition, statement
    assert "does not inspect them" not in definition, "the criteria name the host's ROS 2 and DDS configuration"
    needs = _usage_doc("VC-MW-017")
    assert needs.startswith("Not started. Bench: the Linux host with the layer running and each guest domain of the "
                            "layer up, with a reachability probe in each guest domain."), needs[:200]
    for statement in ("With the AAOS SDV broker path that the owner chose on 2026-10-28, these are the SDV Core VM "
                      "and the IVI VM, and someipd serves the SDV Core VM.",
                      "For ROS 2 (DDS), it needs the Launch Manager configuration and the launch configuration of the "
                      "member on the Linux host.",
                      "It also needs the DDS configuration of the Linux host and the host configuration that makes "
                      "the DDS ports unreachable from the guest domains."):
        assert statement in needs, statement
    gap = _flat_doc(_raw_body(SLICE.read_text(encoding="utf-8"),
                              r"\bpart\s+<'GAP-MW-044'>\s*\w+\s*:\s*IncrementGap\s*\{"))
    assert ("The inspection cases VC-MW-018 and VC-MW-021 need no run. They need the configurations and the wiring "
            "that the execution slices author. VC-MW-017 needs them too, and a run for its reachability probe from "
            "each guest domain of the layer.") in gap, gap


def test_the_slice_header_names_its_three_exceptions_to_the_preflight_rule() -> None:
    """Preflight checks verify no requirement, apart from the three that a case holds."""
    (header,) = re.findall(r"\A/\*(.*?)\*/", SLICE.read_text(encoding="utf-8"), re.DOTALL)
    flat = " ".join(" ".join(re.sub(r"^\s*\*\s?", "", line) for line in header.splitlines()).split())
    exceptions = ("The adapter restart is a test condition of VC-MW-014.",
                  "The clock offset shows whether ASM-MW-030 holds, which the criteria of REQ-MW-019 need, so "
                  "VC-MW-020 records it.",
                  "VC-MW-017 inspects the ROS 2 environment of each ROS 2 process on the host, for the DDS criteria of "
                  "REQ-MW-016.")
    assert "They verify no requirement, so no case of this slice holds them. Three exceptions apply. " in flat, flat
    for exception in exceptions:
        assert exception in flat, exception


def test_the_emergency_command_case_needs_only_the_hmi_path_configurations_of_vc_mw_017() -> None:
    """VC-MW-018 needs no ROS 2 (DDS) or network configuration of the host."""
    needs = _usage_doc("VC-MW-018")
    assert "the mw::com, gateway, vsomeip and receiver configurations that VC-MW-017 needs" in needs, needs
    assert "and the configurations that VC-MW-017 needs" not in needs, needs
