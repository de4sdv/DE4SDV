"""INC-MW-011 phase 5: the success criteria of REQ-MW-016 and REQ-MW-019 (owner decision of 2026-10-28).

REQ-MW-016 keeps application data of the guest out of the Linux host on three counts: the HMI path and the
configuration of each element of the layer, the ROS 2 (DDS) subscriptions of every process on the host, and no DDS
endpoint of the host on an interface that a guest domain reaches. The third count states an outcome, so a loopback
binding meets it and a firewall could too. REQ-MW-019 declares a margin at the start of a subscription. The margin is
the clock bound of ASM-MW-030, and ASM-MW-030 is also the condition of the criteria. ASM-MW-030 holds the value,
so the criteria state none. The statements and the criteria of both requirements name the guest by its role and
name no element of the realization, so a revision of phase 8 does not change them.

These are lexical source guards; licensed Syside validates the model in CI.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIDDLEWARE = ROOT / "textual-notation-of-model" / "packages" / "features" / "middleware"
NEEDS = MIDDLEWARE / "middleware_score_needs_requirements.sysml"
PHYSICAL = MIDDLEWARE / "middleware_score_physical_software_realization.sysml"

#: Words that name an element, a guest machine or a technology choice of the realization instead of a role.
REALIZATION_WORDS = (r"\breceiver", r"\bIVI\b", r"\bsdv_\w+", r"\bCore VM\b", r"\bsomeipd\b", r"\bgatewayd?\b",
                     r"\badapter\b", r"\bLaunch Manager\b", r"\bSOME/IP\b", r"\bvsomeip\b", r"\bCycloneDDS\b",
                     r"\bbroker\b", r"\bData Tunnel\b", r"\bphase\b", r"\bCuttlefish\b")


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


def test_req_mw_016_criteria_cover_the_hmi_path_the_ros2_subscriptions_and_dds_on_loopback() -> None:
    body = _requirement("REQ-MW-016")
    assert _attribute(body, "verificationMethod") == "inspect"
    criteria = _attribute(body, "successCriteria")
    assert criteria.startswith("Met when inspection finds three things. A guest domain of the layer is a domain "
                               "under the hypervisor that the HMI path enters. "), criteria
    for clause in ("First, the interface definition of the HMI path and the configuration of each element of the "
                   "layer declare no endpoint on the Linux host for application data from a guest domain of the "
                   "layer.",
                   "Second, no ROS 2 (DDS) subscription of any process on the Linux host is reachable from a guest "
                   "domain of the layer.",
                   "Third, the DDS and network configuration of the Linux host offers no DDS endpoint on a network "
                   "interface that a guest domain of the layer reaches."):
        assert clause in criteria, clause
    assert "loopback" not in criteria, "the third clause states the outcome, not the loopback design"
    assert "owner decision 2026-10-28 (the ROS 2 (DDS) criteria)" in _attribute(body, "source")
    assert ("For the processes outside the layer, ASM-MW-031 states the condition that the context must meet, and "
            "the inspection checks it on the member.") in _attribute(body, "rationale")


def test_req_mw_019_criteria_take_their_margin_and_their_condition_from_asm_mw_030() -> None:
    body = _requirement("REQ-MW-019")
    assert _attribute(body, "verificationMethod") == "test"
    criteria = _attribute(body, "successCriteria")
    for statement in ("Met when, while ASM-MW-030 holds, the HMI application receives no frame that the AEBS stack "
                      "produced more than a margin before the start of its current subscription.",
                      "The margin is the bound of ASM-MW-030 on the offset between the clock of the frame's producer "
                      "and the clock at the HMI application's subscription.",
                      "The production time is on the first clock, and the start of the subscription is on the "
                      "second."):
        assert statement in criteria, statement
    assert not re.search(r"\d\s*ms\b", criteria), "ASM-MW-030 holds the value of the margin; the criteria state none"
    assert "owner decision 2026-10-28 (the margin at the start of a subscription)" in _attribute(body, "source")
    # The bound that the criteria take is stated once, in ASM-MW-030.
    (doc,) = re.findall(r"\bpart <'ASM-MW-030'> \w+ : IncrementAssumption \{\s*doc /\*(.*?)\*/",
                        PHYSICAL.read_text(encoding="utf-8"), re.DOTALL)
    assert re.search(r"differ by less than \d+ ms\.", _flat(doc)), "ASM-MW-030 states no clock bound"


def test_the_two_requirements_name_roles_and_no_element_of_the_realization() -> None:
    """The statements and criteria name the guest by its role, so they hold for any realization of the HMI path."""
    for short_name in ("REQ-MW-016", "REQ-MW-019"):
        body = _requirement(short_name)
        for text in (_statement(body), _attribute(body, "successCriteria")):
            found = [word for word in REALIZATION_WORDS if re.search(word, text, re.IGNORECASE)]
            assert not found, (short_name, found, text)


def test_the_realization_check_reads_realization_words() -> None:
    """Negative case: the old criteria of REQ-MW-016 named the elements of the realization."""
    old = ("Met when inspection of the interface definition of the HMI path and of the configuration of the S-CORE "
           "services, the adapter, gatewayd, someipd and the SOME/IP receiver finds no receiver on the Linux host "
           "for application data from the AAOS SDV guest.")
    found = [word for word in REALIZATION_WORDS if re.search(word, old, re.IGNORECASE)]
    assert found == [r"\breceiver", r"\bsomeipd\b", r"\bgatewayd?\b", r"\badapter\b", r"\bSOME/IP\b"], found
