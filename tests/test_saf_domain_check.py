"""The advisory SAF-domain check of the baseline phase (``concernAnsweredInDomain``).

A concern typed by an SAF concern definition is framed by a viewpoint of a view
of the increment whose definition is an SAF viewpoint definition of the same
SAF domain. The domain is native lineage: each definition of the SAF catalogue
specializes the abstract definition of its domain, bound by identity through
the library pins (ADR 0011's file-mapped rule), never by a name. The workflow
is the checkout's live one; the catalogue and the increment are synthetic
export-shaped content, not copies of production model files.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from de4sdv.semantic.export_evaluation import export_document_inputs
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from de4sdv.semantic.method_checks import _concern_answered_in_domain
import pytest

from de4sdv.semantic.relation_checks import SAF_CATALOGUE, SAF_DOMAINS, MethodSideInput, saf_domain_pin
from de4sdv.semantic.remedies import check_remedy
from de4sdv.sysml_api.qualified_names import QualifiedNameIndex
from increment_model_fixtures import ModelBuilder, ref
from test_phase_progression import P11, REVISION, framing_only, phase
from test_remedies import _problems
from test_revision_index import _traversal

GATE = "concernAnsweredInItsDomain"
CHECK = "concernAnsweredInDomain"
INCREMENT = "INC-PROGRESSION-001"


def _named(builder: ModelBuilder, name: str) -> dict:
    (element,) = [e for e in builder.elements if e.get("declaredName") == name]
    return element


class Increment:
    """The progression framing plus a synthetic SAF catalogue and helpers to add concerns and views."""

    def __init__(self, *, roots: bool = True) -> None:
        b = self.b = framing_only()
        self.framing = _named(b, "DE4SDV_ProgressionFraming")
        self.role = _named(b, "ProgressionEngineer")
        self.framing_viewpoint = _named(b, "selectedViewpoint")
        self.catalogue = b.package("SAF_Viewpoints", source=SAF_CATALOGUE)
        self.roots: dict[tuple[str, str], dict] = {}
        if roots:
            for domain in SAF_DOMAINS:
                for keyword, kind in (("concern", "ConcernDefinition"), ("viewpoint", "ViewpointDefinition")):
                    self.roots[(domain, keyword)] = b.definition(
                        kind, f"{domain}Domain{keyword.capitalize()}", self.catalogue)
        self.physical_exchange = self.saf("concern", "PhysicalInternalExchangeConcern", "Physical")
        self.functional_interface = self.saf("concern", "FunctionalInterfaceConcern", "Conceptual")
        self.physical_viewpoint = self.saf("viewpoint", "PhysicalInternalExchangeViewpoint", "Physical")
        self.conceptual_viewpoint = self.saf("viewpoint", "SystemInterfaceDefinitionViewpoint", "Conceptual")
        self.stakeholder_viewpoint = self.saf("viewpoint", "StakeholderIdentificationViewpoint", "Operational")

    def saf(self, keyword: str, name: str, domain: str) -> dict:
        kind = "ConcernDefinition" if keyword == "concern" else "ViewpointDefinition"
        generals = [self.roots[(domain, keyword)]] if self.roots else []
        return self.b.definition(kind, name, self.catalogue, generals)

    def concern(self, name: str, *typed_by: dict) -> dict:
        """A concern of the increment with a stakeholder, framed by the framing view's viewpoint (no SAF domain)."""
        concern = self.b.usage("ConcernUsage", name, self.framing, list(typed_by))
        self.b.stakeholder(concern, "engineer", self.role)
        self.b.frame(self.framing_viewpoint, concern)
        return concern

    def view(self, name: str, viewpoint_type: dict | None, *concerns: dict) -> dict:
        view = self.b.usage("ViewUsage", name, self.framing)
        viewpoint = self.b.usage("ViewpointUsage", f"{name}Viewpoint", view, [viewpoint_type] if viewpoint_type else [],
                                 membership="FeatureMembership")
        for concern in concerns:
            self.b.frame(viewpoint, concern)
        self.b.relationship("NamespaceExpose", view, importedNamespace=ref(self.framing))
        return view

    def evaluate(self):
        b = self.b
        view = ModelView(b.elements, _traversal(b), **export_document_inputs(b.elements, b.sources, ()))
        return evaluate_increment(view, INCREMENT, revision=REVISION)

    def outcome(self, concern: dict):
        evaluation = self.evaluate()
        return _concern_answered_in_domain(evaluation.view, evaluation.scope, concern["@id"])


def _diagnostics(outcome) -> str:
    return " ".join(outcome.diagnostics)


# -- the contract -----------------------------------------------------------------------------------------


def test_the_check_is_an_advisory_check_about_the_concerns_of_the_live_baseline_step():
    evaluation = Increment().evaluate()
    (gate,) = [g for g in evaluation.phase_contract(P11)["gates"] if g["obligation_id"] == GATE]
    assert (gate["predicate"], gate["required"], gate["parameter"]) == (CHECK, False, "concerns")


def test_the_pins_bind_the_abstract_domain_definitions_of_the_catalogue_only():
    increment = Increment()
    inputs = export_document_inputs(increment.b.elements, increment.b.sources, ())
    for domain in SAF_DOMAINS:
        for keyword in ("concern", "viewpoint"):
            assert inputs["library_bindings"][saf_domain_pin(domain, keyword)] == increment.roots[(domain, keyword)]["@id"]


# -- verdicts ---------------------------------------------------------------------------------------------


def test_a_concern_framed_only_by_the_framing_view_is_not_answered_in_its_domain():
    """INC-MW-011's HMI concern: an SAF concern only the framing viewpoint frames has no answering view."""
    increment = Increment()
    concern = increment.concern("pathConcern", increment.physical_exchange)
    outcome = increment.outcome(concern)
    assert outcome.status == "violated"
    text = _diagnostics(outcome)
    assert "asks a question of the SAF Physical Domain, and no viewpoint of that domain frames it" in text
    assert "framed by: DE4SDV_ProgressionFraming::progressionView::selectedViewpoint (no SAF domain)" in text


def test_a_view_of_the_concern_domain_answers_it():
    increment = Increment()
    concern = increment.concern("pathConcern", increment.physical_exchange)
    increment.view("pathExchangeView", increment.physical_viewpoint, concern)
    outcome = increment.outcome(concern)
    assert outcome.status == "satisfied"
    assert outcome.targets == (_named(increment.b, "pathExchangeViewViewpoint")["@id"],)


def test_a_mistyped_concern_answered_only_by_another_domain_is_named_with_the_framing_domain():
    """The S-CORE path question typed as the Conceptual interface concern and answered by a Physical
    internal-exchange view: the type and the answering view disagree."""
    increment = Increment()
    concern = increment.concern("scorePathConcern", increment.functional_interface)
    increment.view("scorePathExchangeView", increment.physical_viewpoint, concern)
    outcome = increment.outcome(concern)
    assert outcome.status == "violated"
    text = _diagnostics(outcome)
    assert "SAF Conceptual Domain, and no viewpoint of that domain frames it" in text
    assert "DE4SDV_ProgressionFraming::scorePathExchangeView::scorePathExchangeViewViewpoint (Physical)" in text
    assert "its SAF concern definition is the wrong one" in text


def test_another_domain_framing_beside_an_answer_is_not_refused():
    """A stakeholder overview (Operational) also framing the concern does not count against it."""
    increment = Increment()
    concern = increment.concern("pathConcern", increment.physical_exchange)
    increment.view("stakeholderView", increment.stakeholder_viewpoint, concern)
    increment.view("pathExchangeView", increment.physical_viewpoint, concern)
    assert increment.outcome(concern).status == "satisfied"


def test_a_concern_of_no_saf_definition_is_outside_the_rule():
    increment = Increment()
    boundary = _named(increment.b, "progressionBoundary")
    outcome = increment.outcome(boundary)
    assert outcome.status == "satisfied"
    assert "typed by no SAF concern definition" in _diagnostics(outcome)


# -- lineage ----------------------------------------------------------------------------------------------


def test_a_specialization_of_an_saf_concern_definition_keeps_its_domain():
    increment = Increment()
    local = increment.b.definition("ConcernDefinition", "ScorePathConcern", increment.framing,
                                   [increment.physical_exchange])
    concern = increment.concern("pathConcern", local)
    increment.view("conceptualView", increment.conceptual_viewpoint, concern)
    assert increment.outcome(concern).status == "violated"
    increment.view("pathExchangeView", increment.physical_viewpoint, concern)
    assert increment.outcome(concern).status == "satisfied"


def test_a_viewpoint_typed_by_a_specialization_of_an_saf_viewpoint_definition_keeps_its_domain():
    increment = Increment()
    local = increment.b.definition("ViewpointDefinition", "ScoreExchangeViewpoint", increment.framing,
                                   [increment.physical_viewpoint])
    concern = increment.concern("pathConcern", increment.physical_exchange)
    increment.view("pathExchangeView", local, concern)
    assert increment.outcome(concern).status == "satisfied"


def test_a_frame_the_viewpoint_inherits_from_its_definition_counts():
    increment = Increment()
    concern = increment.concern("pathConcern", increment.physical_exchange)
    local = increment.b.definition("ViewpointDefinition", "ScoreExchangeViewpoint", increment.framing,
                                   [increment.physical_viewpoint])
    increment.b.frame(local, concern)
    increment.view("pathExchangeView", local)
    assert increment.outcome(concern).status == "satisfied"


def test_a_concern_that_references_a_typed_concern_keeps_its_domain():
    """A concern with no type of its own keeps the types of the feature it narrows."""
    increment = Increment()
    typed = increment.concern("pathConcern", increment.physical_exchange)
    narrowing = increment.concern("pathConcernReference")
    increment.b.reference_subsetting(narrowing, typed)
    increment.view("conceptualView", increment.conceptual_viewpoint, narrowing)
    outcome = increment.outcome(narrowing)
    assert outcome.status == "violated" and "SAF Physical Domain" in _diagnostics(outcome)


def test_a_same_named_domain_root_outside_the_catalogue_is_not_a_domain():
    increment = Increment()
    impostor_root = increment.b.definition("ConcernDefinition", "PhysicalDomainConcern", increment.framing)
    impostor = increment.b.definition("ConcernDefinition", "LookalikeConcern", increment.framing, [impostor_root])
    concern = increment.concern("lookalike", impostor)
    outcome = increment.outcome(concern)
    assert outcome.status == "satisfied" and "typed by no SAF concern definition" in _diagnostics(outcome)


# -- unreadable inputs ------------------------------------------------------------------------------------


def test_an_unbound_domain_root_is_method_side():
    increment = Increment(roots=False)
    concern = increment.concern("pathConcern", increment.physical_exchange)
    evaluation = increment.evaluate()
    with pytest.raises(MethodSideInput) as raised:
        _concern_answered_in_domain(evaluation.view, evaluation.scope, concern["@id"])
    assert raised.value.marker == f"library-binding:{saf_domain_pin('ArchitectureManagement', 'concern')}"
    entry = next(e for e in evaluation.gaps()["advisory"] if e["gate"] == GATE)
    assert entry["kind"] == "method-side"


def test_a_dangling_typing_without_a_readable_domain_is_an_input_problem():
    increment = Increment()
    concern = increment.concern("pathConcern")
    increment.b.relationship("FeatureTyping", concern, type={"@id": "absent-definition"},
                             general={"@id": "absent-definition"}, specific=ref(concern), typedFeature=ref(concern))
    outcome = increment.outcome(concern)
    assert outcome.status == "indeterminate" and outcome.missing == ("model-witness:concern-lineage",)


def test_a_dangling_typing_beside_a_readable_saf_type_is_judged_by_the_readable_one():
    increment = Increment()
    concern = increment.concern("pathConcern", increment.physical_exchange)
    increment.b.relationship("FeatureTyping", concern, type={"@id": "absent-definition"},
                             general={"@id": "absent-definition"}, specific=ref(concern), typedFeature=ref(concern))
    increment.view("pathExchangeView", increment.physical_viewpoint, concern)
    assert increment.outcome(concern).status == "satisfied"


# -- the evaluation ---------------------------------------------------------------------------------------


def test_an_unanswered_concern_is_advised_never_blocking_and_never_next():
    increment = Increment()
    increment.concern("pathConcern", increment.physical_exchange)
    evaluation = increment.evaluate()
    block = phase(evaluation, P11)
    assert block["gates"][GATE] == "FAIL"
    assert GATE in [entry["gate"] for entry in block["advisory_open"]]
    assert GATE not in [entry["gate"] for entry in block["blocking"]]
    entry = next(e for e in evaluation.gaps()["advisory"] if e["gate"] == GATE)
    (subject,) = entry["subjects"]
    assert subject["qualified_name"] == "DE4SDV_ProgressionFraming::pathConcern"
    assert ("frame DE4SDV_ProgressionFraming::pathConcern by a viewpoint of the SAF Physical Domain"
            in entry["what_to_author"])
    assert entry["authoring"]["declarations"][0] == (
        "viewpoint def <ViewpointName> :> SAF_Viewpoints::PhysicalDomainViewpoint "
        "{ doc /* <what the view shows> */ }")
    assert "private import SAF_Viewpoints::*;" in entry["authoring"]["imports"]
    names = QualifiedNameIndex(increment.b.elements)
    assert _problems(entry, names, "DE4SDV_ProgressionFraming") == []
    # The SAF viewpoint definitions of the concern's domain are named, read by identity from the catalogue.
    assert "may instead be an SAF viewpoint definition of the Physical Domain: PhysicalInternalExchangeViewpoint;" in (
        entry["what_to_author"])
    assert evaluation.next_obligation()["next"]["gate"] != GATE


def test_without_a_subject_the_remedy_says_how_without_a_type_placeholder():
    increment = Increment()
    view = ModelView(increment.b.elements, _traversal(increment.b), sources=increment.b.sources)
    remedy = check_remedy(view, CHECK)
    assert remedy.declarations == ()
    assert remedy.instruction.startswith("nothing to author for a concern typed by no SAF concern definition;")
    assert "specializes <Domain>DomainViewpoint as the concern's definition specializes <Domain>DomainConcern" in (
        remedy.instruction)
    assert "or retype the concern by the SAF concern definition of the domain its question belongs to" in (
        remedy.instruction)
    assert "concrete platform, product or component is a Physical Domain question" in " ".join(remedy.notes)
