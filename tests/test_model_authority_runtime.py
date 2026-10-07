"""Model-authority runtime (O4 Wave B): synthetic exact-binding fixtures.

Real constructors and the real router run; only API transport is replaced.
No privileged closure, activation or live-API claim follows from these tests.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import mcp.client.stdio  # noqa: F401 — bind stderr during collection

from de4sdv.semantic import model_authority_runtime as mar
from de4sdv.semantic import model_projection_coverage as coverage
from de4sdv.semantic import o3_bundle as ob
from de4sdv.semantic.definition_candidate import load_definition_candidate
from de4sdv.semantic.kernel_contract import KernelContract, declaration_identity
from de4sdv.sysml_api.repository import SysMLRepository
from de4sdv.sysml_api.revisions import RevisionBinding

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / ob.ONTOLOGY_PATH
REVISION = "a" * 40
EC_DEFS = 8


def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _elements_and_bindings(ec_defs=EC_DEFS):
    candidate = load_definition_candidate(ROOT)
    contract = mar.generate_successor_contract(ROOT)
    pins = {}
    for name in candidate.identities:
        row = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        pins[name] = (row["source_file"], row["declaration"])
    for name, pin in {**contract["classes"], **contract["carriers"]}.items():
        pins.setdefault(name, (pin["file"], pin["declaration"]))
    legacy = KernelContract.load(ONTOLOGY)
    ec = legacy.class_mapping("EvidenceContract")
    pins["EvidenceContract"] = (ec.file, ec.declaration)
    for name, spec in legacy.classes.items():  # complete lineage roots (e.g. DerivesFromNeed)
        kernel = (spec or {}).get("kernel") or {}
        if "file" in kernel and kernel["declaration"] not in {p[1] for p in pins.values()}:
            pins.setdefault(name, (kernel["file"], kernel["declaration"]))
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
    return elements, bindings, legacy


def _edge(kind, source, target, name, **kwargs):
    return {"@id": name, "@type": kind, "source": [{"@id": source}], "target": [{"@id": target}],
            "owningNamespace": {"@id": "context"}, **kwargs}


def _fixture(tmp_path, *, eligible=True, ec_defs=EC_DEFS):
    elements, bindings, legacy = _elements_and_bindings(ec_defs)
    elements += [
        _edge("AllocationUsage", "use-Requirement", "use-Function", "alloc-rf"),
        _edge("AllocationUsage", "use-Function", "use-LogicalElement", "alloc-fl"),
        _edge("AllocationUsage", "use-LogicalElement", "use-PhysicalElement", "alloc-lp"),
        _edge("ConnectionUsage", "use-Need", "use-ValidationScenario", "plan",
              type=[{"@id": "root-hasValidationScenario"}]),
        _edge("ConnectionUsage", "use-Requirement", "use-RegulatorySource", "source",
              type=[{"@id": "root-hasRegulatorySource"}]),
    ]
    document = dict(git_repository="de4sdv/DE4SDV", git_commit=REVISION, sysml_project_id="pid",
                    sysml_commit_id="cid", import_timestamp="2026-10-07T00:00:00Z",
                    import_tool_version="fixture", semantic_validation="passed", scope="full-model",
                    ontology=legacy.identity.to_dict(), kernel_bindings=bindings)
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(document))
    binding = RevisionBinding.load(binding_path)
    o3 = ob.build_candidate_bundle(ROOT, git_revision=REVISION)
    o3_validations = {}
    for name in ob.REQUIRED_VALIDATIONS:
        evidence = tmp_path / f"o3-{name}.json"
        evidence.write_text(json.dumps({"synthetic": name}))
        o3_validations[name] = dict(status="passed", artifact=name, path=str(evidence),
                                    sha256=ob.sha256_file(evidence))
    o3 = ob.close_bundle(o3, ob.build_closure_attestation(
        o3, binding=binding, binding_sha256=_sha(binding_path), element_count=len(elements),
        export_identity_sha256=None, validations=o3_validations,
        verification_case_grounding={"result": "EQUIVALENT"},
        generated_at="1970-01-01T00:00:00+00:00"))
    o3_path = tmp_path / "o3.json"
    o3_path.write_text(json.dumps(o3))
    bundle = mar.build_model_bundle(ROOT, o3_bundle=o3, git_revision=REVISION)
    validations = {}
    for name in mar.REQUIRED_MODEL_VALIDATIONS:
        evidence = tmp_path / f"model-{name}.json"
        evidence.write_text(json.dumps({"synthetic": name}))
        validations[name] = dict(status="passed" if eligible else "failed", path=str(evidence),
                                 sha256=_sha(evidence))
    closed = mar.close_model_bundle(bundle, mar.build_model_closure_attestation(
        bundle, binding=binding, binding_sha256=_sha(binding_path), definition_closure_closed=True,
        validations=validations, generated_at="1970-01-01T00:00:00+00:00"))
    bundle_path = tmp_path / "model.json"
    bundle_path.write_text(json.dumps(closed))
    return dict(elements=elements, binding_path=binding_path, binding=binding, o3=o3,
                o3_path=o3_path, bundle=closed, bundle_path=bundle_path, candidate=bundle)


@pytest.fixture
def fx(tmp_path, monkeypatch):
    data = _fixture(tmp_path)
    monkeypatch.setattr(SysMLRepository, "list_elements", lambda self, *a, **k: data["elements"])
    return data


def _build(fx, *, authority, environ=None, **kwargs):
    from de4sdv.semantic.composition_construction import build_explicit_semantic_runtime
    args = dict(api_url="http://127.0.0.1:1", binding_path=fx["binding_path"],
                expected_git_revision=REVISION, ontology_path=ONTOLOGY)
    if authority == "o3":
        args.update(bundle_path=fx["o3_path"], bundle_id=fx["o3"]["bundle_id"])
    if authority == "model":
        args.update(model_bundle_path=fx["bundle_path"], model_bundle_id=fx["bundle"]["bundle_id"])
    args.update(kwargs)
    return build_explicit_semantic_runtime(authority=authority if environ is None else None,
                                           environ=environ if environ is not None else {}, **args)


# -- bundle schema / id / closure / tamper / disjointness -------------------


def test_bundle_schema_id_and_components(fx):
    bundle = fx["bundle"]
    assert bundle["schema"] == mar.MODEL_BUNDLE_SCHEMA
    assert mar.BUNDLE_ID_RE.fullmatch(bundle["bundle_id"])
    assert bundle["bundle_id"] == mar.compute_model_bundle_id(bundle)
    assert mar.verify_model_bundle(fx["candidate"], root=ROOT) == []
    assert mar.verify_model_bundle(bundle, root=ROOT, binding=fx["binding"],
                                   binding_sha256=_sha(fx["binding_path"]), require_closed=True) == []
    components = bundle["components"]
    assert [r["layer"] for r in components["layers"]] == [
        "definition", "o2plus", "vocabulary-carrier", "definition-batch2"]
    for record in components["layers"]:
        for side in ("projection", "profile"):
            assert record[side]["sha256"] == _sha(ROOT / record[side]["path"])
    assert components["o3"]["bundle_id"] == fx["o3"]["bundle_id"]
    assert set(components["implementation_manifest"]["files"]) == set(mar.IMPLEMENTATION_FILES)
    assert components["successor_contract"]["id"] == mar.generate_successor_contract(ROOT)["id"]
    assert bundle["closure"]["activation_eligible"] is True


def _tamper(bundle, path, value):
    target = bundle
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


@pytest.mark.parametrize("path,value,message", [
    (("components", "routing", "residual"), {}, "routing"),
    (("components", "layers", 0, "projection", "sha256"), "sha256:" + "0" * 64, "layers"),
    (("components", "successor_contract", "id"), "sha256:" + "1" * 64, "successor_contract"),
    (("components", "implementation_manifest", "id"), "mai-" + "2" * 32, "implementation_manifest"),
    (("components", "o3", "sha256"), "sha256:" + "3" * 64, "'o3'"),
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


def test_activation_eligibility_is_required_by_default(tmp_path, monkeypatch):
    """Fail closed: only an explicit opt-out (compare/test) serves an ineligible bundle."""
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


def test_routing_is_disjoint_and_a_planted_duplicate_is_refused(fx):
    routing = fx["bundle"]["components"]["routing"]
    assert routing["duplicates"] == []
    assert not set(routing["providers"]) & set(routing["residual"])
    assert sum(1 for v in routing["providers"].values() if v == "o3") == 13
    legacy = KernelContract.load(ONTOLOGY)
    _, provisions = mar.load_layers(ROOT)
    planted = provisions + [mar.Provision("Need", "class", "o2plus",
                                          mapping=mar.KernelNativeMapping("impostor"))]
    result = mar.compute_routing(legacy=legacy, provisions=planted,
                                 successor_contract=mar.generate_successor_contract(ROOT))
    assert result.duplicates
    with pytest.raises(mar.ModelAuthorityRefused, match="duplicate"):
        mar.ModelAuthorityFacade(legacy=legacy, o3_facade=type("F", (), {"identity": legacy.identity})(),
                                 routing=result, successor_contract=mar.generate_successor_contract(ROOT),
                                 bundle_id="mab-" + "0" * 32, components={})


# -- batch-2 layer loader (B1 schema de4sdv.o4-definition-batch2-*/v1) -------


def _kbc(name):
    mapping = KernelContract.load(ONTOLOGY).class_mapping(name)
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
        (dict(_b2_relation("realizedBy", "deprecated-alias", "Requirement", "ArchitectureElement"),
              alias={"deprecated": True, "successor": "allocatedTo",
                     "successor_navigation": "allocatedTo", "answer_mode": "successor-facts"}),
         {"alias_resolution": {"successor": "allocatedTo", "navigation": "allocatedTo",
                               "answer_mode": "successor-facts"}}),
        (dict(_b2_relation("constrainedBy", "deprecated-alias", "Requirement", "RegulatoryConstraint"),
              alias={"deprecated": True, "successor": "hasRegulatorySource",
                     "successor_navigation": "hasRegulatorySource",
                     "answer_mode": "documentation-only"}),
         {"alias_resolution": {"successor": "hasRegulatorySource", "navigation": "hasRegulatorySource",
                               "answer_mode": "documentation-only"}}),
        (_b2_class("Function", kernel_native=(
            "SysML v2 action/state/behavior definitions in functional-architecture slices")), {}),
        (_b2_class("AllocatableFunction", kernel_binding_contract=_kbc("AllocatableFunction"),
                   ontology_relations={"sub_class_of": "Function", "disjoint_with": []}), {}),
        (dict(_b2_relation("validatesFitnessForUse", "deprecated-alias", "ValidationScenario", "Need"),
              alias={"deprecated": True, "successor": "hasValidationScenario",
                     "successor_navigation": "validationScenarioFor",
                     "answer_mode": "successor-facts"}),
         {"alias_resolution": {"successor": "hasValidationScenario",
                               "navigation": "validationScenarioFor",
                               "answer_mode": "successor-facts"}}),
    ]
    return rows


def _b2_root(tmp_path, rows):
    root = tmp_path / "root"
    for spec in mar.LAYERS:
        for relative in (spec.projection_path, spec.profile_path):
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
    return mar.compute_routing(legacy=KernelContract.load(ONTOLOGY), provisions=provisions,
                               successor_contract=mar.generate_successor_contract(ROOT),
                               register_rows=mar.load_register_rows(ROOT))


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
    legacy = KernelContract.load(ONTOLOGY)
    for name in ("EvidenceContract", "Interface", "EvidenceStatus", "variesAt", "hasStakeholder",
                 "hasRelevantEvidenceContract", "hasEvidence"):
        assert routing.providers[name].layer == "definition-batch2", name
        assert name not in routing.residual
    for name in ("EvidenceContract", "Interface", "EvidenceStatus"):
        assert routing.providers[name].mapping == legacy.mapping(name)
    for name in ("hasRelevantEvidenceContract", "hasEvidence"):
        assert routing.providers[name].relationship == legacy.relationship_mapping(name)
    discriminator = routing.providers["hasRelevantEvidenceContract"].spec["range_discriminator"]
    assert discriminator["kind"] == "type-lineage" and len(discriminator["closure"]) == 8
    # The successor row corroborates the model-generated successor contract.
    assert routing.providers["allocatedTo"].layer == "successor-contract"
    assert "definition-batch2" in routing.corroborations["allocatedTo"]
    # Deprecated-alias rows document the alias table; they never become providers.
    # A natively represented successor endpoint class: the model-derived lineage
    # pin owns the runtime mapping; the batch-2 row corroborates it.
    assert routing.providers["Function"].layer == "successor-contract"
    assert routing.corroborations["Function"] == ("definition-batch2",)
    assert routing.providers["AllocatableFunction"].layer == "definition-batch2"
    for name in ("realizedBy", "constrainedBy", "validatesFitnessForUse"):
        assert name not in routing.providers and name not in routing.residual
        assert routing.corroborations[name] == ("definition-batch2",)


@pytest.mark.parametrize("mutate,match", [
    (lambda rows: rows[8][0]["alias"].update(successor="hasValidationScenario"), "alias"),
    (lambda rows: rows[9][0]["alias"].update(answer_mode="successor-facts"), "alias"),
    (lambda rows: rows[5][0]["relation"]["range"]["discriminator"]["closure"].pop(), "closure"),
    (lambda rows: rows[7][0]["successor"]["end_pairs"].pop(), "allocatedTo"),
    (lambda rows: rows[1][0]["grounding"].update(kernel_native="impostor"), "Interface"),
    (lambda rows: rows[0][0].update(admission_class="invented"), "admission_class"),
    (lambda rows: rows[11][0]["grounding"]["ontology_relations"].update(sub_class_of=None), "Function"),
    (lambda rows: rows[12][1]["alias_resolution"].update(navigation="hasValidationScenario"), "alias"),
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


# -- router + rollback -------------------------------------------------------


def test_model_selection_via_environment(fx):
    environ = {mar.AUTHORITY_ENV: "model", mar.MODEL_BUNDLE_PATH_ENV: str(fx["bundle_path"]),
               mar.MODEL_BUNDLE_ID_ENV: fx["bundle"]["bundle_id"]}
    from de4sdv.semantic.composition_construction import build_explicit_semantic_runtime
    service, selection = build_explicit_semantic_runtime(
        api_url="http://127.0.0.1:1", binding_path=fx["binding_path"],
        expected_git_revision=REVISION, ontology_path=ONTOLOGY, environ=environ)
    assert service.semantic_authority_id == "mab:" + fx["bundle"]["bundle_id"]
    assert selection.provenance()["kind"] == "model"
    status = service.model_status()
    assert status["semantic_authority"]["kind"] == "model"
    assert status["semantic_authority"]["id"].startswith("mab:mab-")


def test_entry_contract_positional_builder_and_authority_status(fx):
    """B3 entry seam: builder(repo_root, bundle_path, expected_id, **runtime) -> runtime."""
    bundle_id = fx["bundle"]["bundle_id"]
    service = mar.build_model_authority_runtime(
        mar.ROOT, fx["bundle_path"], bundle_id, api_url="http://127.0.0.1:1",
        binding_path=fx["binding_path"], expected_git_revision=REVISION, ontology_path=ONTOLOGY,
        environ={})
    status = service.authority_status()
    assert {"authority", "bundle_id", "source_revision", "residual", "rollback"} <= set(status)
    assert status["authority"] == "model" and status["rollback"] == "o3"
    assert status["bundle_id"] == bundle_id and status["source_revision"] == REVISION
    assert status["residual"] == sorted(fx["bundle"]["components"]["routing"]["residual"])
    assert service.semantic_authority_id == f"mab:{bundle_id}"
    assert service.selection.bundle_id == bundle_id
    other = "mab-" + "f" * 32
    with pytest.raises(mar.ModelAuthorityRefused, match="does not equal"):
        mar.build_model_authority_runtime(
            mar.ROOT, fx["bundle_path"], other, api_url="http://127.0.0.1:1",
            binding_path=fx["binding_path"], expected_git_revision=REVISION,
            ontology_path=ONTOLOGY, environ={})


@pytest.mark.parametrize("environ,match", [
    ({mar.AUTHORITY_ENV: "model"}, "DE4SDV_MODEL_AUTHORITY_BUNDLE"),
    ({mar.AUTHORITY_ENV: "model", mar.MODEL_BUNDLE_PATH_ENV: "x", mar.MODEL_BUNDLE_ID_ENV: " mab-" + "0" * 32},
     "exact mab-"),
])
def test_incomplete_model_selection_fails_closed(fx, environ, match):
    from de4sdv.semantic.composition_construction import build_explicit_semantic_runtime
    with pytest.raises(mar.ModelAuthorityRefused, match=match):
        build_explicit_semantic_runtime(api_url="http://127.0.0.1:1", binding_path=fx["binding_path"],
                                        expected_git_revision=REVISION, ontology_path=ONTOLOGY,
                                        environ=environ)


def test_tampered_model_bundle_never_falls_back(fx, tmp_path):
    bundle = copy.deepcopy(fx["bundle"])
    bundle["components"]["routing"]["residual"] = {}
    bundle["bundle_id"] = mar.compute_model_bundle_id(bundle)
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(bundle))
    with pytest.raises(mar.ModelAuthorityRefused, match="routing"):
        _build(fx, authority="model", model_bundle_path=path, model_bundle_id=bundle["bundle_id"])


def test_argument_crossing_is_refused(fx):
    from de4sdv.semantic.authority_selection import AuthoritySelectionError
    with pytest.raises(AuthoritySelectionError, match="model_bundle_path"):
        _build(fx, authority="model", bundle_path=fx["o3_path"])
    with pytest.raises(AuthoritySelectionError, match="authority='model'"):
        _build(fx, authority="legacy", model_bundle_id=fx["bundle"]["bundle_id"])


@pytest.mark.parametrize("authority", ["legacy", "o3", None])
def test_legacy_and_o3_reach_the_frozen_selector_with_identical_arguments(fx, monkeypatch, authority):
    from de4sdv.semantic import composition_construction as cc
    calls = []
    monkeypatch.setattr(cc, "build_selected_semantic_runtime", lambda **kw: calls.append(kw) or ("s", "sel"))
    kwargs = dict(api_url="u", binding_path=fx["binding_path"], expected_git_revision=REVISION,
                  ontology_path=ONTOLOGY, authority=authority, bundle_path=None, bundle_id=None,
                  environ={"DE4SDV_SEMANTIC_AUTHORITY": "o3"} if authority is None else {})
    assert cc.build_explicit_semantic_runtime(**kwargs) == ("s", "sel")
    assert calls == [kwargs]


def _answer(service, identifier, predicate):
    report = service.semantic_neighbors(identifier, predicates=[predicate])
    return {key: report[key] for key in ("edges", "gaps", "nodes", "root")}


def test_model_o3_legacy_identical_answers_on_the_13_with_isolated_caches(fx):
    from tools.sysml_html_viewer import ask_model_semantic as viewer
    services = {}
    for authority in ("model", "o3", "legacy"):  # activate -> rollback -> second fallback
        services[authority], _ = _build(fx, authority=authority)
    model, o3, legacy = services["model"], services["o3"], services["legacy"]
    for name in ob.MIGRATED_CLASSES:
        # Model and its o3 rollback share the O3 projection mapping; legacy keeps
        # its authored native text for VerificationCase (pre-existing O3 behavior).
        assert model.contract.mapping(name) == o3.contract.mapping(name)
        if name != "VerificationCase":
            assert o3.contract.mapping(name) == legacy.contract.mapping(name)
    for name in ob.MIGRATED_RELATIONSHIPS:
        assert model.contract.relationship_mapping(name) == o3.contract.relationship_mapping(name)
        assert o3.contract.relationship_mapping(name) == legacy.contract.relationship_mapping(name)
        for identifier in ("use-Requirement", "use-Need"):
            assert _answer(model, identifier, name) == _answer(o3, identifier, name) \
                == _answer(legacy, identifier, name)
    ids = {s.semantic_authority_id for s in services.values()}
    assert len(ids) == 3
    paths = {viewer._snapshot_path(s) for s in services.values()}
    assert len(paths) == 3
    # Per-authority cache slots: filling one never fills or reuses another.
    model._impact_cache["probe"] = {"authority": model.semantic_authority_id}
    assert "probe" not in o3._impact_cache and "probe" not in legacy._impact_cache
    identities = [viewer._snapshot_identity(s)["semantic_authority_id"] for s in services.values()]
    assert len(set(identities)) == 3


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


def test_legacy_path_keeps_the_evidence_contract_blocked(fx):
    service, _ = _build(fx, authority="legacy")
    assert "hasRelevantEvidenceContract" in service.traversal.blocked_predicates()


# -- successor exposure + deprecated aliases ---------------------------------


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


@pytest.mark.parametrize("source,alias,target,api", [
    ("use-Requirement", "realizedBy", "use-Function", "alloc-rf"),
    ("use-LogicalElement", "deployedTo", "use-PhysicalElement", "alloc-lp"),
    ("use-Need", "validatedBy", "use-ValidationScenario", "plan"),
    ("use-ValidationScenario", "validatesFitnessForUse", "use-Need", "plan"),
])
def test_old_names_answer_only_as_marked_deprecated_aliases(fx, source, alias, target, api):
    service, _ = _build(fx, authority="model")
    assert alias not in service._mapped_predicates()
    report = service.semantic_neighbors(source, predicates=[alias])
    assert [(e["predicate"], e["target"], e["api_object_id"]) for e in report["edges"]] == [
        (alias, target, api)]
    marker = report["edges"][0]["witness"]["deprecated_alias"]
    assert marker["deprecated"] is True and marker["successor"] == mar.DEPRECATED_ALIASES[alias].successor
    assert report["deprecated_aliases"] == [mar.alias_marker(alias)]


def test_constrained_by_is_a_documentation_only_deprecated_name(fx):
    """The model retirement record: constrainedBy is NOT an alias of hasRegulatorySource."""
    service, _ = _build(fx, authority="model")
    assert "constrainedBy" not in service._mapped_predicates()
    assert mar.DEPRECATED_ALIASES["constrainedBy"].answer_mode == "documentation-only"
    report = service.semantic_neighbors("use-Requirement", predicates=["constrainedBy"])
    assert report["edges"] == []
    assert report["deprecated_aliases"] == [mar.alias_marker("constrainedBy")]
    assert mar.alias_marker("constrainedBy")["answer_mode"] == "documentation-only"
    assert mar.alias_marker("constrainedBy")["successor"] == "hasRegulatorySource"


def test_alias_end_pair_does_not_widen_to_other_successor_pairs(fx):
    service, _ = _build(fx, authority="model")
    assert service.semantic_neighbors("use-Function", predicates=["realizedBy"])["edges"] == []
    assert service.semantic_neighbors("use-Function", predicates=["deployedTo"])["edges"] == []


def test_default_impact_carries_no_alias_edges(fx):
    service, _ = _build(fx, authority="model")
    report = service.impact("use-Requirement")
    predicates = {edge["predicate"] for edge in report["edges"]}
    assert "allocatedTo" in predicates
    assert not predicates & set(mar.DEPRECATED_ALIASES)
    assert "deprecated_aliases" not in report


def test_successor_contract_mismatch_refuses_construction(fx, monkeypatch):
    original = mar.generate_successor_contract
    def changed(root):
        contract = copy.deepcopy(original(root))
        contract["id"] = "sha256:" + "9" * 64
        return contract
    monkeypatch.setattr(mar, "generate_successor_contract", changed)
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
    assert report["summary"]["unregistered_yaml_identities"] == 12
    assert report["duplicates"] == []
    for value in report["identities"].values():
        assert value["status"] in {"projected", "residual"}
        assert ("layer_digest" in value) if value["status"] == "projected" else value["reason"]
    assert report["kernel_declarations"]
    assert coverage.compare(report, coverage.load_baseline(ROOT)) == []


def test_coverage_compare_detects_drift_duplicates_and_digest_mismatch():
    report = coverage.build_report(ROOT)
    baseline = coverage.baseline_from_report(report)
    grown = dict(report, residual=report["residual"] + ["Planted"])
    assert any("new residual" in e for e in coverage.compare(grown, baseline))
    # The retained residual is empty once batch 2 is admitted, so plant the
    # resolved entry in the baseline rather than removing one from the report.
    stale = dict(baseline, residual=list(baseline["residual"]) + ["Planted"])
    assert any("resolved" in e for e in coverage.compare(report, stale))
    assert coverage.compare(dict(report, duplicates=["X: a and b"]), baseline)
    assert coverage.compare(report, dict(baseline, routing_digest="sha256:" + "0" * 64))


def test_coverage_bundle_cross_check(fx):
    report = coverage.build_report(ROOT)
    assert coverage.bundle_errors(report, fx["bundle"], ROOT) == []
    bundle = copy.deepcopy(fx["bundle"])
    bundle["components"]["layers"][0]["profile"]["sha256"] = "sha256:" + "0" * 64
    assert any("layer digests" in e for e in coverage.bundle_errors(report, bundle, ROOT))


def test_coverage_baseline_has_no_binding_block():
    document = coverage.load_baseline(ROOT)
    assert "binding" not in document and document["mode"] == "shadow"


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
