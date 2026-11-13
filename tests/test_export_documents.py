"""The export documents a revision binding records: the source documents and external references of the export.

The API listing carries neither. The importer records both in the revision binding (``export_documents``),
from the export that the served-model record names, after the full-payload read-back. An evaluation over
the API then reads the export's own documents, never files at the server's checkout. The record is
lossless: it decodes to exactly the export's element sources and external references, in the export's
order. Its digest covers the schema, the export it names, the element count and those decoded values,
computed the same way for an export, so a record equals an export's documents exactly when the digests
agree. Any change to it is refused, an edited label or an unused URI included.
"""
from __future__ import annotations

import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from de4sdv.sysml_api.baseline import build_export_bundle
from de4sdv.sysml_api.export_documents import EXPORT_DOCUMENTS_SCHEMA, ExportDocuments, documents_digest
from de4sdv.sysml_api.revisions import RevisionBinding
from de4sdv.sysml_api.served_model import ServedModel
from tests.model_contract_fixtures import binding_dict

EXPORT_SHA = "e" * 64
LIBRARY = "file:///opt/site-packages/_syside/sysml.library/Kernel%20Libraries/ScalarValues.kerml"
PARTS = "file:///opt/site-packages/_syside/sysml.library/Systems%20Library/Parts.sysml"


def _bundle():
    """Two documents; three references to elements outside the export, two of one library document."""
    return build_export_bundle(git_commit="b" * 40, source_documents={
        "model/b.sysml": [
            {"@id": "pkg-b", "@type": "Package", "ownedRelationship": [{"@id": "import"}]},
            {"@id": "import", "@type": "NamespaceImport",
             "importedNamespace": {"@id": "scalar-values", "@uri": LIBRARY}},
        ],
        "model/a.sysml": [
            {"@id": "pkg-a", "@type": "Package", "ownedRelationship": [{"@id": "typing"}]},
            {"@id": "typing", "@type": "FeatureTyping", "typedFeature": {"@id": "pkg-a"},
             "type": {"@id": "part", "@uri": PARTS}},
            {"@id": "subset", "@type": "Subsetting",
             "subsettedFeature": [{"@id": "parts", "@uri": PARTS}, {"@id": "pkg-a"}]},
        ],
    })


def _record():
    return ExportDocuments.from_export(_bundle(), source_export_sha256=EXPORT_SHA)


def test_the_record_decodes_to_the_exports_own_documents_in_the_exports_order() -> None:
    bundle = _bundle()
    record = ExportDocuments.from_dict(json.loads(json.dumps(_record().to_dict())))
    assert dict(record.element_sources) == bundle.element_sources
    assert [dict(item) for item in record.external_references] == list(bundle.external_references)
    assert record.content_sha256 == documents_digest(bundle.element_sources, bundle.external_references,
                                                     source_export_sha256=EXPORT_SHA)
    assert record.source_export_sha256 == EXPORT_SHA and record.element_count == len(bundle.elements)
    assert record == _record()


def test_the_serialized_record_names_each_element_once_and_each_uri_once() -> None:
    value = _record().to_dict()
    assert value["schema"] == EXPORT_DOCUMENTS_SCHEMA
    assert value["documents"] == {"model/a.sysml": ["pkg-a", "subset", "typing"],
                                  "model/b.sysml": ["import", "pkg-b"]}
    assert value["external_reference_uris"] == sorted({LIBRARY, PARTS})
    assert [row[:3] for row in value["external_references"]] == [
        ["import", "importedNamespace", "scalar-values"], ["typing", "type", "part"],
        ["subset", "subsettedFeature[0]", "parts"]]


def test_the_digest_is_the_same_for_an_export_and_its_record_and_moves_with_any_value() -> None:
    bundle = _bundle()

    def digest(sources=bundle.element_sources, references=bundle.external_references, export=EXPORT_SHA):
        return documents_digest(sources, references, source_export_sha256=export)

    assert digest() == _record().content_sha256
    assert digest(sources={**bundle.element_sources, "typing": "model/b.sysml"}) != digest()
    assert digest(references=list(reversed(bundle.external_references))) != digest()
    assert digest(export="f" * 64) != digest()  # the export it names
    assert digest(sources={k: v for k, v in bundle.element_sources.items() if k != "pkg-b"}) != digest()
    assert digest(sources=dict(reversed(list(bundle.element_sources.items())))) == digest()


def _mutated(mutate):
    value = copy.deepcopy(_record().to_dict())
    mutate(value)
    return value


@pytest.mark.parametrize("mutate", [
    lambda v: v["documents"]["model/b.sysml"].append(v["documents"]["model/a.sysml"].pop()),  # moved element
    lambda v: v["documents"]["model/a.sysml"].append("pkg-b"),          # one element in two documents
    lambda v: v["documents"]["model/a.sysml"].append("pkg-a"),          # one element twice
    lambda v: v["external_references"].pop(),                            # a dropped reference
    lambda v: v["external_references"].reverse(),                        # another order
    lambda v: v["external_references"][0].__setitem__(2, "other"),      # another target
    lambda v: v["external_references"][0].__setitem__(3, 1 - v["external_references"][0][3]),  # another uri
    lambda v: v["external_references"][0].__setitem__(3, 7),            # no such uri
    lambda v: v["external_references"][0].__setitem__(3, True),         # not an index
    lambda v: v["external_references"][1].__setitem__(3, True),         # not an index, though True == 1 here
    lambda v: v["external_references"][0].append("extra"),              # another row shape
    lambda v: v["external_reference_uris"].append(LIBRARY),             # a uri twice
    lambda v: v["external_reference_uris"].append("file:///unused.sysml"),  # a uri no reference uses
    lambda v: v.__setitem__("source_export_sha256", "f" * 64),          # another export, label edited only
    lambda v: v.__setitem__("element_count", 4),                        # another count
    lambda v: v.__setitem__("content_sha256", "sha256:" + "0" * 64),    # another digest
    lambda v: v.__setitem__("source_export_sha256", "E" * 64),          # not a digest
    lambda v: v.__setitem__("schema", "de4sdv.export-documents/v0"),
    lambda v: v.__setitem__("extra", True),
    lambda v: v.pop("documents"),
    lambda v: v.__setitem__("documents", {}),
])
def test_a_changed_record_is_refused(mutate) -> None:
    with pytest.raises(ValueError):
        ExportDocuments.from_dict(_mutated(mutate))


def test_an_external_reference_the_record_cannot_carry_exactly_is_refused() -> None:
    bundle = _bundle()
    widened = SimpleNamespace(element_sources=bundle.element_sources, external_references=(
        {**bundle.external_references[0], "note": "not an exporter field"},))
    with pytest.raises(ValueError, match="external reference"):
        ExportDocuments.from_export(widened, source_export_sha256=EXPORT_SHA)


def test_the_record_covers_exactly_the_corpus_it_was_recorded_for() -> None:
    record = _record()
    corpus = [{"@id": identifier, "@type": "Element"} for identifier in _bundle().element_sources]
    assert record.problem_for(corpus) is None
    assert "1 served element(s) without a recorded document" in record.problem_for(
        [*corpus, {"@id": "new", "@type": "Element"}])
    assert "1 recorded element(s) not served" in record.problem_for(corpus[1:])


# -- the revision binding ---------------------------------------------------------------------------


def _served(count: int = 5) -> dict:
    return ServedModel.from_dict({"schema": "de4sdv.served-model/v1", "source_export_sha256": EXPORT_SHA,
                                  "element_count": count, "content_sha256": "sha256:" + "c" * 64}).to_dict()


def test_a_binding_carries_the_record_and_round_trips() -> None:
    document = binding_dict(served_model=_served(), export_documents=_record().to_dict())
    binding = RevisionBinding.from_dict(json.loads(json.dumps(document)))
    assert binding.export_documents == _record()
    assert RevisionBinding.from_dict(json.loads(json.dumps(binding.to_dict()))).to_dict() == binding.to_dict()
    assert binding.to_dict()["export_documents"] == _record().to_dict()


def test_a_binding_without_the_record_still_loads_and_writes_none() -> None:
    binding = RevisionBinding.from_dict(binding_dict(served_model=_served()))
    assert binding.export_documents is None
    assert "export_documents" not in binding.to_dict()


@pytest.mark.parametrize("served", [
    {**_served(), "source_export_sha256": "f" * 64},  # another export
    _served(count=6),                                   # another element count
    None,                                               # no served model to bind it to
])
def test_a_binding_whose_record_names_another_export_is_refused(served) -> None:
    document = binding_dict(export_documents=_record().to_dict())
    if served is not None:
        document["served_model"] = served
    with pytest.raises(ValueError, match="export_documents"):
        RevisionBinding.from_dict(document)


# -- the importer -----------------------------------------------------------------------------------


def _run_import(tmp_path, monkeypatch, *, readback_ids, imported_count=None, main=False):
    from scripts import import_sysml_api_baseline as importer
    from de4sdv.sysml_api.ingestion import BaselineImportResult

    head = "b" * 40
    bundle = _bundle()
    bundle = SimpleNamespace(git_commit=head, elements=bundle.elements, element_sources=bundle.element_sources,
                             source_manifest=[], external_references=list(bundle.external_references),
                             require_current_sources=lambda manifest: None)
    export_path = tmp_path / "export.json"
    export_path.write_bytes(b'{"synthetic": "export bytes"}')
    readback = [{"@id": identifier, "@type": "Element"} for identifier in readback_ids]
    passing = SimpleNamespace(passed=True, summary={"unresolved": 0}, entries=[],
                              to_dict=lambda: {"passed": True})
    monkeypatch.setattr(importer, "_git_head", lambda: head)
    monkeypatch.setattr(importer.BaselineExportBundle, "load", staticmethod(lambda path: bundle))
    monkeypatch.setattr(importer.BaselineManifest, "discover", staticmethod(lambda root: None))
    count = len(readback) if imported_count is None else imported_count
    monkeypatch.setattr(importer, "import_baseline", lambda client, b, project_name: BaselineImportResult(
        project_id="p-1", commit_id="c-1", element_count=count, internal_reference_count=1,
        content_sha256="sha256:" + "c" * 64))
    monkeypatch.setattr(importer.SysMLRepository, "list_elements", lambda self, p, c: readback)
    monkeypatch.setattr(importer, "validate_ontology_bindings", lambda *a, **k: passing)
    monkeypatch.setattr(importer, "cross_check_model_provider", lambda *a, **k: {"classification": "EQUIVALENT"})
    monkeypatch.setattr(importer, "targetless_check", lambda *a, **k: {"passed": True})
    if main:
        monkeypatch.setattr("sys.argv", ["import_sysml_api_baseline.py", "--api-url", "http://api.invalid",
                                         "--export", str(export_path), "--binding", str(tmp_path / "binding.json"),
                                         "--report", str(tmp_path / "report.json"), "--project-name", "t"])
        assert importer.main() == 0
    else:
        importer.run_import(api_url="http://api.invalid", export_path=export_path,
                            binding_path=tmp_path / "binding.json", report_path=tmp_path / "report.json",
                            project_name="t", git_repository="de4sdv/DE4SDV")
    return hashlib.sha256(export_path.read_bytes()).hexdigest()


def test_the_importer_records_the_export_documents_in_the_binding_and_the_report(tmp_path, monkeypatch) -> None:
    bundle = _bundle()
    export_sha = _run_import(tmp_path, monkeypatch, readback_ids=list(bundle.element_sources))
    binding = RevisionBinding.load(tmp_path / "binding.json")
    record = binding.export_documents
    assert record is not None and record.source_export_sha256 == export_sha
    assert dict(record.element_sources) == bundle.element_sources
    assert [dict(item) for item in record.external_references] == list(bundle.external_references)
    assert binding.served_model is not None and binding.served_model.source_export_sha256 == export_sha
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["export_documents"] == {
        "content_sha256": record.content_sha256, "document_count": 2, "element_count": 5,
        "external_reference_count": 3}


def test_the_importer_writes_no_binding_when_the_read_back_is_not_the_recorded_corpus(
        tmp_path, monkeypatch) -> None:
    with pytest.raises(RuntimeError, match="export documents"):
        _run_import(tmp_path, monkeypatch, readback_ids=["pkg-a", "typing", "subset", "import", "other"])
    assert not (tmp_path / "binding.json").exists()


def test_the_importer_writes_no_binding_that_would_not_load(tmp_path, monkeypatch) -> None:
    """The import reports another element count than the record lists: the binding would be refused when it
    loads, so the importer refuses to write it."""
    with pytest.raises(RuntimeError, match="the revision binding does not load"):
        _run_import(tmp_path, monkeypatch, readback_ids=list(_bundle().element_sources), imported_count=6)
    assert not (tmp_path / "binding.json").exists()


def test_the_importer_prints_a_summary_and_not_the_binding(tmp_path, monkeypatch, capsys) -> None:
    _run_import(tmp_path, monkeypatch, readback_ids=list(_bundle().element_sources), main=True)
    printed = capsys.readouterr().out
    summary = json.loads(printed)
    binding_bytes = (tmp_path / "binding.json").read_bytes()
    assert summary["binding_sha256"] == "sha256:" + hashlib.sha256(binding_bytes).hexdigest()
    record = RevisionBinding.load(tmp_path / "binding.json").export_documents
    assert summary["export_documents"] == record.summary()
    assert summary["served_model"]["element_count"] == 5
    # No record content: neither the per-document id lists nor any element id.
    assert '"documents"' not in printed and "pkg-a" not in printed and "kernel_bindings" not in summary
