"""INC-MW-011: who holds NEED-MW-002 and its concern.

The need for the one-way AEBS signal path to the HMI is held by the vehicle
occupant who reads the display, by the system architect who owns the domain
boundary, and by the safety expert who owns the one-way property. The
verification engineer holds the concern and reviews the planned validation
scenario, not the need itself: the need states what must be true, the review
states how it will be confirmed.

These are lexical source guards; licensed Syside validates the model in CI.
"""

from __future__ import annotations

import re
from pathlib import Path

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
MIDDLEWARE = ROOT / "textual-notation-of-model" / "packages" / "features" / "middleware"
NEEDS = MIDDLEWARE / "middleware_score_needs_requirements.sysml"
FRAMING = MIDDLEWARE / "middleware_score_framing.sysml"

NEED_HOLDERS = [("occupant", "VehicleOccupant"),
                ("systemArchitect", "SystemArchitect"),
                ("safetyExpert", "SafetyExpert")]
CONCERN_HOLDERS = [("occupant", "VehicleOccupant"),
                   ("systemArchitect", "SystemArchitect"),
                   ("safetyExpert", "SafetyExpert"),
                   ("verificationEngineer", "VerificationEngineer")]


def _need_body(short_name: str) -> str:
    """The body of the one requirement usage with ``short_name``."""
    code = strip_comments(NEEDS.read_text(encoding="utf-8"))
    pattern = rf"\brequirement <'{re.escape(short_name)}'> \w+ : \w+ \{{(.*?)\n  \}}"
    matches = list(re.finditer(pattern, code, re.DOTALL))
    assert len(matches) == 1, f"expected one requirement <'{short_name}'>, found {len(matches)}"
    return matches[0][1]


def _stakeholders(body: str) -> list[tuple[str, str]]:
    """The (role, type) pairs of the stakeholder usages, in source order."""
    return re.findall(r"\bstakeholder\s+(\w+)\s*:\s*(\w+)\s*;", body)


def _concern_body() -> str:
    code = strip_comments(FRAMING.read_text(encoding="utf-8"))
    assert re.search(r"\bconcern\s+hmiDomainBoundaryConcern\s*:\s*PhysicalContextExchangeConcern\s*\{", code)
    return braced_body(code, "concern hmiDomainBoundaryConcern : PhysicalContextExchangeConcern")


def test_the_need_is_held_by_the_occupant_the_architect_and_the_safety_expert():
    """The occupant who reads the HMI holds the need with the two engineering roles."""
    assert _stakeholders(_need_body("NEED-MW-002")) == NEED_HOLDERS


def test_each_need_holder_holds_the_concern():
    """Every holder of the need is a stakeholder of the concern the need comes from."""
    concern = _stakeholders(_concern_body())
    for holder in NEED_HOLDERS:
        assert holder in concern, f"{holder[1]} holds the need but not the concern"


def test_the_concern_is_held_by_the_three_need_holders_and_the_verification_engineer():
    """The verification engineer holds the concern and reviews the planned scenario."""
    assert _stakeholders(_concern_body()) == CONCERN_HOLDERS


def test_the_concern_opens_with_the_occupant_not_the_reviewer():
    """The concern states what the occupants and the engineering roles need, not what reviewers need."""
    raw = FRAMING.read_text(encoding="utf-8")
    concern = raw[raw.index("concern hmiDomainBoundaryConcern : PhysicalContextExchangeConcern"):]
    doc = concern[concern.index("doc /*") + len("doc /*"):concern.index("*/")]
    text = " ".join(line.strip().lstrip("*").strip() for line in doc.splitlines()).strip()
    assert not text.startswith("Reviewers need"), text
    assert text.startswith("Vehicle occupants need"), text
