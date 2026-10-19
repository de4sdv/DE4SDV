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
import copy
import gzip
import json

import mcp.client.stdio  # noqa: F401 - keep session-global stderr for later MCP tests
import pytest

from de4sdv.semantic import relation_checks as rc
from de4sdv.semantic import successor_parity as sp
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


def _service(snapshot, elements=None):
    """The production service assembly over a revision binding that carries the export's validated
    kernel bindings; only the API transport is replaced (it serves ``elements``, by default the cut)."""
    elements = snapshot.elements if elements is None else elements

    class Repository:
        def list_elements(self, *args):
            return elements

    document = binding_dict(git_commit=snapshot.revision.git_commit, kernel_bindings=[
        dict(ontology_class=b.ontology_class, element_id=b.element_id, source_file=b.source_file,
             declaration=b.declaration) for b in snapshot.kernel_bindings])
    return model_service(RevisionBinding.from_dict(document), Repository())


def method_facts(view: ModelView, relation: str) -> frozenset[sp.Fact]:
    """(source, target, end pair, witness) the method's relation check finds from every connector end."""
    facts, problems = sp.method_facts(view, relation)
    assert problems == (), problems
    return facts


def traversal_facts(traversal, view: ModelView, relation: str, predicate: str | None = None
                    ) -> frozenset[sp.Fact]:
    """(source, target, end pair, witness) the successor traversal returns from every connector end."""
    facts, incomplete = sp.traversal_facts(traversal, view, relation, predicate)
    assert incomplete == (), incomplete
    return facts


def _connectors(view: ModelView, relation: str) -> dict[str, tuple[tuple[str, ...], str]]:
    return sp.connectors(view, relation)


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


# The cut's facts by qualified name (review round 1, R7): the parity compares two readings by one
# reader, so a reader change that moves both alike passes it; these pins do not.
F = "DE4SDV_AEBSVisualizationFunctionalArchitecture::"
L = "DE4SDV_AEBSVisualizationLogicalArchitecture::"
P = "DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::"
N = "DE4SDV_AEBSVisualizationNeedsRequirements::"
FF = F + "AebsVisualizationFunctionalFlow::"
LI, LS = L + "AEBSVisualizationLogicalInstrument::", L + "AEBSVisualizationLogicalSystem::"
PI, PS = P + "AEBSVisualizationInstrumentRealization::", P + "AEBSVisualizationPhysicalSystem::"
NR, NN = N + "VisualizationRequirements::", N + "VisualizationNeeds::"
RF, FL, LP, VP = ("RequirementFunctionAssignment", "FunctionLogicalAssignment", "LogicalPhysicalAssignment",
                  "ValidationPlanningAssociation")
PINNED_ALLOCATIONS = {
    (FF + "assemble", LI + "sourceAdapter", FL, L + "assembleByAdapter"),
    (FF + "observe", LI + "sourceAdapter", FL, L + "observeBySources"),
    (FF + "present", LI + "application", FL, L + "presentByApplication"),
    (FF + "publish", LI + "ingress", FL, L + "publishByIngress"),
    (FF + "record", LI + "evidence", FL, L + "recordByEvidence"),
    (FF + "supervise", LI + "healthSupervisor", FL, L + "superviseByHealth"),
    (FF + "transport", LI + "transport", FL, L + "transportByTransport"),
    (FF + "validate", LI + "sourceAdapter", FL, L + "validateByAdapter"),
    (LI + "application", PI + "iviGuest::displayApp", LP, P + "applicationAllocated"),
    (LI + "displayService", PI + "iviGuest::dataTunnel", LP, P + "serviceAllocated"),
    (LI + "evidence", PI + "evidenceRecorder", LP, P + "evidenceAllocated"),
    (LI + "healthSupervisor", PI + "iviGuest::displayApp", LP, P + "healthAllocated"),
    (LI + "ingress", PI + "iviGuest::gatewayIngress", LP, P + "ingressAllocated"),
    (LI + "sourceAdapter", PI + "sourceAdapter", LP, P + "adapterAllocated"),
    (LI + "transport", PI + "transport", LP, P + "transportAllocated"),
    (LS + "coordinatorSource", PS + "coordinator", LP, P + "coordinatorAllocated"),
    (LS + "nativeAebSource", PS + "pinnedAeb", LP, P + "aebSourceAllocated"),
    (NR + "reqAvailabilityDisposition", FF + "supervise", RF, F + "availabilityDispositionAllocation"),
    (NR + "reqDe4sdvParticipation", FF + "observe", RF, F + "de4sdvParticipationAllocation"),
    (NR + "reqEvidenceCorrelation", FF + "record", RF, F + "evidenceCorrelationAllocation"),
    (NR + "reqFailClosedFreshness", FF + "supervise", RF, F + "failClosedFreshnessAllocation"),
    (NR + "reqInvalidRejection", FF + "validate", RF, F + "invalidRejectionAllocation"),
    (NR + "reqNativeParticipation", FF + "observe", RF, F + "nativeParticipationAllocation"),
    (NR + "reqNonInterference", FF + "observe", RF, F + "nonInterferenceAllocation"),
    (NR + "reqRealAAOSRendering", FF + "present", RF, F + "realAaosRenderingAllocation"),
    (NR + "reqRestorationBehavior", FF + "supervise", RF, F + "restorationBehaviorAllocation"),
    (NR + "reqSourceFidelity", FF + "assemble", RF, F + "sourceFidelityAllocation"),
}
PINNED_PLANNING = {
    (NN + "needCorrelatableEvidence", N + "correlatableEvidenceValidationPlan",
     VP, N + "correlatableEvidenceValidationPlanning"),
    (NN + "needFailClosedDegradation", N + "failClosedDegradationValidationPlan",
     VP, N + "failClosedDegradationValidationPlanning"),
    (NN + "needLiveVisualizationOnAAOS", N + "liveVisualizationOnAAOSValidationPlan",
     VP, N + "liveVisualizationOnAAOSValidationPlanning"),
    (NN + "needNonInterference", N + "nonInterferenceValidationPlan", VP, N + "nonInterferenceValidationPlanning"),
    (NN + "needPreservedSourceProvenance", N + "preservedSourceProvenanceValidationPlan",
     VP, N + "preservedSourceProvenanceValidationPlanning"),
}


def test_the_cut_facts_are_pinned_by_qualified_name(view) -> None:
    """Source, target, end pair and witness of every fact on the cut, by qualified name: ten
    requirement-to-function, eight function-to-logical and nine logical-to-physical allocations, and
    the five planning connections. The chained ends read as the feature each chain ends in."""
    for relation, pinned in ((ALLOCATED_TO, PINNED_ALLOCATIONS), (VALIDATION, PINNED_PLANNING)):
        facts, problems = sp.method_facts(view, relation)
        assert not problems
        assert {(view.label(s), view.label(t), pair, view.label(w)) for s, t, pair, w in facts} == pinned, relation


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


# -- the privileged parity over an API revision (successor_parity) -------------------------------------


def _api_view(snapshot, elements=None) -> ModelView:
    """The production service assembly over a revision binding, serving ``elements`` (default: the cut)."""
    service = _service(snapshot) if elements is None else _service(snapshot, elements)
    return ModelView(service._elements(), service.traversal)


def test_the_parity_report_holds_over_a_revision_binding_on_the_genuine_cut(snapshot, view) -> None:
    """Export snapshot and API revision of one revision: both relations equal, end-pair classes closed."""
    report = sp.parity_report(view, _api_view(snapshot))
    assert report["passed"], report
    assert {name: len(record["facts"]) for name, record in report["relations"].items()} == {
        ALLOCATED_TO: 27, VALIDATION: 5}
    closure = report["allocation_end_closure"]
    assert closure["passed"] and closure["allocations"] == 27
    assert sorted(closure["end_pair_classes"]) == ["Function", "LogicalElement", "PhysicalElement", "Requirement"]
    assert all(record["closed"] for record in closure["end_pair_classes"].values())


def _without(elements, identifiers):
    return [element for element in elements if element["@id"] not in identifiers]


def test_the_parity_report_fails_closed_when_the_api_loses_an_allocation_end(snapshot, view) -> None:
    allocation = _resolve(view, CHAIN[1])
    (membership, *_rest) = [r["@id"] for r in view.index.owned_relationships(allocation, "EndFeatureMembership")]
    api = _api_view(snapshot, _without(snapshot.elements, {membership}))
    report = sp.parity_report(view, api)
    assert not report["passed"]
    allocated = report["relations"][ALLOCATED_TO]
    assert not allocated["checks"]["the API-served traversal returns the method's facts"]
    assert [fact[3] for fact in allocated["only_method"]] == [allocation]
    closure = report["allocation_end_closure"]
    assert closure["unreadable"] == [allocation] and closure["differing_from_export"] == [allocation]
    assert not closure["passed"]


def test_the_parity_report_fails_closed_on_an_end_pair_class_the_api_does_not_serve(snapshot, view) -> None:
    function_root = view.kernel_element("Function")
    report = sp.parity_report(view, _api_view(snapshot, _without(snapshot.elements, {function_root})))
    assert not report["passed"]
    record = report["allocation_end_closure"]["end_pair_classes"]["Function"]
    assert not record["closed"] and "does not exist in the bound revision" in record["served_error"]
    assert not report["relations"][ALLOCATED_TO]["passed"]


# -- the viewer's Ask reads allocatedTo the same way ---------------------------------------------------


def test_the_ask_allocated_to_family_gives_the_method_and_traversal_facts(snapshot, view) -> None:
    """The Ask window's ``allocated_to`` family (tools/sysml_html_viewer/ask_model_semantic.py), asked
    for each allocation source end of the cut, names exactly the targets the method and the traversal
    find: the export's shape carries no top-level ``source``, so a derived-key read finds none."""
    from tools.sysml_html_viewer import ask_model_semantic as ams

    service = _service(snapshot)
    elements = service._elements()
    method = {(source, target) for source, target, _pair, _witness in method_facts(view, ALLOCATED_TO)}
    traversal = {(source, target) for source, target, _pair, _witness in
                 traversal_facts(service.traversal, ModelView(elements, service.traversal), ALLOCATED_TO)}
    by_id = {element["@id"]: element for element in elements}
    asked = set()
    ams._SEMANTIC_CTX_CACHE.clear()
    try:
        for source in sorted({source for source, _target in method}):
            context = ams.api_method_context(service, [by_id[source]], elements, max_hops=1)
            asked |= {(source, entry["element_id"]) for entry in context.get("allocated_to", ())}
            assert "allocated_to_unreadable" not in context
    finally:
        ams._SEMANTIC_CTX_CACHE.clear()
    assert len(method) == 27
    assert asked == method == traversal


# -- valid models pass the parity, real defects still fail it (review round 1, D1) -------------------


def _ids(value) -> list[str]:
    if isinstance(value, dict):
        return [value["@id"]] if "@id" in value else []
    return [i for item in value for i in _ids(item)] if isinstance(value, list) else []


def _cloned_allocation(export: dict, name: str, prefix: str) -> list[dict]:
    """A second allocation of the same pair: ``name``'s owned subtree with new identities, owned by the
    same package through a new OwningMembership."""
    by_id = {e["@id"]: e for e in export["elements"]}
    allocation = next(e for e in export["elements"] if e.get("declaredName") == name)
    subtree, stack = [], [allocation["@id"]]
    while stack:
        current = stack.pop()
        if current in subtree or current not in by_id:
            continue
        subtree.append(current)
        stack += _ids(by_id[current].get("ownedRelationship")) + _ids(by_id[current].get("ownedRelatedElement"))
    owning = allocation["owningRelationship"]["@id"]
    rename = {old: f"{prefix}-{old}" for old in subtree + [owning]}

    def renamed(value):
        if isinstance(value, dict):
            return {key: (rename.get(item, item) if key in ("@id", "elementId") else renamed(item))
                    for key, item in value.items()}
        return [renamed(item) for item in value] if isinstance(value, list) else value

    clones = [renamed(copy.deepcopy(by_id[old])) for old in subtree + [owning]]
    next(c for c in clones if c["@id"] == rename[allocation["@id"]])["declaredName"] = name + "Again"
    package = next(e for e in export["elements"] if e["@id"] == by_id[owning]["owningRelatedElement"]["@id"])
    package["ownedRelationship"] = list(package.get("ownedRelationship", [])) + [{"@id": rename[owning]}]
    export["element_sources"].update({rename[old]: export["element_sources"][old] for old in subtree + [owning]})
    return clones


def _untyped_connection(export: dict, view: ModelView, source: str, target: str, prefix: str) -> list[dict]:
    """An untyped ConnectionUsage from ``source`` to ``target`` in the export's end shape, owned by the
    package that owns the first planning connection."""
    package = view.index.owner_of(sorted(sp.connectors(view, VALIDATION))[0])
    added = [
        {"@id": f"{prefix}-own", "@type": "OwningMembership", "owningRelatedElement": {"@id": package},
         "ownedRelatedElement": [{"@id": f"{prefix}-conn"}], "memberElement": {"@id": f"{prefix}-conn"}},
        {"@id": f"{prefix}-conn", "@type": "ConnectionUsage", "declaredName": f"{prefix}Link",
         "owningRelationship": {"@id": f"{prefix}-own"},
         "ownedRelationship": [{"@id": f"{prefix}-end-1"}, {"@id": f"{prefix}-end-2"}]}]
    for index, usage in ((1, source), (2, target)):
        added += [
            {"@id": f"{prefix}-end-{index}", "@type": "EndFeatureMembership",
             "owningRelatedElement": {"@id": f"{prefix}-conn"}, "ownedRelatedElement": [{"@id": f"{prefix}-f-{index}"}],
             "memberElement": {"@id": f"{prefix}-f-{index}"}},
            {"@id": f"{prefix}-f-{index}", "@type": "Feature", "isEnd": True,
             "owningRelationship": {"@id": f"{prefix}-end-{index}"}, "ownedRelationship": [{"@id": f"{prefix}-rs-{index}"}]},
            {"@id": f"{prefix}-rs-{index}", "@type": "ReferenceSubsetting",
             "owningRelatedElement": {"@id": f"{prefix}-f-{index}"}, "specific": {"@id": f"{prefix}-f-{index}"},
             "subsettingFeature": {"@id": f"{prefix}-f-{index}"}, "general": {"@id": usage},
             "subsettedFeature": {"@id": usage}, "referencedFeature": {"@id": usage}}]
    package_element = next(e for e in export["elements"] if e["@id"] == package)
    package_element["ownedRelationship"] = list(package_element.get("ownedRelationship", [])) + [{"@id": f"{prefix}-own"}]
    source_file = export["element_sources"][package]
    export["element_sources"].update({e["@id"]: source_file for e in added})
    return added


def _changed_cut(tmp_path, view, change) -> tuple[ModelView, ModelView]:
    """The cut with ``change(export, view) -> added elements``: its export snapshot view, and the
    production assembly over the same changed elements (the API side)."""
    export = json.loads(gzip.decompress(GENUINE_EXPORT.read_bytes()))
    export["elements"] = export["elements"] + change(export, view)
    path = tmp_path / "changed-export.json"
    path.write_text(json.dumps(export), encoding="utf-8")
    changed = load_export_snapshot(path)
    return export_view(changed), _api_view(changed)


def test_a_duplicate_allocation_and_an_untyped_connection_from_a_need_pass_the_parity(view, tmp_path) -> None:
    """Valid models that pass CI and the PR Method Check pass the parity: a second allocation of one
    requirement-to-function pair (two witnesses of one pair: the method's check keeps one per target,
    the facts keep both), and an untyped connection from a planning need to another requirement (no
    carrier candidate: absence, as the method answers)."""
    need = sorted(sp.connectors(view, VALIDATION).values())[0][0][0]
    other = _resolve(view, "DE4SDV_AEBSVisualizationNeedsRequirements::VisualizationRequirements::reqSourceFidelity")

    def change(export, view_):
        return (_cloned_allocation(export, "realAaosRenderingAllocation", "again")
                + _untyped_connection(export, view_, need, other, "informal"))

    export_side, api_side = _changed_cut(tmp_path, view, change)
    report = sp.parity_report(export_side, api_side)
    assert report["passed"], json.dumps({n: r["checks"] for n, r in report["relations"].items()})
    witnesses = [fact for fact in report["relations"][ALLOCATED_TO]["facts"] if fact[2] == "RequirementFunctionAssignment"
                 and fact[0] == _resolve(view, REQUIREMENT)]
    assert len(witnesses) == 2 and len({tuple(fact[:3]) for fact in witnesses}) == 1
    assert len(report["relations"][ALLOCATED_TO]["facts"]) == 28
    assert sp.export_parity(export_side)["passed"]


def test_an_untyped_planning_shaped_connection_fails_the_parity_on_the_export_already(view, tmp_path) -> None:
    """A real defect still fails: an untyped connection from a need to a validation scenario could be
    a planning connection that lacks its carrier typing, so the planning answers are incomplete. The
    export-side half, which the PR Method Check runs, shows it before any privileged run."""
    need, scenario = sorted(sp.connectors(view, VALIDATION).values())[0][0]
    export_side, api_side = _changed_cut(
        tmp_path, view, lambda export, view_: _untyped_connection(export, view_, need, scenario, "untypedPlan"))
    report = sp.parity_report(export_side, api_side)
    assert not report["passed"]
    assert not report["relations"][VALIDATION]["checks"]["no incomplete traversal answer on either corpus"]
    export_report = sp.export_parity(export_side)
    assert not export_report["passed"]
    record = export_report["relations"][VALIDATION]
    assert not record["checks"]["the export-snapshot traversal answers completely"]
    assert f"from {export_side.label(need)}: carrier typing evidence is missing or unresolved" in record["details"]


def test_the_export_side_closure_holds_on_the_cut_and_refuses_an_allocation_without_ends(view, tmp_path) -> None:
    """The PR Method Check runs the export half of the allocation-end closure too: every end-pair class
    resolves to one validated kernel element of the export, and every allocation is readable and binary
    (the privileged closure's rule, so an allocation without its own ends fails on the pull request
    first, not in the privileged run)."""
    closure = sp.export_parity(view)["allocation_end_closure"]
    assert closure["passed"] and closure["allocations"] == 27
    assert sorted(closure["end_pair_classes"]) == ["Function", "LogicalElement", "PhysicalElement", "Requirement"]

    def change(export, view_):
        package = view_.index.owner_of(sorted(sp.connectors(view_, ALLOCATED_TO))[0])
        package_element = next(e for e in export["elements"] if e["@id"] == package)
        package_element["ownedRelationship"] = list(package_element.get("ownedRelationship", [])) + [
            {"@id": "endless-own"}]
        export["element_sources"].update(dict.fromkeys(("endless-own", "endless"), export["element_sources"][package]))
        return [{"@id": "endless-own", "@type": "OwningMembership", "owningRelatedElement": {"@id": package},
                 "ownedRelatedElement": [{"@id": "endless"}], "memberElement": {"@id": "endless"}},
                {"@id": "endless", "@type": "AllocationUsage", "declaredName": "endlessAllocation",
                 "owningRelationship": {"@id": "endless-own"}}]

    export_side, api_side = _changed_cut(tmp_path, view, change)
    report = sp.export_parity(export_side)
    assert not report["passed"] and report["relations"][ALLOCATED_TO]["passed"]
    assert not report["allocation_end_closure"]["checks"]["every allocation is readable and binary"]
    assert report["allocation_end_closure"]["unreadable"] == ["endless"]
    assert report["allocation_end_closure"]["unreadable_reasons"] == [
        f"{export_side.label('endless')}: it has no ends of its own; " + sp.ACCEPTED_ALLOCATION_FORM]
    assert sp.ACCEPTED_ALLOCATION_FORM == ("author the allocation as `allocate <source> to <target>`; "
                                           "allocations without their own ends are not an accepted form")
    privileged = sp.parity_report(export_side, api_side)["allocation_end_closure"]
    assert not privileged["checks"]["every served allocation is readable and binary"]
