"""The successor traversal reads native connector ends with the method's reader (genuine export).

``semantic_neighbors``, ``trace`` and ``impact`` (and the MCP tools over them)
answer ``allocatedTo`` and ``hasValidationScenario`` through the successor
traversal. The method checks read the same connectors through
``relation_checks``: ``allocation_ends`` for native allocations (an end written
as a feature chain reads as its last chaining feature) and ``connection_ends``
for typed connections. These tests run the traversal over the frozen
genuine-export cut (``fixtures/genuine_export``, real serializer shapes: no
top-level ``source``, no owner key, chained ends, implied relationships whose
library targets the export omits) in the two ways it is built: over the export
alone (the PR Method Check) and through the production service assembly over a
revision binding (the MCP path, offline). Parity: both find the same
``(source, target, end pair, witness)`` facts.
"""

from __future__ import annotations

import asyncio
import gzip

import mcp.client.stdio  # noqa: F401 - keep session-global stderr for later MCP tests
import pytest

from de4sdv.semantic import relation_checks as rc
from de4sdv.semantic.export_evaluation import export_view, load_export_snapshot
from de4sdv.semantic.increment_scope import ModelView
from de4sdv.semantic.mcp_server import create_mcp_server
from de4sdv.sysml_api.revisions import RevisionBinding
from increment_model_fixtures import GENUINE_EXPORT
from model_contract_fixtures import binding_dict, model_service

ALLOCATED_TO, VALIDATION, VALIDATION_INVERSE = "allocatedTo", "hasValidationScenario", "validationScenarioFor"
REQUIREMENT = "DE4SDV_AEBSVisualizationNeedsRequirements::VisualizationRequirements::reqRealAAOSRendering"
FUNCTION = "DE4SDV_AEBSVisualizationFunctionalArchitecture::AebsVisualizationFunctionalFlow::present"
LOGICAL = "DE4SDV_AEBSVisualizationLogicalArchitecture::AEBSVisualizationLogicalInstrument::application"
PHYSICAL = "DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::AEBSVisualizationInstrumentRealization::iviGuest::displayApp"
#: The allocations of that chain: a direct requirement-to-function allocation, then two with feature-chain ends.
CHAIN = ("DE4SDV_AEBSVisualizationFunctionalArchitecture::realAaosRenderingAllocation",
         "DE4SDV_AEBSVisualizationLogicalArchitecture::presentByApplication",
         "DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::applicationAllocated")


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory):
    path = tmp_path_factory.mktemp("genuine-export") / "export.json"
    path.write_bytes(gzip.decompress(GENUINE_EXPORT.read_bytes()))
    return load_export_snapshot(path)


@pytest.fixture(scope="module")
def view(snapshot) -> ModelView:
    """The export snapshot view: the PR Method Check's traversal over the export alone."""
    return export_view(snapshot)


def _service(snapshot):
    """The production service assembly over a revision binding that carries the export's validated
    kernel bindings; only the API transport is replaced."""
    elements = snapshot.elements

    class Repository:
        def list_elements(self, *args):
            return elements

    document = binding_dict(git_commit=snapshot.revision.git_commit, kernel_bindings=[
        dict(ontology_class=b.ontology_class, element_id=b.element_id, source_file=b.source_file,
             declaration=b.declaration) for b in snapshot.kernel_bindings])
    return model_service(RevisionBinding.from_dict(document), Repository())


def _connectors(view: ModelView, relation: str) -> dict[str, tuple[tuple[str, ...], str]]:
    """The connectors the method reads for ``relation``: every native allocation, or the connections
    typed by the relation's carrier."""
    if relation == ALLOCATED_TO:
        return dict(rc.allocation_ends(view))
    carriers = view.traversal.class_lineage(relation, view.elements)["explicit_lineage_ids"]
    return {c: ends for c, ends in rc.connection_ends(view).items() if view.index.typed_by(c) & carriers}


def _end_pair(view: ModelView, relation: str, source: str, target: str) -> str:
    rows = (rc.allocation_pairs(view, relation, source, target) if relation == ALLOCATED_TO
            else view.contract.profile["relations"][relation])
    (row,) = rows
    return str(row["carrier"])


def method_facts(view: ModelView, relation: str) -> set[tuple[str, str, str, str]]:
    """(source, target, end pair, witness) the method's relation check finds from every connector end."""
    subjects = {end for ends, _problem in _connectors(view, relation).values() for end in ends}
    found = set()
    for subject in subjects:
        result = rc.check_relation(view, relation, subject)
        assert not result.problem, result
        found |= {(subject, target, _end_pair(view, relation, subject, target), witness)
                  for target, witness in result.hops}
    return found


def traversal_facts(traversal, view: ModelView, relation: str, predicate: str | None = None
                    ) -> set[tuple[str, str, str, str]]:
    """(source, target, end pair, witness) the successor traversal returns from every connector end."""
    subjects = {end for ends, _problem in _connectors(view, relation).values() for end in ends}
    traversal.unsupported = []
    found = {(hop.source["@id"], hop.target["@id"], hop.witness["carrier"], hop.api_object["@id"])
             for subject in subjects
             for hop in traversal.traverse(predicate or relation, view.element(subject), view.elements)}
    assert traversal.unsupported == []
    return found


def test_the_cut_holds_the_native_shapes_the_traversal_must_read(view) -> None:
    """No exported allocation carries a top-level source or an owner key, 17 of the 27 have an end
    written as a feature chain, and the validation planning connections carry no source either."""
    allocations = [view.element(a) for a in rc.allocation_ends(view)]
    assert len(allocations) == 27
    assert not any(a.get(key) for a in allocations for key in ("source", "owningNamespace", "owner"))
    chained = [a for a, (ends, _p) in rc.allocation_ends(view).items()
               if any(view.index.owned_relationships(feature, "FeatureChaining")
                      for record in view.traversal._connection_end_records(view.element(a), view.index.by_id,
                                                                           view.index.graph)
                      for feature in [view.traversal._connected_usage_id(record["end_element_id"],
                                                                         view.index.graph, view.index.by_id)[0]])]
    assert len(chained) == 17
    assert not any(view.element(c).get("source") for c in _connectors(view, VALIDATION))


def test_allocated_to_parity_between_the_method_reader_and_the_successor_traversal(view) -> None:
    """Every allocation the method finds is the fact the traversal returns, end pair included: ten
    requirement-to-function, eight function-to-logical and nine logical-to-physical allocations."""
    method = method_facts(view, ALLOCATED_TO)
    assert sorted(pair for _s, _t, pair, _w in method) == (
        ["FunctionLogicalAssignment"] * 8 + ["LogicalPhysicalAssignment"] * 9
        + ["RequirementFunctionAssignment"] * 10)
    assert {witness for *_rest, witness in method} == set(rc.allocation_ends(view))
    assert traversal_facts(view.traversal, view, ALLOCATED_TO) == method


def test_has_validation_scenario_parity_between_the_method_reader_and_the_successor_traversal(view) -> None:
    """The five ValidationPlanningAssociation connections, forward and through the inverse navigation."""
    method = method_facts(view, VALIDATION)
    assert len(method) == 5
    assert {witness for *_rest, witness in method} == set(_connectors(view, VALIDATION))
    assert traversal_facts(view.traversal, view, VALIDATION) == method
    inverse = traversal_facts(view.traversal, view, VALIDATION, VALIDATION_INVERSE)
    assert inverse == {(target, source, pair, witness) for source, target, pair, witness in method}


def test_the_production_assembly_finds_the_same_facts_over_a_revision_binding(snapshot, view) -> None:
    """The MCP path's traversal (the production service assembly, routed through the revision
    binding's kernel bindings) returns what the export snapshot's traversal and the method find."""
    service = _service(snapshot)
    elements = service._elements()
    api_view = ModelView(elements, service.traversal)
    for relation in (ALLOCATED_TO, VALIDATION):
        assert traversal_facts(service.traversal, api_view, relation) == method_facts(view, relation)


def test_the_mcp_tools_answer_allocated_to_and_trace_the_allocation_chain(snapshot, view) -> None:
    """semantic_neighbors, trace and impact through the MCP tool functions, and the requirement impact
    the privileged run reads, over the revision binding: a requirement is allocated to a function, the
    function to a logical element and that to a physical element (two of the three with chained ends)."""
    service = _service(snapshot)
    server = create_mcp_server(service)

    def call(tool: str, **arguments):
        return asyncio.run(server._tool_manager.call_tool(tool, arguments))

    ids = {name: _resolve(view, name) for name in (REQUIREMENT, FUNCTION, LOGICAL, PHYSICAL)}
    witnesses = [_resolve(view, name) for name in CHAIN]
    chain = [(ids[REQUIREMENT], ids[FUNCTION], witnesses[0]), (ids[FUNCTION], ids[LOGICAL], witnesses[1]),
             (ids[LOGICAL], ids[PHYSICAL], witnesses[2])]
    neighbors = call("semantic_neighbors", identifier=REQUIREMENT, predicates=[ALLOCATED_TO])
    assert neighbors["semantic_status"] == "complete", neighbors["unsupported_predicates"]
    assert [(e["source"], e["target"], e["api_object_id"], e["witness"]["carrier"]) for e in neighbors["edges"]] == [
        (*chain[0], "RequirementFunctionAssignment")]
    trace = call("trace", source_identifier=REQUIREMENT, target_identifier=PHYSICAL, max_depth=3)
    assert [(step["predicate"], step["source"], step["target"], step["api_object_id"]) for step in trace["path"]] == [
        (ALLOCATED_TO, *hop) for hop in chain]
    reachable = call("impact", identifier=REQUIREMENT)
    assert reachable["semantic_status"] == "complete", reachable["unsupported_predicates"]
    assert set(chain) <= {(e["source"], e["target"], e["api_object_id"]) for e in reachable["edges"]
                          if e["predicate"] == ALLOCATED_TO}
    impact = service.impact_service.impact(ids[REQUIREMENT], git_revision=snapshot.revision.git_commit)
    assert [(e["target"], e["api_object_id"]) for e in impact["edges"] if e["predicate"] == ALLOCATED_TO] == [
        chain[0][1:]]
    assert "architecture" not in {gap["category"] for gap in impact["gaps"]}


def _resolve(view: ModelView, qualified_name: str) -> str:
    (found,) = [element for element in view.index.by_id if view.qualified_name(element) == qualified_name]
    return found


def test_a_broken_shared_reader_breaks_the_method_checks_and_the_traversal_alike(snapshot, monkeypatch) -> None:
    """Plant a defect in the shared reader (a feature chain no longer reads as its last chaining
    feature): the method checks and the traversal lose the same seventeen chained allocations, and
    still agree, because both read the ends through it."""
    monkeypatch.setattr(rc, "chained_feature", lambda view, feature: feature)
    traversal = export_view(snapshot).traversal
    broken = ModelView(list(snapshot.elements), traversal)  # a fresh corpus: nothing read before the plant
    method = method_facts(broken, ALLOCATED_TO)
    assert sorted(pair for _s, _t, pair, _w in method) == ["RequirementFunctionAssignment"] * 10
    assert traversal_facts(traversal, broken, ALLOCATED_TO) == method
