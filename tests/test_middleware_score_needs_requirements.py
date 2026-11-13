"""INC-MW-011 phase 5: the success criteria of REQ-MW-016, REQ-MW-017 and REQ-MW-019 (owner decisions of 2026-10-28).

REQ-MW-016 keeps application data of the guest out of the Linux host with two findings. First, the HMI path and
the configuration of each element of the layer give no endpoint on the host for data from a guest domain. Second,
no DDS port of an element of the layer is reachable from any guest domain. The second finding states the
property, real isolation, and names no mechanism. A loopback binding alone does not give it. A reachable port of
an element of the layer fails. The other ROS 2 processes on the host count only while ASM-MW-031 holds; without
it, a verification shows nothing about them.
The criteria of REQ-MW-017 name the layer's elements in a guest domain by their role.
REQ-MW-019 declares a margin at the start of a subscription. The margin is the clock bound of ASM-MW-030, and
ASM-MW-030 is also the condition of the criteria. A run without it is inconclusive. ASM-MW-030 holds the value, so
the criteria state none. Each requirement lists its assumption in its source.

The statements and the criteria of REQ-MW-016 and REQ-MW-019 name the guest by its role. They name no element,
guest machine, technology choice or mechanism of the realization. This guard checks words only. Whether the
criteria still fit a revised phase 8 stays a question for its review.

These are lexical source guards; licensed Syside validates the model in CI.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIDDLEWARE = ROOT / "textual-notation-of-model" / "packages" / "features" / "middleware"
NEEDS = MIDDLEWARE / "middleware_score_needs_requirements.sysml"
PHYSICAL = MIDDLEWARE / "middleware_score_physical_software_realization.sysml"

#: Words that name an element, a guest machine, a technology choice or a mechanism of the realization.
REALIZATION_WORDS = (r"\breceiver", r"\bIVI\b", r"\bsdv_\w+", r"\bCore VM\b", r"\bsomeipd\b", r"\bgatewayd?\b",
                     r"\badapter\b", r"\bLaunch Manager\b", r"\bSOME/IP\b", r"\bvsomeip\b", r"\bCycloneDDS\b",
                     r"\bbroker\b", r"\bData Tunnel\b", r"\bphase\b", r"\bCuttlefish\b", r"\bfirewall",
                     r"\bloopback\b", r"\biptables\b", r"\bnftables\b")


def _flat(text: str) -> str:
    """The text with comment line prefixes removed and whitespace collapsed."""
    lines = (re.sub(r"^\s*\*\s?", "", line) for line in text.splitlines())
    return " ".join(" ".join(lines).split())


def _requirement(short_name: str) -> str:
    """The body of the one requirement usage with ``short_name``."""
    text = NEEDS.read_text(encoding="utf-8")
    pattern = rf"\brequirement <'{re.escape(short_name)}'> \w+ : \w+ \{{(.*?)\n  \}}"
    matches = list(re.finditer(pattern, text, re.DOTALL))
    assert len(matches) == 1, f"expected one requirement <'{short_name}'>, found {len(matches)}"
    return matches[0][1]


def _attribute(body: str, name: str) -> str:
    """The string value of the attribute ``name`` that the requirement body redefines."""
    (value,) = re.findall(rf'\battribute :>> {name} = "([^"]*)";', body)
    return value


def _statement(body: str) -> str:
    """The English statement of the requirement body."""
    (value,) = re.findall(r'\brequire constraint statement \{ language "English" /\*(.*?)\*/ \}', body, re.DOTALL)
    return " ".join(value.split())


def test_req_mw_016_criteria_state_the_hmi_path_and_unreachable_dds_ports() -> None:
    """Two findings; the subscription clause merged into the port finding (owner decision of 2026-10-28)."""
    body = _requirement("REQ-MW-016")
    assert _attribute(body, "verificationMethod") == "inspect"
    criteria = _attribute(body, "successCriteria")
    assert criteria.startswith("Met when two findings hold. A guest domain of the layer is a domain under the "
                               "hypervisor that the HMI path enters. "), criteria
    for clause in ("First, the interface definition of the HMI path and the configuration of each element of the "
                   "layer declare no endpoint on the Linux host for application data from a guest domain of the "
                   "layer.",
                   "Second, no DDS port on the Linux host of an element of the layer, nor, while ASM-MW-031 holds, "
                   "of any other ROS 2 process on the Linux host, is reachable from any guest domain of the layer.",
                   "A reachable port of an element of the layer fails the criteria."):
        assert clause in criteria, clause
    assert "Third," not in criteria and "subscription" not in criteria, "the port finding covers the subscriptions"
    assert "any process on the Linux host" not in criteria, "the findings name the elements of the layer"


def test_req_mw_016_criteria_extend_to_other_host_processes_only_while_asm_mw_031_holds() -> None:
    """The part outside the layer is conditioned on ASM-MW-031, as REQ-MW-019 is on ASM-MW-030."""
    body = _requirement("REQ-MW-016")
    criteria = _attribute(body, "successCriteria")
    for statement in ("nor, while ASM-MW-031 holds, of any other ROS 2 process on the Linux host,",
                      "A verification that finds ASM-MW-031 not holding shows nothing about the other processes, and "
                      "for them its outcome is inconclusive."):
        assert statement in criteria, statement
    assert criteria.endswith("and for them its outcome is inconclusive."), criteria[-120:]
    assert "does not show the criteria met" not in criteria, "a failing layer port is not hidden as inconclusive"
    source = _attribute(body, "source")
    assert "; ASM-MW-031; " in source, source
    assert "owner decision 2026-10-28 (the ROS 2 (DDS) criteria)" in source
    rationale = _attribute(body, "rationale")
    for statement in ("So the criteria ask for ports that no guest domain reaches: a property, not a configuration.",
                      "DDS on the loopback interface alone does not give it. CycloneDDS 0.10.5 binds its receive "
                      "sockets to INADDR_ANY (ddsi_udp.c:453-456, 479-480), and the guests share the host's untagged "
                      "network segment.",
                      "The DDS finding names the elements of the layer. It extends to the other ROS 2 processes on the "
                      "Linux host only while ASM-MW-031 holds, and the verification checks that assumption on the "
                      "member."):
        assert statement in rationale, statement


def test_req_mw_017_criteria_name_the_guest_element_by_its_role() -> None:
    """A knock-on of the path decision: no criterion names the receiver; the statement is unchanged."""
    body = _requirement("REQ-MW-017")
    assert _statement(body) == "The middleware integration layer shall carry no AEBS emergency intervention command."
    criteria = _attribute(body, "successCriteria")
    assert criteria == ("Met when inspection finds no element that carries the AEBS emergency intervention command. "
                        "The inspection covers the S-CORE service configuration, the adapter interfaces, gatewayd, "
                        "someipd, each element of the layer in a guest domain and the interface definition of the HMI "
                        "path. The path of that command from the AEB node to the vehicle command gate on the Linux "
                        "host contains no element of the middleware integration layer."), criteria
    assert not re.search(r"\breceiver", criteria, re.IGNORECASE), criteria


def test_req_mw_019_criteria_take_their_margin_and_their_condition_from_asm_mw_030() -> None:
    body = _requirement("REQ-MW-019")
    assert _attribute(body, "verificationMethod") == "test"
    criteria = _attribute(body, "successCriteria")
    for statement in ("Met when, while ASM-MW-030 holds, the HMI application receives no frame that the AEBS stack "
                      "produced more than a margin before the start of its current subscription.",
                      "The production time comes from the clock of the frame's producer.",
                      "The start of the subscription comes from the clock that times the start of the HMI "
                      "application's subscription.",
                      "The margin is the bound of ASM-MW-030 on the offset between these two clocks.",
                      "A run in which ASM-MW-030 does not hold does not show the criteria met, and its outcome is "
                      "inconclusive."):
        assert statement in criteria, statement
    assert not re.search(r"\d\s*ms\b", criteria), "ASM-MW-030 holds the value of the margin; the criteria state none"
    source = _attribute(body, "source")
    assert "; ASM-MW-030; " in source, source
    assert "owner decision 2026-10-28 (the margin at the start of a subscription)" in source
    rationale = _attribute(body, "rationale")
    assert ("The clock that stamps a frame is not the clock that times the start of the HMI application's "
            "subscription.") in rationale, rationale
    assert "clock at the HMI application's subscription" not in criteria + rationale, "the vague clock name is gone"
    assert rationale.endswith("GAP-MW-045 records the band that the margin leaves."), rationale[-120:]
    assert "twice" not in rationale, "the rationale leaves the width of the band to GAP-MW-045"
    # The bound that the criteria take is stated once, in ASM-MW-030.
    (doc,) = re.findall(r"\bpart <'ASM-MW-030'> \w+ : IncrementAssumption \{\s*doc /\*(.*?)\*/",
                        PHYSICAL.read_text(encoding="utf-8"), re.DOTALL)
    assert re.search(r"differ by less than \d+ ms\.", _flat(doc)), "ASM-MW-030 states no clock bound"


def test_the_frame_purpose_names_the_margin_of_req_mw_019() -> None:
    """The phase-2 doc of the frame item states the purpose of the two read fields as the criteria allow it."""
    operational = (MIDDLEWARE / "middleware_score_operational_context.sysml").read_text(encoding="utf-8")
    (doc,) = re.findall(r"\bitem def AEBSSignalFrame \{\s*doc /\*(.*?)\*/", operational, re.DOTALL)
    assert ("It needs them to discard the frames produced more than the margin of REQ-MW-019 before the HMI "
            "application subscribed (phase 8).") in _flat(doc), _flat(doc)


def test_the_two_requirements_name_roles_and_no_element_of_the_realization() -> None:
    """The statements and criteria name the guest by its role and name no mechanism of the realization."""
    for short_name in ("REQ-MW-016", "REQ-MW-019"):
        body = _requirement(short_name)
        for text in (_statement(body), _attribute(body, "successCriteria")):
            found = [word for word in REALIZATION_WORDS if re.search(word, text, re.IGNORECASE)]
            assert not found, (short_name, found, text)


def test_the_realization_check_reads_realization_words() -> None:
    """Negative cases: the old criteria of REQ-MW-016 named elements, and a mechanism is a realization word too."""
    old = ("Met when inspection of the interface definition of the HMI path and of the configuration of the S-CORE "
           "services, the adapter, gatewayd, someipd and the SOME/IP receiver finds no receiver on the Linux host "
           "for application data from the AAOS SDV guest.")
    found = [word for word in REALIZATION_WORDS if re.search(word, old, re.IGNORECASE)]
    assert found == [r"\breceiver", r"\bsomeipd\b", r"\bgatewayd?\b", r"\badapter\b", r"\bSOME/IP\b"], found
    mechanism = "Third, the host firewall keeps DDS on the loopback interface."
    found = [word for word in REALIZATION_WORDS if re.search(word, mechanism, re.IGNORECASE)]
    assert found == [r"\bfirewall", r"\bloopback\b"], found
