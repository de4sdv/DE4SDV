"""The advisory visibility check of the baseline phase (``phaseContentPublished``).

Each applicable phase with content has at least one of its elements in a view
of the increment: the view itself, the member a member expose names, and the
members of a namespace an expose names, at any depth when the expose is
recursive. A phase's content is the subjects of its checks about what its step
produces. The workflow is the checkout's live one, and the content is the
synthetic framing of ``test_phase_progression``; no production model is copied.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from de4sdv.semantic.increment_scope import ModelView
from de4sdv.semantic.increment_workflow import phase_contents
from de4sdv.semantic.remedies import check_remedy
from increment_model_fixtures import ModelBuilder, ref
from test_phase_progression import P0, P11, evaluate, framing_only, phase
from test_revision_index import _traversal

GATE = "applicablePhaseContentPublished"
CHECK = "phaseContentPublished"
P1 = "phase1_concernFraming"


def _named(builder: ModelBuilder, name: str) -> dict:
    (element,) = [e for e in builder.elements if e.get("declaredName") == name]
    return element


def _expose_only(builder: ModelBuilder, element: dict, *, recursive: bool = False) -> None:
    """Replace the framing view's ``expose <package>::*;`` by ``expose <element>;`` (``::**`` when recursive)."""
    builder.remove(*[e for e in builder.elements if e.get("@type") in ("NamespaceExpose", "MembershipExpose")])
    keys = {"isRecursive": True} if recursive else {}
    builder.relationship("MembershipExpose", _named(builder, "progressionView"),
                         importedMembership=ref(element["owningRelationship"]["@id"]), **keys)


def _gate(evaluation) -> dict:
    return next(entry for entry in evaluation.gaps()["advisory"] if entry["gate"] == GATE)


def test_the_check_is_advisory_in_the_live_baseline_step():
    evaluation = evaluate(framing_only())
    (gate,) = [g for g in evaluation.phase_contract(P11)["gates"] if g["obligation_id"] == GATE]
    assert (gate["predicate"], gate["required"], gate["parameter"]) == (CHECK, False, "charter")


def test_a_framing_view_that_shows_the_framing_package_shows_phases_0_and_1():
    evaluation = evaluate(framing_only())
    assert phase(evaluation, P11)["gates"][GATE] == "PASS"
    # Phases 2 to 10 have no content here and nothing to show; phase 3 is vacuous.
    assert not [entry for entry in evaluation.gaps()["advisory"] if entry["gate"] == GATE]


def test_a_phase_whose_content_no_view_shows_is_named_and_never_blocks():
    builder = framing_only()
    _expose_only(builder, _named(builder, "progressionProblemStatement"))
    evaluation = evaluate(builder)
    block = phase(evaluation, P11)
    assert block["gates"]["publishedViewExposesContent"] == "PASS"
    assert block["gates"][GATE] == "FAIL"
    assert GATE in [entry["gate"] for entry in block["advisory_open"]]
    assert GATE not in [entry["gate"] for entry in block["blocking"]]
    entry = _gate(evaluation)
    text = " ".join(entry.get("diagnostics", []) + [d for s in entry["subjects"] for d in s.get("diagnostics", [])])
    assert f"{P1}: none of 1 element(s) is in a view of the increment (DE4SDV_ProgressionFraming::progressionBoundary)" in text
    assert f"{P0}:" not in text  # the problem statement shows phase 0
    assert evaluation.next_obligation()["next"]["gate"] != GATE


def test_an_undeclared_phase_has_no_content_to_show():
    builder = framing_only(applicable_phases=(P0, P11))
    _expose_only(builder, _named(builder, "progressionProblemStatement"))
    assert phase(evaluate(builder), P11)["gates"][GATE] == "PASS"


def test_the_content_of_one_corpus_follows_the_declared_phases_it_is_read_for():
    """The content is built once per corpus, increment and declared phases: a scope that declares fewer
    phases never reads the content cached for one that declares more."""
    evaluation = evaluate(framing_only())
    view, scope = evaluation.view, evaluation.scope
    everything, _ = phase_contents(view, scope)
    framing, _ = phase_contents(view, dataclasses.replace(scope, declared_phases=(P0,)))
    assert P1 in everything and set(framing) == {P0}


def test_a_member_expose_shows_what_the_member_owns_only_when_recursive():
    plain = framing_only()
    _expose_only(plain, _named(plain, "DE4SDV_ProgressionFraming"))
    entry = _gate(evaluate(plain))
    text = " ".join(d for s in entry["subjects"] for d in s.get("diagnostics", []))
    assert f"{P0}: none of" in text and f"{P1}: none of" in text
    recursive = framing_only()
    _expose_only(recursive, _named(recursive, "DE4SDV_ProgressionFraming"), recursive=True)
    assert phase(evaluate(recursive), P11)["gates"][GATE] == "PASS"


def test_the_remedy_asks_for_an_expose_in_a_view_of_the_increment():
    builder = framing_only()
    remedy = check_remedy(ModelView(builder.elements, _traversal(builder), sources=builder.sources), CHECK)
    assert "expose" in remedy.text and "view of the increment" in remedy.text
    assert any("Visibility is not review" in note for note in remedy.notes)
    assert any("existing view of the increment" in note for note in remedy.notes)
