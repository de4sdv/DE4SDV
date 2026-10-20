"""Synthetic API fixtures: executable slice, not privileged model closure.

Connectors take the licensed export's end shape: each end is an
EndFeatureMembership owning an end Feature whose authored ReferenceSubsetting
names the connected usage. They carry no derived ``source``/``target`` keys,
which the export does not provide and the traversal does not read.
"""
from pathlib import Path
import pytest
import mcp.client.stdio  # keep session-global stderr for later MCP tests
from de4sdv.semantic.kernel_contract import declaration_identity
from de4sdv.sysml_api.revisions import RevisionBinding
from model_contract_fixtures import binding_dict, model_facade, model_service

ROOT = Path(__file__).resolve().parents[1]
REVISION = "a" * 40


def model_pins():
    """Class pins of the trace-vocabulary contract (from the projection layers)."""
    from de4sdv.semantic import model_contract as mc
    _records, provisions = mc.load_model_layers(ROOT)
    return mc.model_class_pins(provisions)


def fixture_service():
    import copy
    contract = copy.deepcopy(model_facade().profile)
    bindings, elements = [], []
    for name, row in {**contract["classes"], **contract["carriers"]}.items():
        declared, metaclass = declaration_identity(row["declaration"])
        bindings.append(dict(ontology_class=name, element_id="root-" + name,
                             source_file=row["file"], declaration=row["declaration"]))
        elements.append({"@id": "root-" + name, "@type": metaclass, "declaredName": declared})
    for name, kind in [("Requirement", "RequirementUsage"), ("Function", "ActionUsage"),
                       ("LogicalElement", "PartUsage"), ("PhysicalElement", "PartUsage"),
                       ("Need", "RequirementUsage"), ("ValidationScenario", "PartUsage"),
                       ("RegulatorySource", "PartUsage")]:
        elements.append({"@id": "use-" + name, "@type": kind,
                         "type": [{"@id": "root-" + name}]})
    elements.append({"@id": "context", "@type": "Package"})
    elements.extend(edge("AllocationUsage", "use-Requirement", "use-Function", name="allocation"))
    binding = RevisionBinding.from_dict(binding_dict(git_commit=REVISION, scope="fixture",
        kernel_bindings=bindings))
    class Repository:
        def list_elements(self, *args): return elements
    service = model_service(binding, Repository(), expected_git_revision=REVISION)
    return service, elements, binding, contract


def test_first_public_requirement_allocation_slice():
    service, elements, binding, contract = fixture_service()
    result = service.semantic_neighbors("use-Requirement", predicates=["allocatedTo"])
    assert [(e["predicate"], e["target"], e["semantic_strength"]) for e in result["edges"]] == [
        ("allocatedTo", "use-Function", "allocation")]
    assert result["edges"][0]["api_object_id"] == "allocation"
    assert result["semantic_status"] == "complete"
    assert service.binder.bind_class("Function").sysml.element_id == "root-Function"



def rebuild(elements, binding, contract=None):
    """Reassemble the production services over the (possibly mutated) binding.

    The trace-vocabulary contract is always the generated one the facade
    loads; a supplied contract must equal it."""
    from de4sdv.semantic import model_contract as mc
    class Repository:
        def list_elements(self, *args): return elements
    if contract is not None and contract != mc.load_trace_contract(ROOT):
        raise ValueError("supplied trace contract differs from the generated contract")
    return model_service(binding, Repository(), expected_git_revision=REVISION)


def native_end(connector, role, usage):
    """One connector end in the export's shape: the EndFeatureMembership, its end Feature and the end
    Feature's authored ReferenceSubsetting naming the connected usage."""
    membership, end, subsetting = f"{connector}-{role}-end", f"{connector}-{role}", f"{connector}-{role}-reference"
    return [
        {"@id": membership, "@type": "EndFeatureMembership", "memberName": role,
         "memberElement": {"@id": end}, "ownedRelatedElement": [{"@id": end}],
         "owningRelatedElement": {"@id": connector}},
        {"@id": end, "@type": "Feature", "name": role, "isEnd": True,
         "owningRelationship": {"@id": membership}, "ownedRelationship": [{"@id": subsetting}]},
        {"@id": subsetting, "@type": "ReferenceSubsetting", "owningRelatedElement": {"@id": end},
         "specific": {"@id": end}, "subsettingFeature": {"@id": end}, "general": {"@id": usage},
         "subsettedFeature": {"@id": usage}, "referencedFeature": {"@id": usage}},
    ]


def edge(kind, source, target, name="extra", **kwargs):
    """A binary connector from ``source`` to ``target`` in the export's shape, followed by its end
    elements: extend the corpus with the list."""
    ends = native_end(name, "source", source) + native_end(name, "target", target)
    connector = {"@id": name, "@type": kind, "owningNamespace": {"@id": "context"},
                 "ownedRelationship": [{"@id": ends[0]["@id"]}, {"@id": ends[3]["@id"]}], **kwargs}
    return [connector, *ends]


@pytest.mark.parametrize("source,target", [("Function", "LogicalElement"), ("LogicalElement", "PhysicalElement")])
def test_other_approved_native_pairs(source, target):
    service, elements, _, _ = fixture_service()
    elements.extend(edge("AllocationUsage", "use-" + source, "use-" + target))
    result = service.semantic_neighbors("use-" + source, predicates=["allocatedTo"])
    assert [(e["target"], e["api_object_id"]) for e in result["edges"]] == [("use-" + target, "extra")]


@pytest.mark.parametrize("source,target", [("Requirement", "LogicalElement"), ("PhysicalElement", "LogicalElement"), ("Need", "Function")])
def test_unapproved_pairs_and_need_cannot_masquerade_as_requirement(source, target):
    service, elements, _, _ = fixture_service()
    elements[:] = [e for e in elements if e["@id"] != "allocation" and not e["@id"].startswith("allocation-")]
    elements.extend(edge("AllocationUsage", "use-" + source, "use-" + target))
    result = service.semantic_neighbors("use-" + source, predicates=["allocatedTo"])
    assert result["edges"] == []
    assert result["semantic_status"] == "complete"


@pytest.mark.parametrize("predicate", ["hasValidationScenario", "hasRegulatorySource"])
def test_typed_planning_and_source_provenance_through_public_binder(predicate):
    service, elements, _, contract = fixture_service()
    row = contract["relations"][predicate][0]
    elements.extend(edge("ConnectionUsage", "use-" + row["sourceClass"], "use-" + row["targetClass"],
        type=[{"@id": "root-" + predicate}]))
    report = service.semantic_neighbors("use-" + row["sourceClass"], predicates=[predicate])
    assert len(report["edges"]) == 1
    assert report["edges"][0]["semantic_strength"] == row["strength"]
    # The carrier pin routes from its exact ingestion binding (the carrier is a
    # successor-profile pin, not a kernel-contract class).
    by_id = {e["@id"]: e for e in elements}
    assert service.binder.kernel_bindings.element_id_for(predicate, by_id) == "root-" + predicate
    if row["inverse"]:
        inverse = service.semantic_neighbors("use-" + row["targetClass"], predicates=[row["inverse"]])
        assert inverse["edges"][0]["api_object_id"] == report["edges"][0]["api_object_id"]
        assert inverse["edges"][0]["target"] == "use-" + row["sourceClass"]


def test_missing_lineage_binding_is_incomplete_on_every_public_surface():
    from dataclasses import replace
    _, elements, binding, contract = fixture_service()
    binding = replace(binding, kernel_bindings=tuple(b for b in binding.kernel_bindings if b.ontology_class != "Function"))
    service = rebuild(elements, binding, contract)
    reports = [service.semantic_neighbors("use-Requirement", predicates=["allocatedTo"]),
               service.trace("use-Requirement", "use-Function"),
               service.impact("use-Requirement"), service.verification_coverage("use-Requirement")]
    for report in reports:
        assert report["semantic_status"] == "incomplete"
        assert any(r["predicate"] == "allocatedTo" and "Function" in r["reason"] for r in report["unsupported_predicates"])
        assert not any(e["predicate"] == "allocatedTo" for e in report.get("edges", report.get("path", [])))
    assert reports[-1]["status"] == "incomplete"


@pytest.mark.parametrize("field,value", [("source_file", "foreign.sysml"), ("declaration", "action def Impostor")])
def test_wrong_exact_model_pin_refuses_before_queries(field, value):
    from dataclasses import replace
    from de4sdv.sysml_api.errors import IdentityNotFoundError
    _, elements, binding, contract = fixture_service()
    changed = tuple(replace(b, **{field:value}) if b.ontology_class == "Function" else b for b in binding.kernel_bindings)
    with pytest.raises(IdentityNotFoundError, match="exact successor binding"):
        rebuild(elements, replace(binding, kernel_bindings=changed), contract)


def test_overlapping_validated_roots_refuse_identity_routing():
    from dataclasses import replace
    _, elements, binding, contract = fixture_service()
    changed = tuple(replace(b, element_id="root-LogicalElement") if b.ontology_class == "PhysicalElement" else b for b in binding.kernel_bindings)
    with pytest.raises(ValueError, match="overlapping"):
        rebuild(elements, replace(binding, kernel_bindings=changed), contract)


def test_retired_stronger_claims_are_refused_not_aliases():
    from de4sdv.semantic.kernel_contract import RetiredIdentityError
    service, _, _, contract = fixture_service()
    assert contract["retired"]
    for name in contract["retired"]:
        with pytest.raises(RetiredIdentityError, match="retired"):
            service.semantic_neighbors("use-Requirement", predicates=[name])
        assert service.traversal.traverse(name, {"@id": "use-Requirement"}, []) == []
        assert service.traversal.unsupported[-1]["authority_state"] == "retired"
    assert "hasRelevantFunction" not in service.contract.relationships
    assert not set(contract["retired"]) & set(service._mapped_predicates())


def test_public_impact_reports_allocation_without_mandatory_chain_or_duplicate_dependency():
    service, elements, _, _ = fixture_service()
    elements.extend(edge("AllocationUsage", "use-Function", "use-LogicalElement", name="logical"))
    report = service.impact("use-Requirement")
    assert {(e["source"], e["target"]) for e in report["edges"] if e["predicate"] == "allocatedTo"} == {
        ("use-Requirement", "use-Function"), ("use-Function", "use-LogicalElement")}
    assert not any(e["predicate"] in {"realizedBy", "deployedTo", "hasRelevantFunction"} for e in report["edges"])
    assert not any("mandatory" in g["reason"] for g in report["gaps"])


def test_real_native_dependency_direction_and_weaker_witness_are_retained():
    service, elements, _, _ = fixture_service()
    elements.append({"@id": "dependency", "@type": "Dependency",
                     "client": [{"@id": "use-Requirement"}], "supplier": [{"@id": "use-Function"}]})
    report = service.semantic_neighbors("use-Requirement", predicates=["specifiesFunction"])
    assert report["edges"][0]["semantic_strength"] == "relevance"
    assert report["edges"][0]["api_object_id"] == "dependency"
    assert report["edges"][0]["witness"]["native_client"] == ["use-Requirement"]


def test_absent_or_dangling_allocation_context_cannot_be_a_fact():
    service, elements, _, _ = fixture_service()
    allocation = next(e for e in elements if e["@id"] == "allocation")
    allocation.pop("owningNamespace")
    report = service.semantic_neighbors("use-Requirement", predicates=["allocatedTo"])
    assert report["edges"] == []
    assert report["semantic_status"] == "incomplete"
    assert "context" in report["unsupported_predicates"][0]["reason"]


def test_contract_tampering_refuses(tmp_path):
    import json
    from copy import deepcopy
    from de4sdv.semantic import model_authority_runtime as mar
    from de4sdv.semantic import model_contract as mc
    _, elements, binding, contract = fixture_service()
    changed = deepcopy(contract)
    changed["relations"]["allocatedTo"][0]["targetClass"] = "PhysicalElement"
    with pytest.raises(ValueError, match="differs from the generated contract"):
        rebuild(elements, binding, changed)
    # The runtime refuses a generated file edited by hand: its id no longer
    # digests its meaning.
    document = json.loads((ROOT / mc.TRACE_CONTRACT_PATH).read_text())
    document["contract"] = changed
    path = tmp_path / mc.TRACE_CONTRACT_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(document))
    _records, provisions = mc.load_model_layers(ROOT)
    with pytest.raises(mc.ModelAuthorityRefused, match="id is not the digest of its meaning"):
        mc.load_trace_contract(tmp_path, provisions=provisions)
    # A bundle binding a tampered successor record is refused at load time.
    assert mar._successor_record(changed) != model_facade()._components["successor_contract"]


# ---- Reviewed SPEC findings: reference shapes, meanings, discrimination, grammar.
def _spec_query(mutate, predicate="allocatedTo", source="use-Requirement"):
    _, elements, binding, contract = fixture_service()
    binding = mutate(elements, binding, contract) or binding
    return rebuild(elements, binding, contract).semantic_neighbors(source, predicates=[predicate])


def _with_method(mutate, predicate="allocatedTo", source="use-Requirement"):
    """The traversal's answer and the method check's result over the same mutated corpus."""
    from de4sdv.semantic.increment_scope import ModelView
    from de4sdv.semantic.relation_checks import check_relation
    _, elements, binding, contract = fixture_service()
    mutate(elements)
    service = rebuild(elements, binding, contract)
    report = service.semantic_neighbors(source, predicates=[predicate])
    return report, check_relation(ModelView(service._elements(), service.traversal), predicate, source)


def _element(elements, identifier):
    return next(e for e in elements if e["@id"] == identifier)


def test_the_witness_is_the_connector_and_its_read_ends():
    report, method = _with_method(lambda elements: None)
    assert report["semantic_status"] == "complete"
    (edge_record,) = report["edges"]
    assert (edge_record["target"], edge_record["api_object_id"]) == ("use-Function", "allocation")
    assert edge_record["witness"] == {
        "native_source": "use-Requirement", "native_target": "use-Function", "context_id": "context",
        "carrier": "RequirementFunctionAssignment", "canonical_predicate": "allocatedTo",
        "source_lineage": "explicit", "target_lineage": "explicit",
        "source_root": "root-Requirement", "target_root": "root-Function",
        "claim_boundary": "no satisfaction, execution, result, fulfillment, deployment or compliance"}
    assert method.hops == (("use-Function", "allocation"),)


def test_a_planning_witness_names_its_carrier_lineage_and_roots():
    def mutate(elements):
        elements.extend(edge("ConnectionUsage", "use-Need", "use-ValidationScenario", name="plan",
                             type=[{"@id": "root-hasValidationScenario"}]))
    report, _method = _with_method(mutate, "hasValidationScenario", "use-Need")
    (edge_record,) = report["edges"]
    assert edge_record["witness"] == {
        "native_source": "use-Need", "native_target": "use-ValidationScenario", "context_id": "context",
        "carrier": "ValidationPlanningAssociation", "canonical_predicate": "hasValidationScenario",
        "source_lineage": "explicit", "target_lineage": "explicit",
        "source_root": "root-Need", "target_root": "root-ValidationScenario",
        "claim_boundary": "no satisfaction, execution, result, fulfillment, deployment or compliance"}


def _mcp_answers(elements, binding, contract):
    """semantic_neighbors, impact and trace through the MCP tool functions (never an exception)."""
    import asyncio

    from de4sdv.semantic.mcp_server import create_mcp_server

    server = create_mcp_server(rebuild(elements, binding, contract))
    calls = (("semantic_neighbors", {"identifier": "use-Requirement", "predicates": ["allocatedTo"]}),
             ("impact", {"identifier": "use-Requirement"}),
             ("trace", {"source_identifier": "use-Requirement", "target_identifier": "use-Function"}))
    return {tool: asyncio.run(server._tool_manager.call_tool(tool, arguments)) for tool, arguments in calls}


@pytest.mark.parametrize("missing, reason", [
    (("allocation-target", "allocation-target-reference"), "its end 'allocation-target' is not in the bound revision"),
    (("allocation-source-end",), "its owned relationship 'allocation-source-end' is not in the bound revision"),
    (("allocation-target-end",), "its owned relationship 'allocation-target-end' is not in the bound revision"),
    ((), "its owned relationship 'allocation-note' is not in the bound revision"),
], ids=["end-feature", "source-end-membership", "target-end-membership", "other-owned-relationship"])
def test_an_allocation_end_not_in_the_revision_is_incomplete_on_every_public_surface(missing, reason):
    """An end feature, an end membership, or any other owned relationship (it may be an end) that the
    revision does not hold: the allocation cannot be read, so every answer is incomplete, from either
    end, never a crash and never an absence."""
    _, elements, binding, contract = fixture_service()
    elements[:] = [e for e in elements if e["@id"] not in missing]
    if not missing:
        _element(elements, "allocation")["ownedRelationship"].append({"@id": "allocation-note"})
    answers = _mcp_answers(elements, binding, contract)
    for tool, report in answers.items():
        assert report["semantic_status"] == "incomplete", (tool, report)
        assert {"predicate": "allocatedTo", "authority_state": "incomplete", "reason": f"allocation: {reason}"} in (
            report["unsupported_predicates"]), (tool, report["unsupported_predicates"])
    assert answers["semantic_neighbors"]["edges"] == [] and answers["trace"]["path"] == []
    from_target = rebuild(elements, binding, contract).semantic_neighbors("use-Function", predicates=["allocatedTo"])
    assert from_target["semantic_status"] == "incomplete"


@pytest.mark.parametrize("shape", ["dangling-owning-relationship", "two-parents"])
def test_an_owning_relationship_that_cannot_name_one_owner_refuses_the_context(shape):
    """The owning relationship decides the context: one that is not in the revision, or that names
    two owners, refuses it even where a derived owner key is present."""
    def mutate(elements):
        allocation = _element(elements, "allocation")
        if shape == "dangling-owning-relationship":
            allocation["owningRelationship"] = {"@id": "missing-membership"}
        else:
            elements.append({"@id": "owning", "@type": "OwningMembership",
                             "owningRelatedElement": [{"@id": "context"}, {"@id": "use-Need"}],
                             "ownedRelatedElement": [{"@id": "allocation"}]})
            allocation["owningRelationship"] = {"@id": "owning"}
    report, _method = _with_method(mutate)
    assert report["edges"] == [] and report["semantic_status"] == "incomplete"
    assert any("context" in r["reason"] for r in report["unsupported_predicates"])


def test_a_method_side_input_missing_inside_the_witness_loop_is_incomplete(monkeypatch):
    """The end pair of a witness needs a method-side input (a kernel binding) that is missing: the
    answer is incomplete with the method's detail, never an exception and never an absence."""
    from de4sdv.semantic import trace_vocabulary_traversal as tvt
    from de4sdv.semantic.relation_checks import MethodSideInput

    def missing(*_args, **_kwargs):
        raise MethodSideInput("kernel-binding:Function", "method side: no validated kernel binding for Function")

    monkeypatch.setattr(tvt, "allocation_pairs", missing)
    report, _method = _with_method(lambda elements: None)
    assert report["edges"] == [] and report["semantic_status"] == "incomplete"
    assert any(r["reason"] == "method side: no validated kernel binding for Function"
               for r in report["unsupported_predicates"]), report["unsupported_predicates"]


def _connector(kind, name, ends, **kwargs):
    """A connector with the ``(role, usage)`` ends in order, in the export's shape."""
    elements = [element for role, usage in ends for element in native_end(name, role, usage)]
    connector = {"@id": name, "@type": kind, "owningNamespace": {"@id": "context"},
                 "ownedRelationship": [{"@id": e["@id"]} for e in elements if e["@type"] == "EndFeatureMembership"],
                 **kwargs}
    return [connector, *elements]


THREE_ENDS = [("a", "use-Need"), ("b", "use-ValidationScenario"), ("c", "use-Function")]


@pytest.mark.parametrize("typing", [None, "root-hasRegulatorySource"], ids=["untyped", "another-carrier"])
def test_a_connection_that_is_no_binary_planning_carrier_leaves_the_answer_complete(typing):
    """Three ends from a need, untyped or typed by another relation's carrier: it cannot carry the
    binary planning relation, so the answer stays complete, as the method's."""
    def mutate(elements):
        elements.extend(_connector("ConnectionUsage", "triple", THREE_ENDS,
                                   **({"type": [{"@id": typing}]} if typing else {})))
    report, method = _with_method(mutate, "hasValidationScenario", "use-Need")
    assert report["edges"] == [] and report["semantic_status"] == "complete", report["unsupported_predicates"]
    assert method.hops == () and not method.problem


def test_a_planning_connection_with_three_ends_is_incomplete_from_every_need():
    """A connection typed by the planning carrier with three ends: its planning fact cannot be read,
    so every planning answer is incomplete, also from a need it does not name."""
    def mutate(elements):
        elements.append({"@id": "use-OtherNeed", "@type": "RequirementUsage", "type": [{"@id": "root-Need"}]})
        elements.extend(_connector("ConnectionUsage", "triple", THREE_ENDS,
                                   type=[{"@id": "root-hasValidationScenario"}]))
    report, _method = _with_method(mutate, "hasValidationScenario", "use-OtherNeed")
    assert report["edges"] == [] and report["semantic_status"] == "incomplete"
    assert any("3 ends" in r["reason"] for r in report["unsupported_predicates"]), report["unsupported_predicates"]


@pytest.mark.parametrize("typing, expected", [(None, "incomplete"), ("root-hasValidationScenario", "incomplete"),
                                              ("root-hasRegulatorySource", "complete")],
                         ids=["untyped", "planning-carrier", "another-carrier"])
def test_a_connection_whose_source_end_membership_is_missing(typing, expected):
    """The source end membership of a need-to-scenario connection is not in the revision. If the
    connection may be a planning connection (typed by the carrier, or untyped), the need's answer is
    incomplete, never a complete absence; typed by another relation's carrier, it carries no planning
    fact."""
    def mutate(elements):
        elements.extend(_connector("ConnectionUsage", "plan",
                                   [("source", "use-Need"), ("target", "use-ValidationScenario")],
                                   **({"type": [{"@id": typing}]} if typing else {})))
        elements[:] = [e for e in elements
                       if e["@id"] not in ("plan-source-end", "plan-source", "plan-source-reference")]
    report, _method = _with_method(mutate, "hasValidationScenario", "use-Need")
    assert report["edges"] == [] and report["semantic_status"] == expected, report["unsupported_predicates"]


def test_an_untyped_connection_that_is_no_carrier_candidate_is_no_answer_at_all():
    """An untyped connection whose ends ground in no typed-connection end pair (a need to a function)
    cannot carry the relation: absence, as the method answers, not incomplete. One whose ends do ground
    in the planning pair stays incomplete (test_untyped_carrier_candidate_is_incomplete_not_silent_absence)."""
    def mutate(elements):
        elements.extend(edge("ConnectionUsage", "use-Need", "use-Function", name="plain"))
    report, method = _with_method(mutate, "hasValidationScenario", "use-Need")
    assert report["edges"] == [] and report["semantic_status"] == "complete", report["unsupported_predicates"]
    assert method.hops == () and not method.problem


def test_a_feature_chain_end_reads_as_its_last_chaining_feature():
    """``allocate requirement to holder.function``: the end names a chain whose last chaining feature
    is the function, for the traversal as for the method."""
    def mutate(elements):
        elements.extend([
            {"@id": "holder", "@type": "PartUsage"},
            {"@id": "chain", "@type": "Feature", "ownedRelationship": [{"@id": "chaining-1"}, {"@id": "chaining-2"}]},
            {"@id": "chaining-1", "@type": "FeatureChaining", "owningRelatedElement": {"@id": "chain"},
             "chainingFeature": {"@id": "holder"}},
            {"@id": "chaining-2", "@type": "FeatureChaining", "owningRelatedElement": {"@id": "chain"},
             "chainingFeature": {"@id": "use-Function"}}])
        _element(elements, "allocation-target-reference").update(
            general={"@id": "chain"}, subsettedFeature={"@id": "chain"}, referencedFeature={"@id": "chain"})
    report, method = _with_method(mutate)
    assert report["semantic_status"] == "complete"
    assert [(e["target"], e["witness"]["native_target"]) for e in report["edges"]] == [("use-Function", "use-Function")]
    assert method.hops == (("use-Function", "allocation"),)


def _unreadable(mode, end):
    """An end the shared reader refuses: two authored references, an implied one only, a missing
    referenced feature, or a chain that ends in a feature not in the revision."""
    def mutate(elements):
        reference = _element(elements, end + "-reference")
        if mode == "ambiguous":
            elements.append({**reference, "@id": end + "-second", "general": {"@id": "use-LogicalElement"},
                             "subsettedFeature": {"@id": "use-LogicalElement"},
                             "referencedFeature": {"@id": "use-LogicalElement"}})
            _element(elements, end)["ownedRelationship"].append({"@id": end + "-second"})
        elif mode == "implied-only":
            reference["isImplied"] = True
        elif mode == "dangling":
            reference.update(general={"@id": "missing"}, subsettedFeature={"@id": "missing"},
                             referencedFeature={"@id": "missing"})
        else:
            elements.extend([
                {"@id": "chain", "@type": "Feature", "ownedRelationship": [{"@id": "chaining"}]},
                {"@id": "chaining", "@type": "FeatureChaining", "owningRelatedElement": {"@id": "chain"},
                 "chainingFeature": {"@id": "missing"}}])
            reference.update(general={"@id": "chain"}, subsettedFeature={"@id": "chain"},
                             referencedFeature={"@id": "chain"})
    return mutate


@pytest.mark.parametrize("mode", ["ambiguous", "implied-only", "dangling", "dangling-chain"])
def test_an_allocation_end_the_reader_refuses_is_incomplete_for_the_traversal_and_the_method(mode):
    report, method = _with_method(_unreadable(mode, "allocation-target"))
    assert report["edges"] == [] and report["semantic_status"] == "incomplete"
    (record,) = [r for r in report["unsupported_predicates"] if r["predicate"] == "allocatedTo"]
    assert record["reason"].startswith("allocation: ")
    assert method.hops == () and method.problem == "model-witness:allocatedTo"
    assert record["reason"] in method.reason


@pytest.mark.parametrize("mode", ["ambiguous", "implied-only", "dangling"])
def test_a_planning_end_the_reader_refuses_is_incomplete_for_the_traversal_and_the_method(mode):
    def mutate(elements):
        elements.extend(edge("ConnectionUsage", "use-Need", "use-ValidationScenario", name="plan",
                             type=[{"@id": "root-hasValidationScenario"}]))
        _unreadable(mode, "plan-target")(elements)
    report, method = _with_method(mutate, "hasValidationScenario", "use-Need")
    assert report["edges"] == [] and report["semantic_status"] == "incomplete"
    (record,) = [r for r in report["unsupported_predicates"] if r["predicate"] == "hasValidationScenario"]
    assert method.hops == () and method.problem == "model-witness:ValidationPlanningAssociation"
    assert record["reason"] in method.reason


def test_an_end_grounding_in_two_layer_classes_is_incomplete_for_the_traversal_and_the_method():
    def mutate(elements):
        _element(elements, "use-LogicalElement")["type"].append({"@id": "root-PhysicalElement"})
        elements.extend(edge("AllocationUsage", "use-Function", "use-LogicalElement", name="layered"))
    report, method = _with_method(mutate, source="use-Function")
    assert report["edges"] == [] and report["semantic_status"] == "incomplete"
    (record,) = [r for r in report["unsupported_predicates"] if r["predicate"] == "allocatedTo"]
    assert "grounds in more than one of" in record["reason"]
    assert method.problem == "model-witness:allocatedTo" and record["reason"] in method.reason


def test_derived_source_and_target_keys_are_not_read():
    """A connector with derived keys and no native ends is no fact; with native ends, the ends decide."""
    def mutate(elements):
        elements.append({"@id": "derived-only", "@type": "AllocationUsage", "owningNamespace": {"@id": "context"},
                         "source": [{"@id": "use-Function"}], "target": [{"@id": "use-LogicalElement"}]})
        _element(elements, "allocation").update(source=[{"@id": "use-Need"}], target=[{"@id": "use-PhysicalElement"}])
    report, method = _with_method(mutate)
    assert [(e["target"], e["api_object_id"]) for e in report["edges"]] == [("use-Function", "allocation")]
    assert method.hops == (("use-Function", "allocation"),)
    from_function, method_from_function = _with_method(mutate, source="use-Function")
    assert from_function["edges"] == [] and from_function["semantic_status"] == "complete"
    assert method_from_function.hops == ()


def test_a_relationship_naming_no_target_is_an_omitted_library_reference():
    """The export leaves out references to elements outside it: an implied or authored specialization
    without a target supplies no meaning, while a target that is named but missing stays undecided."""
    def omitted(elements):
        elements.extend([
            {"@id": "omitted-implied", "@type": "Subclassification", "isImplied": True,
             "owningRelatedElement": {"@id": "root-Function"}, "specific": {"@id": "root-Function"}},
            {"@id": "omitted-authored", "@type": "FeatureTyping", "owningRelatedElement": {"@id": "use-Function"},
             "typedFeature": {"@id": "use-Function"}}])
    report, _method = _with_method(omitted)
    assert report["semantic_status"] == "complete"
    assert [e["target"] for e in report["edges"]] == ["use-Function"]

    def named_but_missing(elements):
        omitted(elements)
        _element(elements, "omitted-implied")["general"] = {"@id": "missing-general"}
    report, _method = _with_method(named_but_missing)
    assert report["edges"] == [] and report["semantic_status"] == "incomplete"


def test_dangling_endpoint_typing_is_incomplete_not_complete_absence():
    def mutate(elements, binding, contract):
        next(e for e in elements if e["@id"] == "use-Function")["type"] = [{"@id": "absent-definition"}]
    report = _spec_query(mutate)
    assert report["edges"] == []
    assert report["semantic_status"] == "incomplete"
    assert any(r["predicate"] == "allocatedTo" for r in report["unsupported_predicates"])


def test_dangling_carrier_typing_is_incomplete_not_complete_absence():
    def mutate(elements, binding, contract):
        elements.extend(edge("ConnectionUsage", "use-Need", "use-ValidationScenario", name="plan",
                             type=[{"@id": "absent-carrier"}]))
    report = _spec_query(mutate, "hasValidationScenario", "use-Need")
    assert report["edges"] == []
    assert report["semantic_status"] == "incomplete"


def test_untyped_carrier_candidate_is_incomplete_not_silent_absence():
    def mutate(elements, binding, contract):
        elements.extend(edge("ConnectionUsage", "use-Need", "use-ValidationScenario", name="plan"))
    report = _spec_query(mutate, "hasValidationScenario", "use-Need")
    assert report["edges"] == []
    assert report["semantic_status"] == "incomplete"


@pytest.mark.parametrize("mode", ["mixed-valid", "mixed-unrelated", "dangling-supertype", "mixed-carrier"])
def test_every_discrimination_branch_must_be_resolved(mode):
    def mutate(elements, binding, contract):
        if mode == "mixed-carrier":
            elements.extend(edge("ConnectionUsage", "use-Need", "use-ValidationScenario", name="plan",
                type=[{"@id": "root-hasValidationScenario"}, {"@id": "missing-other-meaning"}]))
        else:
            endpoint = next(e for e in elements if e["@id"] == "use-Function")
            if mode == "mixed-valid":
                endpoint["type"].append({"@id": "missing-definition"})
            elif mode == "mixed-unrelated":
                elements.append({"@id": "unrelated", "@type": "ActionDefinition"})
                endpoint["type"] = [{"@id": "unrelated"}, {"@id": "missing-definition"}]
            else:
                elements.extend([
                    {"@id": "derived", "@type": "ActionDefinition"},
                    {"@id": "parent", "@type": "Subclassification",
                     "subclassifier": {"@id": "derived"}, "superclassifier": {"@id": "missing-definition"}}])
                endpoint["type"] = [{"@id": "derived"}]
    predicate = "hasValidationScenario" if mode == "mixed-carrier" else "allocatedTo"
    source = "use-Need" if mode == "mixed-carrier" else "use-Requirement"
    report = _spec_query(mutate, predicate, source)
    assert report["semantic_status"] == "incomplete"
    assert report["edges"] == []
    assert any(r["predicate"] == predicate for r in report["unsupported_predicates"])


@pytest.mark.parametrize("shape", ["inline-uri", "relationship-uri", "unrelated-uri"])
def test_external_typing_requires_uri_on_its_exact_reference(shape):
    def mutate(elements, binding, contract):
        endpoint = next(e for e in elements if e["@id"] == "use-Function")
        reference = {"@id": "external-type", "@uri": "synthetic://library/type"}
        if shape == "relationship-uri":
            elements.append({"@id": "typing", "@type": "FeatureTyping",
                "typedFeature": {"@id": "use-Function"}, "type": reference})
        else:
            endpoint["type"].append(reference if shape == "inline-uri" else {"@id": "external-type"})
            if shape == "unrelated-uri":
                endpoint["unrelatedData"] = reference
    report = _spec_query(mutate)
    if shape == "unrelated-uri":
        assert report["semantic_status"] == "incomplete"
        assert report["edges"] == []
    else:
        assert report["semantic_status"] == "complete"
        assert report["edges"][0]["target"] == "use-Function"


def test_one_carrier_cannot_acquire_two_governed_meanings():
    service, elements, _, _ = fixture_service()
    next(e for e in elements if e["@id"] == "use-Need")["type"].append({"@id": "root-Requirement"})
    next(e for e in elements if e["@id"] == "use-ValidationScenario")["type"].append({"@id": "root-RegulatorySource"})
    elements.extend(edge("ConnectionUsage", "use-Need", "use-ValidationScenario", name="both-carriers",
                         type=[{"@id": "root-hasValidationScenario"}, {"@id": "root-hasRegulatorySource"}]))
    combined = service.semantic_neighbors("use-Need", predicates=["hasValidationScenario", "hasRegulatorySource"])
    assert combined["edges"] == []
    assert combined["semantic_status"] == "incomplete"
    for predicate in ("hasValidationScenario", "hasRegulatorySource"):
        single = service.semantic_neighbors("use-Need", predicates=[predicate])
        assert single["edges"] == [], predicate
        assert single["semantic_status"] == "incomplete", predicate


@pytest.mark.parametrize("mode", ["comment_only_carrier_end", "nested_carrier_end",
                                  "comment_version_value", "nested_version_value"])
def test_construction_requires_direct_owned_code(mode):
    from de4sdv.semantic.trace_vocabulary_contract import MODEL
    text = (ROOT / MODEL).read_text()
    if mode == "comment_only_carrier_end":
        text = text.replace("    end source : RequirementCandidate;",
            "    end source : StakeholderNeedCandidate;\n"
            "    doc /* end source : RequirementCandidate; */", 1)
    elif mode == "nested_carrier_end":
        text = text.replace("    end source : RequirementCandidate;",
            "    end source : StakeholderNeedCandidate;\n"
            "    connection def Foreign { end source : RequirementCandidate; }", 1)
    elif mode == "comment_version_value":
        text = text.replace('attribute :>> version = "de4sdv.relationship-successor/v1";',
            '/* attribute :>> version = "de4sdv.relationship-successor/v1"; */', 1)
    else:
        text = text.replace('attribute :>> version = "de4sdv.relationship-successor/v1";',
            'part foreign { attribute version = "de4sdv.relationship-successor/v1";'
            ' /* attribute :>> version = "de4sdv.relationship-successor/v1"; */ }', 1)
    with pytest.raises(ValueError):
        _contract_from_model_text(text)


def _contract_from_model_text(text):
    """Overlay one source read in memory; never create a real-model mirror."""
    from unittest.mock import patch
    from de4sdv.semantic.trace_vocabulary_contract import extract_contract, MODEL
    read_text, read_bytes = Path.read_text, Path.read_bytes
    def text_read(path, *args, **kwargs):
        return text if path == ROOT / MODEL else read_text(path, *args, **kwargs)
    def bytes_read(path, *args, **kwargs):
        return text.encode() if path == ROOT / MODEL else read_bytes(path, *args, **kwargs)
    pins = model_pins()
    with patch.object(Path, "read_text", text_read), patch.object(Path, "read_bytes", bytes_read):
        return extract_contract(ROOT, class_pins=pins)


@pytest.mark.parametrize("literal", ["synthetic://review", "synthetic:/*review*/", "synthetic://{\"quoted\"}"])
def test_comment_tokens_inside_owned_literal_are_not_comments(literal):
    import json
    from de4sdv.semantic.trace_vocabulary_contract import MODEL
    text = (ROOT / MODEL).read_text()
    old = '"Function-to-LogicalElement allocatedTo signature; historical provenance constrainedBy; stronger realizedBy/deployedTo active claims"'
    text = text.replace(old, json.dumps(literal), 1)
    assert _contract_from_model_text(text)["supersedes"] == literal


@pytest.mark.parametrize("field", ["supersedes", "retirement-predicate"])
def test_missing_required_record_field_is_a_controlled_refusal(field):
    from de4sdv.semantic.trace_vocabulary_contract import MODEL
    text = (ROOT / MODEL).read_text()
    if field == "supersedes":
        start = text.index("    attribute :>> supersedes =")
    else:
        start = text.index('    attribute :>> predicate = "realizedBy";')
    end = text.index("\n", start)
    with pytest.raises(ValueError):
        _contract_from_model_text(text[:start] + text[end:])


def test_class_pins_come_from_projection_layers_not_model_records():
    """The model carries no file-path class records: the pins come from the
    generated projection layers, and the contract records no input digests."""
    from de4sdv.semantic.model_contract import TRACE_CONTRACT_FIELDS
    from de4sdv.semantic.trace_vocabulary_contract import MODEL, extract_contract
    text = (ROOT / MODEL).read_text()
    assert "ClassRecord" not in text
    assert "sourceFile" not in text
    contract = extract_contract(ROOT, class_pins=model_pins())
    assert set(contract) == set(TRACE_CONTRACT_FIELDS) | {"id"}
    assert contract["classes"]["Function"] == {"file": MODEL, "declaration": "action def AllocatableFunction"}
    assert contract["classes"]["Requirement"]["declaration"] == "requirement def RequirementCandidate"


@pytest.mark.parametrize("mutation", ["remove-mapping", "ambiguous-specialization"])
def test_missing_or_ambiguous_class_pin_refuses(mutation):
    from dataclasses import replace
    from de4sdv.semantic import model_contract as mc
    from de4sdv.semantic.kernel_contract import KernelFileMapping
    from de4sdv.semantic.trace_vocabulary_contract import extract_contract
    _records, provisions = mc.load_model_layers(ROOT)
    if mutation == "remove-mapping":
        provisions = [p for p in provisions if p.identity != "AllocatableFunction"]
    else:
        template = next(p for p in provisions if p.identity == "AllocatableFunction")
        provisions = provisions + [replace(template, identity="SecondAllocatableFunction",
            mapping=KernelFileMapping("x.sysml", "action def Other"))]
    with pytest.raises(ValueError, match="missing endpoint class pin: Function"):
        extract_contract(ROOT, class_pins=mc.model_class_pins(provisions))


@pytest.mark.parametrize("declaration", ["", None, "part def", "  part def X", 123])
def test_malformed_class_pin_is_a_controlled_refusal(declaration):
    """QUALITY P2: blank/null/malformed pins raise ValueError, never a raw error."""
    from de4sdv.semantic.trace_vocabulary_contract import extract_contract
    pins = dict(model_pins())
    pins["Requirement"] = dict(pins["Requirement"], declaration=declaration)
    with pytest.raises(ValueError, match="malformed class pin"):
        extract_contract(ROOT, class_pins=pins)


def test_unbalanced_or_unreadable_pin_is_a_controlled_refusal():
    """QUALITY S2: malformed source raises ValueError, never IndexError."""
    from de4sdv.semantic.trace_vocabulary_contract import _definition_owner
    with pytest.raises(ValueError, match="unbalanced braces"):
        _definition_owner("}\n{ {\npart def X {}\n", "part def X")
    with pytest.raises(ValueError, match="not directly owned"):
        _definition_owner("part def X {}\n", "part def X")


def _semantics(contract):
    """Contract meaning without its id, which legitimately moves with the source."""
    return {key: value for key, value in contract.items() if key != "id"}


def test_commented_duplicate_record_cannot_override_the_active_record():
    """R2-SPEC-1: a commented decoy must not supply schema or supersedes."""
    import json
    from de4sdv.semantic.trace_vocabulary_contract import MODEL
    text = (ROOT / MODEL).read_text()
    anchor = "  part version : TraceVocabularyVersionRecord {"
    assert anchor in text
    decoy = ("/*\n  part version : TraceVocabularyVersionRecord {\n"
             '    attribute :>> version = "synthetic-decoy";\n'
             '    attribute :>> supersedes = "synthetic-decoy";\n'
             "  }\n*/\n")
    baseline = _semantics(_contract_from_model_text(text))
    commented = _semantics(_contract_from_model_text(text.replace(anchor, decoy + anchor, 1)))
    assert commented == baseline
    assert commented["schema"] == "de4sdv.relationship-successor/v1"
    assert "synthetic-decoy" not in json.dumps(commented)


@pytest.mark.parametrize("noise", ["attribute 'noise }' : String;",
                                   "attribute 'noise {' : String;",
                                   "attribute 'noise /*' : String;",
                                   'attribute noise : String = "} // /*";'])
def test_quoted_nonfield_tokens_do_not_move_the_record_boundary(noise):
    """Quoted tokens in a nested owner cannot supply direct record fields."""
    from de4sdv.semantic.trace_vocabulary_contract import MODEL
    text = (ROOT / MODEL).read_text()
    anchor = "  part version : TraceVocabularyVersionRecord {\n"
    assert anchor in text
    baseline = _semantics(_contract_from_model_text(text))
    nested = "    part def SyntheticNoise { " + noise + " }\n"
    inserted = _semantics(_contract_from_model_text(
        text.replace(anchor, anchor + nested, 1)))
    assert inserted == baseline


def test_duplicate_live_record_declaration_refuses_instead_of_first_match():
    from de4sdv.semantic.trace_vocabulary_contract import MODEL
    text = (ROOT / MODEL).read_text()
    anchor = "  part version : TraceVocabularyVersionRecord {\n"
    duplicate = anchor + '    attribute :>> version = "synthetic-decoy";\n' \
                         '    attribute :>> supersedes = "synthetic-decoy";\n  }\n'
    with pytest.raises(ValueError):
        _contract_from_model_text(text.replace(anchor, duplicate + anchor, 1))
