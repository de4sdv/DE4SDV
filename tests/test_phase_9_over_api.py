"""The phase-9 checks over the API: the view reads the export documents the revision binding records.

The derivation of the feature configurations reads the source documents and the external references of an
export. An API listing carries neither, so the importer records both in the revision binding
(``export_documents``, :mod:`de4sdv.sysml_api.export_documents`). The query service gives them to the
method view of the served corpus, with the library pins bound from them by the export loader's own rule.
The API view then holds what the export view holds, and the method answers equal the export path's.

A binding without the record, or with a record that does not list the served corpus, keeps the
method-side marker ``evaluation-input:export-documents``: never a pass, never ``next``. Identity still
decides: a part typed by a homonym of the projection is configured by no configuration over the API too.

The synthetic increment is the one of ``test_configured_product_and_baseline_checks``; its configurations
are given to each view (``_given``), as there. The genuine cut runs the real export path. With
``DE4SDV_FULL_EXPORT`` set to a licensed full-model export, the last test compares both paths for every
increment of that export, the real derivation included.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import pytest

from de4sdv.semantic import method_checks as mc, method_evaluator as me
from de4sdv.semantic.export_evaluation import export_document_inputs, export_view, load_export_snapshot
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from de4sdv.semantic.method_parity import PARITY_SCHEMA, increment_parity, method_parity
from de4sdv.semantic.relation_checks import VSS_SIGNAL_METADATA, MethodSideInput, library_lineage
from de4sdv.sysml_api.baseline import BaselineExportBundle
from de4sdv.sysml_api.export_documents import ExportDocuments
from de4sdv.sysml_api.revisions import RevisionBinding
from de4sdv.sysml_api.served_model import ServedModel
from increment_model_fixtures import GENUINE_EXPORT
from test_configured_product_and_baseline_checks import (
    CONFIGURED_BY,
    P9,
    REVISION,
    _increment,
    _method_side_over_the_api,
    _phase,
    _unit,
    _verdicts,
)
from test_revision_index import _traversal
from tests.model_contract_fixtures import binding_dict, model_service

EXPORT_SHA = "e" * 64
#: Values the pinned API adds to every element: schema fields without a value.
PADDING = {"qualifiedName": None, "documentation": [], "aliasIds": []}
#: Answer fields that name the revision or the service, never the evaluation's content.
REVISION_FIELDS = {"evaluation_key", "revision", "provenance", "service_provenance"}


def _api_listing(elements):
    """The API listing of a corpus: equal content in new objects, padded with valueless fields."""
    return [{**copy.deepcopy(element), **PADDING} for element in elements]


class _Repository:
    def __init__(self, elements):
        self.elements = elements
        self.listings = 0

    def list_elements(self, project_id, commit_id):
        self.listings += 1
        return self.elements


def _binding(elements, sources, external_references, *, kernel_bindings, record=True, **changes):
    served = ServedModel.from_elements(elements, source_export_sha256=EXPORT_SHA)
    document = binding_dict(kernel_bindings=kernel_bindings, served_model=served.to_dict(), **changes)
    if record:
        documents = ExportDocuments.from_export(
            SimpleNamespace(element_sources=sources, external_references=external_references),
            source_export_sha256=EXPORT_SHA)
        document["export_documents"] = documents.to_dict()
    return RevisionBinding.from_dict(json.loads(json.dumps(document)))


def _sources(builder) -> dict[str, str]:
    """The fixture's source documents of the elements it holds (an export lists exactly its elements)."""
    return {element["@id"]: builder.sources[element["@id"]] for element in builder.elements}


def _service(increment, *, record=True, listing=None):
    b = increment.builder
    listing = _api_listing(b.elements) if listing is None else listing
    binding = _binding(b.elements, _sources(b), (), kernel_bindings=b.bindings, record=record)
    return model_service(binding, _Repository(listing)), binding


def _given(view: ModelView, projections) -> None:
    """The configurations the derivation would give this view's inputs (as the export tests give them)."""
    view.index.memo_bound(mc.CONFIGURATION_MEMO, mc.configuration_inputs(view),
                          lambda: (MappingProxyType(dict(projections)), None))


def _export_view(increment) -> ModelView:
    b = increment.builder
    return ModelView(b.elements, _traversal(b), **export_document_inputs(b.elements, _sources(b), ()))


def _revision(binding) -> me.RevisionIdentity:
    return me.RevisionIdentity(binding.git_commit, binding.sysml_project_id, binding.sysml_commit_id, binding.scope)


def _content(value):
    if isinstance(value, dict):
        return {k: _content(v) for k, v in value.items() if k not in REVISION_FIELDS}
    if isinstance(value, list):
        return [_content(v) for v in value]
    return value


def _answers(evaluation) -> dict:
    return {"status": evaluation.status(), "gaps": evaluation.gaps(), "next": evaluation.next_obligation()}


# -- the view ---------------------------------------------------------------------------------------


def test_over_a_binding_with_the_record_the_api_view_reads_the_exports_documents() -> None:
    increment = _increment()
    service, binding = _service(increment)
    view = service._method_view()
    export = _export_view(increment)
    assert dict(view.sources) == dict(export.sources) == _sources(increment.builder)
    assert view.external_references == export.external_references == ()
    assert (dict(view.library_bindings), dict(view.library_problems)) == (
        dict(export.library_bindings), dict(export.library_problems))
    # One served corpus, one set of inputs: the derivation is built once per corpus and binding.
    again = service._method_view()
    assert again.elements is view.elements and again.index is view.index
    assert mc.configuration_inputs(again) == mc.configuration_inputs(view)
    assert all(a is b for a, b in zip(mc.configuration_inputs(again), mc.configuration_inputs(view)))


def test_over_the_api_phase_9_answers_as_the_export_path() -> None:
    """Given one derivation result, the API evaluation and the export evaluation of the same revision are
    the same evaluation: the same key and the same status, gaps and next."""
    increment = _increment()
    service, binding = _service(increment)
    _given(service._method_view(), increment.projections)
    api = service.increment_evaluation(increment.scenario.increment_id)
    export_view_ = _export_view(increment)
    _given(export_view_, increment.projections)
    export = evaluate_increment(export_view_, increment.scenario.increment_id, revision=_revision(binding))
    assert _verdicts(api, CONFIGURED_BY) == {"configuredProduct": me.VERDICT_PASS}
    assert _phase(api, P9)["phase_exit"] == "READY"
    assert api.evaluation_key == export.evaluation_key
    assert _answers(api) == _answers(export)


def test_over_the_api_a_homonym_of_the_projection_still_configures_nothing() -> None:
    """Identity, never a name: with the record, a part typed by a definition that only shares the
    projection's name fails over the API as over the export."""
    increment = _increment()
    b = increment.builder
    b.remove(increment.platform_stack)
    homonym = b.definition("PartDefinition", "FixtureProjection", increment.product_package)
    b.usage("PartUsage", "platformStack", increment.product_def, [homonym], membership="FeatureMembership")
    service, _binding_ = _service(increment)
    _given(service._method_view(), increment.projections)
    api = service.increment_evaluation(increment.scenario.increment_id)
    assert _verdicts(api, CONFIGURED_BY) == {"configuredProduct": me.VERDICT_FAIL}
    assert _phase(api, P9)["phase_exit"] == "BLOCKED"


# -- without the record ------------------------------------------------------------------------------


def test_a_binding_without_the_record_keeps_the_method_side_marker() -> None:
    increment = _increment()
    service, binding = _service(increment, record=False)
    assert binding.export_documents is None
    view = service._method_view()
    assert not view.sources and view.external_references is None
    evaluation = service.increment_evaluation(increment.scenario.increment_id)
    _method_side_over_the_api(evaluation)
    (entry,) = [b for b in evaluation.next_obligation()["method_side_blockers"] if b["gate"] == CONFIGURED_BY]
    assert entry["missing"] == [mc.EXPORT_DOCUMENTS]
    assert any("records no export documents" in d for r in evaluation.canonical.results
               if r.unit_id == CONFIGURED_BY for d in r.diagnostics)


def test_a_record_that_does_not_list_the_served_corpus_is_not_read() -> None:
    """A record of another corpus never reaches the view: the check keeps the method-side marker."""
    increment = _increment()
    listing = _api_listing(increment.builder.elements)
    listing.append({"@id": "an-element-the-export-did-not-hold", "@type": "Package"})
    service, binding = _service(increment, listing=listing)
    assert binding.export_documents is not None
    view = service._method_view()
    assert not view.sources and view.external_references is None
    evaluation = service.increment_evaluation(increment.scenario.increment_id)
    assert _unit(evaluation, CONFIGURED_BY).verdict is None
    _method_side_over_the_api(evaluation)


# -- the genuine cut, through the real export path -----------------------------------------------------


def _genuine(tmp_path: Path, path: Path):
    """(the export snapshot, its bundle, the export's sha256) of a genuine export file."""
    snapshot = load_export_snapshot(path)
    return snapshot, BaselineExportBundle.load(path), hashlib.sha256(path.read_bytes()).hexdigest()


def _genuine_service(snapshot, bundle, export_sha, *, record=True):
    listing = _api_listing(snapshot.elements)
    served = ServedModel.from_elements(listing, source_export_sha256=export_sha)
    document = binding_dict(
        git_commit=snapshot.revision.git_commit, served_model=served.to_dict(),
        kernel_bindings=[dict(ontology_class=b.ontology_class, element_id=b.element_id, source_file=b.source_file,
                              declaration=b.declaration) for b in snapshot.kernel_bindings])
    if record:
        document["export_documents"] = ExportDocuments.from_export(bundle, source_export_sha256=export_sha).to_dict()
    binding = RevisionBinding.from_dict(json.loads(json.dumps(document)))
    return model_service(binding, _Repository(listing)), binding


def test_over_the_api_the_genuine_cut_reads_its_documents_and_answers_as_its_export(tmp_path: Path) -> None:
    """The cut of a real export: the API view built from the binding's record holds the export view's
    documents, external references and library pins, and evaluated as the same revision it gives the
    export path's answers. Without the record the library pin of the VSS signal metadata is unbound, and a
    check that reads it is method side."""
    path = tmp_path / "export.json"
    path.write_bytes(gzip.decompress(GENUINE_EXPORT.read_bytes()))
    snapshot, bundle, export_sha = _genuine(tmp_path, path)
    export = export_view(snapshot)
    expected = evaluate_increment(export, "INC-AEBS-010", revision=snapshot.revision)

    service, _binding_ = _genuine_service(snapshot, bundle, export_sha)
    view = service._method_view()
    assert dict(view.sources) == dict(export.sources)
    assert view.external_references == export.external_references
    assert dict(view.library_bindings) == dict(export.library_bindings) and view.library_bindings
    assert _content(_answers(evaluate_increment(view, "INC-AEBS-010", revision=snapshot.revision))) == \
        _content(_answers(expected))

    bare, _ = _genuine_service(snapshot, bundle, export_sha, record=False)
    without = bare._method_view()
    assert not without.library_bindings and not without.sources
    assert library_lineage(view, VSS_SIGNAL_METADATA) == library_lineage(export, VSS_SIGNAL_METADATA)
    with pytest.raises(MethodSideInput) as unbound:
        library_lineage(without, VSS_SIGNAL_METADATA)
    assert unbound.value.marker == f"library-binding:{VSS_SIGNAL_METADATA}"


# -- a licensed full-model export (local, when given) --------------------------------------------------


FULL_EXPORT = os.environ.get("DE4SDV_FULL_EXPORT")


@pytest.mark.skipif(not FULL_EXPORT, reason="set DE4SDV_FULL_EXPORT to a licensed full-model export")
def test_over_the_api_every_increment_of_a_full_export_answers_as_the_export(tmp_path: Path) -> None:
    """For every increment the export evaluates: over the API, phase 9 has the export path's result and
    ``next`` is the export path's. Evaluated as the same revision, every answer is the export path's.
    Without the record, phase 9 is method side over the API and never passes."""
    from de4sdv.semantic.increment_discovery import declared_increments

    snapshot, bundle, export_sha = _genuine(tmp_path, Path(str(FULL_EXPORT)))
    export = export_view(snapshot)
    service, _binding_ = _genuine_service(snapshot, bundle, export_sha)
    bare, _ = _genuine_service(snapshot, bundle, export_sha, record=False)
    identifiers = declared_increments(export).increment_ids
    assert identifiers
    # The check the release evidence runs: phase 9 and next, the allocation guard aside.
    report = method_parity(service, export, snapshot.revision)
    assert report["passed"] is True, report
    assert [row["increment"] for row in report["increments"]] == list(identifiers)
    for identifier in identifiers:
        expected = evaluate_increment(export, identifier, revision=snapshot.revision)
        same_revision = evaluate_increment(service._method_view(), identifier, revision=snapshot.revision)
        assert _content(_answers(same_revision)) == _content(_answers(expected)), identifier
        phase9 = _phase(bare.increment_evaluation(identifier), P9)
        if _phase(expected, P9)["gates"]:
            assert phase9["phase_exit"] == "BLOCKED" and phase9["conformance_verdict"] != me.VERDICT_PASS
    assert method_parity(bare, export, snapshot.revision)["passed"] is False


def test_an_export_evaluated_with_a_binding_that_records_other_documents_is_refused(tmp_path: Path) -> None:
    """``evaluate_increment.py --binding``: the binding's evaluation key is the API's only when the binding
    records this export's documents. A record of other documents refuses the evaluation."""
    from de4sdv.semantic.export_evaluation import ExportEvaluationRefused

    path = tmp_path / "export.json"
    path.write_bytes(gzip.decompress(GENUINE_EXPORT.read_bytes()))
    snapshot, bundle, export_sha = _genuine(tmp_path, path)
    service, binding = _genuine_service(snapshot, bundle, export_sha)
    document = binding.to_dict()
    (tmp_path / "binding.json").write_text(json.dumps(document), encoding="utf-8")
    assert load_export_snapshot(path, tmp_path / "binding.json").identity_mode == "validated-revision-binding"

    moved = dict(bundle.element_sources)
    first = sorted(moved)[0]
    moved[first] = moved[first] + ".elsewhere"
    other = SimpleNamespace(element_sources=moved, external_references=bundle.external_references)
    document["export_documents"] = ExportDocuments.from_export(other, source_export_sha256=export_sha).to_dict()
    (tmp_path / "binding.json").write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ExportEvaluationRefused, match="records export documents"):
        load_export_snapshot(path, tmp_path / "binding.json")


# -- the view inputs follow the served corpus and the derivation follows every input ------------------


def test_a_new_served_corpus_rebuilds_the_view_inputs_and_rechecks_the_record() -> None:
    increment = _increment()
    service, _binding_ = _service(increment)
    first = service._method_view()
    assert first.sources
    service._element_cache = [*first.elements, {"@id": "an-element-the-record-does-not-list", "@type": "Package"}]
    second = service._method_view()
    assert second.elements is not first.elements
    assert not second.sources and second.external_references is None


def test_the_derivation_is_bound_to_the_external_references_object_too() -> None:
    """Two views over one corpus with the same source documents object and different external-reference
    objects: the configurations given to the first are never the second's."""
    increment = _increment()
    b = increment.builder
    traversal, sources = _traversal(b), _sources(b)
    record = {"source_element_id": b.elements[0]["@id"], "property_path": "type", "target_id": "outside",
              "uri": "file:///outside.sysml"}
    first = ModelView(b.elements, traversal, sources=sources, external_references=(record,))
    second = ModelView(b.elements, traversal, sources=sources, external_references=(dict(record),))
    assert first.index is second.index and first.sources is second.sources
    _given(first, increment.projections)
    identifier = increment.scenario.increment_id
    assert _verdicts(evaluate_increment(first, identifier, revision=REVISION), CONFIGURED_BY) == {
        "configuredProduct": me.VERDICT_PASS}
    assert _verdicts(evaluate_increment(second, identifier, revision=REVISION), CONFIGURED_BY) != {
        "configuredProduct": me.VERDICT_PASS}


# -- method parity: the check the release evidence runs ------------------------------------------------


def test_method_parity_passes_when_the_api_answers_phase_9_and_next_as_the_export() -> None:
    increment = _increment()
    service, binding = _service(increment)
    _given(service._method_view(), increment.projections)
    export = _export_view(increment)
    _given(export, increment.projections)
    report = method_parity(service, export, _revision(binding))
    assert report["schema"] == PARITY_SCHEMA and report["passed"] is True
    (row,) = report["increments"]
    assert row["increment"] == increment.scenario.increment_id and row["phase9_equal"] and row["next_equal"]
    assert row["api_phase9"]["phase_exit"] == row["export_phase9"]["phase_exit"] == "READY"


def test_method_parity_fails_over_a_binding_without_the_record() -> None:
    increment = _increment()
    service, binding = _service(increment, record=False)
    export = _export_view(increment)
    _given(export, increment.projections)
    report = method_parity(service, export, _revision(binding))
    assert report["passed"] is False
    (row,) = report["increments"]
    assert row["phase9_equal"] is False
    assert (row["api_phase9"]["phase_exit"], row["export_phase9"]["phase_exit"]) == ("BLOCKED", "READY")


def _answer(*, exit_="READY", next_gate=None, withheld=(), marker="allocation-admission:allocatedTo"):
    """An evaluation's answers, as method parity reads them."""
    results = [SimpleNamespace(unit_id=gate, missing=(marker,)) for gate in withheld]
    return SimpleNamespace(
        status=lambda: {"phases": [{"phase": P9, "phase_exit": exit_, "conformance_verdict": "PASS",
                                    "evaluation_state": "COMPLETE"}]},
        next_obligation=lambda: {"next": None if next_gate is None else {"gate": next_gate, "stage": "s"}},
        canonical=SimpleNamespace(results=results))


@pytest.mark.parametrize("api,export,passed", [
    (_answer(), _answer(), True),
    (_answer(exit_="BLOCKED"), _answer(), False),
    (_answer(next_gate="b"), _answer(next_gate="a"), False),
    # The export's next is a gate the API binding withholds (the allocation-admission guard): next is not
    # compared.
    (_answer(next_gate="b", withheld=("a",)), _answer(next_gate="a"), True),
    # A withheld gate elsewhere changes nothing: the export's next is compared.
    (_answer(next_gate="b", withheld=("c",)), _answer(next_gate="a"), False),
    # A governed relation the method cannot read is not the admission guard: its marker excuses nothing, so
    # the export's next is compared and the differing answer fails.
    (_answer(next_gate="b", withheld=("a",), marker="governed-relation:derivesRequirementFromNeed"),
     _answer(next_gate="a"), False),
    # Neither is the reader's own allocation failure.
    (_answer(next_gate="b", withheld=("a",), marker="governed-relation:native-allocation"),
     _answer(next_gate="a"), False),
])
def test_method_parity_compares_next_unless_the_api_binding_withholds_the_export_s_next(api, export, passed):
    row = increment_parity("INC-EXAMPLE-001", api, export)
    assert row["passed"] is passed
