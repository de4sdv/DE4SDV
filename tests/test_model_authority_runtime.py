"""Model-authority runtime (O4 Wave C2, bundle v2): synthetic exact-binding fixtures.

Real constructors and the real router run; only API transport is replaced.
No privileged closure, activation or live-API claim follows from these tests.
The authored ontology, the O3 bundle and the legacy/o3 selectors were removed
in Wave C2; the contract is the model-built kernel contract.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import mcp.client.stdio  # noqa: F401 — bind stderr during collection

from de4sdv.semantic import model_authority_runtime as mar
from de4sdv.semantic import model_contract as mc
from de4sdv.semantic import model_projection_coverage as coverage
from de4sdv.semantic.definition_candidate import load_definition_candidate
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


def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _elements_and_bindings(ec_defs=EC_DEFS):
    candidate = load_definition_candidate(ROOT)
    contract = mar.generate_successor_contract(ROOT)
    model = model_contract()
    pins = {}
    for name in candidate.identities:
        row = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        pins[name] = (row["source_file"], row["declaration"])
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


def _attested_members(ids=None):
    """The bound closure members, attested with the fixture's ec-def ids."""
    ids = ids or [f"ec-def-{i}" for i in range(EC_DEFS)]
    return [{**member, "element_id": element}
            for member, element in zip(mar.bound_evidence_contract_closure(ROOT), ids)]


def _edge(kind, source, target, name, **kwargs):
    return {"@id": name, "@type": kind, "source": [{"@id": source}], "target": [{"@id": target}],
            "owningNamespace": {"@id": "context"}, **kwargs}


def _close(bundle, binding, binding_path, tmp_path, *, eligible=True, generated_at=None):
    validations = {}
    for name in mar.REQUIRED_MODEL_VALIDATIONS:
        evidence = tmp_path / f"model-{name}.json"
        evidence.write_text(json.dumps({"synthetic": name}))
        validations[name] = dict(status="passed" if eligible else "failed", path=str(evidence),
                                 sha256=_sha(evidence))
    return mar.close_model_bundle(bundle, mar.build_model_closure_attestation(
        bundle, binding=binding, binding_sha256=_sha(binding_path), definition_closure_closed=True,
        validations=validations, generated_at=generated_at or "1970-01-01T00:00:00+00:00",
        evidence_contract_closure=_attested_members()))


def _fixture(tmp_path, *, eligible=True, ec_defs=EC_DEFS):
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
    binding = RevisionBinding.load(binding_path)
    bundle = mar.build_model_bundle(ROOT, git_revision=REVISION)
    closed = _close(bundle, binding, binding_path, tmp_path, eligible=eligible)
    bundle_path = tmp_path / "model.json"
    bundle_path.write_text(json.dumps(closed))
    return dict(elements=elements, binding_path=binding_path, binding=binding,
                bundle=closed, bundle_path=bundle_path, candidate=bundle, tmp_path=tmp_path)


@pytest.fixture
def fx(tmp_path, monkeypatch):
    data = _fixture(tmp_path)
    monkeypatch.setattr(SysMLRepository, "list_elements", lambda self, *a, **k: data["elements"])
    return data


def _build(fx, *, authority, environ=None, **kwargs):
    from de4sdv.semantic.composition_construction import build_explicit_semantic_runtime
    args = dict(api_url="http://127.0.0.1:1", binding_path=fx["binding_path"],
                expected_git_revision=REVISION)
    if authority == "model":
        args.update(model_bundle_path=fx["bundle_path"], model_bundle_id=fx["bundle"]["bundle_id"])
    args.update(kwargs)
    return build_explicit_semantic_runtime(authority=authority if environ is None else None,
                                           environ=environ if environ is not None else {}, **args)


# -- bundle schema / id / closure / tamper / disjointness -------------------


def test_bundle_schema_id_and_components(fx):
    bundle = fx["bundle"]
    assert bundle["schema"] == mar.MODEL_BUNDLE_SCHEMA == "de4sdv.model-authority-bundle/v2"
    assert mar.BUNDLE_ID_RE.fullmatch(bundle["bundle_id"])
    assert bundle["bundle_id"] == mar.compute_model_bundle_id(bundle)
    assert mar.verify_model_bundle(fx["candidate"], root=ROOT) == []
    assert mar.verify_model_bundle(bundle, root=ROOT, binding=fx["binding"],
                                   binding_sha256=_sha(fx["binding_path"]), require_closed=True) == []
    assert "o3_document" not in bundle and "ontology_compatibility_identity" not in bundle
    components = bundle["components"]
    assert set(components) == {"layers", "semantic_authority", "successor_contract", "routing",
                               "implementation_manifest"}
    assert [r["layer"] for r in components["layers"]] == [
        "o2-chain", "definition", "o2plus", "vocabulary-carrier", "definition-batch2"]
    chain = components["layers"][0]
    assert chain["frozen"] is True and len(chain["chain"]) == 6
    for item in chain["chain"]:
        assert item["sha256"] == _sha(ROOT / item["path"])
    for record in components["layers"][1:]:
        for side in ("projection", "profile"):
            assert record[side]["sha256"] == _sha(ROOT / record[side]["path"])
    assert components["semantic_authority"] == model_contract().identity.to_dict()
    assert components["routing"]["residual"] == {}
    assert set(components["implementation_manifest"]["files"]) == set(mar.IMPLEMENTATION_FILES)
    assert components["successor_contract"]["id"] == mar.generate_successor_contract(ROOT)["id"]
    assert bundle["closure"]["activation_eligible"] is True
    assert bundle["closure"]["semantic_authority_id"] == components["semantic_authority"]["id"]


def _tamper(bundle, path, value):
    target = bundle
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


@pytest.mark.parametrize("path,value,message", [
    (("components", "routing", "residual"), {"Planted": "x"}, "routing"),
    (("components", "layers", 1, "projection", "sha256"), "sha256:" + "0" * 64, "layers"),
    (("components", "layers", 0, "chain", 0, "sha256"), "sha256:" + "0" * 64, "layers"),
    (("components", "semantic_authority", "id"), "sai-" + "0" * 32, "semantic_authority"),
    (("components", "successor_contract", "id"), "sha256:" + "1" * 64, "successor_contract"),
    (("components", "implementation_manifest", "id"), "mai-" + "2" * 32, "implementation_manifest"),
    (("git_revision",), "b" * 40, "content digest"),
])
def test_tampered_component_is_refused_even_with_recomputed_id(fx, path, value, message):
    bundle = copy.deepcopy(fx["bundle"])
    _tamper(bundle, path, value)
    errors = mar.verify_model_bundle(bundle, root=ROOT)
    assert any("content digest" in e for e in errors)
    bundle["bundle_id"] = mar.compute_model_bundle_id(bundle)  # coherent rewrite
    bundle["closure"]["bundle_id"] = bundle["bundle_id"]
    errors = mar.verify_model_bundle(bundle, root=ROOT)
    assert errors and any(message in e or "revision" in e for e in errors), errors


def test_closure_eligibility_is_recomputed_not_trusted(fx):
    bundle = copy.deepcopy(fx["bundle"])
    bundle["closure"]["validation"]["verification_anchor_readback"]["status"] = "failed"
    assert any("recomputed" in e for e in mar.verify_model_bundle(bundle, root=ROOT))
    del bundle["closure"]["validation"]["verification_anchor_readback"]
    bundle["closure"]["activation_eligible"] = False
    assert mar.verify_model_bundle(bundle, root=ROOT) == []
    assert mar._eligibility(bundle["closure"]) is False


def test_required_validations_include_the_three_batteries():
    assert set(mar.REQUIRED_MODEL_VALIDATIONS) == {
        "model_projection_coverage", "model_runtime_answers", "verification_anchor_readback",
        "full_model_semantic_queries", "product_line_scope", "semantic_mcp"}


def _deployment_binding(fx, tmp_path, *, commit_id, generated_at, **changes):
    document = json.loads(fx["binding_path"].read_text())
    document.update(sysml_commit_id=commit_id, import_timestamp=generated_at, **changes)
    path = tmp_path / f"binding-{commit_id}.json"
    path.write_text(json.dumps(document))
    return RevisionBinding.load(path), path


def test_mab_id_is_reproducible_across_deployment_reclosure(fx, tmp_path):
    """The deployment re-closure reproduces the privileged mab- id exactly."""
    binding, binding_path = _deployment_binding(
        fx, tmp_path, commit_id="cid-deployment", generated_at="2026-10-08T12:00:00+00:00")
    redeployed = mar.build_model_bundle(ROOT, git_revision=REVISION)
    assert redeployed["bundle_id"] == fx["candidate"]["bundle_id"] == fx["bundle"]["bundle_id"]
    # The closure attestation, not the id, carries the deployment binding.
    closed = _close(redeployed, binding, binding_path, tmp_path,
                    generated_at="2026-10-08T12:00:01+00:00")
    assert closed["bundle_id"] == fx["bundle"]["bundle_id"]
    assert closed["closure"]["sysml_commit_id"] == "cid-deployment"
    assert closed["closure"]["binding_sha256"] != fx["bundle"]["closure"]["binding_sha256"]
    assert mar.verify_model_bundle(closed, root=ROOT, binding=binding,
                                   binding_sha256=_sha(binding_path), require_closed=True) == []
    # The privileged closure is refused against the deployment binding.
    assert any("binding" in e for e in mar.verify_model_bundle(
        fx["bundle"], root=ROOT, binding=binding, binding_sha256=_sha(binding_path)))
    # A model layer digest change still changes the id.
    for index, record in enumerate(fx["candidate"]["components"]["layers"]):
        changed = copy.deepcopy(fx["candidate"])
        if record.get("frozen"):
            changed["components"]["layers"][index]["chain"][0]["sha256"] = "sha256:" + "0" * 64
            assert mar.compute_model_bundle_id(changed) != fx["candidate"]["bundle_id"]
            continue
        for side in ("projection", "profile"):
            changed = copy.deepcopy(fx["candidate"])
            changed["components"]["layers"][index][side]["sha256"] = "sha256:" + "0" * 64
            assert mar.compute_model_bundle_id(changed) != fx["candidate"]["bundle_id"]
    changed = copy.deepcopy(fx["candidate"])
    changed["components"]["semantic_authority"]["id"] = "sai-" + "0" * 32
    assert mar.compute_model_bundle_id(changed) != fx["candidate"]["bundle_id"]


def test_binding_with_another_semantic_authority_is_refused(fx, tmp_path):
    other = dict(model_contract().identity.to_dict(), id="sai-" + "1" * 32)
    binding, binding_path = _deployment_binding(
        fx, tmp_path, commit_id="cid-other", generated_at="2026-10-09T00:00:00+00:00",
        semantic_authority=other)
    closed = _close(fx["candidate"], binding, binding_path, tmp_path)
    errors = mar.verify_model_bundle(closed, root=ROOT, binding=binding,
                                     binding_sha256=_sha(binding_path), require_closed=True)
    assert any("semantic authority" in e for e in errors), errors


def test_closure_semantic_authority_swap_is_refused(fx):
    bundle = copy.deepcopy(fx["bundle"])
    bundle["closure"]["semantic_authority_id"] = "sai-" + "2" * 32
    assert any("semantic_authority_id" in e for e in mar.verify_model_bundle(bundle, root=ROOT))


def test_v1_bundle_is_refused(fx, tmp_path):
    bundle = copy.deepcopy(fx["bundle"])
    bundle["schema"] = "de4sdv.model-authority-bundle/v1"
    assert mar.verify_model_bundle(bundle, root=ROOT)[0].startswith("model bundle schema mismatch")
    path = tmp_path / "v1.json"
    path.write_text(json.dumps(bundle))
    with pytest.raises(mar.ModelAuthorityRefused, match="schema mismatch"):
        _build(fx, authority="model", model_bundle_path=path)


def test_activation_eligibility_is_required_by_default(tmp_path, monkeypatch):
    """Fail closed: only an explicit opt-out (evidence/test) serves an ineligible bundle."""
    data = _fixture(tmp_path, eligible=False)
    monkeypatch.setattr(SysMLRepository, "list_elements", lambda self, *a, **k: data["elements"])
    with pytest.raises(mar.ModelAuthorityRefused, match="activation-eligible"):
        _build(data, authority="model")
    with pytest.raises(mar.ModelAuthorityRefused, match="activation-eligible"):
        _build(data, authority="model", require_activation_eligible=False, production=True)
    service, selection = _build(data, authority="model", require_activation_eligible=False)
    assert selection.activation_blocked is True
    assert service.authority_status()["activation_blocked"] is True


def test_candidate_bundle_builds_only_with_the_explicit_opt_out(fx, tmp_path):
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(fx["candidate"]))
    args = dict(model_bundle_path=path, model_bundle_id=fx["candidate"]["bundle_id"])
    with pytest.raises(mar.ModelAuthorityRefused, match="not closed"):
        _build(fx, authority="model", **args)
    service, selection = _build(fx, authority="model", require_activation_eligible=False, **args)
    assert selection.activation_blocked is True
    assert service.authority_status()["bundle_id"] == fx["candidate"]["bundle_id"]


def test_model_refusal_is_an_authority_selection_error():
    from de4sdv.semantic.authority_selection import AuthoritySelectionError
    assert issubclass(mar.ModelAuthorityRefused, AuthoritySelectionError)
    assert issubclass(mar.ModelAuthorityRefused, ValueError)


def _split(provisions):
    return ([p for p in provisions if p.layer != mc.O2_CHAIN_LAYER],
            [p for p in provisions if p.layer == mc.O2_CHAIN_LAYER])


def test_routing_is_disjoint_and_a_planted_duplicate_is_refused(fx):
    routing = fx["bundle"]["components"]["routing"]
    assert routing["duplicates"] == [] and routing["residual"] == {}
    assert sum(1 for v in routing["providers"].values() if v == "o2-chain") == 13
    _, provisions = mar.load_layers(ROOT)
    layered, chain = _split(provisions)
    planted = layered + [mar.Provision("Need", "class", "o2plus", mapping=KernelNativeMapping("impostor"))]
    successor = mar.generate_successor_contract(ROOT)
    result = mar.compute_routing(provisions=planted, successor_contract=successor, seed=chain)
    assert result.duplicates
    with pytest.raises(mar.ModelAuthorityRefused, match="duplicate"):
        mar.ModelAuthorityFacade(contract=model_contract(), routing=result, successor_contract=successor,
                                 bundle_id="mab-" + "0" * 32, components={})


def test_retained_row_without_provider_is_a_refused_residual(fx):
    _, provisions = mar.load_layers(ROOT)
    layered, chain = _split(provisions)
    dropped = [p for p in layered if p.identity != "specifiesFunction"]
    result = mar.compute_routing(provisions=dropped,
                                 successor_contract=mar.generate_successor_contract(ROOT),
                                 register_rows=mar.load_register_rows(ROOT), seed=chain)
    assert "specifiesFunction" in result.residual
    with pytest.raises(mar.ModelAuthorityRefused, match="residual"):
        mar.ModelAuthorityFacade(contract=model_contract(), routing=result,
                                 successor_contract=mar.generate_successor_contract(ROOT),
                                 bundle_id="mab-" + "0" * 32, components={})


# -- batch-2 layer loader (schema de4sdv.o4-definition-batch2-*/v1) ----------


def _kbc(name):
    mapping = model_contract().class_mapping(name)
    return {"source_file": mapping.file, "declaration": mapping.declaration}


def _b2_class(name, **grounding):
    return {"identity": name, "semantic_kind": "class", "admission_class": "definition",
            "accounting": "retained", "support": "vocabulary-only", "traversal": False,
            "grounding": {"ontology_relations": {"sub_class_of": None, "disjoint_with": []},
                          **grounding}}


def _b2_relation(name, admission, domain, range_, strength=None, **extra):
    return {"identity": name, "semantic_kind": "relationship", "admission_class": admission,
            "accounting": "retained", "support": "vocabulary-only", "traversal": False,
            "relation": {"domain": {"ontology_class": domain}, "range": {"ontology_class": range_},
                         "semantic_strength": strength}, **extra}


def _b2_entry(name, **extra):
    return {"profile_identity": f"de4sdv.o4-definition-batch2-profile/v1#{name}",
            "for_concept": name, "representation_class": "synthetic", **extra}


def _retired(name, domain, range_, successor, navigation):
    row = dict(_b2_relation(name, "retired-name", domain, range_),
               retired={"successor": successor, "successor_navigation": navigation,
                        "refusal": f"retired; use {navigation}"})
    return row, {"retired_resolution": {"successor": successor, "navigation": navigation}}


def _b2_rows():
    contract = mar.generate_successor_contract(ROOT)
    pairs = [{"source_class": r["sourceClass"], "target_class": r["targetClass"]}
             for r in contract["relations"]["allocatedTo"]]
    dependency = {"strategy": "dependency", "relationship_types": ["Dependency"],
                  "direction": "incoming", "source_property": "source",
                  "target_property": "target", "source_types": ["RequirementUsage"]}
    closure = [{"source_file": f"f{i}.sysml", "declaration": f"requirement def C{i}"}
               for i in range(mar.EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS)]
    hrec = _b2_relation("hasRelevantEvidenceContract", "relationship-runtime", "Requirement",
                        "EvidenceContract", "relevance")
    hrec["relation"]["range"]["discriminator"] = {"kind": "type-lineage",
                                                  "lineage": _kbc("EvidenceContract"),
                                                  "closure": closure}
    rows = [
        (_b2_class("EvidenceContract", kernel_binding_contract=_kbc("EvidenceContract")), {}),
        (_b2_class("Interface", kernel_native="SysML v2 port def and connection elements"), {}),
        (_b2_class("EvidenceStatus", kernel_external=(
            "ODE4HERA requirements-management library VVStatus (NRM A13+A14) via the "
            "DE4SDV method-context adapter")), {}),
        (_b2_relation("variesAt", "relationship-vocabulary", "Feature", "VariationPoint"), {}),
        (dict(_b2_relation("hasStakeholder", "relationship-vocabulary", "EngineeringIncrement",
                           "Stakeholder"),
              carrier={"source_file": "x.sysml", "declaration": "connection def HasStakeholder"}), {}),
        (hrec, {"serializer_mechanics": dependency}),
        (_b2_relation("hasEvidence", "external-reference", "VerificationCase", "EvidenceArtifact",
                      "external-data-required"),
         {"serializer_mechanics": {"strategy": "external"}}),
        ({"identity": "allocatedTo", "semantic_kind": "relationship", "admission_class": "successor",
          "accounting": "retained", "support": "runtime-mapped-candidate", "traversal": False,
          "successor": {"contract": contract["schema"], "end_pairs": pairs}}, {}),
        _retired("realizedBy", "Requirement", "ArchitectureElement", "allocatedTo", "allocatedTo"),
        _retired("constrainedBy", "Requirement", "RegulatoryConstraint", "hasRegulatorySource",
                 "hasRegulatorySource"),
        (_b2_class("Function", kernel_native=(
            "SysML v2 action/state/behavior definitions in functional-architecture slices")), {}),
        (_b2_class("AllocatableFunction", kernel_binding_contract=_kbc("AllocatableFunction"),
                   ontology_relations={"sub_class_of": "Function", "disjoint_with": []}), {}),
        _retired("validatesFitnessForUse", "ValidationScenario", "Need", "hasValidationScenario",
                 "validationScenarioFor"),
    ]
    return rows


def _b2_root(tmp_path, rows):
    root = tmp_path / "root"
    paths = [relative for spec in mar.LAYERS for relative in (spec.projection_path, spec.profile_path)]
    paths += [relative for relative, _ in mc.O2_PROJECTION_CHAIN + mc.O2_PROFILE_CHAIN]
    for relative in paths:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_bytes((ROOT / relative).read_bytes())
    spec = mar.BATCH2_LAYER
    binding = {"source_revision": REVISION}
    (root / spec.projection_path).write_text(json.dumps(
        {"schema": spec.projection_schema, "binding": binding, "rows": [r for r, _ in rows]}))
    (root / spec.profile_path).write_text(json.dumps(
        {"schema": spec.profile_schema, "binding": binding,
         "entries": [_b2_entry(r["identity"], **e) for r, e in rows]}))
    return root


def _b2_routing(root):
    _, provisions = mar.load_layers(root)
    layered, chain = _split(provisions)
    return mar.compute_routing(provisions=layered,
                               successor_contract=mar.generate_successor_contract(ROOT),
                               register_rows=mar.load_register_rows(ROOT), seed=chain)


def test_batch2_layer_is_loaded_exactly_when_its_pair_is_present():
    records, _ = mar.load_layers(ROOT)
    present = (ROOT / mar.BATCH2_LAYER.projection_path).exists()
    assert ("definition-batch2" in [r["layer"] for r in records]) is present


def test_batch2_rows_route_through_the_batch2_layer(tmp_path):
    root = _b2_root(tmp_path, _b2_rows())
    records, provisions = mar.load_layers(root)
    assert [r["layer"] for r in records][-1] == "definition-batch2"
    routing = _b2_routing(root)
    assert routing.duplicates == ()
    for name in ("EvidenceContract", "Interface", "EvidenceStatus", "variesAt", "hasStakeholder",
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


@pytest.mark.parametrize("mutate,match", [
    (lambda rows: rows[8][0]["retired"].update(successor="hasValidationScenario"), "retired name"),
    (lambda rows: rows[9][0]["retired"].update(refusal="retired"), "retired name"),
    (lambda rows: rows[5][0]["relation"]["range"]["discriminator"]["closure"].pop(), "closure"),
    (lambda rows: rows[7][0]["successor"]["end_pairs"].pop(), "allocatedTo"),
    (lambda rows: rows[1][0]["grounding"].update(kernel_external="impostor"), "Interface"),
    (lambda rows: rows[0][0].update(admission_class="invented"), "admission_class"),
    (lambda rows: rows[11][0]["grounding"]["ontology_relations"].update(sub_class_of=None), "Function"),
    (lambda rows: rows[12][1]["retired_resolution"].update(navigation="hasValidationScenario"),
     "retired name"),
    (lambda rows: rows[3][0].update(identity="hasStakeholder2", admission_class="retired-name",
                                    retired={"successor": "allocatedTo",
                                             "successor_navigation": "allocatedTo",
                                             "refusal": "retired; use allocatedTo"}),
     "retirement record"),
])
def test_batch2_disagreement_is_refused_not_guessed(tmp_path, mutate, match):
    rows = _b2_rows()
    mutate(rows)
    root = _b2_root(tmp_path, rows)
    try:
        routing = _b2_routing(root)
    except mar.ModelAuthorityRefused as exc:
        assert match in str(exc)
        return
    assert any(match in d for d in routing.duplicates), routing.duplicates


# -- router: model only ------------------------------------------------------


def test_model_selection_via_environment(fx):
    environ = {mar.AUTHORITY_ENV: "model", mar.MODEL_BUNDLE_PATH_ENV: str(fx["bundle_path"]),
               mar.MODEL_BUNDLE_ID_ENV: fx["bundle"]["bundle_id"]}
    from de4sdv.semantic.composition_construction import build_explicit_semantic_runtime
    service, selection = build_explicit_semantic_runtime(
        api_url="http://127.0.0.1:1", binding_path=fx["binding_path"],
        expected_git_revision=REVISION, environ=environ)
    assert service.semantic_authority_id == "mab:" + fx["bundle"]["bundle_id"]
    assert selection.provenance()["kind"] == "model"
    status = service.model_status()
    assert status["semantic_authority"]["kind"] == "model"
    assert status["semantic_authority"]["id"].startswith("mab:mab-")
    assert status["semantic_authority"]["semantic_authority"] == model_contract().identity.id


def test_entry_contract_positional_builder_and_authority_status(fx):
    """Entry seam: builder(repo_root, bundle_path, expected_id, **runtime) -> runtime."""
    bundle_id = fx["bundle"]["bundle_id"]
    service = mar.build_model_authority_runtime(
        mar.ROOT, fx["bundle_path"], bundle_id, api_url="http://127.0.0.1:1",
        binding_path=fx["binding_path"], expected_git_revision=REVISION, environ={})
    status = service.authority_status()
    assert {"authority", "bundle_id", "source_revision", "refused", "rollback"} <= set(status)
    assert status["authority"] == "model"
    assert status["rollback"] == "redeploy the pre-Wave-C production revision"
    assert status["bundle_id"] == bundle_id and status["source_revision"] == REVISION
    assert status["refused"] == sorted(model_contract().refused)
    assert service.semantic_authority_id == f"mab:{bundle_id}"
    assert service.selection.bundle_id == bundle_id
    other = "mab-" + "f" * 32
    with pytest.raises(mar.ModelAuthorityRefused, match="does not equal"):
        mar.build_model_authority_runtime(
            mar.ROOT, fx["bundle_path"], other, api_url="http://127.0.0.1:1",
            binding_path=fx["binding_path"], expected_git_revision=REVISION, environ={})


def test_v1_binding_is_refused_at_construction(fx, tmp_path):
    document = json.loads(fx["binding_path"].read_text())
    document.pop("schema")
    document.pop("semantic_authority")
    document["ontology"] = {"path": "approach/framework/ontology/de4sdv-basic-ontology.yaml",
                            "sha256": "0" * 64}
    path = tmp_path / "v1-binding.json"
    path.write_text(json.dumps(document))
    with pytest.raises(mar.ModelAuthorityRefused, match="revision binding v1"):
        _build(fx, authority="model", binding_path=path)


@pytest.mark.parametrize("environ,match", [
    ({mar.AUTHORITY_ENV: "model"}, "DE4SDV_MODEL_AUTHORITY_BUNDLE"),
    ({mar.AUTHORITY_ENV: "model", mar.MODEL_BUNDLE_PATH_ENV: "x", mar.MODEL_BUNDLE_ID_ENV: " mab-" + "0" * 32},
     "exact mab-"),
])
def test_incomplete_model_selection_fails_closed(fx, environ, match):
    from de4sdv.semantic.composition_construction import build_explicit_semantic_runtime
    with pytest.raises(mar.ModelAuthorityRefused, match=match):
        build_explicit_semantic_runtime(api_url="http://127.0.0.1:1", binding_path=fx["binding_path"],
                                        expected_git_revision=REVISION, environ=environ)


def test_tampered_model_bundle_never_falls_back(fx, tmp_path):
    bundle = copy.deepcopy(fx["bundle"])
    bundle["components"]["routing"]["residual"] = {"Planted": "x"}
    bundle["bundle_id"] = mar.compute_model_bundle_id(bundle)
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(bundle))
    with pytest.raises(mar.ModelAuthorityRefused, match="routing"):
        _build(fx, authority="model", model_bundle_path=path, model_bundle_id=bundle["bundle_id"])


def test_retired_runtime_arguments_are_refused(fx):
    from de4sdv.semantic.authority_selection import AuthoritySelectionError
    with pytest.raises(AuthoritySelectionError, match="unsupported semantic-runtime arguments"):
        _build(fx, authority="model", bundle_path="o3.json")
    with pytest.raises(AuthoritySelectionError, match="unsupported semantic-runtime arguments"):
        _build(fx, authority="model", ontology_path=ROOT / "x.yaml")
    with pytest.raises(AuthoritySelectionError, match="retired by O4 Wave C2"):
        _build(fx, authority="legacy", model_bundle_id=fx["bundle"]["bundle_id"])
    with pytest.raises(AuthoritySelectionError, match="retired"):
        _build(fx, authority="model", composition="o3+definitions")


@pytest.mark.parametrize("authority,environ,match", [
    ("legacy", {}, "retired by O4 Wave C2"),
    ("o3", {}, "retired by O4 Wave C2"),
    (None, {}, "is unset"),
    (None, {"DE4SDV_SEMANTIC_AUTHORITY": ""}, "is unset"),
    (None, {"DE4SDV_SEMANTIC_AUTHORITY": "o3"}, "retired by O4 Wave C2"),
    ("other", {}, "unknown DE4SDV_SEMANTIC_AUTHORITY value"),
])
def test_only_the_model_authority_is_selectable(fx, authority, environ, match):
    """D6: an unset selector is refused; legacy and o3 are retired (rollback = redeploy)."""
    from de4sdv.semantic import composition_construction as cc
    from de4sdv.semantic.authority_selection import AuthoritySelectionError
    with pytest.raises(AuthoritySelectionError, match=match):
        cc.build_explicit_semantic_runtime(api_url="u", binding_path=fx["binding_path"],
                                           expected_git_revision=REVISION, authority=authority,
                                           environ=environ)


def _answer(service, identifier, predicate):
    report = service.semantic_neighbors(identifier, predicates=[predicate])
    return {key: report[key] for key in ("edges", "gaps", "nodes", "root")}


def test_the_13_are_served_from_the_frozen_o2_chain_with_isolated_caches(fx, tmp_path):
    from tools.sysml_html_viewer import ask_model_semantic as viewer
    service, _ = _build(fx, authority="model")
    chain = {p.identity: p for p in mc.o2_chain_provisions(ROOT)}
    assert set(chain) == set(mc.O2_CHAIN_IDENTITIES) and len(chain) == 13
    for name in mc.O2_CHAIN_CLASSES:
        assert service.contract.provider_of(name) == "o2-chain"
        assert service.contract.mapping(name) == chain[name].mapping
    for name in mc.O2_CHAIN_RELATIONSHIPS:
        assert service.contract.relationship_mapping(name) == chain[name].relationship
        for identifier in ("use-Requirement", "use-Need"):
            assert _answer(service, identifier, name)["root"]["element_id"] == identifier
    # A second (re-closed) candidate is another authority: no shared cache slot.
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(fx["candidate"]))
    other_bundle = copy.deepcopy(fx["candidate"])
    other_bundle["claim_boundary"] = "x"  # not part of the id
    services = [service]
    services.append(mar.assemble_model_services(
        mar.model_facade(ROOT, bundle_id="mab-" + "e" * 32), fx["binding"],
        service.repository, expected_git_revision=REVISION))
    assert len({s.semantic_authority_id for s in services}) == 2
    assert len({viewer._snapshot_path(s) for s in services}) == 2
    services[0]._impact_cache["probe"] = {"authority": services[0].semantic_authority_id}
    assert "probe" not in services[1]._impact_cache
    identities = [viewer._snapshot_identity(s)["semantic_authority_id"] for s in services]
    assert len(set(identities)) == 2


# -- discriminator -----------------------------------------------------------


def test_evidence_contract_discriminator_population(fx):
    service, _ = _build(fx, authority="model")
    assert "hasRelevantEvidenceContract" not in service.traversal.blocked_predicates()
    report = service.semantic_neighbors("use-Requirement", predicates=["hasRelevantEvidenceContract"])
    targets = sorted(edge["target"] for edge in report["edges"])
    assert targets == sorted(f"ec-use-{i}" for i in range(EC_DEFS))
    assert "ac-use" not in targets
    assert report["semantic_status"] == "complete"


@pytest.mark.parametrize("defs", [EC_DEFS - 1, EC_DEFS + 1])
def test_evidence_contract_closure_with_wrong_population_fails_closed(tmp_path, monkeypatch, defs):
    data = _fixture(tmp_path, ec_defs=defs)
    monkeypatch.setattr(SysMLRepository, "list_elements", lambda self, *a, **k: data["elements"])
    service, _ = _build(data, authority="model")
    report = service.semantic_neighbors("use-Requirement", predicates=["hasRelevantEvidenceContract"])
    assert report["edges"] == []
    assert report["semantic_status"] == "incomplete"
    assert any(mar.MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON in r["reason"]
               for r in report["unsupported_predicates"])


def test_evidence_contract_member_swap_keeping_the_count_fails_closed(tmp_path, monkeypatch):
    """Eight live definitions are not enough; they must be the bound eight (by id)."""
    data = _fixture(tmp_path)
    swapped = []
    for element in data["elements"]:
        element = dict(element)
        if element["@id"] == "ec-def-7":
            element["@id"] = "ec-def-impostor"
        if element.get("type") == [{"@id": "ec-def-7"}]:
            element["type"] = [{"@id": "ec-def-impostor"}]
        swapped.append(element)
    monkeypatch.setattr(SysMLRepository, "list_elements", lambda self, *a, **k: swapped)
    service, _ = _build(data, authority="model")
    assert service.traversal.closure_member_ids == {f"ec-def-{i}" for i in range(EC_DEFS)}
    report = service.semantic_neighbors("use-Requirement", predicates=["hasRelevantEvidenceContract"])
    assert report["edges"] == [] and report["semantic_status"] == "incomplete"
    assert any("attested bound members" in r["reason"] for r in report["unsupported_predicates"])


def test_closure_must_attest_exactly_the_bound_members(fx):
    for mutate in (lambda m: m.pop(), lambda m: m[0].update(declaration="requirement def Impostor"),
                   lambda m: m[1].update(element_id=m[0]["element_id"])):
        bundle = copy.deepcopy(fx["bundle"])
        mutate(bundle["closure"]["evidence_contract_closure"])
        assert any("evidence_contract_closure" in e for e in mar.verify_model_bundle(bundle, root=ROOT))


def test_closure_members_are_validated_by_the_ingestion_binding_rule():
    members = mar.bound_evidence_contract_closure(ROOT)
    assert len(members) == mar.EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS
    elements, sources = [], {}
    for index, member in enumerate(members):
        name, kind = declaration_identity(member["declaration"])
        elements.append({"@id": f"id-{index}", "@type": kind, "declaredName": name})
        sources[f"id-{index}"] = member["source_file"]
    validated = mar.validate_closure_members(members, elements, sources)
    assert [m["element_id"] for m in validated] == [f"id-{i}" for i in range(len(members))]
    # Same name and type from another source file is not the bound member.
    sources["id-0"] = "elsewhere.sysml"
    with pytest.raises(mar.ModelAuthorityRefused, match="not validated"):
        mar.validate_closure_members(members, elements, sources)


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
    service, _ = _build(fx, authority="model")
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
    service, _ = _build(fx, authority="model")
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
    service, _ = _build(fx, authority="model")
    assert disposition in service.contract.refused[name]
    lookup = service.contract.mapping if kind == "class" else service.contract.relationship_mapping
    with pytest.raises(RetiredIdentityError, match=disposition):
        lookup(name)
    assert name not in service.contract.classes and name not in service.contract.relationships


def test_default_impact_carries_no_retired_edges(fx):
    service, _ = _build(fx, authority="model")
    report = service.impact("use-Requirement")
    predicates = {edge["predicate"] for edge in report["edges"]}
    assert "allocatedTo" in predicates
    assert not predicates & set(model_contract().refused)
    assert "deprecated_aliases" not in report


def test_successor_contract_mismatch_refuses_construction(fx, monkeypatch):
    original = mar.generate_model_successor_contract
    def changed(root, **kwargs):
        contract = copy.deepcopy(original(root, **kwargs))
        contract["id"] = "sha256:" + "9" * 64
        return contract
    monkeypatch.setattr(mar, "generate_model_successor_contract", changed)
    with pytest.raises(mar.ModelAuthorityRefused):
        _build(fx, authority="model")


def test_external_implementation_source_is_refused(monkeypatch, tmp_path):
    fake = tmp_path / "relationship_successor.py"
    fake.write_text((ROOT / "de4sdv/semantic/relationship_successor.py").read_text())
    sources = mar._executed_sources()
    monkeypatch.setattr(mar, "_executed_sources", lambda: {
        **sources, "de4sdv/semantic/relationship_successor.py": str(fake)})
    with pytest.raises(mar.ModelAuthorityRefused, match="implementation source"):
        mar.implementation_manifest(ROOT)


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
    assert report["refused"] == ["IncrementTraceabilityShell", "derivesNeedFromConcern"]
    assert {n: report["identities"][n]["register"]["final_disposition"] for n in report["refused"]} == {
        "IncrementTraceabilityShell": "MERGE", "derivesNeedFromConcern": "REMOVE"}
    assert report["retired"] == ["constrainedBy", "deployedTo", "realizedBy", "validatedBy",
                                 "validatesFitnessForUse"]
    for name in report["retired"]:
        assert report["identities"][name]["reason"].startswith("retired; use ")
    assert report["summary"]["refused"] == 2 and report["summary"]["retired"] == 5
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
    assert coverage.compare(report, dict(baseline, layer_digests={}))


def test_coverage_bundle_cross_check(fx):
    report = coverage.build_report(ROOT)
    assert coverage.bundle_errors(report, fx["bundle"], ROOT) == []
    bundle = copy.deepcopy(fx["bundle"])
    bundle["components"]["layers"][1]["profile"]["sha256"] = "sha256:" + "0" * 64
    assert any("layer digests" in e for e in coverage.bundle_errors(report, bundle, ROOT))
    bundle = copy.deepcopy(fx["bundle"])
    bundle["components"]["semantic_authority"]["id"] = "sai-" + "0" * 32
    assert any("semantic authority" in e for e in coverage.bundle_errors(report, bundle, ROOT))


def test_coverage_baseline_has_no_binding_block():
    document = coverage.load_baseline(ROOT)
    assert "binding" not in document and document["mode"] == "blocking"


def _gate_mocks():
    """Every other check_repo gate passes; each attribute is patched once."""
    from unittest import mock
    from de4sdv.semantic import external_reference_contract, o4_consumers
    from tests.test_o4_consumer_ledger import _passing_gate_mocks
    mocks = list(_passing_gate_mocks())
    patched = {(id(m.getter()), m.attribute) for m in mocks}
    for target, attribute in ((external_reference_contract, "run_check_errors"),
                              (o4_consumers, "load_and_check")):
        if (id(target), attribute) not in patched:
            mocks.append(mock.patch.object(target, attribute, return_value=[]))
    return mocks


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
