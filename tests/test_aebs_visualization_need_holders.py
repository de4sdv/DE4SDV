"""INC-AEBS-010 need holder guard tests.

N-AEBS-010 and N-AEBS-013 must state what the visualization instrument
provides to the stakeholders each need declares. N-AEBS-013 keeps only
holders that use the instrument, so its statement states the observed
behavior instead of asking a holder to be assured of it, and its planned
validation names those same holders.
"""

import re
from pathlib import Path

NEEDS = (
    Path("textual-notation-of-model/packages/features/aebs")
    / "aebs_visualization_needs_requirements.sysml"
)

PROVENANCE_STATEMENT = (
    "Systems engineers and verification engineers need source provenance, "
    "units, coordinate frame, timestamps, rate and freshness, validity, and "
    "bounded displayed cardinality preserved between native Autoware output, "
    "DE4SDV AEBS coordination state, and display-derived presentation."
)

NON_INTERFERENCE_STATEMENT = (
    "Systems engineers and verification engineers need the visualization "
    "instrumentation to observe AEBS detection, warning, intervention and "
    "release behavior without commanding or modifying it, so that what it "
    "shows is the behavior of the unchanged AEBS."
)

SYSTEMS_ENGINEER = "stakeholder systemsEngineer : SystemsEngineer;"
VERIFICATION_ENGINEER = "stakeholder verificationEngineer : VerificationEngineer;"


def _brace_block(text: str, open_index: int) -> str:
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[open_index + 1:index]
    raise AssertionError("unbalanced braces")


def _block(name: str, kind: str = "requirement") -> str:
    text = NEEDS.read_text(encoding="utf-8")
    match = re.search(
        rf"\b{kind}\s+{re.escape(name)}\s*:\s*\w+\s*\{{", text
    )
    assert match, (kind, name)
    return _brace_block(text, match.end() - 1)


def _stakeholders(name: str) -> list[str]:
    return [
        " ".join(line.split())
        for line in _block(name).splitlines()
        if line.strip().startswith("stakeholder ")
    ]


def _statement(name: str) -> str:
    body = _block(name)
    constraint = re.search(r"require constraint statement\s*\{[^}]*\}", body)
    assert constraint, name
    prose = re.search(r"/\*(.*?)\*/", constraint.group(0), re.S)
    assert prose, name
    return " ".join(prose.group(1).split())


def test_n_aebs_013_declares_only_holders_that_use_the_instrument() -> None:
    assert _stakeholders("needNonInterference") == [
        SYSTEMS_ENGINEER,
        VERIFICATION_ENGINEER,
    ]


def test_n_aebs_013_statement_states_what_the_instrument_provides() -> None:
    statement = _statement("needNonInterference")
    assert statement == NON_INTERFERENCE_STATEMENT
    lowered = statement.lower()
    assert "need assurance" not in lowered
    assert "maintainer" not in lowered


def test_n_aebs_010_statement_names_both_declared_stakeholders() -> None:
    assert _stakeholders("needPreservedSourceProvenance") == [
        SYSTEMS_ENGINEER,
        VERIFICATION_ENGINEER,
    ]
    assert _statement("needPreservedSourceProvenance") == PROVENANCE_STATEMENT


def test_n_aebs_013_planned_validation_names_the_declared_holders() -> None:
    plan = " ".join(
        re.sub(r"\n\s*\*(?!/)", "\n", _block("nonInterferenceValidationPlan", "part")).split()
    )
    assert "SC-AEBS-010-11, N-AEBS-013" in plan
    assert "systems engineers and verification engineers" in plan
    assert "maintainer" not in plan.lower()
