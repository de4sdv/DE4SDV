"""Model-authority runtime: the model-built contract served through the live services.

Synthetic exact-binding fixtures over the real model-built contract; the real
facade and the production service assembly run, only the API transport is
replaced. The startup check that precedes this assembly in production (exact
commit, clean tree, ``sai-`` identity, served model) is tested in
``test_deployment_runtime.py``; there is no bundle, closure or activation
step (owner decision 2026-10-11). No live-API claim follows from these tests.
"""
import json
from pathlib import Path

import pytest
import mcp.client.stdio  # noqa: F401 — bind stderr during collection

from de4sdv.semantic import model_authority_runtime as mar
from de4sdv.semantic import model_contract as mc
from de4sdv.semantic import model_projection_coverage as coverage
from de4sdv.semantic.kernel_contract import (
    KernelFileMapping,
    KernelNativeMapping,
    RetiredIdentityError,
    declaration_identity,
)
from de4sdv.sysml_api.repository import SysMLRepository
from de4sdv.sysml_api.revisions import RevisionBinding
from tests.model_contract_fixtures import binding_dict, model_contract

ROOT = Path(__file__).resolve().parents[1]
REVISION = "a" * 40
EC_DEFS = 8


def _elements_and_bindings(ec_defs=EC_DEFS):
    """Synthetic API elements and ingestion-validated kernel bindings.

    Every file-mapped class of the model-built contract (and the successor
    profile pins) gets one root element and one kernel binding, so lineage,
    successor routing and the EvidenceContract discriminator resolve by
    validated identity, never by name.
    """
    contract = mar.trace_contract(ROOT)
    model = model_contract()
    pins = {}
    for name, pin in {**contract["classes"], **contract["carriers"]}.items():
        pins.setdefault(name, (pin["file"], pin["declaration"]))
    ec = model.class_mapping("EvidenceContract")
    pins["EvidenceContract"] = (ec.file, ec.declaration)
    for name in model.classes:  # complete lineage roots (e.g. DerivesFromNeed)
        mapping = model.mapping(name)
        if (isinstance(mapping, KernelFileMapping) and name not in model.lineage_pinned
                and mapping.declaration not in {p[1] for p in pins.values()}):
            pins.setdefault(name, (mapping.file, mapping.declaration))
    bindings, elements = [], []
    for name, (source_file, declaration) in sorted(pins.items()):
        declared, metaclass = declaration_identity(declaration)
        bindings.append(dict(ontology_class=name, element_id="root-" + name,
                             source_file=source_file, declaration=declaration))
        elements.append({"@id": "root-" + name, "@type": metaclass, "declaredName": declared})
    for name, kind in [("Requirement", "RequirementUsage"), ("Function", "ActionUsage"),
                       ("LogicalElement", "PartUsage"), ("PhysicalElement", "PartUsage"),
                       ("Need", "RequirementUsage"), ("ValidationScenario", "PartUsage"),
                       ("RegulatorySource", "PartUsage")]:
        elements.append({"@id": "use-" + name, "@type": kind, "type": [{"@id": "root-" + name}]})
    elements.append({"@id": "context", "@type": "Package"})
    for index in range(ec_defs):
        elements.append({"@id": f"ec-def-{index}", "@type": "RequirementDefinition",
                         "superclassifier": [{"@id": "root-EvidenceContract"}]})
        elements.append({"@id": f"ec-use-{index}", "@type": "RequirementUsage",
                         "type": [{"@id": f"ec-def-{index}"}]})
        elements.append({"@id": f"ec-dep-{index}", "@type": "Dependency",
                         "source": [{"@id": f"ec-use-{index}"}],
                         "target": [{"@id": "use-Requirement"}]})
    # An acceptance-criterion-like verified requirement usage must stay outside.
    elements.append({"@id": "ac-use", "@type": "RequirementUsage", "type": [{"@id": "root-Requirement"}]})
    elements.append({"@id": "ac-dep", "@type": "Dependency", "source": [{"@id": "ac-use"}],
                     "target": [{"@id": "use-Requirement"}]})
    return elements, bindings


def _edge(kind, source, target, name, **kwargs):
    return {"@id": name, "@type": kind, "source": [{"@id": source}], "target": [{"@id": target}],
            "owningNamespace": {"@id": "context"}, **kwargs}


def _fixture(tmp_path, *, ec_defs=EC_DEFS):
    elements, bindings = _elements_and_bindings(ec_defs)
    elements += [
        _edge("AllocationUsage", "use-Requirement", "use-Function", "alloc-rf"),
        _edge("AllocationUsage", "use-Function", "use-LogicalElement", "alloc-fl"),
        _edge("AllocationUsage", "use-LogicalElement", "use-PhysicalElement", "alloc-lp"),
        _edge("ConnectionUsage", "use-Need", "use-ValidationScenario", "plan",
              type=[{"@id": "root-hasValidationScenario"}]),
        _edge("ConnectionUsage", "use-Requirement", "use-RegulatorySource", "source",
              type=[{"@id": "root-hasRegulatorySource"}]),
    ]
    document = binding_dict(git_repository="de4sdv/DE4SDV", git_commit=REVISION,
                            import_timestamp="2026-10-07T00:00:00Z",
                            import_tool_version="fixture", kernel_bindings=bindings)
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(document))
    return dict(elements=elements, binding_path=binding_path,
                binding=RevisionBinding.load(binding_path), tmp_path=tmp_path)


@pytest.fixture
def fx(tmp_path, monkeypatch):
    data = _fixture(tmp_path)
    monkeypatch.setattr(SysMLRepository, "list_elements", lambda self, *a, **k: data["elements"])
    return data


def _service(fx):
    """The production service assembly over the synthetic transport."""
    from de4sdv.sysml_api.client import ApiClient

    return mar.assemble_model_services(
        mar.model_facade(ROOT), fx["binding"], SysMLRepository(ApiClient("http://127.0.0.1:1")),
        expected_git_revision=REVISION)


def test_model_refusal_is_a_value_error():
    assert issubclass(mar.ModelAuthorityRefused, ValueError)


def test_served_authority_is_the_contract_identity(fx):
    service = _service(fx)
    identity = model_contract().identity.id
    assert service.semantic_authority_id == identity == service.contract.authority_id
    status = service.model_status()["semantic_authority"]
    assert status["id"] == status["semantic_authority"] == identity
    sources = [entry["source"] for entry in service._provenance()]
    assert f"semantic-authority://{identity}" in sources
    assert not any(s.startswith(("model-authority://", "implementation://")) for s in sources)


def _split(provisions):
    return ([p for p in provisions if p.layer != mc.FROZEN_RECORD_LAYER],
            [p for p in provisions if p.layer == mc.FROZEN_RECORD_LAYER])


def test_routing_is_disjoint_and_a_planted_duplicate_is_refused():
    routing = mar.model_facade(ROOT)._components["routing"]
    assert routing["duplicates"] == [] and routing["residual"] == {}
    assert sum(1 for v in routing["providers"].values() if v == "o2-chain") == 13
    _, provisions = mar.load_layers(ROOT)
    layered, chain = _split(provisions)
    planted = layered + [mar.Provision("Need", "class", "o2plus", mapping=KernelNativeMapping("impostor"))]
    successor = mar.trace_contract(ROOT)
    result = mar.compute_routing(provisions=planted, successor_contract=successor, seed=chain)
    assert result.duplicates
    with pytest.raises(mar.ModelAuthorityRefused, match="duplicate"):
        mar.ModelAuthorityFacade(contract=model_contract(), routing=result, successor_contract=successor,
                                 components={})


def test_retained_row_without_provider_is_a_refused_residual():
    _, provisions = mar.load_layers(ROOT)
    layered, chain = _split(provisions)
    dropped = [p for p in layered if p.identity != "specifiesFunction"]
    result = mar.compute_routing(provisions=dropped,
                                 successor_contract=mar.trace_contract(ROOT),
                                 register_rows=mar.load_register_rows(ROOT), seed=chain)
    assert "specifiesFunction" in result.residual
    with pytest.raises(mar.ModelAuthorityRefused, match="residual"):
        mar.ModelAuthorityFacade(contract=model_contract(), routing=result,
                                 successor_contract=mar.trace_contract(ROOT),
                                 components={})


# -- batch-2 layer loader (schema de4sdv.o4-definition-batch2-*/v1) ----------


def _kbc(name):
    mapping = model_contract().class_mapping(name)
    return {"source_file": mapping.file, "declaration": mapping.declaration}


def _kernel_vocabulary_class_row(name, **grounding):
    return {"identity": name, "semantic_kind": "class", "admission_class": "definition",
            "accounting": "retained", "support": "vocabulary-only", "traversal": False,
            "grounding": {"ontology_relations": {"sub_class_of": None, "disjoint_with": []},
                          **grounding}}


def _kernel_vocabulary_relation_row(name, admission, domain, range_, strength=None, **extra):
    return {"identity": name, "semantic_kind": "relationship", "admission_class": admission,
            "accounting": "retained", "support": "vocabulary-only", "traversal": False,
            "relation": {"domain": {"ontology_class": domain}, "range": {"ontology_class": range_},
                         "semantic_strength": strength}, **extra}


def _kernel_vocabulary_profile_entry(name, **extra):
    return {"profile_identity": f"de4sdv.o4-definition-batch2-profile/v1#{name}",
            "for_concept": name, "representation_class": "synthetic", **extra}


def _retired(name, domain, range_, successor, navigation):
    row = dict(_kernel_vocabulary_relation_row(name, "retired-name", domain, range_),
               retired={"successor": successor, "successor_navigation": navigation,
                        "refusal": f"retired; use {navigation}"})
    return row, {"retired_resolution": {"successor": successor, "navigation": navigation}}


def _kernel_vocabulary_rows():
    contract = mar.trace_contract(ROOT)
    pairs = [{"source_class": r["sourceClass"], "target_class": r["targetClass"]}
             for r in contract["relations"]["allocatedTo"]]
    dependency = {"strategy": "dependency", "relationship_types": ["Dependency"],
                  "direction": "incoming", "source_property": "source",
                  "target_property": "target", "source_types": ["RequirementUsage"]}
    closure = [{"source_file": f"f{i}.sysml", "declaration": f"requirement def C{i}"}
               for i in range(EC_DEFS)]
    hrec = _kernel_vocabulary_relation_row("hasRelevantEvidenceContract", "relationship-runtime", "Requirement",
                                           "EvidenceContract", "relevance")
    hrec["relation"]["range"]["discriminator"] = {"kind": "type-lineage",
                                                  "lineage": _kbc("EvidenceContract"),
                                                  "closure": closure}
    rows = [
        (_kernel_vocabulary_class_row("EvidenceContract", kernel_binding_contract=_kbc("EvidenceContract")), {}),
        (_kernel_vocabulary_class_row("Interface", kernel_native="SysML v2 port def and connection elements"), {}),
        (_kernel_vocabulary_class_row("EvidenceStatus", kernel_external=(
            "ODE4HERA requirements-management library VVStatus (NRM A13+A14) via the "
            "DE4SDV method-context adapter")), {}),
        (_kernel_vocabulary_relation_row("variesAt", "relationship-vocabulary", "Feature", "VariationPoint"), {}),
        (dict(_kernel_vocabulary_relation_row("syntheticCarrierRelation", "relationship-vocabulary",
                                              "EngineeringIncrement", "Stakeholder"),
              carrier={"source_file": "x.sysml", "declaration": "connection def SyntheticCarrierRelation"}), {}),
        (hrec, {"serializer_mechanics": dependency}),
        (_kernel_vocabulary_relation_row("hasEvidence", "external-reference", "VerificationCase", "EvidenceArtifact",
                                         "external-data-required"),
         {"serializer_mechanics": {"strategy": "external"}}),
        ({"identity": "allocatedTo", "semantic_kind": "relationship", "admission_class": "successor",
          "accounting": "retained", "support": "runtime-mapped-candidate", "traversal": False,
          "successor": {"contract": contract["schema"], "end_pairs": pairs}}, {}),
        _retired("realizedBy", "Requirement", "ArchitectureElement", "allocatedTo", "allocatedTo"),
        _retired("constrainedBy", "Requirement", "RegulatoryConstraint", "hasRegulatorySource",
                 "hasRegulatorySource"),
        (_kernel_vocabulary_class_row("Function", kernel_native=(
            "SysML v2 action/state/behavior definitions in functional-architecture slices")), {}),
        (_kernel_vocabulary_class_row("AllocatableFunction", kernel_binding_contract=_kbc("AllocatableFunction"),
                                      ontology_relations={"sub_class_of": "Function", "disjoint_with": []}), {}),
        _retired("validatesFitnessForUse", "ValidationScenario", "Need", "hasValidationScenario",
                 "validationScenarioFor"),
    ]
    return rows


def _kernel_vocabulary_root(tmp_path, rows):
    root = tmp_path / "root"
    paths = [relative for spec in mar.LAYERS for relative in (spec.projection_path, spec.profile_path)]
    paths += [relative for relative, _ in mc.FROZEN_PROJECTION_RECORDS + mc.FROZEN_PROFILE_RECORDS]
    for relative in paths:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_bytes((ROOT / relative).read_bytes())
    spec = mar.KERNEL_VOCABULARY_LAYER
    binding = {"source_revision": REVISION}
    (root / spec.projection_path).write_text(json.dumps(
        {"schema": spec.projection_schema, "binding": binding, "rows": [r for r, _ in rows]}))
    (root / spec.profile_path).write_text(json.dumps(
        {"schema": spec.profile_schema, "binding": binding,
         "entries": [_kernel_vocabulary_profile_entry(r["identity"], **e) for r, e in rows]}))
    return root


def _kernel_vocabulary_routing(root):
    _, provisions = mar.load_layers(root)
    layered, chain = _split(provisions)
    return mar.compute_routing(provisions=layered,
                               successor_contract=mar.trace_contract(ROOT),
                               register_rows=mar.load_register_rows(ROOT), seed=chain)


def test_kernel_vocabulary_layer_is_loaded_exactly_when_its_pair_is_present():
    records, _ = mar.load_layers(ROOT)
    present = (ROOT / mar.KERNEL_VOCABULARY_LAYER.projection_path).exists()
    assert ("definition-batch2" in [r["layer"] for r in records]) is present


def test_kernel_vocabulary_rows_route_through_their_layer(tmp_path):
    root = _kernel_vocabulary_root(tmp_path, _kernel_vocabulary_rows())
    records, provisions = mar.load_layers(root)
    assert [r["layer"] for r in records][-1] == "definition-batch2"
    routing = _kernel_vocabulary_routing(root)
    assert routing.duplicates == ()
    for name in ("EvidenceContract", "Interface", "EvidenceStatus", "variesAt", "syntheticCarrierRelation",
                 "hasRelevantEvidenceContract", "hasEvidence"):
        assert routing.providers[name].layer == "definition-batch2", name
        assert name not in routing.residual
    assert routing.providers["EvidenceContract"].mapping == model_contract().mapping("EvidenceContract")
    assert routing.providers["Interface"].mapping == KernelNativeMapping(
        "SysML v2 port def and connection elements")
    assert routing.providers["hasRelevantEvidenceContract"].relationship.strategy == "dependency"
    assert routing.providers["hasEvidence"].relationship.strategy == "external"
    discriminator = routing.providers["hasRelevantEvidenceContract"].spec["range_discriminator"]
    assert discriminator["kind"] == "type-lineage" and len(discriminator["closure"]) == 8
    # The successor row corroborates the model-generated successor contract.
    assert routing.providers["allocatedTo"].layer == "successor-contract"
    assert "definition-batch2" in routing.corroborations["allocatedTo"]
    # A natively represented successor endpoint class: the model-derived lineage
    # pin owns the runtime mapping; the batch-2 row corroborates it.
    assert routing.providers["Function"].layer == "successor-contract"
    assert routing.corroborations["Function"] == ("definition-batch2",)
    assert routing.providers["AllocatableFunction"].layer == "definition-batch2"
    # Retired-name rows (D4) never become providers; they name the refusal target.
    for name, navigation in (("realizedBy", "allocatedTo"), ("constrainedBy", "hasRegulatorySource"),
                             ("validatesFitnessForUse", "validationScenarioFor")):
        assert name not in routing.providers and name not in routing.residual
        assert routing.corroborations[name] == ("definition-batch2",)
        assert routing.retired_names[name] == navigation


def test_a_declared_closure_of_any_size_routes(tmp_path):
    """The discriminator closure is the set of evidence contracts the model
    declares: one more well-formed member is served, not refused by a count."""
    rows = _kernel_vocabulary_rows()
    closure = rows[5][0]["relation"]["range"]["discriminator"]["closure"]
    closure.append({"source_file": "f-new.sysml", "declaration": "requirement def CNew"})
    routing = _kernel_vocabulary_routing(_kernel_vocabulary_root(tmp_path, rows))
    discriminator = routing.providers["hasRelevantEvidenceContract"].spec["range_discriminator"]
    assert [m["declaration"] for m in discriminator["closure"]] == [m["declaration"] for m in closure]


def _facade_declaring(tmp_path, size):
    """The checkout's contract with its evidence-contract closure grown to ``size`` members."""
    import shutil

    root = tmp_path / "declared"
    shutil.copytree(ROOT / "de4sdv/semantic/contract-data", root / "de4sdv/semantic/contract-data")
    path = root / mar.KERNEL_VOCABULARY_LAYER.projection_path
    document = json.loads(path.read_text(encoding="utf-8"))
    (row,) = [r for r in document["rows"] if r["identity"] == "hasRelevantEvidenceContract"]
    closure = row["relation"]["range"]["discriminator"]["closure"]
    while len(closure) < size:
        closure.append({"source_file": f"synthetic/evidence_{len(closure)}.sysml",
                        "declaration": f"requirement def SyntheticEvidenceContract{len(closure)}"})
    path.write_text(json.dumps(document), encoding="utf-8")
    return mar.model_facade(root)


def test_the_runtime_serves_every_evidence_contract_the_contract_declares(tmp_path, monkeypatch):
    """A ninth evidence contract, declared by the model and present in the
    served model, is served; no population count refuses it."""
    from de4sdv.sysml_api.client import ApiClient

    data = _fixture(tmp_path, ec_defs=EC_DEFS + 1)
    monkeypatch.setattr(SysMLRepository, "list_elements", lambda self, *a, **k: data["elements"])
    facade = _facade_declaring(tmp_path, EC_DEFS + 1)
    # The binding validates the grown contract, which has its own identity.
    document = json.loads(data["binding_path"].read_text())
    document["semantic_authority"] = facade.identity.to_dict()
    data["binding_path"].write_text(json.dumps(document))
    service = mar.assemble_model_services(
        facade, RevisionBinding.load(data["binding_path"]),
        SysMLRepository(ApiClient("http://127.0.0.1:1")), expected_git_revision=REVISION)
    report = service.semantic_neighbors("use-Requirement", predicates=["hasRelevantEvidenceContract"])
    assert sorted(edge["target"] for edge in report["edges"]) == sorted(
        f"ec-use-{i}" for i in range(EC_DEFS + 1))
    assert report["semantic_status"] == "complete"


def _retired_without_model_record(rows):
    # Keep the profile complete so this reaches the model-retirement check.
    row, entry = rows[3]
    row.update(identity="syntheticRetiredName", admission_class="retired-name",
               retired={"successor": "allocatedTo",
                        "successor_navigation": "allocatedTo",
                        "refusal": "retired; use allocatedTo"})
    entry["retired_resolution"] = {"successor": "allocatedTo", "navigation": "allocatedTo"}


@pytest.mark.parametrize("mutate,match", [
    (lambda rows: rows[8][0]["retired"].update(successor="hasValidationScenario"), "retired name"),
    (lambda rows: rows[9][0]["retired"].update(refusal="retired"), "retired name"),
    (lambda rows: rows[5][0]["relation"]["range"]["discriminator"]["closure"].clear(), "closure"),
    (lambda rows: rows[5][0]["relation"]["range"]["discriminator"]["closure"].append(
        dict(rows[5][0]["relation"]["range"]["discriminator"]["closure"][0])), "closure"),
    (lambda rows: rows[5][0]["relation"]["range"]["discriminator"]["closure"][0].update(
        declaration="part def C0"), "closure"),
    (lambda rows: rows[7][0]["successor"]["end_pairs"].pop(), "allocatedTo"),
    (lambda rows: rows[1][0]["grounding"].update(kernel_external="impostor"), "Interface"),
    (lambda rows: rows[0][0].update(admission_class="invented"), "admission_class"),
    (lambda rows: rows[11][0]["grounding"]["ontology_relations"].update(sub_class_of=None), "Function"),
    (lambda rows: rows[12][1]["retired_resolution"].update(navigation="hasValidationScenario"),
     "retired name"),
    (_retired_without_model_record, "retirement record"),
])
def test_kernel_vocabulary_disagreement_is_refused_not_guessed(tmp_path, mutate, match):
    rows = _kernel_vocabulary_rows()
    mutate(rows)
    root = _kernel_vocabulary_root(tmp_path, rows)
    try:
        routing = _kernel_vocabulary_routing(root)
    except mar.ModelAuthorityRefused as exc:
        assert match in str(exc)
        return
    assert any(match in d for d in routing.duplicates), routing.duplicates


def _answer(service, identifier, predicate):
    report = service.semantic_neighbors(identifier, predicates=[predicate])
    return {key: report[key] for key in ("edges", "gaps", "nodes", "root")}


def test_the_13_are_served_from_the_frozen_records(fx):
    service = _service(fx)
    chain = {p.identity: p for p in mc.frozen_record_provisions(ROOT)}
    assert set(chain) == set(mc.FROZEN_RECORD_IDENTITIES) and len(chain) == 13
    for name in mc.FROZEN_RECORD_CLASSES:
        assert service.contract.provider_of(name) == "o2-chain"
        assert service.contract.mapping(name) == chain[name].mapping
    for name in mc.FROZEN_RECORD_RELATIONSHIPS:
        assert service.contract.relationship_mapping(name) == chain[name].relationship
        for identifier in ("use-Requirement", "use-Need"):
            assert _answer(service, identifier, name)["root"]["element_id"] == identifier


# -- discriminator -----------------------------------------------------------


def test_evidence_contract_discriminator_population(fx):
    service = _service(fx)
    assert "hasRelevantEvidenceContract" not in service.traversal.blocked_predicates()
    report = service.semantic_neighbors("use-Requirement", predicates=["hasRelevantEvidenceContract"])
    targets = sorted(edge["target"] for edge in report["edges"])
    assert targets == sorted(f"ec-use-{i}" for i in range(EC_DEFS))
    assert "ac-use" not in targets
    assert report["semantic_status"] == "complete"


@pytest.mark.parametrize("defs", [EC_DEFS - 1, EC_DEFS + 1])
def test_a_live_population_other_than_the_declared_closure_fails_closed(tmp_path, monkeypatch, defs):
    """The served model's authored closure must match the closure the
    contract declares (eight members at this revision)."""
    data = _fixture(tmp_path, ec_defs=defs)
    monkeypatch.setattr(SysMLRepository, "list_elements", lambda self, *a, **k: data["elements"])
    service = _service(data)
    report = service.semantic_neighbors("use-Requirement", predicates=["hasRelevantEvidenceContract"])
    assert report["edges"] == []
    assert report["semantic_status"] == "incomplete"
    assert any(mar.MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON in r["reason"]
               for r in report["unsupported_predicates"])


def test_closure_members_are_validated_by_the_ingestion_binding_rule():
    members = mc.bound_evidence_contract_closure(ROOT)
    declared = model_contract().relationships["hasRelevantEvidenceContract"]["range_discriminator"]["closure"]
    assert members == sorted(declared, key=lambda m: (m["source_file"], m["declaration"]))
    elements, sources = [], {}
    for index, member in enumerate(members):
        name, kind = declaration_identity(member["declaration"])
        elements.append({"@id": f"id-{index}", "@type": kind, "declaredName": name})
        sources[f"id-{index}"] = member["source_file"]
    validated = mc.validate_closure_members(members, elements, sources)
    assert [m["element_id"] for m in validated] == [f"id-{i}" for i in range(len(members))]
    # Same name and type from another source file is not the bound member.
    sources["id-0"] = "elsewhere.sysml"
    with pytest.raises(mar.ModelAuthorityRefused, match="not validated"):
        mc.validate_closure_members(members, elements, sources)


# -- successor exposure, retired names (D4) and exceptions (D5) --------------


@pytest.mark.parametrize("source,predicate,target,api", [
    ("use-Requirement", "allocatedTo", "use-Function", "alloc-rf"),
    ("use-Function", "allocatedTo", "use-LogicalElement", "alloc-fl"),
    ("use-LogicalElement", "allocatedTo", "use-PhysicalElement", "alloc-lp"),
    ("use-Need", "hasValidationScenario", "use-ValidationScenario", "plan"),
    ("use-ValidationScenario", "validationScenarioFor", "use-Need", "plan"),
    ("use-Requirement", "hasRegulatorySource", "use-RegulatorySource", "source"),
])
def test_successor_predicates_are_exposed(fx, source, predicate, target, api):
    service = _service(fx)
    assert predicate in service._mapped_predicates()
    report = service.semantic_neighbors(source, predicates=[predicate])
    assert [(e["predicate"], e["target"], e["api_object_id"]) for e in report["edges"]] == [
        (predicate, target, api)]
    assert "deprecated_aliases" not in report


@pytest.mark.parametrize("source,name,successor", [
    ("use-Requirement", "realizedBy", "allocatedTo"),
    ("use-LogicalElement", "deployedTo", "allocatedTo"),
    ("use-Need", "validatedBy", "hasValidationScenario"),
    ("use-ValidationScenario", "validatesFitnessForUse", "validationScenarioFor"),
    ("use-Requirement", "constrainedBy", "hasRegulatorySource"),
])
def test_retired_names_are_refused_with_their_successor(fx, source, name, successor):
    """D4: the five former deprecated aliases answer no fact: 'retired; use <successor>'."""
    service = _service(fx)
    assert name not in service._mapped_predicates()
    assert service.contract.refused[name] == f"retired; use {successor}"
    with pytest.raises(RetiredIdentityError, match=f"retired; use {successor}"):
        service.semantic_neighbors(source, predicates=[name])
    hops = service.traversal.traverse(name, {"@id": source}, [])
    assert hops == []
    assert any(r["predicate"] == name and r["authority_state"] == "retired"
               and r["reason"] == f"retired; use {successor}" for r in service.traversal.unsupported)
    assert service.contract.provider_of(name) == "refused"


@pytest.mark.parametrize("name,kind,disposition", [
    ("IncrementTraceabilityShell", "class", "register disposition MERGE"),
    ("derivesNeedFromConcern", "relationship", "register disposition REMOVE"),
])
def test_owner_visible_exceptions_are_refused_with_their_register_disposition(fx, name, kind, disposition):
    """D5: no source serves them; derivesNeedFromConcern moves from gap to refusal."""
    service = _service(fx)
    assert disposition in service.contract.refused[name]
    lookup = service.contract.mapping if kind == "class" else service.contract.relationship_mapping
    with pytest.raises(RetiredIdentityError, match=disposition):
        lookup(name)
    assert name not in service.contract.classes and name not in service.contract.relationships


def test_default_impact_carries_no_retired_edges(fx):
    service = _service(fx)
    report = service.impact("use-Requirement")
    predicates = {edge["predicate"] for edge in report["edges"]}
    assert "allocatedTo" in predicates
    assert not predicates & set(model_contract().refused)
    assert "deprecated_aliases" not in report


# -- coverage gate -----------------------------------------------------------


def test_coverage_report_classifies_every_population_member():
    report = coverage.build_report(ROOT)
    register = mar.load_register_rows(ROOT)
    retained = {n for n, r in register.items() if r["accounting_status"] == "retained"}
    assert retained and retained <= set(report["identities"])
    assert set(register) <= set(report["identities"])
    assert report["duplicates"] == []
    for value in report["identities"].values():
        assert value["status"] in {"projected", "refused", "retired"}
        assert ("layer_digest" in value) if value["status"] == "projected" else value["reason"]
    assert report["kernel_declarations"]
    assert report["residual"] == [] and report["residual_declarations"] == []
    assert report["summary"]["residual_empty"] is True
    assert coverage.compare(report, coverage.load_baseline(ROOT)) == []


def test_coverage_refused_and_retired_carry_their_dispositions():
    report = coverage.build_report(ROOT)
    register = mar.load_register_rows(ROOT)
    removed = ["addressesConcern", "derivesNeedFromConcern", "hasStakeholder", "producesView", "recordsAssumption",
               "recordsGap", "selectedViewpoint"]
    assert report["refused"] == sorted(["IncrementTraceabilityShell", *removed])
    assert {n: report["identities"][n]["register"]["final_disposition"] for n in report["refused"]} == {
        "IncrementTraceabilityShell": "MERGE", **{name: "REMOVE" for name in removed}}
    assert report["retired"] == ["constrainedBy", "deployedTo", "realizedBy", "validatedBy",
                                 "validatesFitnessForUse"]
    for name in report["retired"]:
        assert report["identities"][name]["reason"].startswith("retired; use ")
    assert report["summary"]["refused"] == 8 and report["summary"]["retired"] == 5
    baseline = coverage.load_baseline(ROOT)
    assert baseline["refused"] == report["refused"] and baseline["retired"] == report["retired"]
    shrunk = dict(baseline, refused=["IncrementTraceabilityShell"])
    assert any("refused drift" in e for e in coverage.compare(report, shrunk))
    assert all(register[n]["accounting_status"] != "retained" for n in report["refused"])


def test_coverage_compare_detects_residual_duplicates_and_digest_mismatch():
    report = coverage.build_report(ROOT)
    baseline = coverage.baseline_from_report(report)
    grown = dict(report, residual=report["residual"] + ["Planted"])
    errors = coverage.compare(grown, baseline)
    assert any("residual is blocking" in e for e in errors)
    # Absolute: updating the baseline can never admit a residual.
    assert any("residual is blocking" in e for e in coverage.compare(grown, coverage.baseline_from_report(grown)))
    assert coverage.compare(dict(report, duplicates=["X: a and b"]), baseline)
    assert coverage.compare(report, dict(baseline, routing_digest="sha256:" + "0" * 64))
    assert "layer_digests" not in baseline
    assert coverage.compare(report, dict(baseline, layer_digests={})) == []


def test_coverage_baseline_has_no_binding_block():
    document = coverage.load_baseline(ROOT)
    assert "binding" not in document and document["mode"] == "blocking"


def _gate_mocks():
    """Every other check_repo gate passes; each attribute is patched once."""
    from tests.test_retired_semantic_authority import _passing_gate_mocks

    return list(_passing_gate_mocks())


def _run_check_repo(patch):
    import contextlib
    from scripts import check_repo
    with contextlib.ExitStack() as stack:  # unwinds in reverse: no leaked mock
        for m in _gate_mocks():
            stack.enter_context(m)
        stack.enter_context(patch)
        return check_repo.main()


def test_check_repo_fails_when_the_coverage_gate_fails():
    from unittest import mock
    assert _run_check_repo(mock.patch.object(
        coverage, "run_check_errors", return_value=["sentinel coverage drift"])) == 1


def test_check_repo_passes_when_every_gate_passes():
    from unittest import mock
    assert _run_check_repo(mock.patch.object(coverage, "run_check_errors", return_value=[])) == 0


def test_check_repo_invokes_the_coverage_gate():
    from unittest import mock
    calls = []
    original = coverage.run_check_errors
    def spy(root):
        calls.append(root)
        return original(root)
    assert _run_check_repo(mock.patch.object(coverage, "run_check_errors", side_effect=spy)) == 0
    assert calls, "check_repo did not invoke the model-projection coverage gate"
