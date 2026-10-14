"""What to author, over the frozen genuine-export cut: real serializer shapes, the real workflow.

The cut is evaluated as ``scripts/evaluate_increment.py`` evaluates an export
(kernel identity validated from the export). Two increments: INC-AEBS-010,
which the cut declares, and a new one it does not (INC-EXAMPLE-001, as in the
throwaway-increment test's first call, when nothing is authored yet).

The oracles are not the code under test:

- the package that declares a type is read from the cut's own records: the
  source document the serializer recorded for the type, and the one package
  the cut records from that document;
- where the checkout still holds that document unchanged (the sha256 the cut
  records for it), the document's text is read too, lexically: it declares
  that package and the type;
- the accepted forms and the qualified-name resolution of
  ``test_remedies.py``.

No value is pinned here: a re-cut needs no edit of this file.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path

import pytest

from de4sdv.semantic.export_evaluation import evaluate_export
from de4sdv.sysml_api.qualified_names import QualifiedNameIndex
from increment_model_fixtures import GENUINE_EXPORT
from sysml_shapes import REPO_ROOT, strip_comments
from test_remedies import _problems, _remedied

NEW = "INC-EXAMPLE-001"
PLACEHOLDERS = ("<IncrementDefinition>", "<role>", "<Viewpoint>", "<Definition>", "MethodPhase::...")


@pytest.fixture(scope="module")
def cut(tmp_path_factory: pytest.TempPathFactory):
    path = tmp_path_factory.mktemp("genuine-export") / "export.json"
    raw = gzip.decompress(GENUINE_EXPORT.read_bytes())
    path.write_bytes(raw)
    return path, json.loads(raw)


@pytest.fixture(scope="module")
def answers(cut):
    path, _export = cut
    _snapshot, declared = evaluate_export(path, "INC-AEBS-010")
    _snapshot, new = evaluate_export(path, NEW)
    return {"contract": declared.phase_contract(), "gaps": declared.gaps(), "new": new.gaps(),
            "new_next": new.next_obligation()}


def _declaring_package(export: dict, element_id: str) -> str:
    """The package the source document of an element declares, from the cut's own records."""
    sources = export["element_sources"]
    document = sources[element_id]
    packages = [e for e in export["elements"] if e.get("@type") in ("Package", "LibraryPackage")
                and sources.get(e["@id"]) == document]
    assert len(packages) == 1, (document, [p.get("declaredName") for p in packages])
    return packages[0]["declaredName"]


def _typed_records(answers) -> list[tuple[str, dict]]:
    return [(name, record) for name in ("contract", "gaps", "new") for record in _remedied(answers[name])]


def test_every_remedy_of_the_cut_s_workflow_is_authorable_sysml(cut, answers) -> None:
    """Every check the cut's workflow declares (phase_contract), every gap of INC-AEBS-010 and every
    remedy of a new increment: accepted forms, qualified names that resolve, their imports, no type
    placeholder, no construct that is not SysML."""
    _path, export = cut
    names = QualifiedNameIndex(export["elements"])
    own = "DE4SDV_AEBSVisualizationFraming"  # INC-AEBS-010's framing package, which no remedy imports
    gates = {gate["obligation_id"] for gate in answers["contract"]["gates"]}
    assert len(gates) >= 20
    problems = {}
    for name, record in _typed_records(answers):
        found = _problems(record, names, own if name != "new" else None)
        if found:
            problems[(name, record.get("gate") or record.get("obligation_id"))] = found
    assert problems == {}


def test_a_new_increment_is_told_what_to_author_without_a_type_placeholder(answers) -> None:
    """The throwaway-increment test's first call, on real data: every phase-0 and later remedy names
    types, never a type placeholder."""
    texts = [record["what_to_author"] for record in _remedied(answers["new"])]
    assert len(texts) >= 20
    assert {placeholder: [t for t in texts if placeholder in t] for placeholder in PLACEHOLDERS} == {
        placeholder: [] for placeholder in PLACEHOLDERS}
    step = answers["new_next"]["next"]
    assert step["gate"] == "incrementHasIdentifier" and step["authoring"]["imports"]


def test_each_type_a_remedy_names_is_qualified_by_the_package_its_source_declares(cut, answers) -> None:
    """The qualified name and the import of each named type agree with the package the type's source
    document declares (the cut's records)."""
    _path, export = cut
    checked = 0
    for _name, record in _typed_records(answers):
        authoring = record["authoring"]
        for named in authoring["types"]:
            if not named.get("qualified_name"):
                continue
            package = _declaring_package(export, named["element_id"])
            assert named["qualified_name"] == f"{package}::{named['name']}", named
            if package != "DE4SDV_AEBSVisualizationFraming":
                assert f"private import {package}::*;" in authoring["imports"], (named, authoring["imports"])
            checked += 1
    assert checked >= 20


def test_where_the_checkout_holds_a_type_s_document_unchanged_its_text_declares_the_package(cut, answers) -> None:
    """The lexical oracle: a source document the checkout still holds byte for byte (the sha256 the cut
    records) declares the package a remedy imports, and the type the remedy names in it."""
    _path, export = cut
    recorded = {entry["path"]: entry["sha256"] for entry in export["source_manifest"]}
    sources = export["element_sources"]
    pairs = {(sources[named["element_id"]], named["qualified_name"]) for _n, record in _typed_records(answers)
             for named in record["authoring"]["types"] if named.get("qualified_name")}
    unchanged = {}
    for document, qualified in sorted(pairs):
        path = REPO_ROOT / document
        if document in recorded and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == recorded[document]:
            unchanged.setdefault(document, []).append(qualified)
    if not unchanged:
        pytest.skip("no source document of a named type is unchanged since the cut; the record oracle above holds")
    for document, qualifieds in unchanged.items():
        text = strip_comments((REPO_ROOT / document).read_text(encoding="utf-8"))
        for qualified in qualifieds:
            package, _sep, name = qualified.rpartition("::")
            assert re.search(rf"\bpackage\s+{re.escape(package)}\s*\{{", text), (document, package)
            assert re.search(rf"\bdef\s+{re.escape(name)}\b", text), (document, name)
