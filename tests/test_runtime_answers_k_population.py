"""The K pair is checked against the export's DerivesFromNeed connections, by id.

The reference population is every ``ConnectionUsage`` of the export that carries
an authored typing to the K pair's connection definition (or an authored
specialization of it), resolved through the ingestion-validated kernel binding,
never by name. Both navigations must return exactly that id set: counts are
never compared, so model growth cannot trip the gate and a count-preserving swap
cannot pass it. An absent or empty reference is never equivalence.

Synthetic collected records and synthetic element shapes; the end-to-end cases
run the real traversal over the minimized real-serializer K corpus. No API.
"""
from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from de4sdv.semantic import runtime_answers as ra
from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.revisions import KernelElementBinding

FORWARD, INVERSE = "derivedRequirementsOfNeed", "derivesRequirementFromNeed"


def _collected(forward, inverse=None, *, unresolved=()):
    inverse = forward if inverse is None else inverse

    def records(witnesses):
        return {f"s-{w}": {"witnesses": [w]} for w in witnesses}

    return {FORWARD: {"records": records(forward), "unresolved": list(unresolved)},
            INVERSE: {"records": records(inverse), "unresolved": []}}


def _ids(count, prefix="c"):
    return [f"{prefix}-{i}" for i in range(count)]


# -- k_self_evidence: sets of ids, never counts --------------------------------


@pytest.mark.parametrize("count", [1, 5, 27, 28, 40])
def test_navigations_equal_to_the_export_population_are_equivalent(count):
    """Any population size passes when both navigations return exactly the export's ids."""
    facts = _ids(count)
    result = ra.k_self_evidence(_collected(facts), facts)
    assert result["classification"] == "EQUIVALENT", result
    assert result["population_complete"] is True
    assert result["export_witness_population"] == sorted(facts)
    assert result["forward_witness_population"] == result["inverse_witness_population"] == sorted(facts)
    assert not result["errors"] and not result["missing"]


def test_a_missed_export_connection_is_never_equivalence():
    facts = _ids(27)
    runtime = [f for f in facts if f != "c-7"]
    result = ra.k_self_evidence(_collected(runtime), facts)
    assert result["classification"] == "NOT_YET_COMPARABLE"
    assert result["population_complete"] is False
    assert any(m.startswith("forward") and "c-7" in m for m in result["missing"]), result["missing"]
    assert any(m.startswith("inverse") and "c-7" in m for m in result["missing"]), result["missing"]


def test_a_witness_that_is_not_an_export_connection_blocks():
    facts = _ids(27)
    result = ra.k_self_evidence(_collected(facts + ["not-a-derivation"]), facts)
    assert result["classification"] == "BLOCKING_MISMATCH"
    assert any("not-a-derivation" in e for e in result["errors"]), result["errors"]


def test_a_count_preserving_swap_is_caught():
    """27 runtime witnesses against 27 export connections, one of them different."""
    facts = _ids(27)
    swapped = [f for f in facts if f != "c-3"] + ["other-connection"]
    assert len(swapped) == len(facts)
    result = ra.k_self_evidence(_collected(swapped), facts)
    assert result["classification"] == "BLOCKING_MISMATCH"
    assert any("other-connection" in e for e in result["errors"])
    assert any("c-3" in m for m in result["missing"])


def test_each_navigation_must_match_on_its_own():
    facts = _ids(6)
    result = ra.k_self_evidence(_collected(facts[:-1], facts), facts)
    assert result["classification"] == "BLOCKING_MISMATCH"
    assert any("do not share one witness population" in e for e in result["errors"])
    assert any(m.startswith("forward") and "c-5" in m for m in result["missing"])
    assert not any(m.startswith("inverse") for m in result["missing"])


def test_an_empty_export_population_is_never_equivalence():
    result = ra.k_self_evidence(_collected([]), [])
    assert result["classification"] == "NOT_YET_COMPARABLE"
    assert result["population_complete"] is False
    assert any("no DerivesFromNeed connection" in m for m in result["missing"]), result["missing"]


def test_runtime_witnesses_against_an_empty_export_population_block():
    result = ra.k_self_evidence(_collected(["c-0"]), [])
    assert result["classification"] == "BLOCKING_MISMATCH"
    assert any("c-0" in e for e in result["errors"])


def test_without_an_export_reference_the_pair_is_never_equivalent():
    result = ra.k_self_evidence(_collected(_ids(27)))
    assert result["classification"] == "NOT_YET_COMPARABLE"
    assert result["export_witness_population"] is None
    assert any("no export reference" in m for m in result["missing"]), result["missing"]


def test_an_export_reference_error_is_reported():
    result = ra.k_self_evidence(_collected(_ids(3)), None, export_error="binding lacks the definition")
    assert result["classification"] == "NOT_YET_COMPARABLE"
    assert "binding lacks the definition" in result["missing"][0]


def test_a_fact_answered_twice_still_blocks():
    facts = _ids(3)
    collected = _collected(facts)
    collected[FORWARD]["records"]["s-extra"] = {"witnesses": ["c-0"]}
    result = ra.k_self_evidence(collected, facts)
    assert result["classification"] == "BLOCKING_MISMATCH"
    assert any("duplicates modeled facts" in e for e in result["errors"])


def test_an_unresolved_subject_is_never_equivalence():
    facts = _ids(3)
    collected = _collected(facts, unresolved=[{"subject_id": "s-x", "error": "broken end"}])
    result = ra.k_self_evidence(collected, facts)
    assert result["classification"] == "NOT_YET_COMPARABLE"
    assert any("unresolved K subject" in m for m in result["missing"])


def test_no_reviewed_count_remains():
    assert not hasattr(ra, "READINESS_BASELINE_K_WITNESS_COUNT")


# -- k_export_witnesses: the export's modeled facts, by kernel-bound identity --

DFN = "def-derives"
DFN_SPECIAL = "def-derives-special"
OTHER_DEF = "def-other"
HOMONYM = "def-homonym"


def _index(element_id=DFN):
    binding = SimpleNamespace(kernel_bindings=(KernelElementBinding(
        ontology_class="DerivesFromNeed", element_id=element_id,
        source_file="textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml",
        declaration="connection def DerivesFromNeed"),))
    return KernelBindingIndex.from_binding(binding)


def _typing(typing_id, feature, type_id, *, implied=False):
    element = {"@id": typing_id, "@type": "FeatureTyping", "owningRelatedElement": {"@id": feature},
               "typedFeature": {"@id": feature}, "type": {"@id": type_id}}
    if implied:
        element["isImplied"] = True
    return element


def _corpus():
    return [
        {"@id": DFN, "@type": "ConnectionDefinition", "declaredName": "DerivesFromNeed"},
        {"@id": DFN_SPECIAL, "@type": "ConnectionDefinition", "declaredName": "SpecialDerivation"},
        {"@id": "sub-special", "@type": "Subclassification", "subclassifier": {"@id": DFN_SPECIAL},
         "superclassifier": {"@id": DFN}},
        {"@id": OTHER_DEF, "@type": "ConnectionDefinition", "declaredName": "Satisfies"},
        # a homonym of the bound definition, never bound: names never finish identity
        {"@id": HOMONYM, "@type": "ConnectionDefinition", "declaredName": "DerivesFromNeed"},
        {"@id": "c-typed", "@type": "ConnectionUsage"},
        _typing("t-typed", "c-typed", DFN),
        {"@id": "c-special", "@type": "ConnectionUsage"},
        _typing("t-special", "c-special", DFN_SPECIAL),
        {"@id": "c-other", "@type": "ConnectionUsage"},
        _typing("t-other", "c-other", OTHER_DEF),
        {"@id": "c-implied", "@type": "ConnectionUsage"},
        _typing("t-implied", "c-implied", DFN, implied=True),
        {"@id": "c-homonym", "@type": "ConnectionUsage"},
        _typing("t-homonym", "c-homonym", HOMONYM),
        {"@id": "dep", "@type": "Dependency", "client": [{"@id": "x"}], "supplier": [{"@id": "y"}]},
    ]


def _export_witnesses(elements, index=None):
    return ra.k_export_witnesses(elements, connection_definition="DerivesFromNeed",
                                 kernel_bindings=index or _index())


def test_export_witnesses_are_the_connections_typed_by_the_bound_definition():
    assert _export_witnesses(_corpus()) == ["c-special", "c-typed"]


def test_export_witnesses_never_use_names():
    elements = _corpus()
    for element in elements:
        if element["@id"] == DFN:
            element["declaredName"] = "RenamedInTheExport"
    assert _export_witnesses(elements) == ["c-special", "c-typed"]
    # the binding, not the name, selects the definition
    assert _export_witnesses(_corpus(), _index(HOMONYM)) == ["c-homonym"]


def test_export_witnesses_require_a_validated_binding():
    with pytest.raises(IdentityNotFoundError):
        ra.k_export_witnesses(_corpus(), connection_definition="DerivesFromNeed",
                              kernel_bindings=KernelBindingIndex.from_binding(
                                  SimpleNamespace(kernel_bindings=())))
    with pytest.raises(IdentityNotFoundError):  # the bound element is absent from this export
        _export_witnesses([e for e in _corpus() if e["@id"] != DFN])
    with pytest.raises(IdentityNotFoundError):
        ra.k_export_witnesses(_corpus(), connection_definition="DerivesFromNeed", kernel_bindings=None)


def test_export_witnesses_are_empty_when_no_connection_carries_the_definition():
    elements = [e for e in _corpus() if e["@id"] not in ("t-typed", "t-special")]
    assert _export_witnesses(elements) == []
    assert ra.k_self_evidence(_collected([]), _export_witnesses(elements))["classification"] \
        == "NOT_YET_COMPARABLE"


def test_the_k_pair_names_one_connection_definition():
    from model_contract_fixtures import model_contract

    assert ra.k_connection_definition(model_contract()) == "DerivesFromNeed"
    split = SimpleNamespace(relationship_mapping=lambda name: SimpleNamespace(
        configuration={"connection_definition": "A" if name == FORWARD else "B"}))
    with pytest.raises(ValueError, match="one connection definition"):
        ra.k_connection_definition(split)


# -- end to end: the real traversal over the real-serializer K corpus ----------

BICYCLE = "r6-conn-reqBicycleTargetResponse"


def _service():
    from model_contract_fixtures import model_contract
    from test_k_real_serializer_shapes import _binding_index

    from de4sdv.semantic.traversal import SemanticTraversal

    contract = model_contract()
    return SimpleNamespace(
        contract=contract,
        traversal=SemanticTraversal(contract, kernel_bindings=_binding_index()),
        binding=SimpleNamespace(git_commit="0" * 40, sysml_project_id="p", sysml_commit_id="c",
                                scope="full-model"))


def _k_pair(service, live, export):
    collected = {p: ra.collect_predicate(service, p, live) for p in ra.K_PAIR}
    return ra.k_pair_evidence(service, collected, export)


def test_runtime_navigations_cover_exactly_the_export_connections():
    from test_k_real_serializer_shapes import real_shape_elements

    elements = real_shape_elements()
    result = _k_pair(_service(), elements, elements)
    assert result["classification"] == "EQUIVALENT", result
    connections = sorted(e["@id"] for e in elements if str(e.get("@type")) == "ConnectionUsage")
    assert result["export_witness_population"] == connections
    assert result["forward_witness_population"] == result["inverse_witness_population"] == connections


def test_a_connection_the_runtime_does_not_answer_is_named():
    """The queried corpus lost one connection's definition typing; the export still models it."""
    from test_k_real_serializer_shapes import real_shape_elements

    export = real_shape_elements()
    typing = "r6-conn-typing-reqBicycleTargetResponse"
    live = [e for e in copy.deepcopy(export) if e["@id"] != typing]
    for element in live:
        if element["@id"] == BICYCLE:
            element["ownedRelationship"] = [r for r in element["ownedRelationship"]
                                            if r["@id"] != typing]
    result = _k_pair(_service(), live, export)
    assert result["classification"] == "NOT_YET_COMPARABLE", result
    assert BICYCLE in result["export_witness_population"]
    assert BICYCLE not in result["forward_witness_population"]
    assert any(m.startswith("forward") and BICYCLE in m for m in result["missing"]), result["missing"]


def test_an_unresolvable_export_reference_is_recorded_not_raised():
    from test_k_real_serializer_shapes import real_shape_elements

    elements = real_shape_elements()
    export = [e for e in elements if e["@id"] != "r6-def"]
    result = _k_pair(_service(), elements, export)
    assert result["classification"] == "NOT_YET_COMPARABLE"
    assert result["export_witness_population"] is None
    assert any("cannot be resolved" in m for m in result["missing"]), result["missing"]


def test_collect_answers_checks_the_k_pair_against_the_supplied_export(monkeypatch):
    seen = {}

    def fake_collect(service, predicate, elements):
        return {"subjects": ["s-c-0"], "records": {"s-c-0": {"witnesses": ["c-0"]}},
                "unresolved": []}

    def fake_evidence(service, collected, export_elements):
        seen["export"] = export_elements
        return {"classification": "EQUIVALENT"}

    monkeypatch.setattr(ra, "collect_predicate", fake_collect)
    monkeypatch.setattr(ra, "class_identities", lambda service, **kwargs: {})
    monkeypatch.setattr(ra, "k_pair_evidence", fake_evidence)
    service = SimpleNamespace(binding=SimpleNamespace(git_commit="a" * 40, sysml_project_id="p",
                                                      sysml_commit_id="c", scope="full-model"))
    report = ra.collect_answers(service, [{"@id": "live"}], label="mab:x",
                                export_elements=[{"@id": "export"}])
    assert seen["export"] == [{"@id": "export"}]
    assert report["k_pair"] == {"classification": "EQUIVALENT"}
    ra.collect_answers(service, [], label="mab:x")
    assert seen["export"] is None
