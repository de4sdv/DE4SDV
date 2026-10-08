"""Revision-scoped index over one element corpus, shared by the traversal.

A SysML API commit is immutable, so everything derived from its element
corpus (element lookup, ownership, typing and specialization indexes, the
relationship graph) is built once and reused for every query over that exact
corpus. These tests pin the accessors, prove that a traversal reusing the
index returns exactly what a fresh traversal returns, and that the index is
keyed by the corpus itself, never shared across corpora.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from de4sdv.semantic import relationship_successor as successor_module
from de4sdv.semantic import traversal as traversal_module
from de4sdv.semantic.model_authority_runtime import ModelAuthorityTraversal
from de4sdv.semantic.model_edges import lineage_index, typing_index
from de4sdv.semantic.relationship_successor import route_successor_bindings
from de4sdv.semantic.revision_index import RevisionIndex, ValueLeaf
from de4sdv.sysml_api.revisions import KernelElementBinding
from increment_model_fixtures import INFINITY, ModelBuilder
from model_contract_fixtures import model_facade


def _derivation_model(with_connection: bool = True):
    builder = ModelBuilder(label="derivation")
    need_root = builder.kernel_definition("Need")
    requirement_root = builder.kernel_definition("Requirement")
    derives = builder.kernel_definition("DerivesFromNeed")
    package = builder.package("FixturePackage")
    need_def = builder.definition("RequirementDefinition", "FixtureNeed", package, [need_root])
    requirement_def = builder.definition("RequirementDefinition", "FixtureRequirement", package,
                                         [requirement_root])
    needs = [builder.usage("RequirementUsage", f"need{i}", package, [need_def]) for i in range(2)]
    requirements = [builder.usage("RequirementUsage", f"requirement{i}", package, [requirement_def])
                    for i in range(3)]
    if with_connection:
        builder.connection("requirement0DerivedFromNeed0", package, derives,
                           [("need", needs[0]), ("derivedRequirement", requirements[0])])
        builder.connection("requirement1DerivedFromNeed1", package, derives,
                           [("need", needs[1]), ("derivedRequirement", requirements[1])])
    case_def = builder.definition("VerificationCaseDefinition", "FixtureCaseDefinition", package)
    builder.objective(case_def, "fixtureObjective", [requirements[0], requirements[2]])
    builder.usage("VerificationCaseUsage", "fixtureCase", package, [case_def])
    return builder, requirements


def _traversal(builder: ModelBuilder) -> ModelAuthorityTraversal:
    facade = model_facade()
    bindings = SimpleNamespace(kernel_bindings=tuple(
        KernelElementBinding.from_dict(item) for item in builder.bindings))
    index, _routes = route_successor_bindings(facade.profile, bindings)
    return ModelAuthorityTraversal(facade, kernel_bindings=index)


def _hops(traversal, predicate, source, elements):
    return sorted(
        (hop.predicate, hop.strategy, hop.source["@id"], hop.target["@id"], hop.api_object["@id"],
         repr(sorted(hop.witness.items())) if hop.witness else "")
        for hop in traversal.traverse(predicate, source, elements)
    )


def test_index_accessors_follow_export_shapes() -> None:
    builder = ModelBuilder(label="accessors")
    package = builder.package("FixturePackage")
    phase = builder.enumeration("MethodPhase", ["phase4_needs", "phase5_requirements"])
    part_def = builder.definition("PartDefinition", "FixturePart", package)
    part = builder.usage("PartUsage", "fixturePart", package, [part_def], short="INC-FIXTURE-001")
    builder.attribute(part, "label", "text value")
    builder.attribute(part, "count", 3)
    builder.attribute(part, "flag", True)
    builder.attribute(part, "upper", INFINITY)
    builder.attribute(part, "phases", [phase["phase4_needs"], phase["phase5_requirements"]])
    holder = builder.references(package, part)
    index = RevisionIndex(builder.elements, sources=builder.sources)

    assert index.by_id[part["@id"]] is part
    assert index.owner_of(part["@id"]) == package["@id"]
    assert part["@id"] in index.owned_members(package["@id"], "PartUsage")
    assert index.with_short_name("INC-FIXTURE-001") == (part["@id"],)
    assert index.feature_values(part["@id"], "label") == (ValueLeaf("string", "text value"),)
    assert index.feature_values(part["@id"], "count") == (ValueLeaf("integer", 3),)
    assert index.feature_values(part["@id"], "flag") == (ValueLeaf("boolean", True),)
    assert index.feature_values(part["@id"], "upper") == (ValueLeaf("infinity", None),)
    assert index.feature_values(part["@id"], "phases") == (
        ValueLeaf("reference", phase["phase4_needs"]["@id"]),
        ValueLeaf("reference", phase["phase5_requirements"]["@id"]),
    )
    assert index.feature_values(part["@id"], "missing") == ()
    assert index.declared_of(holder["@id"]) == part["@id"]
    assert index.qualified_name(part["@id"]) == "FixturePackage::fixturePart"
    assert index.source_of(part["@id"]) == builder.sources[part["@id"]]
    assert index.typed_by(part["@id"]) == frozenset({part_def["@id"]})


def test_graph_indexes_equal_the_direct_computation() -> None:
    builder, _ = _derivation_model()
    index = RevisionIndex(builder.elements)
    node_ids = list(index.by_id)
    explicit, implied = lineage_index(index.graph, node_ids)
    typed, typed_implied = typing_index(index.graph, node_ids)
    indexes = index.graph_indexes()
    assert (indexes.explicit_specifics, indexes.implied_specifics) == (explicit, implied)
    assert (indexes.typed_by, indexes.typed_by_implied) == (typed, typed_implied)
    assert index.graph_indexes() is indexes


def test_reused_traversal_equals_fresh_traversal() -> None:
    builder, requirements = _derivation_model()
    elements = builder.elements
    reused = _traversal(builder)
    for predicate in ("derivesRequirementFromNeed", "verifiedBy"):
        for requirement in requirements:
            fresh = _traversal(builder)
            assert _hops(reused, predicate, requirement, elements) == _hops(
                fresh, predicate, requirement, elements
            ), (predicate, requirement["declaredName"])
    assert [h[3] for h in _hops(reused, "derivesRequirementFromNeed", requirements[0], elements)]


def test_traversal_builds_the_relationship_graph_once_per_corpus(monkeypatch: pytest.MonkeyPatch) -> None:
    builder, requirements = _derivation_model()
    builds: list[int] = []
    original = traversal_module.build_relationship_graph

    def counting(elements):
        builds.append(1)
        return original(elements)

    monkeypatch.setattr(traversal_module, "build_relationship_graph", counting)
    monkeypatch.setattr("de4sdv.semantic.revision_index.build_relationship_graph", counting)
    monkeypatch.setattr(successor_module, "build_relationship_graph", counting)
    traversal = _traversal(builder)
    for requirement in requirements:
        traversal.traverse("derivesRequirementFromNeed", requirement, builder.elements)
        traversal.traverse("verifiedBy", requirement, builder.elements)
    assert len(builds) == 1


def test_index_is_keyed_by_the_corpus_never_shared_across_corpora() -> None:
    with_connection, requirements = _derivation_model(with_connection=True)
    without = copy.deepcopy(with_connection.elements)
    connection_ids = {e["@id"] for e in without if e["@type"] == "ConnectionUsage"}
    without = [e for e in without if e["@id"] not in connection_ids]
    traversal = _traversal(with_connection)
    source = requirements[0]
    assert _hops(traversal, "derivesRequirementFromNeed", source, with_connection.elements)
    assert _hops(traversal, "derivesRequirementFromNeed", source, without) == []
    assert _hops(traversal, "derivesRequirementFromNeed", source, with_connection.elements)
    assert traversal.revision_index(with_connection.elements).elements is with_connection.elements
    assert traversal.revision_index(without).elements is without
