"""The ingestion gate on the traversal's target-less skip (review round 1 of #401, R4).

The successor traversal skips a typing or specialization relationship that names no target: the
licensed serializer omits every reference to an element outside the export, which is the standard
library, and records it in ``external_references``. That skip is sound only while every such
relationship really is a standard-library omission; the import step asserts it and fails closed
otherwise (scripts/import_sysml_api_baseline.py).
"""

from __future__ import annotations

import pytest

from de4sdv.semantic.trace_vocabulary_traversal import SuccessorTraversal, targetless_check

LIBRARY = "file:///opt/site-packages/_syside/sysml.library/Systems%20Library/Parts.sysml"
MODEL = "textual-notation-of-model/packages/features/aebs/aebs.sysml"


def _elements() -> list[dict]:
    """A part typed by a library definition (omitted), a definition specializing one (omitted),
    and a part typed by a definition in the export (named)."""
    return [
        {"@id": "part", "@type": "PartUsage", "ownedRelationship": [{"@id": "typing"}]},
        {"@id": "typing", "@type": "FeatureTyping", "typedFeature": {"@id": "part"},
         "owningRelatedElement": {"@id": "part"}, "isImplied": True},
        {"@id": "definition", "@type": "PartDefinition", "ownedRelationship": [{"@id": "subclassification"}]},
        {"@id": "subclassification", "@type": "Subclassification", "subclassifier": {"@id": "definition"},
         "specific": {"@id": "definition"}, "owningRelatedElement": {"@id": "definition"}},
        {"@id": "typed", "@type": "PartUsage", "ownedRelationship": [{"@id": "named-typing"}]},
        {"@id": "named-typing", "@type": "FeatureTyping", "typedFeature": {"@id": "typed"},
         "owningRelatedElement": {"@id": "typed"}, "type": {"@id": "definition"}},
    ]


def _rows(uri: str = LIBRARY) -> list[dict]:
    return [{"source_element_id": "typing", "property_path": "type", "target_id": "lib-1", "uri": uri},
            {"source_element_id": "typing", "property_path": "general", "target_id": "lib-1", "uri": uri},
            {"source_element_id": "subclassification", "property_path": "superclassifier", "target_id": "lib-2",
             "uri": uri},
            {"source_element_id": "subclassification", "property_path": "general", "target_id": "lib-2", "uri": uri}]


SOURCES = {identifier: MODEL for identifier in ("part", "typing", "definition", "subclassification", "typed",
                                                "named-typing")}


def test_the_gate_reads_exactly_the_relationships_the_traversal_skips() -> None:
    assert SuccessorTraversal.targetless_relationships(_elements()) == ["subclassification", "typing"]


def test_recorded_standard_library_omissions_pass() -> None:
    report = targetless_check(_elements(), _rows(), SOURCES)
    assert report["passed"] and report["violation_count"] == 0
    assert (report["targetless"], report["standard_library"]) == (2, 2)


def test_a_relative_uri_from_a_standard_library_source_stays_in_the_library() -> None:
    sources = dict(SOURCES, typing="@library/Systems Library/VerificationCases.sysml")
    rows = [dict(row, uri="../Kernel%20Libraries/Kernel%20Semantic%20Library/Base.kerml")
            if row["source_element_id"] == "typing" else row for row in _rows()]
    assert targetless_check(_elements(), rows, sources)["passed"]


@pytest.mark.parametrize("case, rows, sources, reason", [
    ("no row", [row for row in _rows() if row["source_element_id"] != "typing"], SOURCES,
     "no external reference records its target"),
    ("a row on no target key", [dict(row, property_path="featuringType") if row["source_element_id"] == "typing"
                                else row for row in _rows()], SOURCES, "no external reference records its target"),
    ("a model file", [dict(row, uri="file:///work/textual-notation-of-model/other.sysml")
                      if row["source_element_id"] == "typing" else row for row in _rows()], SOURCES,
     "its target is outside the standard library"),
    ("a relative uri from a model file", [dict(row, uri="../other.sysml") if row["source_element_id"] == "typing"
                                          else row for row in _rows()], SOURCES,
     "its target is outside the standard library"),
    ("a relative uri leaving the library", [dict(row, uri="../../outside.sysml")
                                            if row["source_element_id"] == "typing" else row for row in _rows()],
     dict(SOURCES, typing="@library/Systems Library/VerificationCases.sysml"),
     "its target is outside the standard library"),
    ("one row of two outside", [*_rows()[:1], dict(_rows()[1], uri="file:///work/model/x.sysml"), *_rows()[2:]],
     SOURCES, "its target is outside the standard library"),
], ids=lambda value: value if isinstance(value, str) else "")
def test_anything_else_is_a_violation(case, rows, sources, reason) -> None:
    report = targetless_check(_elements(), rows, sources)
    assert not report["passed"] and report["violation_count"] == 1, case
    (violation,) = report["violations"]
    assert violation["relationship"] == "typing" and violation["reason"] == reason
