"""Synthetic API fixtures: executable slice, not privileged model closure."""
from pathlib import Path
import pytest
import mcp.client.stdio  # keep session-global stderr for later MCP tests
from de4sdv.semantic import composition_construction
from de4sdv.semantic.kernel_contract import KernelContract, declaration_identity
from de4sdv.sysml_api.revisions import RevisionBinding

ROOT = Path(__file__).resolve().parents[1]
REVISION = "a" * 40


def fixture_service():
    from de4sdv.semantic.relationship_successor_contract import generate_contract
    from de4sdv.semantic.composition_construction import build_successor_service
    contract = generate_contract(ROOT)
    legacy = KernelContract.load(ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml")
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
    elements.append({"@id": "allocation", "@type": "AllocationUsage",
                     "owningNamespace": {"@id": "context"},
                     "source": [{"@id": "use-Requirement"}],
                     "target": [{"@id": "use-Function"}]})
    binding = RevisionBinding.from_dict(dict(git_repository="fixture", git_commit=REVISION,
        sysml_project_id="pid", sysml_commit_id="cid", import_timestamp="2026-10-02T00:00:00Z",
        import_tool_version="synthetic", semantic_validation="passed", scope="fixture",
        ontology=legacy.identity.to_dict(), kernel_bindings=bindings))
    class Repository:
        def list_elements(self, *args): return elements
    service = build_successor_service(base_contract=legacy, contract=contract,
        binding=binding, repository=Repository(), expected_git_revision=REVISION, root=ROOT)
    return service, elements, binding, contract


def test_first_public_requirement_allocation_slice():
    # Feature-missing assertion is intentionally executed before implementation.
    assert hasattr(composition_construction, "build_relationship_successor_runtime")
    service, elements, binding, contract = fixture_service()
    result = service.semantic_neighbors("use-Requirement", predicates=["allocatedTo"])
    assert [(e["predicate"], e["target"], e["semantic_strength"]) for e in result["edges"]] == [
        ("allocatedTo", "use-Function", "allocation")]
    assert result["edges"][0]["api_object_id"] == "allocation"
    assert result["semantic_status"] == "complete"
    assert service.binder.bind_class("Function").sysml.element_id == "root-Function"



def rebuild(elements, binding, contract):
    from de4sdv.semantic.composition_construction import build_successor_service
    class Repository:
        def list_elements(self, *args): return elements
    return build_successor_service(base_contract=KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"),
        contract=contract, binding=binding, repository=Repository(),
        expected_git_revision=REVISION, root=ROOT)


def edge(kind, source, target, name="extra", **kwargs):
    return {"@id": name, "@type": kind, "source": [{"@id": source}],
            "target": [{"@id": target}], "owningNamespace": {"@id": "context"}, **kwargs}


@pytest.mark.parametrize("source,target", [("Function", "LogicalElement"), ("LogicalElement", "PhysicalElement")])
def test_other_approved_native_pairs(source, target):
    service, elements, _, _ = fixture_service()
    elements.append(edge("AllocationUsage", "use-" + source, "use-" + target))
    result = service.semantic_neighbors("use-" + source, predicates=["allocatedTo"])
    assert [(e["target"], e["api_object_id"]) for e in result["edges"]] == [("use-" + target, "extra")]


@pytest.mark.parametrize("source,target", [("Requirement", "LogicalElement"), ("PhysicalElement", "LogicalElement"), ("Need", "Function")])
def test_unapproved_pairs_and_need_cannot_masquerade_as_requirement(source, target):
    service, elements, _, _ = fixture_service()
    elements[:] = [e for e in elements if e["@id"] != "allocation"]
    elements.append(edge("AllocationUsage", "use-" + source, "use-" + target))
    result = service.semantic_neighbors("use-" + source, predicates=["allocatedTo"])
    assert result["edges"] == []
    assert result["semantic_status"] == "complete"


@pytest.mark.parametrize("predicate", ["hasValidationScenario", "hasRegulatorySource"])
def test_typed_planning_and_source_provenance_through_public_binder(predicate):
    service, elements, _, contract = fixture_service()
    row = contract["relations"][predicate][0]
    elements.append(edge("ConnectionUsage", "use-" + row["sourceClass"], "use-" + row["targetClass"],
        type=[{"@id": "root-" + predicate}]))
    report = service.semantic_neighbors("use-" + row["sourceClass"], predicates=[predicate])
    assert len(report["edges"]) == 1
    assert report["edges"][0]["semantic_strength"] == row["strength"]
    assert service.binder.bind_class(predicate).sysml.element_id == "root-" + predicate
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


def test_retired_stronger_claims_are_unsupported_not_aliases():
    service, _, _, contract = fixture_service()
    for name in contract["retired"]:
        report = service.semantic_neighbors("use-Requirement", predicates=[name])
        assert report["edges"] == []
        assert report["semantic_status"] == "incomplete"
        assert report["unsupported_predicates"][0]["authority_state"] == "retired"
    assert "hasRelevantFunction" not in service.contract.relationships
    assert not set(contract["retired"]) & set(service._mapped_predicates())


def test_public_impact_reports_allocation_without_mandatory_chain_or_duplicate_dependency():
    service, elements, _, _ = fixture_service()
    elements.append(edge("AllocationUsage", "use-Function", "use-LogicalElement", name="logical"))
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


def test_contract_tampering_and_production_refuse():
    from copy import deepcopy
    from de4sdv.semantic.composition_construction import build_successor_service
    _, elements, binding, contract = fixture_service()
    changed = deepcopy(contract)
    changed["relations"]["allocatedTo"][0]["targetClass"] = "PhysicalElement"
    with pytest.raises(ValueError, match="contract/source mismatch"):
        rebuild(elements, binding, changed)
    with pytest.raises(ValueError, match="non-production"):
        build_successor_service(base_contract=None, contract=contract, binding=binding,
            repository=None, expected_git_revision=REVISION, root=ROOT, production=True)


# ---- Reviewed SPEC findings: reference shapes, meanings, discrimination, grammar.
def _spec_query(mutate, predicate="allocatedTo", source="use-Requirement"):
    _, elements, binding, contract = fixture_service()
    binding = mutate(elements, binding, contract) or binding
    return rebuild(elements, binding, contract).semantic_neighbors(source, predicates=[predicate])


def test_supported_graph_reference_preserves_exact_witness():
    def mutate(elements, binding, contract):
        elements.extend([
            {"@id": "shadow", "@type": "ReferenceUsage"},
            {"@id": "ref", "@type": "ReferenceSubsetting", "subsettingFeature": {"@id": "shadow"},
             "subsettedFeature": {"@id": "use-Function"}}])
        next(e for e in elements if e["@id"] == "allocation")["target"] = [{"@id": "shadow"}]
    report = _spec_query(mutate)
    assert report["semantic_status"] == "complete"
    assert report["edges"][0]["target"] == "use-Function"
    assert report["edges"][0]["witness"]["native_target"] == "use-Function"
    assert report["edges"][0]["witness"]["reference_witnesses"][0]["api_object_id"] == "ref"


@pytest.mark.parametrize("shape", ["inlined", "conflicting-flat", "equivalent-graph"])
def test_inline_reference_is_normalized_with_other_witness_shapes(shape):
    def mutate(elements, binding, contract):
        elements.append({"@id": "shadow", "@type": "ReferenceUsage",
                         "referencedFeature": {"@id": "use-Function"}})
        if shape == "conflicting-flat":
            elements.append({"@id": "ref", "@type": "ReferenceSubsetting",
                "owningRelatedElement": {"@id": "shadow"}, "referencedFeature": {"@id": "use-LogicalElement"}})
        elif shape == "equivalent-graph":
            elements.append({"@id": "ref", "@type": "ReferenceSubsetting",
                "subsettingFeature": {"@id": "shadow"}, "subsettedFeature": {"@id": "use-Function"}})
        next(e for e in elements if e["@id"] == "allocation")["target"] = [{"@id": "shadow"}]
    report = _spec_query(mutate)
    if shape == "conflicting-flat":
        assert report["semantic_status"] == "incomplete"
        assert report["edges"] == []
    else:
        assert report["semantic_status"] == "complete"
        assert report["edges"][0]["target"] == "use-Function"
        witnesses = report["edges"][0]["witness"]["reference_witnesses"]
        assert witnesses
        if shape == "inlined":
            assert witnesses == [{"source": "shadow", "target": "use-Function",
                                  "kind": "referencedFeature", "api_object_id": "shadow"}]


def test_conflicting_flat_and_graph_reference_refuses_structurally():
    def mutate(elements, binding, contract):
        elements.extend([
            {"@id": "shadow", "@type": "ReferenceUsage"},
            {"@id": "ref", "@type": "ReferenceSubsetting", "owningRelatedElement": {"@id": "shadow"},
             "referencedFeature": {"@id": "use-Function"}, "target": {"@id": "use-LogicalElement"}}])
        next(e for e in elements if e["@id"] == "allocation")["target"] = [{"@id": "shadow"}]
    report = _spec_query(mutate)
    assert report["edges"] == []
    assert report["semantic_status"] == "incomplete"


def test_dangling_endpoint_typing_is_incomplete_not_complete_absence():
    def mutate(elements, binding, contract):
        next(e for e in elements if e["@id"] == "use-Function")["type"] = [{"@id": "absent-definition"}]
    report = _spec_query(mutate)
    assert report["edges"] == []
    assert report["semantic_status"] == "incomplete"
    assert any(r["predicate"] == "allocatedTo" for r in report["unsupported_predicates"])


def test_dangling_carrier_typing_is_incomplete_not_complete_absence():
    def mutate(elements, binding, contract):
        elements.append(edge("ConnectionUsage", "use-Need", "use-ValidationScenario", name="plan",
                             type=[{"@id": "absent-carrier"}]))
    report = _spec_query(mutate, "hasValidationScenario", "use-Need")
    assert report["edges"] == []
    assert report["semantic_status"] == "incomplete"


def test_untyped_carrier_candidate_is_incomplete_not_silent_absence():
    def mutate(elements, binding, contract):
        elements.append(edge("ConnectionUsage", "use-Need", "use-ValidationScenario", name="plan"))
    report = _spec_query(mutate, "hasValidationScenario", "use-Need")
    assert report["edges"] == []
    assert report["semantic_status"] == "incomplete"


@pytest.mark.parametrize("mode", ["mixed-valid", "mixed-unrelated", "dangling-supertype", "mixed-carrier"])
def test_every_discrimination_branch_must_be_resolved(mode):
    def mutate(elements, binding, contract):
        if mode == "mixed-carrier":
            elements.append(edge("ConnectionUsage", "use-Need", "use-ValidationScenario", name="plan",
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
    elements.append(edge("ConnectionUsage", "use-Need", "use-ValidationScenario", name="both-carriers",
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
    from de4sdv.semantic.relationship_successor_contract import MODEL
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
    from de4sdv.semantic.relationship_successor_contract import generate_contract, MODEL
    read_text, read_bytes = Path.read_text, Path.read_bytes
    def text_read(path, *args, **kwargs):
        return text if path == ROOT / MODEL else read_text(path, *args, **kwargs)
    def bytes_read(path, *args, **kwargs):
        return text.encode() if path == ROOT / MODEL else read_bytes(path, *args, **kwargs)
    with patch.object(Path, "read_text", text_read), patch.object(Path, "read_bytes", bytes_read):
        return generate_contract(ROOT)


@pytest.mark.parametrize("literal", ["synthetic://review", "synthetic:/*review*/", "synthetic://{\"quoted\"}"])
def test_comment_tokens_inside_owned_literal_are_not_comments(literal):
    import json
    from de4sdv.semantic.relationship_successor_contract import MODEL
    text = (ROOT / MODEL).read_text()
    old = '"Function-to-LogicalElement allocatedTo signature; historical provenance constrainedBy; stronger realizedBy/deployedTo active claims"'
    text = text.replace(old, json.dumps(literal), 1)
    assert _contract_from_model_text(text)["supersedes"] == literal


@pytest.mark.parametrize("field", ["supersedes", "retirement-predicate"])
def test_missing_required_record_field_is_a_controlled_refusal(field):
    from de4sdv.semantic.relationship_successor_contract import MODEL
    text = (ROOT / MODEL).read_text()
    if field == "supersedes":
        start = text.index("    attribute :>> supersedes =")
    else:
        start = text.index('    attribute :>> predicate = "realizedBy";')
    end = text.index("\n", start)
    with pytest.raises(ValueError):
        _contract_from_model_text(text[:start] + text[end:])


def test_class_pins_come_from_ontology_not_model_records():
    """Review R2: the model carries no file-path class records."""
    from de4sdv.semantic.relationship_successor_contract import MODEL, ONTOLOGY, generate_contract
    text = (ROOT / MODEL).read_text()
    assert "SuccessorClassRecord" not in text
    assert "sourceFile" not in text
    contract = generate_contract(ROOT)
    assert ONTOLOGY in contract["bound_inputs"]
    assert contract["classes"]["Function"] == {"file": MODEL, "declaration": "action def AllocatableFunction"}
    assert contract["classes"]["Requirement"]["declaration"] == "requirement def RequirementCandidate"


@pytest.mark.parametrize("mutation", ["remove-mapping", "ambiguous-specialization"])
def test_missing_or_ambiguous_ontology_class_pin_refuses(mutation):
    from unittest.mock import patch
    import yaml
    from de4sdv.semantic.relationship_successor_contract import ONTOLOGY, generate_contract
    document = yaml.safe_load((ROOT / ONTOLOGY).read_text())
    if mutation == "remove-mapping":
        del document["classes"]["AllocatableFunction"]
    else:
        document["classes"]["SecondAllocatableFunction"] = {
            "subClassOf": "Function", "kernel": {"file": "x.sysml", "declaration": "action def Other"}}
    overlay = yaml.safe_dump(document)
    read_text = Path.read_text

    def text_read(path, *args, **kwargs):
        return overlay if path == ROOT / ONTOLOGY else read_text(path, *args, **kwargs)
    with patch.object(Path, "read_text", text_read):
        with pytest.raises(ValueError, match="missing endpoint class pin: Function"):
            generate_contract(ROOT)


def test_unbalanced_or_unreadable_pin_is_a_controlled_refusal():
    """QUALITY S2: malformed source raises ValueError, never IndexError."""
    from de4sdv.semantic.relationship_successor_contract import _definition_owner
    with pytest.raises(ValueError, match="unbalanced braces"):
        _definition_owner("}\n{ {\npart def X {}\n", "part def X")
    with pytest.raises(ValueError, match="not directly owned"):
        _definition_owner("part def X {}\n", "part def X")


def _semantics(contract):
    """Contract meaning without the digests that legitimately move with source."""
    return {key: value for key, value in contract.items() if key not in {"id", "bound_inputs"}}


def test_commented_duplicate_record_cannot_override_the_active_record():
    """R2-SPEC-1: a commented decoy must not supply schema or supersedes."""
    import json
    from de4sdv.semantic.relationship_successor_contract import MODEL
    text = (ROOT / MODEL).read_text()
    anchor = "  part version : SuccessorVersionRecord {"
    assert anchor in text
    decoy = ("/*\n  part version : SuccessorVersionRecord {\n"
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
    """R2-SPEC-2: an unrestricted name is one inert token at any boundary."""
    from de4sdv.semantic.relationship_successor_contract import MODEL
    text = (ROOT / MODEL).read_text()
    anchor = "  part version : SuccessorVersionRecord {\n"
    assert anchor in text
    baseline = _semantics(_contract_from_model_text(text))
    inserted = _semantics(_contract_from_model_text(
        text.replace(anchor, anchor + "    " + noise + "\n", 1)))
    assert inserted == baseline


def test_duplicate_live_record_declaration_refuses_instead_of_first_match():
    from de4sdv.semantic.relationship_successor_contract import MODEL
    text = (ROOT / MODEL).read_text()
    anchor = "  part version : SuccessorVersionRecord {\n"
    duplicate = anchor + '    attribute :>> version = "synthetic-decoy";\n' \
                         '    attribute :>> supersedes = "synthetic-decoy";\n  }\n'
    with pytest.raises(ValueError):
        _contract_from_model_text(text.replace(anchor, duplicate + anchor, 1))
