"""Identities use consumed semantics, never copied authoritative fixtures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from de4sdv.semantic import model_contract as mc
from de4sdv.semantic import model_projection_coverage as coverage
from de4sdv.semantic import relationship_successor_contract as successor
from de4sdv.sysml_api.revisions import SemanticAuthorityIdentity


PIN_FILE = "synthetic/endpoints.sysml"
PIN_INPUT = "synthetic/projection.json"
CLASS_PINS = {
    "Origin": {"file": PIN_FILE, "declaration": "part def Origin"},
    "Destination": {"file": PIN_FILE, "declaration": "part def Destination"},
}
EXPECTED_O2_CLASSES = (
    "MethodPhase", "MethodContractObligation", "EvaluationScopeMembership", "EvaluationSourceKind",
    "TestedScopeDeclaration", "RetainedExecutionRecordReference", "AcceptanceAttestationReference",
    "VerificationCase",
)
EXPECTED_O2_RELATIONSHIPS = (
    "hasSubject", "verifiedBy", "derivesRequirementFromNeed", "derivedRequirementsOfNeed",
    "hasRelevantArchitecture",
)
# Small invented construction inputs, not snapshots of governed model files.
SUCCESSOR_SOURCE = '''package DE4SDV_RelationshipSuccessor {
  connection def SyntheticLink {
    end source : SyntheticEndpoints::Origin;
    end target : SyntheticEndpoints::Destination;
  }
  part version : SuccessorVersionRecord {
    attribute :>> version = "synthetic.successor/v1";
    attribute :>> supersedes = "synthetic prior contract";
  }
  part link : SuccessorRelationRecord {
    attribute :>> predicate = "linksTo";
    attribute :>> carrier = "SyntheticLink";
    attribute :>> mechanism = "typed-connection";
    attribute :>> strength = "trace-only";
    attribute :>> sourceClass = "Origin";
    attribute :>> targetClass = "Destination";
    attribute :>> sourceUsage = "origin";
    attribute :>> targetUsage = "destination";
    attribute :>> inverse = "linkedFrom";
  }
  part retired : SuccessorRetirementRecord {
    attribute :>> predicate = "oldLink";
    attribute :>> reason = "retired; use linksTo";
  }
}
'''
EXPECTED_SUCCESSOR = {
    "schema": "synthetic.successor/v1",
    "supersedes": "synthetic prior contract",
    "classes": CLASS_PINS,
    "carriers": {"linksTo": {"file": successor.MODEL,
                              "declaration": "connection def SyntheticLink"}},
    "relations": {"linksTo": [{
        "predicate": "linksTo", "carrier": "SyntheticLink",
        "mechanism": "typed-connection", "strength": "trace-only",
        "sourceClass": "Origin", "targetClass": "Destination",
        "sourceUsage": "origin", "targetUsage": "destination",
        "inverse": "linkedFrom",
    }]},
    "retired": {"oldLink": "retired; use linksTo"},
}


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def synthetic_successor_root(tmp_path):
    _write(tmp_path, successor.MODEL, SUCCESSOR_SOURCE)
    _write(tmp_path, PIN_FILE,
           "package SyntheticEndpoints {\n  part def Origin {}\n"
           "  part def Destination {}\n}\n")
    _write(tmp_path, PIN_INPUT, '{"binding":{"source_revision":"' + "a" * 40 + '"}}\n')
    for relative in successor.PROGRAM_INPUTS:
        _write(tmp_path, relative, "# synthetic incidental construction input\n")
    return tmp_path


def _generate(root):
    return successor.generate_contract(root, class_pins=CLASS_PINS, pin_inputs=(PIN_INPUT,))


@pytest.mark.parametrize("field", [
    'attribute unknownSemanticRule : String = "policy";',
    'attribute unknownSemanticRule;',
    'attribute \'unknown semantic rule\' : String = "policy";',
    'attribute <rule> unknownSemanticRule : String = "policy";',
    'attribute predicate : String = "different predicate";',
])
def test_successor_refuses_unsupported_direct_owned_attributes(synthetic_successor_root, field):
    root = synthetic_successor_root
    assert successor.semantic_payload(_generate(root)) == EXPECTED_SUCCESSOR
    marker = "part link : SuccessorRelationRecord {"
    assert SUCCESSOR_SOURCE.count(marker) == 1
    changed = SUCCESSOR_SOURCE.replace(marker, marker + "\n    " + field)
    _write(root, successor.MODEL, changed)
    with pytest.raises(ValueError, match="unsupported record field"):
        _generate(root)


@pytest.mark.parametrize("noise", [
    '/* attribute unknownSemanticRule : String = "policy"; */',
    '// attribute unknownSemanticRule : String = "policy";\n',
    'part def NestedOwner { attribute unknownSemanticRule : String = "policy"; }',
])
def test_successor_field_inventory_ignores_nonowned_or_commented_attributes(synthetic_successor_root, noise):
    root = synthetic_successor_root
    marker = "part link : SuccessorRelationRecord {"
    _write(root, successor.MODEL, SUCCESSOR_SOURCE.replace(marker, marker + "\n    " + noise))
    assert successor.semantic_payload(_generate(root)) == EXPECTED_SUCCESSOR


def test_successor_field_inventory_keeps_attribute_words_inside_literal_values(synthetic_successor_root):
    root = synthetic_successor_root
    reason = 'retired; use linksTo; attribute unknownSemanticRule : String = "policy";'
    changed = SUCCESSOR_SOURCE.replace('"retired; use linksTo"', json.dumps(reason))
    _write(root, successor.MODEL, changed)
    observed = successor.semantic_payload(_generate(root))
    expected = {**EXPECTED_SUCCESSOR, "retired": {"oldLink": reason}}
    assert observed == expected


def test_successor_id_ignores_runtime_python_bytes(synthetic_successor_root):
    root = synthetic_successor_root
    before = _generate(root)
    semantic_keys = {"schema", "supersedes", "classes", "carriers", "relations", "retired"}
    assert {key: before[key] for key in semantic_keys} == EXPECTED_SUCCESSOR
    expected_id = "sha256:" + hashlib.sha256(json.dumps(
        EXPECTED_SUCCESSOR, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    runtime_file = "de4sdv/semantic/query.py"
    _write(root, runtime_file, "# an unrelated Python refactor\n")
    after = _generate(root)
    assert after["bound_inputs"][runtime_file] != before["bound_inputs"][runtime_file]
    assert before["id"] == after["id"] == expected_id


def _write_json(root, relative, value):
    _write(root, relative, json.dumps(value, indent=2, sort_keys=True) + "\n")


@pytest.fixture
def synthetic_layers_root(synthetic_successor_root):
    root = synthetic_successor_root
    definition, o2plus, vocabulary = mc.LAYERS
    batch2 = mc.BATCH2_LAYER
    rows = {
        definition.name: [{"identity": "Origin", "semantic_kind": "class",
                           "grounding": {"kernel_binding_contract": CLASS_PINS["Origin"]}}],
        o2plus.name: [{"identity": "SyntheticNative", "category": "native",
                      "construct": "SysML::PartUsage"}],
        vocabulary.name: [{"identity": "documents", "domain": {"identity": "Origin"},
                           "range": {"identity": "Destination"}, "support": "vocabulary-only",
                           "carrier": {"file": PIN_FILE, "declaration": "connection def Documents"}}],
        batch2.name: [
            {"identity": "Destination", "semantic_kind": "class", "admission_class": "definition",
             "grounding": {"kernel_binding_contract": CLASS_PINS["Destination"]}},
            {"identity": "describes", "semantic_kind": "relationship",
             "admission_class": "relationship-runtime", "support": "runtime",
             "relation": {"domain": {"ontology_class": "Origin"},
                          "range": {"ontology_class": "Destination"},
                          "semantic_strength": "declared"}},
            {"identity": "oldLink", "semantic_kind": "relationship", "admission_class": "retired-name",
             "relation": {"domain": {"ontology_class": "Origin"},
                          "range": {"ontology_class": "Destination"}},
             "retired": {"successor": "linksTo", "successor_navigation": "linkedFrom",
                         "refusal": "retired; use linkedFrom"}},
        ],
    }
    for spec in mc.LAYERS + mc.BATCH2_LAYERS:
        entries = [{"identity": row["identity"]} for row in rows[spec.name]]
        if spec == batch2:
            entries[1]["serializer_mechanics"] = {"strategy": "synthetic-membership",
                                                   "property": "ownedMember"}
            entries[2]["retired_resolution"] = {"successor": "linksTo", "navigation": "linkedFrom"}
        binding = {"source_revision": "a" * 40, "bound_inputs": {"synthetic.py": "sha256:" + "1" * 64}}
        _write_json(root, spec.projection_path, {"schema": spec.projection_schema,
                                               "binding": binding, "rows": rows[spec.name]})
        _write_json(root, spec.profile_path, {"schema": spec.profile_schema,
                                            "binding": binding, "entries": entries})
    _write(root, PIN_FILE, (root / PIN_FILE).read_text().replace(
        "\n}", "\n  connection def Documents {}\n}"))
    o2_classes = []
    for name in EXPECTED_O2_CLASSES:
        if name == "VerificationCase":
            o2_classes.append({"identity": name, "construct": {
                "kind": "native", "native_grounding": {"identity": "SysML::VerificationCaseUsage"}}})
        else:
            o2_classes.append({"identity": name, "grounding": {"kernel_binding_contract": {
                "source_file": "synthetic/o2.sysml", "declaration": "part def " + name}}})
    o2_relations = [{"identity": name, "relation": {
        "domain": {"ontology_class": "MethodPhase"},
        "range": {"ontology_class": "VerificationCase"}, "semantic_strength": "trace-only"}}
        for name in EXPECTED_O2_RELATIONSHIPS]
    o2_profiles = [{"for_identity": name, "serializer_mechanics": {
        "strategy": "synthetic-o2-membership", "property": "memberElement"}}
        for name in EXPECTED_O2_RELATIONSHIPS]
    for index, (relative, schema) in enumerate(mc.O2_PROJECTION_CHAIN):
        _write_json(root, relative, {"schema": schema, "concepts": o2_classes if index == 0 else [],
                                    "predicates": o2_relations if index == 0 else [],
                                    "binding": {"source_revision": "c" * 40}})
    for index, (relative, schema) in enumerate(mc.O2_PROFILE_CHAIN):
        _write_json(root, relative, {"schema": schema, "profiles": o2_profiles if index == 0 else [],
                                    "binding": {"source_revision": "c" * 40}})
    _write(root, "synthetic/o2.sysml", "package SyntheticO2 {\n" + "".join(
        "  part def " + name + " {}\n" for name in EXPECTED_O2_CLASSES if name != "VerificationCase") + "}\n")
    _write_json(root, "de4sdv/semantic/contract-data/ontology-identity-register.json", {"rows": [
        {"identity": "Origin", "accounting_status": "retained"},
        {"identity": "RemovedName", "accounting_status": "removed", "final_disposition": "REMOVE",
         "migration_class": "synthetic", "retirement_condition": "no replacement"},
    ]})
    _write(root, mc.KERNEL_INTERNAL_PATH,
           "schema: de4sdv.kernel-internal-declarations/v1\ngoverned_directory: synthetic\ndeclarations: {}\n")
    return root


def test_authority_identity_ignores_live_git_binding_metadata(synthetic_layers_root):
    root = synthetic_layers_root
    before = mc.build_model_contract(root)
    assert set(before.classes) == set(EXPECTED_O2_CLASSES) | {"Origin", "Destination", "SyntheticNative"}
    assert set(before.relationships) == set(EXPECTED_O2_RELATIONSHIPS) | {
        "documents", "describes", "linksTo", "linkedFrom"}
    assert dict(before.refused) == {
        "RemovedName": "refused: removed (register disposition REMOVE, synthetic); no replacement",
        "oldLink": "retired; use linkedFrom",
    }
    frozen = {path: (root / path).read_bytes() for path, _ in mc.O2_PROJECTION_CHAIN + mc.O2_PROFILE_CHAIN}
    for spec in mc.LAYERS + mc.BATCH2_LAYERS:
        for path in (spec.projection_path, spec.profile_path):
            document = json.loads((root / path).read_text())
            document["binding"]["source_revision"] = "b" * 40
            document["binding"]["bound_inputs"]["synthetic.py"] = "sha256:" + "2" * 64
            _write_json(root, path, document)
    after = mc.build_model_contract(root)
    assert after.classes == before.classes and after.relationships == before.relationships
    assert after.refused == before.refused
    assert frozen == {path: (root / path).read_bytes() for path in frozen}
    assert before.identity == after.identity
    assert SemanticAuthorityIdentity.from_dict(after.identity.to_dict()) == before.identity


LIVE_DOCUMENTS = tuple((spec, profile) for spec in mc.LAYERS + mc.BATCH2_LAYERS
                       for profile in (False, True))


@pytest.mark.parametrize("spec,profile", LIVE_DOCUMENTS)
@pytest.mark.parametrize("location", ["wrapper", "record"])
def test_live_document_duplicate_json_keys_refuse_before_decode(synthetic_layers_root, spec, profile, location):
    root = synthetic_layers_root
    path = spec.profile_path if profile else spec.projection_path
    document = json.loads((root / path).read_text())
    raw = json.dumps(document, sort_keys=True)
    if location == "wrapper":
        raw = '{"status": "draft", "status": "admitted", ' + raw[1:]
    else:
        record = document["entries" if profile else "rows"][0]
        token = '"identity": ' + json.dumps(record["identity"])
        assert raw.count(token) >= 1
        raw = raw.replace(token, '"identity": "ConflictingSyntheticIdentity", ' + token, 1)
    _write(root, path, raw)
    with pytest.raises(mc.ModelAuthorityRefused, match="duplicate JSON object key"):
        mc.KernelContract.from_layers(root)


@pytest.mark.parametrize("spec,profile", LIVE_DOCUMENTS)
def test_live_document_refuses_unclassified_wrapper_field(synthetic_layers_root, spec, profile):
    root = synthetic_layers_root
    path = spec.profile_path if profile else spec.projection_path
    document = json.loads((root / path).read_text())
    document["new_semantic_rule"] = {"forbidden_relationship": "documents"}
    _write_json(root, path, document)
    with pytest.raises(mc.ModelAuthorityRefused, match="unclassified semantic document fields.*new_semantic_rule"):
        mc.build_model_contract(root)


@pytest.mark.parametrize("spec,profile", LIVE_DOCUMENTS)
@pytest.mark.parametrize("field", ["status", "warning"])
def test_live_document_wrapper_meaning_is_identity_sensitive(synthetic_layers_root, spec, profile, field):
    root = synthetic_layers_root
    path = spec.profile_path if profile else spec.projection_path
    document = json.loads((root / path).read_text())
    document[field] = "synthetic draft; vocabulary only, no traversal"
    _write_json(root, path, document)
    before = mc.build_model_contract(root)
    document[field] = "synthetic admitted; traversal claimed"
    _write_json(root, path, document)
    after = mc.build_model_contract(root)
    assert before.classes == after.classes and before.relationships == after.relationships
    assert before.refused == after.refused and before.lineage_pinned == after.lineage_pinned
    assert before.identity.id != after.identity.id


@pytest.mark.parametrize("spec,field,value", [
    (mc.LAYERS[0], "scope", {"admitted": ["Origin"], "note": "bounded synthetic admission"}),
    (mc.BATCH2_LAYER, "scope", {"admitted": ["Destination"], "exceptions": []}),
    (mc.LAYERS[1], "scope", {"projection_rows": ["SyntheticNative"], "api_profile_entries": []}),
    (mc.LAYERS[2], "candidates", ["documents", "unadmitted"]),
    (mc.LAYERS[2], "admitted", ["documents"]),
])
def test_live_document_scope_and_population_meaning_is_identity_sensitive(synthetic_layers_root, spec, field, value):
    root = synthetic_layers_root
    path = spec.projection_path
    document = json.loads((root / path).read_text())
    document[field] = value
    _write_json(root, path, document)
    before = mc.build_model_contract(root)
    if isinstance(value, dict):
        document[field]["new_boundary"] = {"forbidden_relationship": "documents"}
    else:
        document[field].append("changed-synthetic-population")
    _write_json(root, path, document)
    after = mc.build_model_contract(root)
    assert before.classes == after.classes and before.relationships == after.relationships
    assert before.identity.id != after.identity.id


@pytest.mark.parametrize("spec", mc.LAYERS + mc.BATCH2_LAYERS)
def test_live_document_profile_does_not_admit_projection_fields(synthetic_layers_root, spec):
    root = synthetic_layers_root
    document = json.loads((root / spec.profile_path).read_text())
    document["rows"] = []
    _write_json(root, spec.profile_path, document)
    with pytest.raises(mc.ModelAuthorityRefused, match="unclassified semantic document fields.*rows"):
        mc.build_model_contract(root)


def test_authority_id_covers_successor_endpoint_usage(synthetic_layers_root):
    root = synthetic_layers_root
    before = mc.build_model_contract(root)
    first_successor = mc.generate_model_successor_contract(root)
    source = (root / successor.MODEL).read_text()
    changed = source.replace('sourceUsage = "origin"', 'sourceUsage = "otherOrigin"')
    assert changed != source
    _write(root, successor.MODEL, changed)
    after = mc.build_model_contract(root)
    second_successor = mc.generate_model_successor_contract(root)
    assert first_successor["id"] != second_successor["id"]
    # Class pins and traversal mappings alone do not encode endpoint usage.
    assert after.classes == before.classes and after.relationships == before.relationships
    assert after.identity.id != before.identity.id


def test_coverage_baseline_ratchets_routing_and_dispositions_only(synthetic_layers_root):
    report = coverage.build_report(synthetic_layers_root)
    assert report["residual"] == report["residual_declarations"] == []
    assert report["kernel_accounting_errors"] == report["duplicates"] == []
    assert report["refused"] == ["RemovedName"] and report["retired"] == ["oldLink"]
    assert report["kernel_declarations"] and report["identities"]
    expected = {"schema": coverage.BASELINE_SCHEMA, "mode": "blocking",
                "routing_digest": report["routing_digest"],
                "refused": ["RemovedName"], "retired": ["oldLink"]}
    assert coverage.compare(report, expected) == []
    baseline = coverage.baseline_from_report(report)
    assert set(baseline) == set(expected) | {"note"}
    assert {key: baseline[key] for key in expected} == expected
    changed = dict(report, layer_digests={"diagnostic-only": "sha256:" + "0" * 64})
    assert coverage.compare(changed, baseline) == []
    # Previously committed digest fields are also harmless provenance, not a ratchet.
    assert coverage.compare(changed, dict(baseline, layer_digests=report["layer_digests"])) == []


@pytest.mark.parametrize("change", ["remove-bindings", "json-format", "python", "pilot", "aebs", "pin-comment"])
def test_incidental_changes_preserve_both_identities_and_cache_key(synthetic_layers_root, change):
    from de4sdv.semantic.corpus_cache import corpus_snapshot_path

    root = synthetic_layers_root
    before = mc.build_model_contract(root)
    first_successor = mc.generate_model_successor_contract(root)
    if change in {"remove-bindings", "json-format"}:
        for spec in mc.LAYERS + mc.BATCH2_LAYERS:
            for path in (spec.projection_path, spec.profile_path):
                document = json.loads((root / path).read_text())
                if change == "remove-bindings":
                    del document["binding"]
                _write(root, path, json.dumps(document, sort_keys=False, separators=(",", ":")) + "\n\n")
    else:
        relative = {
            "python": "de4sdv/semantic/model_contract.py",
            "pilot": "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml",
            "aebs": "textual-notation-of-model/packages/features/aebs/aebs_logical_architecture.sysml",
            "pin-comment": PIN_FILE,
        }[change]
        _write(root, relative, (root / relative).read_text() + "\n// synthetic nonsemantic comment\n")
    after = mc.build_model_contract(root)
    second_successor = mc.generate_model_successor_contract(root)
    assert successor.semantic_payload(first_successor) == EXPECTED_SUCCESSOR
    assert successor.semantic_payload(second_successor) == EXPECTED_SUCCESSOR
    assert first_successor["bound_inputs"] != second_successor["bound_inputs"]
    assert first_successor["id"] == second_successor["id"]
    assert before.identity == after.identity
    services = [SimpleNamespace(binding=SimpleNamespace(sysml_commit_id="same-api-revision"),
                                semantic_authority_id=c.identity.id) for c in (before, after)]
    assert corpus_snapshot_path(services[0], directory=root) == corpus_snapshot_path(services[1], directory=root)


@pytest.mark.parametrize("old,new", [
    ('version = "synthetic.successor/v1"', 'version = "synthetic.successor/v2"'),
    ('supersedes = "synthetic prior contract"', 'supersedes = "different prior contract"'),
    ('targetUsage = "destination"', 'targetUsage = "otherDestination"'),
    ('strength = "trace-only"', 'strength = "native"'),
    ('mechanism = "typed-connection"', 'mechanism = "native-allocation"'),
    ("SyntheticLink", "RenamedLink"),
    ('reason = "retired; use linksTo"', 'reason = "never serve the retired name"'),
])
def test_successor_semantic_changes_alter_both_ids(synthetic_layers_root, old, new):
    from de4sdv.semantic.corpus_cache import corpus_snapshot_path

    root = synthetic_layers_root
    before = mc.build_model_contract(root)
    first_successor = mc.generate_model_successor_contract(root)
    source = (root / successor.MODEL).read_text()
    changed = source.replace(old, new)
    assert changed != source
    _write(root, successor.MODEL, changed)
    after = mc.build_model_contract(root)
    second_successor = mc.generate_model_successor_contract(root)
    assert first_successor["id"] != second_successor["id"]
    assert before.identity.id != after.identity.id
    services = [SimpleNamespace(binding=SimpleNamespace(sysml_commit_id="same-api-revision"),
                                semantic_authority_id=c.identity.id) for c in (before, after)]
    assert corpus_snapshot_path(services[0], directory=root) != corpus_snapshot_path(services[1], directory=root)


@pytest.mark.parametrize("path,old,new", [
    (mc.BATCH2_LAYER.projection_path, '"semantic_strength": "declared"', '"semantic_strength": "native"'),
    (mc.BATCH2_LAYER.profile_path, '"property": "ownedMember"', '"property": "memberElement"'),
    (mc.LAYERS[1].projection_path, '"SysML::PartUsage"', '"SysML::ItemUsage"'),
    (mc.LAYERS[2].projection_path, '"vocabulary-only"', '"unsupported"'),
    (mc.LAYERS[2].projection_path, '"connection def Documents"', '"connection def OtherDocuments"'),
    ("de4sdv/semantic/contract-data/ontology-identity-register.json", '"no replacement"', '"explicitly removed"'),
])
def test_served_contract_semantic_changes_alter_authority_id(synthetic_layers_root, path, old, new):
    root = synthetic_layers_root
    before = mc.build_model_contract(root)
    source = (root / path).read_text()
    changed = source.replace(old, new)
    assert changed != source
    _write(root, path, changed)
    assert mc.build_model_contract(root).identity.id != before.identity.id


def test_proven_endpoint_pin_change_alters_both_ids(synthetic_layers_root):
    root = synthetic_layers_root
    before = mc.build_model_contract(root)
    first_successor = mc.generate_model_successor_contract(root)
    projection_path = mc.LAYERS[0].projection_path
    document = json.loads((root / projection_path).read_text())
    document["rows"][0]["grounding"]["kernel_binding_contract"]["file"] = "synthetic/moved-endpoints.sysml"
    _write_json(root, projection_path, document)
    _write(root, "synthetic/moved-endpoints.sysml", "package SyntheticEndpoints {\n  part def Origin {}\n}\n")
    after = mc.build_model_contract(root)
    second_successor = mc.generate_model_successor_contract(root)
    assert second_successor["classes"]["Origin"] == {
        "file": "synthetic/moved-endpoints.sysml", "declaration": "part def Origin"}
    assert first_successor["id"] != second_successor["id"]
    assert before.identity.id != after.identity.id


@pytest.mark.parametrize("profile,field,before_value,after_value", [
    (False, "definition", {"documentation": "A synthetic origin."},
     {"documentation": "A destination, not an origin."}),
    (False, "grounding", {"kernel_binding_contract": CLASS_PINS["Origin"],
                          "ontology_relations": {"disjoint_with": ["Destination"]}},
     {"kernel_binding_contract": CLASS_PINS["Origin"], "ontology_relations": {"disjoint_with": []}}),
    (False, "traversal", False, True),
    (True, "representation_class", "part-definition", "item-definition"),
    (True, "binding_contract_echo", {"api_metaclass": "PartDefinition", **CLASS_PINS["Origin"]},
     {"api_metaclass": "ItemDefinition", **CLASS_PINS["Origin"]}),
    (True, "witness_forms", ["synthetic owned documentation"], ["synthetic referenced documentation"]),
])
def test_declared_semantics_outside_runtime_mapping_are_identity_sensitive(
        synthetic_layers_root, profile, field, before_value, after_value):
    root = synthetic_layers_root
    spec = mc.LAYERS[0]
    path, section = (spec.profile_path, "entries") if profile else (spec.projection_path, "rows")
    document = json.loads((root / path).read_text())
    document[section][0][field] = before_value
    _write_json(root, path, document)
    before = mc.build_model_contract(root)
    document[section][0][field] = after_value
    _write_json(root, path, document)
    after = mc.build_model_contract(root)
    assert before.classes == after.classes and before.relationships == after.relationships
    assert before.identity.id != after.identity.id


def test_unclassified_projection_field_refuses_instead_of_becoming_metadata(synthetic_layers_root):
    root = synthetic_layers_root
    path = mc.LAYERS[0].projection_path
    document = json.loads((root / path).read_text())
    document["rows"][0]["new_semantic_rule"] = "must be classified before identity can be built"
    _write_json(root, path, document)
    with pytest.raises(mc.ModelAuthorityRefused, match="unclassified semantic record fields.*new_semantic_rule"):
        mc.build_model_contract(root)


@pytest.mark.parametrize("profile,field", [(False, "review_ref"), (True, "mechanics_refs"),
                                            (True, "representation")])
def test_named_record_provenance_is_excluded_from_identity(synthetic_layers_root, profile, field):
    root = synthetic_layers_root
    spec = mc.LAYERS[1]
    path, section = (spec.profile_path, "entries") if profile else (spec.projection_path, "rows")
    document = json.loads((root / path).read_text())
    value = {"bound_revision": "a" * 40, "program_digest": "sha256:" + "1" * 64}
    document[section][0][field] = ({"construct": "native", "mechanics": ["synthetic usage"],
                                  "toolchain": value} if field == "representation" else value)
    _write_json(root, path, document)
    before = mc.build_model_contract(root)
    value.update(bound_revision="b" * 40, program_digest="sha256:" + "2" * 64)
    _write_json(root, path, document)
    assert mc.build_model_contract(root).identity == before.identity


@pytest.mark.parametrize("spec", mc.LAYERS + mc.BATCH2_LAYERS)
@pytest.mark.parametrize("value", [17, "bad", [None], [[]], [{}], {"x": "bad"}, None])
def test_live_profile_malformed_entries_refuse_public_loader(synthetic_layers_root, spec, value):
    root = synthetic_layers_root
    document = json.loads((root / spec.profile_path).read_text())
    document["entries"] = value
    _write_json(root, spec.profile_path, document)
    with pytest.raises(mc.ModelAuthorityRefused):
        mc.KernelContract.from_layers(root)


@pytest.mark.parametrize("spec", mc.LAYERS + mc.BATCH2_LAYERS)
def test_live_profile_missing_collection_refuses_public_loader(synthetic_layers_root, spec):
    root = synthetic_layers_root
    document = json.loads((root / spec.profile_path).read_text())
    del document["entries"]
    _write_json(root, spec.profile_path, document)
    with pytest.raises(mc.ModelAuthorityRefused):
        mc.KernelContract.from_layers(root)


@pytest.mark.parametrize("spec", [mc.LAYERS[0], mc.LAYERS[2], mc.BATCH2_LAYER])
def test_live_profile_complete_pairs_refuse_missing_row_entry(synthetic_layers_root, spec):
    root = synthetic_layers_root
    document = json.loads((root / spec.profile_path).read_text())
    document["entries"].pop(0)
    _write_json(root, spec.profile_path, document)
    with pytest.raises(mc.ModelAuthorityRefused):
        mc.KernelContract.from_layers(root)


@pytest.mark.parametrize("spec", mc.LAYERS + mc.BATCH2_LAYERS)
@pytest.mark.parametrize("mode", ["agreeing", "conflicting-forward", "conflicting-reverse"])
def test_live_profile_duplicate_identity_refuses_in_either_order(synthetic_layers_root, spec, mode):
    root = synthetic_layers_root
    document = json.loads((root / spec.profile_path).read_text())
    entry = json.loads(json.dumps(document["entries"][-1]))
    if mode != "agreeing":
        entry["serializer_mechanics"] = {"strategy": "synthetic-membership", "property": "conflict"}
    document["entries"].append(entry)
    if mode == "conflicting-reverse":
        document["entries"].reverse()
    _write_json(root, spec.profile_path, document)
    with pytest.raises(mc.ModelAuthorityRefused, match="duplicate profile identity"):
        mc.KernelContract.from_layers(root)


@pytest.mark.parametrize("spec", mc.LAYERS + mc.BATCH2_LAYERS)
def test_live_profile_orphan_identity_refuses_public_loader(synthetic_layers_root, spec):
    root = synthetic_layers_root
    document = json.loads((root / spec.profile_path).read_text())
    document["entries"].append({"identity": "OrphanSyntheticIdentity"})
    _write_json(root, spec.profile_path, document)
    with pytest.raises(mc.ModelAuthorityRefused, match="orphan profile"):
        mc.KernelContract.from_layers(root)


@pytest.mark.parametrize("entry", [
    {"identity": None}, {"identity": ""}, {"identity": " Origin "}, {"identity": 17},
    {"identity": ["Origin"]}, {"identity": {}},
    {"identity": "Origin", "for_identity": "Destination"},
])
def test_live_profile_malformed_or_conflicting_identity_refuses(synthetic_layers_root, entry):
    root = synthetic_layers_root
    spec = mc.LAYERS[0]
    document = json.loads((root / spec.profile_path).read_text())
    document["entries"] = [entry]
    _write_json(root, spec.profile_path, document)
    with pytest.raises(mc.ModelAuthorityRefused):
        mc.KernelContract.from_layers(root)


@pytest.mark.parametrize("spec", mc.LAYERS + mc.BATCH2_LAYERS)
def test_live_profile_duplicate_projection_identity_refuses_before_join(synthetic_layers_root, spec):
    root = synthetic_layers_root
    document = json.loads((root / spec.projection_path).read_text())
    document["rows"].append(json.loads(json.dumps(document["rows"][0])))
    _write_json(root, spec.projection_path, document)
    with pytest.raises(mc.ModelAuthorityRefused, match="duplicate projection identity"):
        mc.KernelContract.from_layers(root)


@pytest.mark.parametrize("flag", ["api_profile_required", "api_profile_entry"])
def test_live_profile_o2plus_requires_only_modeled_outputs(synthetic_layers_root, flag):
    root = synthetic_layers_root
    spec = mc.LAYERS[1]
    projection = json.loads((root / spec.projection_path).read_text())
    projection["rows"][0]["outputs"] = {flag: True}
    projection["rows"].append({"identity": "OptionalNative", "category": "native",
                              "construct": "SysML::ItemUsage", "outputs": {flag: False}})
    _write_json(root, spec.projection_path, projection)
    before = mc.KernelContract.from_layers(root)
    assert {"SyntheticNative", "OptionalNative"} <= set(before.classes)
    profile = json.loads((root / spec.profile_path).read_text())
    profile["entries"] = []
    _write_json(root, spec.profile_path, profile)
    with pytest.raises(mc.ModelAuthorityRefused, match="missing required profile"):
        mc.KernelContract.from_layers(root)


def test_o2plus_partial_profile_witness_uses_actual_generated_documents():
    root = Path(__file__).resolve().parents[1]
    spec = mc.LAYERS[1]
    projection = json.loads((root / spec.projection_path).read_text())
    profile = json.loads((root / spec.profile_path).read_text())
    assert 0 < len(profile["entries"]) < len(projection["rows"])
    required = {r["identity"] for r in projection["rows"] if r["outputs"]["api_profile_entry"]}
    assert required == {mc._row_identity(e) for e in profile["entries"]} == {"Variant", "VariationPoint"}
    contract = mc.KernelContract.from_layers(root)
    assert required <= set(contract.classes)


def test_live_profile_o2plus_unmarked_synthetic_rows_allow_empty_population(synthetic_layers_root):
    root = synthetic_layers_root
    spec = mc.LAYERS[1]
    document = json.loads((root / spec.profile_path).read_text())
    document["entries"] = []
    _write_json(root, spec.profile_path, document)
    assert "SyntheticNative" in mc.KernelContract.from_layers(root).classes


def test_optional_batch2_absent_pair_stays_optional(synthetic_layers_root):
    root = synthetic_layers_root
    definition = mc.LAYERS[0]
    projection = json.loads((root / definition.projection_path).read_text())
    projection["rows"].append({"identity": "Destination", "semantic_kind": "class",
                              "grounding": {"kernel_binding_contract": CLASS_PINS["Destination"]}})
    _write_json(root, definition.projection_path, projection)
    profile = json.loads((root / definition.profile_path).read_text())
    profile["entries"].append({"identity": "Destination"})
    _write_json(root, definition.profile_path, profile)
    (root / mc.BATCH2_LAYER.projection_path).unlink()
    (root / mc.BATCH2_LAYER.profile_path).unlink()
    assert "Destination" in mc.KernelContract.from_layers(root).classes


# Consumed JSON shapes, not a second SysML parser or copies of governed models.
@pytest.mark.parametrize("spec,profile,index,keys,value", [
    (mc.LAYERS[0], False, 0, ("semantic_kind",), ["class"]),
    (mc.LAYERS[0], False, 0, ("grounding",), ["binding"]),
    (mc.BATCH2_LAYER, False, 0, ("admission_class",), ["definition"]),
    (mc.BATCH2_LAYER, False, 0, ("semantic_kind",), 17),
    (mc.BATCH2_LAYER, False, 0, ("grounding",), ["binding"]),
    (mc.BATCH2_LAYER, False, 0, ("grounding", "ontology_relations"), ["Origin"]),
    (mc.BATCH2_LAYER, False, 0, ("grounding", "ontology_relations", "sub_class_of"), ["Origin"]),
    (mc.BATCH2_LAYER, False, 1, ("relation",), ["relation"]),
    (mc.BATCH2_LAYER, False, 1, ("relation", "domain"), ["Origin"]),
    (mc.BATCH2_LAYER, False, 1, ("relation", "range"), ["Destination"]),
    (mc.BATCH2_LAYER, False, 1, ("relation", "domain", "ontology_class"), ["Origin"]),
    (mc.BATCH2_LAYER, False, 1, ("relation", "range", "ontology_class"), 17),
    (mc.BATCH2_LAYER, False, 1, ("relation", "semantic_strength"), ["declared"]),
    (mc.BATCH2_LAYER, False, 1, ("support",), ["runtime"]),
    (mc.BATCH2_LAYER, True, 1, ("serializer_mechanics",), "bad"),
    (mc.BATCH2_LAYER, True, 1, ("serializer_mechanics",), [["strategy", "bad"]]),
    (mc.BATCH2_LAYER, True, 1, ("serializer_mechanics", "strategy"), ["bad"]),
    (mc.BATCH2_LAYER, True, 2, ("retired_resolution",), ["bad"]),
    (mc.BATCH2_LAYER, True, 2, ("retired_resolution", "successor"), ["linksTo"]),
    (mc.BATCH2_LAYER, False, 2, ("retired", "successor_navigation"), ["linkedFrom"]),
    (mc.BATCH2_LAYER, False, 1, ("successor",), ["bad"]),
    (mc.BATCH2_LAYER, False, 1, ("successor", "end_pairs"), "bad"),
    (mc.BATCH2_LAYER, False, 1, ("successor", "end_pairs"), [None]),
    (mc.BATCH2_LAYER, False, 1, ("successor", "end_pairs"), [{"source_class": ["Origin"], "target_class": "Destination"}]),
    (mc.LAYERS[1], False, 0, ("category",), ["native"]),
    (mc.LAYERS[1], False, 0, ("construct",), 17),
    (mc.LAYERS[1], False, 0, ("grounding",), ["bad"]),
    (mc.LAYERS[1], False, 0, ("grounding", "witness"), ["bad"]),
    (mc.LAYERS[1], False, 0, ("grounding", "witness", "contains"), ["part def Origin"]),
    (mc.LAYERS[1], False, 0, ("outputs",), ["bad"]),
    (mc.LAYERS[1], False, 0, ("outputs", "api_profile_entry"), "true"),
    (mc.LAYERS[2], False, 0, ("domain",), ["Origin"]),
    (mc.LAYERS[2], False, 0, ("range",), ["Destination"]),
    (mc.LAYERS[2], False, 0, ("domain", "identity"), ["Origin"]),
    (mc.LAYERS[2], False, 0, ("range", "identity"), 17),
])
def test_live_provider_malformed_consumed_shapes_refuse_public_loader(
        synthetic_layers_root, spec, profile, index, keys, value):
    root = synthetic_layers_root
    path = spec.profile_path if profile else spec.projection_path
    document = json.loads((root / path).read_text())
    record = document["entries" if profile else "rows"][index]
    if spec == mc.LAYERS[1] and keys[0] == "grounding":
        record["category"] = "model-resident-vocabulary"
        record["grounding"] = {"witness": {"file": PIN_FILE, "contains": "part def Origin {"}}
    if keys[0] == "successor":
        record["admission_class"] = "successor"
        record["successor"] = {"end_pairs": [{"source_class": "Origin", "target_class": "Destination"}]}
    _write_json(root, path, document)
    mc.KernelContract.from_layers(root)
    for key in keys[:-1]:
        record = record.setdefault(key, {})
    record[keys[-1]] = value
    _write_json(root, path, document)
    with pytest.raises(mc.ModelAuthorityRefused):
        mc.KernelContract.from_layers(root)


@pytest.mark.parametrize("field,value,needle", [
    ("residual", ["MissingProvider"], "residual is blocking"),
    ("residual_declarations", ["synthetic/x.sysml::part def Missing"], "residual is blocking"),
    ("duplicates", ["Origin: definition and another"], "duplicate provider"),
    ("kernel_accounting_errors", ["unclassified synthetic declaration"], "unclassified"),
    ("refused", ["RemovedName", "AnotherRemoved"], "refused drift"),
    ("retired", ["oldLink", "AnotherRetired"], "retired drift"),
    ("routing_digest", "sha256:" + "0" * 64, "routing digest differs"),
])
def test_simplified_baseline_keeps_semantic_drift_and_absolute_blocks(synthetic_layers_root, field, value, needle):
    report = coverage.build_report(synthetic_layers_root)
    baseline = coverage.baseline_from_report(report)
    changed = dict(report, **{field: value})
    assert any(needle in error for error in coverage.compare(changed, baseline))
    if field in {"residual", "residual_declarations", "duplicates", "kernel_accounting_errors"}:
        assert any(needle in error for error in coverage.compare(changed, coverage.baseline_from_report(changed)))
