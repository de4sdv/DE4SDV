"""Synthetic raw-reference regressions, not licensed model closure.

Connectors take the export's end shape (``edge`` in test_trace_vocabulary_traversal):
their ends are read with the method's reader, never from derived ``source``/``target``
keys, so the member checks below concern the witness itself and the typing and
specialization lineage of its ends. What the reader refuses at an end (an ambiguous,
implied-only or dangling reference, an unreadable chain) is pinned in
test_trace_vocabulary_traversal for the traversal and the method checks alike.
"""
from typing import Any

import pytest

from test_trace_vocabulary_traversal import edge, fixture_service
from test_trace_vocabulary_supplied_api import (
    extension_binding, http_service, supplied_synthetic_api,
)


MALFORMED_REFERENCES = [
    pytest.param({}, id="missing-id"),
    pytest.param({"@type": "ReferenceUsage"}, id="unidentified-object"),
    pytest.param({"@uri": "synthetic://missing-identity"}, id="uri-without-id"),
    pytest.param({"@id": ""}, id="empty-id"),
    pytest.param({"@id": " \t"}, id="blank-id"),
    pytest.param(None, id="null-member"),
    pytest.param("uninterpreted-reference", id="scalar-member"),
]


def candidate(predicate="allocatedTo"):
    service, elements, binding, contract = fixture_service()
    if predicate == "allocatedTo":
        relationship = next(e for e in elements if e["@id"] == "allocation")
        source = "use-Requirement"
    else:
        relationship, *ends = edge("ConnectionUsage", "use-Need", "use-ValidationScenario",
                                   name="planning", type=[{"@id": "root-hasValidationScenario"}])
        elements.extend([relationship, *ends])
        source = "use-Need"
    return service, elements, binding, contract, relationship, source


def assert_incomplete(report, predicate):
    assert report["semantic_status"] == "incomplete", report
    assert report["edges"] == [], report
    assert any(r["predicate"] == predicate and r["authority_state"] == "incomplete"
               for r in report["unsupported_predicates"]), report


def test_supplied_api_read_refuses_an_unreadable_planning_end():
    """Over the supplied HTTP API, a planning connection whose target end carries two authored
    references to different usages cannot be read: incomplete, never a hop or an absence."""
    _, elements, binding, _, relationship, source = candidate("hasValidationScenario")
    reference = next(e for e in elements if e["@id"] == "planning-target-reference")
    elements.append({**reference, "@id": "planning-target-second", "general": {"@id": "use-PhysicalElement"},
                     "subsettedFeature": {"@id": "use-PhysicalElement"},
                     "referencedFeature": {"@id": "use-PhysicalElement"}})
    next(e for e in elements if e["@id"] == "planning-target")["ownedRelationship"].append(
        {"@id": "planning-target-second"})
    with supplied_synthetic_api(elements) as (url, reads):
        report = http_service(extension_binding(binding), url).semantic_neighbors(
            source, predicates=["hasValidationScenario"])
        assert_incomplete(report, "hasValidationScenario")
        assert reads and all(method == "GET" for method, _ in reads)


@pytest.mark.parametrize("member", MALFORMED_REFERENCES)
@pytest.mark.parametrize("mode", [
    "endpoint-typing", "planning-typing", "allocation-typing",
    "endpoint-root-parent", "planning-root-parent", "unrelated-parent",
    "flat-parent", "owned-parent", "flat-typing", "flat-source",
])
def test_every_reachable_lineage_member_must_be_decidable(mode, member):
    predicate = "hasValidationScenario" if mode.startswith("planning") else "allocatedTo"
    service, elements, _, _, relationship, source = candidate(predicate)
    endpoint = next(e for e in elements if e["@id"] == "use-Function")
    if mode == "endpoint-typing":
        endpoint["type"].append(member)
    elif mode in {"planning-typing", "allocation-typing"}:
        relationship["type"] = [{"@id": "root-hasValidationScenario"}, member]
    elif mode == "endpoint-root-parent":
        next(e for e in elements if e["@id"] == "root-Function")["general"] = [member]
    elif mode == "planning-root-parent":
        next(e for e in elements if e["@id"] == "root-hasValidationScenario")["supertype"] = [member]
    elif mode == "unrelated-parent":
        endpoint["type"].append({"@id": "unrelated"})
        elements.append({"@id": "unrelated", "@type": "ActionDefinition", "superclassifier": [member]})
    elif mode in {"flat-parent", "owned-parent"}:
        parent = {"@id": "parent", "@type": "Subclassification",
                  "superclassifier": [{"@id": "external", "@uri": "synthetic://library/root"}, member]}
        if mode == "flat-parent":
            parent["subclassifier"] = {"@id": "root-Function"}
            elements.append(parent)
        else:
            next(e for e in elements if e["@id"] == "root-Function")["ownedRelationship"] = [parent]
    elif mode == "flat-typing":
        elements.append({"@id": "typing", "@type": "FeatureTyping",
                         "typedFeature": {"@id": "use-Function"},
                         "type": [{"@id": "root-Function"}, member]})
    else:
        elements.append({"@id": "typing", "@type": "FeatureTyping",
                         "typedFeature": [{"@id": "use-Function"}, member],
                         "type": {"@id": "root-Function"}})
    assert_incomplete(service.semantic_neighbors(source, predicates=[predicate]), predicate)


def test_identified_dangling_native_allocation_carrier_is_incomplete():
    service, _, _, _, relationship, source = candidate()
    relationship["type"] = [{"@id": "missing-allocation-definition"}]
    assert_incomplete(service.semantic_neighbors(source, predicates=["allocatedTo"]), "allocatedTo")


@pytest.mark.parametrize("shape", ["typing", "specialization"])
def test_unidentified_raw_relationship_witness_cannot_disappear_from_index(shape):
    service, elements, _, _, relationship, source = candidate()
    if shape == "typing":
        witness = {"@type": "FeatureTyping", "typedFeature": {"@id": "use-Function"},
                   "type": {"@id": "root-Function"}}
    else:
        witness = {"@type": "Subclassification", "subclassifier": {"@id": "root-Function"},
                   "superclassifier": {"@id": "external", "@uri": "synthetic://library/root"}}
    elements.append(witness)
    assert_incomplete(service.semantic_neighbors(source, predicates=["allocatedTo"]), "allocatedTo")


def test_flat_list_carrier_typing_cannot_hide_a_second_governed_meaning():
    service, elements, _, _, relationship, source = candidate("hasValidationScenario")
    next(e for e in elements if e["@id"] == "use-Need")["type"].append({"@id": "root-Requirement"})
    next(e for e in elements if e["@id"] == "use-ValidationScenario")["type"].append({"@id": "root-RegulatorySource"})
    elements.append({"@id": "carrier-typing", "@type": "FeatureTyping",
                     "typedFeature": {"@id": "planning"},
                     "type": [{"@id": "root-hasValidationScenario"}, {"@id": "root-hasRegulatorySource"}]})
    assert_incomplete(service.semantic_neighbors(source, predicates=["hasValidationScenario"]), "hasValidationScenario")


@pytest.mark.parametrize("location", ["endpoint", "carrier", "root"])
def test_equivalent_external_targets_coalesce_only_after_identity_validation(location):
    service, elements, _, _, relationship, source = candidate("hasValidationScenario")
    node = relationship if location == "carrier" else next(
        e for e in elements if e["@id"] == ("use-ValidationScenario" if location == "endpoint"
                                           else "root-hasValidationScenario"))
    key = "general" if location == "root" else "type"
    node.setdefault(key, []).extend([
        {"@id": "external"}, {"@id": "external", "@uri": "synthetic://library/root"}])
    report = service.semantic_neighbors(source, predicates=["hasValidationScenario"])
    assert report["semantic_status"] == "complete", report
    assert report["edges"][0]["api_object_id"] == "planning"


@pytest.mark.parametrize("identifier", [None, "", " \t"])
def test_native_carrier_witness_requires_a_nonblank_identity(identifier):
    service, _, _, _, relationship, source = candidate()
    if identifier is None:
        relationship.pop("@id")
    else:
        relationship["@id"] = identifier
    assert_incomplete(service.semantic_neighbors(source, predicates=["allocatedTo"]), "allocatedTo")


def test_equivalent_native_end_references_are_one_reference():
    """Two authored references of one end that name the same usage are one end, not an ambiguity."""
    service, elements, _, _, relationship, source = candidate()
    for role in ("source", "target"):
        reference = next(e for e in elements if e["@id"] == f"allocation-{role}-reference")
        elements.append({**reference, "@id": f"allocation-{role}-again"})
        next(e for e in elements if e["@id"] == f"allocation-{role}")["ownedRelationship"].append(
            {"@id": f"allocation-{role}-again"})
    report = service.semantic_neighbors(source, predicates=["allocatedTo"])
    assert report["semantic_status"] == "complete", report
    assert report["edges"][0]["api_object_id"] == "allocation"
