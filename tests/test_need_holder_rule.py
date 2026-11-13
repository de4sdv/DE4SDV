"""The holder rule: a need is held by the parties whose interest it states.

A stakeholder member of a need names the party the need serves, not the
reviewer who later checks it. This file locks the rule in the two workflow
step docs, in the four method concerns whose holders are product-line or
compliance engineers rather than reviewers, in the method prose, and in the
remedy an author reads when a need has no stakeholder member. Text checks, not
a SysML parser: licensed validation stays the authority for syntax.
"""

from __future__ import annotations

import re

import pytest

from sysml_shapes import MODEL_ROOT

WORKFLOW_FILE = MODEL_ROOT / "packages/methods/de4sdv/de4sdv_increment_workflow.sysml"
CONCERNS_FILE = MODEL_ROOT / "packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml"
WORKFLOW_DOC = MODEL_ROOT.parent / "methodologies/sysmod-sysmlv2/increment-workflow.md"

HOLDER_NOTE = ("A stakeholder member names a party whose interest the element states; "
               "a role that only reviews or verifies it does not hold it.")

#: The four concerns a product-line or compliance engineer holds, with the words
#: their constraint doc must start with.
REWORDED = {
    "ProductLineCapabilityClassificationConcern": "Product-line engineers need model content to show",
    "RegulatoryScopeWithoutComplianceClaimConcern": "Compliance engineers need regulatory anchors",
    "ProductLineConfigurationConcern": "Product-line engineers need the native SysML v2 variation",
    "ProductModelAssemblyConcern": "Product-line engineers and systems engineers need a composite "
                                   "product model's assembly",
}

#: The two method concerns reviewers legitimately hold.
REVIEWER_HELD = ("IncrementBoundaryConcern", "MethodStackConcern")


def _text(raw: str) -> str:
    """A doc body as one line, without the comment decoration."""
    return " ".join(raw.replace("*", " ").split())


def _action_doc(name: str) -> str:
    source = WORKFLOW_FILE.read_text(encoding="utf-8")
    match = re.search(rf"action def {name}\s*:> IncrementStep\s*\{{\s*doc /\*(.*?)\*/", source,
                      re.DOTALL)
    assert match, name
    return _text(match.group(1))


def _concern_doc(name: str) -> str:
    """The doc of a concern definition's first require constraint."""
    source = CONCERNS_FILE.read_text(encoding="utf-8")
    starts = [(m.group(1), m.start()) for m in re.finditer(r"concern def (\w+)\s*\{", source)]
    (index,) = [i for i, (declared, _start) in enumerate(starts) if declared == name]
    begin = starts[index][1]
    end = starts[index + 1][1] if index + 1 < len(starts) else len(source)
    match = re.search(r"require constraint\s*\{\s*doc /\*(.*?)\*/", source[begin:end], re.DOTALL)
    assert match, name
    return _text(match.group(1))


def test_elaborate_needs_doc_says_a_reviewer_does_not_hold_a_need() -> None:
    doc = _action_doc("ElaborateNeeds")
    assert "does not hold it" in doc, doc
    assert "planned validation" in doc, doc


def test_frame_concerns_doc_says_a_concern_names_its_holders_not_only_reviewers() -> None:
    doc = _action_doc("FrameConcerns")
    assert "not only the reviewers" in doc, doc


def test_the_workflow_prose_mirrors_the_holder_rule() -> None:
    prose = " ".join(WORKFLOW_DOC.read_text(encoding="utf-8").split())
    assert "whose interest it states" in prose, "the needs rule in the method prose"
    assert "does not hold it" in prose, "the holder rule next to the needs rule"


@pytest.mark.parametrize(("name", "opening"), sorted(REWORDED.items()))
def test_a_reworded_concern_names_the_engineer_who_holds_it(name: str, opening: str) -> None:
    doc = _concern_doc(name)
    assert not doc.startswith("Reviewers need"), doc
    assert doc.startswith(opening), doc


@pytest.mark.parametrize("name", REVIEWER_HELD)
def test_a_method_concern_keeps_the_reviewer_as_its_holder(name: str) -> None:
    doc = _concern_doc(name)
    assert doc.startswith("Reviewers need"), doc


def test_the_remedy_for_a_need_without_a_stakeholder_states_the_holder_rule() -> None:
    """The same call ``test_remedies`` makes: a need that loses its stakeholder member."""
    from test_remedies import _evaluate, _gap, _kernel_scenario

    scenario, _steps, _types = _kernel_scenario()
    builder = scenario.builder
    need = scenario.needs[1]
    builder.remove(*[e for e in builder.elements
                     if e.get("@type") in ("StakeholderMembership", "SubjectMembership")
                     and e.get("owningRelatedElement", {}).get("@id") == need["@id"]])
    entry = _gap(_evaluate(scenario).gaps(), "needHasStakeholder")
    assert HOLDER_NOTE in entry["authoring"]["notes"], entry["authoring"]["notes"]
    assert "tests no stakeholder type" in entry["authoring"]["types"][0]["admits"]
