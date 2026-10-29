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
criteria of REQ-MW-016 name; VC-MW-018 needs only its HMI-path configurations. The
cases follow the broker path of phase 8 (ADR 0025): the IVI frame relay in the IVI
VM, the SOME/IP broker with its stack in the SDV Core VM, and no SOME/IP receiver.

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
PHYSICAL = MIDDLEWARE / "middleware_score_physical_software_realization.sysml"
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
    return re.findall(rf"\b(?:part|item)\s+{SHORT_NAME}(\w*)\s*:\s*(?:ReceiptBoundMiddlewareEvidence|"
                      r"RetainedMiddlewareEvidence)\b", code)


def _bench_parts(text: str) -> list[tuple[str, str]]:
    """(``ref `` or empty, name) of each part of the bench definition in ``text``, short-named or not."""
    bench = _code_body(text, r"\bpart\s+def\s+SCOREMiddlewareVerificationBench\s*\{")
    return re.findall(rf"\b(ref\s+)?part\s+{SHORT_NAME}(\w*)\s*[:;{{]", bench)


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
    code = _blanked(SLICE.read_text(encoding="utf-8"))
    assert len(re.findall(r"\bverification\s+(?!def\b)", code)) == len(CASES), "a case outside the short-named usages"
    verified = re.findall(r"\bverify\s+(\w+)", code)
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


def _definition_doc(definition: str) -> str:
    """The flattened doc of the verification definition ``definition``."""
    return _flat_doc(_raw_body(SLICE.read_text(encoding="utf-8"),
                               rf"\bverification\s+def\s+{definition}\s*\{{"))


def test_the_cases_follow_the_broker_path_of_phase_8() -> None:
    """The SOME/IP receiver left the product path (ADR 0025, decision 7): the cases name the IVI frame relay, and the
    SDV Core VM where the guest holds the broker."""
    text = SLICE.read_text(encoding="utf-8")
    flat = " ".join(" ".join(re.sub(r"^\s*\*\s?", "", line) for line in text.splitlines()).split())
    assert not re.search(r"SOME/IP receiver|\breceiver's\b|someipReceiver", flat, re.IGNORECASE), (
        "the slice still names the SOME/IP receiver")
    for definition in ("AEBSSignalSourceOrderVerification", "AEBSSignalProvenanceVerification",
                       "NoApplicationDataFromHMIGuestVerification", "NoEmergencyCommandOnMiddlewareVerification",
                       "UnsubscribedFrameDiscardVerification"):
        assert "IVI frame relay" in _definition_doc(definition), definition
    for case in ("VC-MW-015", "VC-MW-017"):
        needs = _usage_doc(case)
        for name in ("SDV Core VM", "IVI VM", "IVI frame relay"):
            assert name in needs, (case, name)
    gap = _flat_doc(_raw_body(text, r"\bpart\s+<'GAP-MW-044'>\s*\w+\s*:\s*IncrementGap\s*\{"))
    assert ("The SDV Core VM is built with the DE4SDV SOME/IP mapping and stack configuration, and the IVI VM runs "
            "the IVI frame relay (GAP-MW-038).") in gap, gap


def test_the_source_order_case_records_every_phase_end() -> None:
    """A phase end that the layer causes while the ingress stays connected is a delivery failure; no phase end in
    the AEBS event lets the run pass (relaySubscriptionPhaseDiscardRule). A delivery failure that does not depend on
    the clock fails the run whatever else holds; only then do the inconclusive conditions apply."""
    case = _definition_doc("AEBSSignalSourceOrderVerification")
    for statement in ("collectData also records every start and end of a subscription phase of the relay, with its "
                      "cause, from the relay's log.",
                      "The IVI frame relay delivers them there, on 127.0.0.1:4731 of the IVI VM.",
                      "Two captures in the IVI VM corroborate each phase start: - a cleartext capture of Data Tunnel "
                      "on VLAN 2, in the UNLOCKED mode, for the subscription through the SDV Gateway on IVI; - the "
                      "loopback capture, for the accept of the ingress. The record holds their difference from the "
                      "relay's log. Where they differ, processData uses the time of the captures.",
                      "A phase end that the layer causes while the ingress stays connected is a delivery failure of "
                      "the layer (relaySubscriptionPhaseDiscardRule).",
                      "The layer causes it by the relay's timeout, PublicationDestroyed or Disconnected.",
                      "If such a phase end falls in the AEBS event, the outcome is failObservedBehavior.",
                      "A delivery failure that does not depend on the clock fails the run whatever else holds. In the "
                      "event, such failures are a phase end that the layer causes, a DATA_LOSS and a change of order. "
                      "Otherwise the three conditions below make the run inconclusive.",
                      "- the ingress disconnects in the event; - another client holds the stream of the frame "
                      "assembler; - ASM-MW-030 does not hold.",
                      # A second client can starve the adapter and end the phase by the relay's timeout: a bench
                      # fault, so a discrepancy record comes first, and the run still never passes.
                      "If the run's records show a second client on port 4721, the execution slice records a bench "
                      "discrepancy before any fail counts against the layer. Such a client breaks ASM-MW-029, so the "
                      "run never passes.",
                      "So no phase end in the AEBS event lets the run pass.",
                      "A DATA_LOSS of the relay in the event is a sequence gap.",
                      # The sport list counts the clients of the frame assembler; only dport names a client process.
                      "The check has two steps: - ss -H -t -n -p state established '( sport = :4721 )' lists the "
                      "connections that the frame assembler accepted. The list must hold exactly one connection, and "
                      "its peer must be a loopback address; - ss -H -t -n -p state established '( dport = :4721 )' "
                      "must name the adapter process for the port of that peer.",
                      "So the path has carried many cycles of SD offers and renewals before the event (GAP-MW-047).",
                      "So the case also checks the order part of ASM-MW-032 end to end, on the AAOS SDV hops."):
        assert statement in case, statement
    # The list comparison runs in every run, so the inconclusive conditions cannot hide a delivery failure.
    assert case.index("processData compares the two lists") < case.index("Otherwise the three conditions"), case
    assert "Otherwise, processData compares" not in case, "the comparison runs only when no condition holds"
    needs = _usage_doc("VC-MW-015")
    assert ("The IVI VM runs the IVI frame relay and the HMI application, and it captures its loopback and Data "
            "Tunnel on VLAN 2.") in needs, needs


def test_the_provenance_case_checks_the_bytes_and_the_sd_offer_from_the_ivi_vm() -> None:
    """A rogue SD offer fails the case if it moves the stack's subscription or stops the frames, not only if a
    received frame differs; the SOME/IP hardening is recorded, never judged."""
    case = _definition_doc("AEBSSignalProvenanceVerification")
    for statement in ("So the case also checks the byte part of ASM-MW-032 end to end, through the wrapper of the "
                      "broker.",
                      "An SD message from the IVI VM must not redirect the subscription of the stack in the SDV Core "
                      "VM to another provider (phase 8).",
                      "If the pin or the filter exists, the run sends an SD offer of the frame service from the IVI "
                      "VM.",
                      "collectData also records, from the SD captures, the provider that the stack subscribes to "
                      "after that offer. If that provider is not 192.168.98.1, the outcome is failObservedBehavior.",
                      "The outcome is also failObservedBehavior if the received frames stop after the offer for the "
                      "inter-arrival bound of REQ-MW-014 or longer.",
                      "If neither the pin nor the filter exists, the run sends no such offer. The record then names the "
                      "residual for REQ-MW-015 under GAP-MW-012, as phase 8 allows.",
                      "The SOME/IP hardening of GAP-MW-046 lets only the bridge port of the SDV Core VM reach the "
                      "SOME/IP ports of the host (VC-MW-017). It is a recorded design measure, and no part of the pass "
                      "condition of this case. The case makes no robustness claim for it (GAP-MW-012)."):
        assert statement in case, statement


def test_the_evidence_record_names_the_guest_builds_and_the_unlocked_claim_boundary() -> None:
    """A guest run names both images, their one revision and their one boot mode; UNLOCKED runs in cleartext."""
    record = _flat_doc(_raw_body(SLICE.read_text(encoding="utf-8"),
                                 r"\bitem\s+def\s+ReceiptBoundMiddlewareEvidence\s*:>\s*RetainedMiddlewareEvidence\s*\{"))
    for statement in ("For a run in the guest, executionEnvironmentIdentity names the builds of the SDV Core image and "
                      "of the IVI image.",
                      "It also names their android17-release revision and their boot mode, which must be the same for "
                      "both (ADR 0025, decision 8).",
                      "In the UNLOCKED mode, claimBoundary states that the SD mesh and Data Tunnel run as cleartext "
                      "HTTP/2 (GAP-MW-038).",
                      "A missing or partial record gives inconclusive, never pass."):
        assert statement in record, statement


def test_the_isolation_case_inspects_the_host_and_probes_from_both_vms() -> None:
    """REQ-MW-016: the DE4SDV configurations of the AAOS SDV elements for the first finding, and the host
    configuration of GAP-MW-046 with a probe from both VMs over every interface for the second (owner decisions of
    2026-10-28 and 2026-10-29)."""
    definition = _definition_doc("NoApplicationDataFromHMIGuestVerification")
    for statement in ("Inspection of REQ-MW-016, with a runtime probe for its second finding.",
                      "the configuration of each element of the layer.",
                      "These elements are the S-CORE services, the adapter, gatewayd, someipd, the health proxy node "
                      "and the IVI frame relay.",
                      "For the first finding, the artifacts also include the configuration that DE4SDV authors for "
                      "the AAOS SDV elements.",
                      "The first is the DE4SDV SOME/IP mapping of the broker, with its VSIDL type and catalog.",
                      "The second is the DE4SDV stack configuration of the SDV Core VM.",
                      "The third is the authorization entries of the broker's publication and of the relay's "
                      "subscription.",
                      "The mapping must map only the frame event, and the stack configuration must offer no SOME/IP "
                      "service.",
                      "By owner decision of 2026-10-29, that configuration drops UDP 30150-30151 and 30160-30401, and "
                      "TCP 4721, on every interface except lo, in an inet input chain.",
                      "The configuration records its two parameters, ROS_DOMAIN_ID 91 and MaxAutoParticipantIndex 120.",
                      "For the ROS 2 processes outside the layer, it records whether ASM-MW-031 holds on the member.",
                      "While the layer runs, collectData also runs a reachability probe from each VM of the guest "
                      "domain. These VMs are the SDV Core VM and the IVI VM.",
                      "It lists the sockets that the ROS 2 processes of the host have bound (ss -ulnp, IPv4 and IPv6, "
                      "unicast and multicast).",
                      "It lists every host address that the VM reaches. These are 192.168.98.1, the host end of the "
                      "buried network of each VM, and any other cvd-* bridge address.",
                      "It does so over each interface of the VM: eth1, buried_eth0, the VLAN interfaces, and wlan if "
                      "present.",
                      "The same observation must show the delivery.",
                      "From the SDV Core VM, the SOME/IP ports of someipd stay the control of the network path.",
                      # The owner approved the SOME/IP hardening as a design measure, not as a verified property.
                      "The probe also records the SOME/IP hardening of GAP-MW-046 (owner decision of 2026-10-29).",
                      "It accepts UDP 30490 and TCP 30509 to the host only from the bridge port of the SDV Core VM. "
                      "It also matches the address and the MAC address of that VM.",
                      "It blocks the IVI VM, also with the source address 192.168.98.3.",
                      "The hardening is a recorded design measure. It is no part of the pass condition of any case, "
                      "and processData does not judge it. No robustness claim is made for it (GAP-MW-012).",
                      "A reachable DDS port of an element of the layer fails the case, whatever the control or "
                      "ASM-MW-031 show.",
                      "If the control fails, an unreachable result shows nothing, and the outcome is "
                      "inconclusiveMissingEvidence.",
                      "If ASM-MW-031 does not hold, the case shows nothing about the other processes, and for them the "
                      "outcome is inconclusiveMissingEvidence.",
                      "If no layer port is reachable but ASM-MW-031 does not hold, the outcome is "
                      "inconclusiveMissingEvidence.",
                      "A reachable port 4721 is a finding against ASM-MW-029, not against these criteria."):
        assert statement in definition, statement
    assert "such as its firewall rules" not in definition, "the owner chose the host configuration"
    assert not re.search(r"\bserves\b|\bmust not reach\b", definition), "the hardening reads as a verified property"
    needs = _usage_doc("VC-MW-017")
    assert needs.startswith("Not started. Bench: the Linux host with the layer running, and the SDV Core VM and the "
                            "IVI VM up with a reachability probe in each. someipd serves the SDV Core VM."), needs[:200]
    for statement in ("The positive control needs a control socket that the host exposes on INADDR_ANY, or a control "
                      "window with the isolation off.",
                      "It needs the DE4SDV SOME/IP mapping, the DE4SDV stack configuration and the authorization "
                      "entries.",
                      "For ROS 2 (DDS), it needs the Launch Manager configuration and the launch configuration of the "
                      "member on the Linux host.",
                      "It needs the host configuration of GAP-MW-046 too, which makes the DDS ports and port 4721 "
                      "unreachable from the guest domain."):
        assert statement in needs, statement
    gap = _flat_doc(_raw_body(SLICE.read_text(encoding="utf-8"),
                              r"\bpart\s+<'GAP-MW-044'>\s*\w+\s*:\s*IncrementGap\s*\{"))
    assert ("The inspection cases VC-MW-018 and VC-MW-021 need no run. They need the configurations and the wiring "
            "that the execution slices author. VC-MW-017 needs them too, and a run for its reachability probe from "
            "both VMs of the guest.") in gap, gap


def test_the_discard_case_runs_the_four_conditions() -> None:
    """REQ-MW-019 in the guest of ADR 0025 and after a pair restart in the host half; the bench recovery of
    GAP-MW-048 is manual and bench only, with no availability claim. After an IVI VM reboot the case judges the phase
    that starts once the clock is set, and keeps the first phase as data outside the judged scope."""
    case = _definition_doc("UnsubscribedFrameDiscardVerification")
    for statement in ("It runs four conditions.",
                      "- the HMI application down;",
                      "- the IVI VM down, with a reboot;",
                      "- the SDV Core VM down: a death of the SOME/IP broker or of its stack, with the bench recovery "
                      "of GAP-MW-048.",
                      "The operator reboots the SDV Core VM by hand, for the bench only;",
                      "- a restart of gatewayd and someipd as a pair (gatewayPairRestartGuardRail).",
                      "A capture of the relay's stream on 127.0.0.1:4731 of the IVI VM gives them",
                      "collectData records the death detection: the line \"Critical agent has died\" in the logcat of "
                      "the SDV Core VM, and VmHealth.",
                      "It records how long the HMI shows stale. No criterion applies to that time, and no availability "
                      "claim is made (GAP-MW-048).",
                      "For the fourth condition, it records the latency of PublicationDestroyed and the time to the new "
                      "publication. It records both on the host clock and on the IVI VM clock corrected by the "
                      "measured offset. No criterion applies to these two times.",
                      "The run applies the clock controls of ASM-MW-030 and records them.",
                      # The clock procedure after an IVI VM reboot (assurance review R6 and author question 1).
                      "After a reboot of the IVI VM, the relay and the ingress start before the bench can set the clock "
                      "(GAP-MW-048).",
                      "So for the second condition, the bench sets the clock after the reboot and then starts the "
                      "ingress again.",
                      "The case judges the phase that starts then.",
                      "collectData still records the first phase after the reboot, as data. The claimBoundary of the "
                      "record names that phase as outside the judged scope (GAP-MW-045).",
                      "The new subscription is the start of a subscription phase of the IVI frame relay, as phase 8 "
                      "defines it (relaySubscriptionPhaseDiscardRule).",
                      "The relay's log shows it. Two captures in the IVI VM corroborate it: - a cleartext capture of "
                      "Data Tunnel on VLAN 2, in the UNLOCKED mode, for the subscription through the SDV Gateway on "
                      "IVI; - the loopback capture, for the accept of the ingress. The record holds their difference "
                      "from the relay's log. Where they differ, processData takes the start of the new subscription "
                      "from the captures.",
                      "For REQ-MW-014, a phase end that the layer causes is a delivery failure (VC-MW-015). For "
                      "REQ-MW-019, the new phase is the current subscription.",
                      "The SOME/IP hardening of GAP-MW-046 is a recorded design measure (VC-MW-017). It is no part of "
                      "the pass condition of this case, and the case makes no robustness claim for it (GAP-MW-012).",
                      "While GAP-MW-039 is open for a restart of gatewayd alone and for a late start of gatewayd, a "
                      "pass does not close REQ-MW-019."):
        assert statement in case, statement


def test_the_discard_case_fails_a_clock_independent_violation_whatever_else_holds() -> None:
    """A frame produced before the new subscription by more than the bound, the larger measured offset and its
    uncertainty fails the run, whatever else holds; only otherwise does a failed ASM-MW-030 make it inconclusive."""
    case = _definition_doc("UnsubscribedFrameDiscardVerification")
    rule = ("Among them are the two offset measurements, at the start and at the end of the session, each with its "
            "uncertainty. If both measurements exist, processData also checks each frame against a wider limit. The "
            "limit is the 20 ms bound of ASM-MW-030, plus the larger absolute offset of the two measurements, plus the "
            "uncertainty of that measurement. A frame that the AEBS stack produced more than that limit before the "
            "new subscription is a clock-independent violation. Such a frame fails the run, whatever else holds.")
    fallback = ("Otherwise, if ASM-MW-030 does not hold in the run, the run does not show the criteria met. In that "
                "case, the outcome is inconclusiveMissingEvidence.")
    assert rule in case, case
    assert fallback in case, case
    assert case.index(rule) < case.index(fallback), "the clock-independent rule must come before the inconclusive one"
    # The bound in the limit is the bound of ASM-MW-030 itself, so the two cannot drift apart.
    (bound,) = re.findall(r"The limit is the (\d+) ms bound of ASM-MW-030", case)
    assumption = _flat_doc(_raw_body(PHYSICAL.read_text(encoding="utf-8"),
                                     r"\bpart\s+<'ASM-MW-030'>\s*\w+\s*:\s*IncrementAssumption\s*\{"))
    assert re.findall(r"differ by less than (\d+) ms", assumption) == [bound], (bound, assumption[:200])


def test_the_slice_header_names_the_steps_that_verify_a_requirement() -> None:
    """Preflight checks verify no requirement, apart from the steps that a case holds. The two times that VC-MW-020
    measures without a criterion are context, not steps."""
    (header,) = re.findall(r"\A/\*(.*?)\*/", SLICE.read_text(encoding="utf-8"), re.DOTALL)
    flat = " ".join(" ".join(re.sub(r"^\s*\*\s?", "", line) for line in header.splitlines()).split())
    intro = ("They verify no requirement, so no case of this slice holds them. Where a check verifies a requirement, "
             "the case of that requirement holds it as a step:")
    context = ("VC-MW-020 also records two measurements as context, with no criterion: - how long the HMI shows stale "
               "while the SDV Core VM is down; - the latency of PublicationDestroyed after a pair restart, on corrected "
               "clocks.")
    assert intro in flat, flat
    assert context in flat, flat
    steps = flat[flat.index(intro) + len(intro):flat.index(context)]
    for step in ("- VC-MW-014: the adapter restart;",
                 "- VC-MW-015: every phase end of the relay, its DATA_LOSS counts and the client check of the frame "
                 "assembler. It also holds the SD offers and renewals of a long session;",
                 "- VC-MW-016: the SD offer from the IVI VM that must not redirect the subscription of the stack;",
                 "- VC-MW-017: the ROS 2 environment of each ROS 2 process on the host, the host configuration of "
                 "GAP-MW-046 and the probe from both VMs;",
                 "- VC-MW-020: the clock controls of ASM-MW-030 and the bench recovery of GAP-MW-048."):
        assert step in steps, step
    for measurement in ("PublicationDestroyed", "stale"):
        assert measurement not in steps, f"a measurement without a criterion is listed as a step: {measurement}"


def test_the_emergency_command_case_needs_only_the_hmi_path_configurations_of_vc_mw_017() -> None:
    """VC-MW-018 needs no ROS 2 (DDS) or network configuration of the host."""
    needs = _usage_doc("VC-MW-018")
    assert "the mw::com, gateway, vsomeip, relay and DE4SDV guest configurations that VC-MW-017 needs" in needs, needs
    assert "and the configurations that VC-MW-017 needs" not in needs, needs
    case = _definition_doc("NoEmergencyCommandOnMiddlewareVerification")
    assert ("In the guest domain, these are the IVI frame relay and the configuration that DE4SDV authors for the AAOS "
            "SDV elements.") in case, case
