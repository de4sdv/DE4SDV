"""Kernel-vocabulary projection: model homes, scope and reviewed contracts.

This cleanup retires live Git binding and the copied documentation oracle, not model
ownership or contract validation. The manifest holds the reviewed contract
fields; the generated rows label them with their pre-deletion comparison
evidence, which is archived at the release-2026-10-11 tag, or say that none
exists for a class a method pull request admitted after the deletion.
Synthetic negative tests preserve successor, retirement, about-target, carrier,
lineage, external-reference, PLE and non-claim guards. No real model copies.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = "de4sdv/semantic/contract-data/"
#: Recorded values of the manifest-held contract fields (fields the model does
#: not carry structurally, held by the reviewed admission manifest).
MANIFEST_HELD_FIXTURE = "tests/fixtures/manifest-held-contract-fields.json"
MANIFEST_PATH = DATA + "kernel-vocabulary-admission.yaml"
REGISTER_PATH = DATA + "ontology-identity-register.json"
SUCCESSOR_FILE = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_trace_vocabulary.sysml"

OTHER_LAYERS = {
    "o2-chain": [
        ("de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.json", ("concepts",)),
        ("de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.1.json", ("concepts", "predicates")),
        ("de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.2.json", ("predicates",)),
    ],
    "definition-batch-1": [(DATA + "class-definition-projection.json", ("rows",))],
    "o2plus": [(DATA + "native-grounding-projection.json", ("rows",))],
}
NEW_SUCCESSOR_PREDICATES = {"hasValidationScenario", "hasRegulatorySource"}
MERGED_ALIASES = {"validatesFitnessForUse"}
#: Classes a method pull request admitted after the authored ontology's
#: deletion (ADR 0022 step S2k): no authored-ontology comparison exists for them.
METHOD_ADMITTED_CLASSES = {"DerivationRule", "DerivedVariation", "ProductModelProjection",
                           "ProductModelProjectionName", "UnassignedBindingTime"}
#: Rows whose manifest-held fields were proven equal to the authored ontology.
ONTOLOGY_COMPARED_HELD_ROWS = 49
#: Owner decision 2026-10-06 (ADR 0020 D4 follow-up): the closure is exactly these.
AEBS = "textual-notation-of-model/packages/features/aebs/"
EC_CLOSURE = {
    (AEBS + "aebs_bicycle_verification.sysml", "requirement def BicycleEvidenceContract"),
    (AEBS + "aebs_degraded_input_verification.sysml", "requirement def DegradedInputEvidenceContract"),
    (AEBS + "aebs_evidence.sysml", "requirement def NominalEvidenceContractRequirement"),
    (AEBS + "aebs_non_activation_verification.sysml", "requirement def NonActivationEvidenceContract"),
    (AEBS + "aebs_override_verification.sysml", "requirement def OverrideEvidenceContract"),
    (AEBS + "aebs_partial_intervention_verification.sysml", "requirement def PartialInterventionEvidenceContract"),
    (AEBS + "aebs_pedestrian_verification.sysml", "requirement def PedestrianEvidenceContract"),
    (AEBS + "aebs_regulatory_criterion_verification.sysml", "requirement def RegulatoryCriterionEvidenceContract"),
}
MODEL_ROOTS = (
    "textual-notation-of-model",
    "model-based-product-line-engineering/product-models",
    "model-based-product-line-engineering/scoping",
)
INVENTORY_GOVERNANCE_FIELDS = (
    "authority_current", "authority_target", "evidence_state", "adoption_status",
    "transition_gate", "conditional_target", "disposition", "confidence", "stage",
    "unknowns", "required_evidence", "exact_fit_decision",
)


def _json(relative):
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def _manifest():
    return yaml.safe_load((REPO_ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))


def _register():
    return {row["identity"]: row for row in _json(REGISTER_PATH)["rows"]}


def _layer_identities():
    layers = {}
    for layer, documents in OTHER_LAYERS.items():
        ids = set()
        for relative, sections in documents:
            document = _json(relative)
            for section in sections:
                ids |= {row["identity"] for row in document[section]}
        layers[layer] = ids
    return layers


def _rows():
    return {row["identity"]: row for row in _manifest()["admitted"]}


def _outputs():
    from de4sdv.semantic import kernel_vocabulary_projection as kernel_vocabulary

    return kernel_vocabulary.build_outputs(REPO_ROOT, kernel_vocabulary.load_document(REPO_ROOT))


# ---------------------------------------------------------------------------
# 1. Family, exceptions and complete coverage
# ---------------------------------------------------------------------------


def test_admitted_set_is_exactly_the_derived_family():
    from de4sdv.semantic.model_contract import FROZEN_RECORD_IDENTITIES as MIGRATED_IDENTITIES

    register = _register()
    other = set().union(*_layer_identities().values())
    retained = {i for i, r in register.items() if r["accounting_status"] == "retained" and not r["o3_complete"]}
    family = (retained - other) | NEW_SUCCESSOR_PREDICATES | MERGED_ALIASES
    from de4sdv.semantic.kernel_vocabulary_projection import ADMISSION_CLASSES

    rows = _rows()
    # Content, not counts: admitting another definition must not trip this test.
    # Every retained register row that no other layer projects is admitted here,
    # with the named successors and the merged retired name; every other
    # admitted row is a class outside the register.
    assert family <= set(rows)
    assert all(rows[i]["semantic_kind"] == "class" for i in set(rows) - family)
    assert not (set(rows) - family) & set(register)
    assert len(rows) == len(_manifest()["admitted"])  # one admitted entry per identity
    assert not set(rows) & set(MIGRATED_IDENTITIES)
    assert not set(rows) & other
    by_class: dict[str, set[str]] = {}
    # Kind-consistency guard only: ADMISSION_CLASSES is the generator's own table.
    for identity, row in rows.items():
        admission = row["admission_class"]
        assert admission in ADMISSION_CLASSES, (identity, admission)
        assert ADMISSION_CLASSES[admission] in (None, row["semantic_kind"]), (identity, admission)
        by_class.setdefault(admission, set()).add(identity)
    assert NEW_SUCCESSOR_PREDICATES <= by_class.get("successor", set())
    assert MERGED_ALIASES <= by_class.get("retired-name", set())
    # The new successors are not register rows.
    assert not NEW_SUCCESSOR_PREDICATES & set(register)
    assert register["validatesFitnessForUse"]["accounting_status"] == "merged"


def test_every_retained_row_and_ontology_identity_has_exactly_one_provider():
    register = _register()
    layers = _layer_identities()
    layers["definition-batch-2"] = set(_rows())
    exceptions = {entry["identity"]: entry for entry in _manifest()["exceptions"]}
    universe = set(register)
    providers = {identity: [name for name, ids in layers.items() if identity in ids] for identity in universe}
    duplicates = {i: p for i, p in providers.items() if len(p) > 1}
    assert duplicates == {}
    uncovered = {i for i, p in providers.items() if not p}
    assert uncovered == set(exceptions)
    # No retained row is an exception: every retained row is model-projected.
    assert all(entry["accounting"] != "retained" for entry in exceptions.values())
    for identity, entry in exceptions.items():
        assert register[identity]["accounting_status"] == entry["accounting"]
    assert set(exceptions) == {"IncrementTraceabilityShell", "derivesNeedFromConcern", "addressesConcern",
                               "producesView", "recordsAssumption", "recordsGap", "selectedViewpoint",
                               "hasStakeholder"}
    retained = {i for i, r in register.items() if r["accounting_status"] == "retained"}
    assert retained <= set().union(*layers.values())


def test_projection_scope_echoes_the_owner_visible_exceptions():
    from de4sdv.semantic.kernel_vocabulary_projection import PROJECTION_PATH

    committed = _json(PROJECTION_PATH)
    assert committed["scope"]["exceptions"] == sorted(
        _manifest()["exceptions"], key=lambda entry: entry["identity"]
    )
    assert committed["scope"]["admitted"] == sorted(_rows())


# ---------------------------------------------------------------------------
# 2. Manifest-held contract labels, successors and retired names
# ---------------------------------------------------------------------------


def test_manifest_held_contract_fields_equal_the_recorded_values():
    """The manifest holds 50 rows' contract fields itself instead of the model
    (the model does not carry them structurally): kernel mapping, subclass and
    disjointness pins, and
    relation domain/range/direction/strength with mechanics. They feed the served
    class mappings and relationship specs, so each value and each row's admission
    class stay locked to the record made when they were last proven equal to the
    authored ontology. Changing one needs a reviewed update of the fixture."""
    from model_contract_fixtures import manifest_held_values

    recorded = _json(MANIFEST_HELD_FIXTURE)
    rows = _rows()
    assert set(recorded["entries"]) == set(rows)
    held = {identity: entry for identity, entry in recorded["entries"].items() if entry["manifest"]}
    assert len(held) == recorded["rows_with_manifest_held_contract_fields"] == (
        ONTOLOGY_COMPARED_HELD_ROWS + len(METHOD_ADMITTED_CLASSES))
    assert {i for i, r in rows.items() if r["register"]["accounting"] == "method-admitted"} == METHOD_ADMITTED_CLASSES
    for identity, row in rows.items():
        entry = recorded["entries"][identity]
        assert row["admission_class"] == entry["admission_class"], identity
        assert manifest_held_values(row) == entry["manifest"], identity
    assert {i for i, r in rows.items() if "mechanics" in r} == {
        "specifiesFunction", "hasRelevantEvidenceContract", "hasEvidence"}
    assert rows["realizedBy"]["admission_class"] == "retired-name"


def test_manifest_gates_match_the_register_gate_decisions():
    """Each retained row's gates are exactly the register's gate decisions (plus
    its row blocker); the merged retired name keeps only its blocker."""
    register = _register()
    for identity, row in _rows().items():
        reg = register.get(identity)
        expected = set()
        if reg is not None and reg["accounting_status"] == "retained":
            expected = set(reg["gate_decisions"]) | ({"row-blocker"} if reg["blockers"] else set())
        elif reg is not None:
            expected = {"row-blocker"} if reg["blockers"] else set()
        assert {gate["gate"] for gate in row["gates"]} == expected, identity


def test_every_contract_row_is_labeled_manifest_held():
    """Every generated row with manifest-held contract fields says so."""
    projected = {row["identity"]: row for row in _outputs()["projection_rows"]}
    labeled = compared = 0
    for identity, row in projected.items():
        for source in ((row.get("relation") or {}).get("contract_source"),
                       (row.get("grounding") or {}).get("contract_source")):
            if source:
                labeled += 1
                assert "reviewed admission-manifest" in source, identity
                assert "test-locked to the authored ontology" not in source, identity
                if identity in METHOD_ADMITTED_CLASSES:
                    # Admitted after the deletion: the row never claims a comparison.
                    assert "no authored-ontology comparison exists" in source, identity
                    assert "contract-equivalence.json" not in source and "parity" not in source, identity
                else:
                    compared += 1
                    assert "closure/contract-equivalence.json" in source, identity
    assert compared == ONTOLOGY_COMPARED_HELD_ROWS
    assert labeled == ONTOLOGY_COMPARED_HELD_ROWS + len(METHOD_ADMITTED_CLASSES)


def test_successors_and_retired_names_follow_the_relationship_redesign():
    """Replaces ``test_successors_and_aliases_follow_the_w6_transition_plan``:
    the former deprecated aliases are retired names (owner decision D4)."""
    rows = _rows()
    assert rows["specifiesFunction"]["admission_class"] == "relationship-runtime"
    assert {row["retired"]["successor"] for row in rows.values() if "retired" in row} <= {
        identity for identity, row in rows.items() if row["admission_class"] == "successor"
    }
    register = _register()
    assert register["validatesFitnessForUse"]["merge_into"] == "validatedBy"
    assert rows["validatesFitnessForUse"]["retired"]["direction"] == "inverse"
    projected = {row["identity"]: row for row in _outputs()["projection_rows"]}
    expected = {"realizedBy": "allocatedTo", "deployedTo": "allocatedTo",
                "validatedBy": "hasValidationScenario",
                "validatesFitnessForUse": "validationScenarioFor",
                "constrainedBy": "hasRegulatorySource"}
    for identity, navigation in expected.items():
        retired = projected[identity]["retired"]
        assert retired["successor_navigation"] == navigation, identity
        assert retired["refusal"] == f"retired; use {navigation}", identity
        assert projected[identity]["support"] == "retired", identity
        assert "alias" not in projected[identity], identity


# ---------------------------------------------------------------------------
# 3. Forward obligations
# ---------------------------------------------------------------------------


def test_runtime_queryable_targets_keep_their_forward_obligation():
    register = _register()
    for identity, row in _rows().items():
        reg = register.get(identity)
        if reg and str(reg["required_runtime_or_consumer_change"]["runtime_support_target"]).startswith("runtime-queryable"):
            assert any("exact-revision traversal evidence" in item for item in row["forward_obligations"]), identity
    rows = _rows()
    assert any("cardinality" in item for item in rows["hasAcceptanceCriterion"]["forward_obligations"])
    assert any("eight-contract" in item for item in rows["hasRelevantEvidenceContract"]["forward_obligations"])
    assert any("blocks activation" in item for item in rows["allocatedTo"]["forward_obligations"])


# ---------------------------------------------------------------------------
# 4. hasRelevantEvidenceContract: type-lineage discriminator, exact closure
# ---------------------------------------------------------------------------


def test_evidence_contract_closure_is_every_model_specialization_repo_wide():
    """Content test, no count: the closure the admission declares is exactly
    the set of model definitions that specialize EvidenceContract, which ADR
    0020 names (EC_CLOSURE)."""
    from de4sdv.semantic.kernel_vocabulary_projection import _Source

    found = set()
    for model_root in MODEL_ROOTS:
        for path in sorted((REPO_ROOT / model_root).rglob("*.sysml")):
            relative = path.relative_to(REPO_ROOT).as_posix()
            source = _Source(relative, path.read_text(encoding="utf-8"))
            for match in re.finditer(r"\b(\w+)\s+def\s+(\w+)\s*(?::>|\bspecializes\b)\s*([^;{]+)", source.mask):
                names = {item.strip().split("::")[-1] for item in match[3].split(",")}
                if "EvidenceContract" in names:
                    found.add((relative, f"{match[1]} def {match[2]}"))
    assert found == EC_CLOSURE
    row = _rows()["hasRelevantEvidenceContract"]
    assert {(p["file"], p["declaration"]) for p in row["range_discriminator"]["closure"]} == found
    projected = {r["identity"]: r for r in _outputs()["projection_rows"]}["hasRelevantEvidenceContract"]
    disc = projected["relation"]["range"]["discriminator"]
    assert disc["kind"] == "type-lineage"
    assert disc["lineage"]["declaration"] == "requirement def EvidenceContract"
    assert {(p["source_file"], p["declaration"]) for p in disc["closure"]} == found
    assert "prefix" in disc["rule"] and "never by name" in disc["rule"]


# ---------------------------------------------------------------------------
# 5. Generated rows
# ---------------------------------------------------------------------------


def test_generated_rows_carry_no_governance_fields_or_executable_claims():
    from de4sdv.semantic.kernel_vocabulary_projection import PROFILE_SCHEMA, SUPPORT

    outputs = _outputs()
    rows = _rows()
    # One projection row and one profile entry per admitted identity (by id, not count).
    projected = sorted(row["identity"] for row in outputs["projection_rows"])
    assert projected == sorted(rows)
    assert sorted(entry["for_concept"] for entry in outputs["profile_entries"]) == projected
    for row in outputs["projection_rows"]:
        serialized = json.dumps(row)
        for field in INVENTORY_GOVERNANCE_FIELDS + ("sysml_mapping", "gates", "forward_obligations"):
            assert f'"{field}"' not in serialized, (row["identity"], field)
        assert row["traversal"] is False and row["api_identity"] == "unclaimed"
        assert row["support"] == SUPPORT[row["admission_class"]]
        observation = row["definition"]["documentation_observation"]
        if rows[row["identity"]]["home"]["form"] in ("owned-doc", "named-doc"):
            assert observation == "model-owned-documentation", row["identity"]
        assert row["definition"]["documentation"].strip(), row["identity"]
    for entry in outputs["profile_entries"]:
        assert entry["profile_identity"] == f"{PROFILE_SCHEMA}#{entry['for_concept']}"
        serialized = json.dumps(entry)
        for field in INVENTORY_GOVERNANCE_FIELDS + ("sysml_mapping",):
            assert f'"{field}"' not in serialized, (entry["for_concept"], field)
        boundary = rows[entry["for_concept"]]["boundary"]
        assert ("configurator_authority" in entry) == (boundary == "ple-no-configurator-authority")
    ple = {r["identity"] for r in rows.values() if r["boundary"] == "ple-no-configurator-authority"}
    assert ple == {"FeatureConfiguration", "appliesToMemberProduct", "selectsFeature",
                   "includesCommonCapability", "selectsVariant"}
    assert all(rows[i]["admission_class"] in ("definition", "relationship-vocabulary") for i in ple)


def test_successor_rows_equal_the_model_records():
    projected = {r["identity"]: r for r in _outputs()["projection_rows"]}
    expected = {
        "allocatedTo": [("Requirement", "Function"), ("Function", "LogicalElement"), ("LogicalElement", "PhysicalElement")],
        "hasValidationScenario": [("Need", "ValidationScenario")],
        "hasRegulatorySource": [("Requirement", "RegulatorySource")],
    }
    for identity, pairs in expected.items():
        successor = projected[identity]["successor"]
        assert successor["contract"] == "de4sdv.relationship-successor/v1"
        assert [(p["source_class"], p["target_class"]) for p in successor["end_pairs"]] == pairs
        for pair in successor["end_pairs"]:
            assert len(pair["carrier"]["ends"]) == 2
    assert projected["hasValidationScenario"]["successor"]["inverse_navigation"] == ["validationScenarioFor"]


# ---------------------------------------------------------------------------
# 6. Negative fixtures (synthetic SysML; never copies of model files)
# ---------------------------------------------------------------------------

_FIXTURE_FILE = "textual-notation-of-model/packages/methods/de4sdv/fixture_batch2.sysml"
_FIXTURE_SYSML = '''package FixtureBatch2 {
  /* decoy: part def Ghost { doc not live } */
  part def Alpha {
    doc /* Alpha is an exact fixture definition. */
    attribute label : String = "brace } and /* not a comment */";
  }
  doc BetaOntologyDefinition /* Beta is a package-owned fixture definition. */
  comment betaLinkVocabularyRole about Alpha, BetaOntologyDefinition /* Vocabulary
   * role of betaLink: domain Alpha, range Beta. */
}
'''
_FIXTURE_CARRIERS = '''package DE4SDV_TraceVocabulary {
  connection def AlphaLink {
    end source : Alpha;
    end target : Alpha;
  }
  comment alphaLinkVocabularyRole about AlphaLink /* Successor definition for alphaLink. */
  part version : TraceVocabularyVersionRecord {
    attribute :>> version = "de4sdv.relationship-successor/v1";
    attribute :>> supersedes = "oldAlphaLink";
  }
  part alphaRecord : TraceRelationRecord {
    attribute :>> predicate = "alphaLink";
    attribute :>> carrier = "AlphaLink";
    attribute :>> mechanism = "typed-connection";
    attribute :>> strength = "fixture";
    attribute :>> sourceClass = "Alpha";
    attribute :>> targetClass = "Alpha";
    attribute :>> sourceUsage = "PartUsage";
    attribute :>> targetUsage = "PartUsage";
    attribute :>> inverse = "";
  }
  part oldAlpha : RetiredRelationRecord {
    attribute :>> predicate = "oldAlphaLink";
    attribute :>> reason = "Retired; alphaLink is the successor.";
  }
}
'''
_PKG = "package DE4SDV_TraceVocabulary"
_FIXTURE_MANIFEST = {
    "schema": "de4sdv.o4-definition-admission-batch2/v1",
    "status": "admitted",
    "warning": "fixture",
    "exceptions": [],
    "admitted": [
        {
            "identity": "Alpha", "semantic_kind": "class", "admission_class": "definition",
            "register": {"wave": "W2", "accounting": "retained"}, "boundary": "none",
            "home": {"form": "owned-doc", "file": _FIXTURE_FILE, "owner": "part def Alpha", "index": 0},
            "grounding": {"kernel_mapping": {"file": _FIXTURE_FILE, "declaration": "part def Alpha"},
                          "sub_class_of": None, "disjoint_with": []},
            "gates": [], "forward_obligations": [],
        },
        {
            "identity": "Beta", "semantic_kind": "class", "admission_class": "definition",
            "register": {"wave": None, "accounting": "unregistered"}, "boundary": "native-grounding",
            "home": {"form": "named-doc", "file": _FIXTURE_FILE, "owner": "package FixtureBatch2",
                     "name": "BetaOntologyDefinition", "index": 0},
            "grounding": {"kernel_mapping": {"native": "fixture native"}, "sub_class_of": "Alpha", "disjoint_with": []},
            "gates": [], "forward_obligations": [],
        },
        {
            "identity": "betaLink", "semantic_kind": "relationship", "admission_class": "relationship-vocabulary",
            "register": {"wave": "W4", "accounting": "retained"}, "boundary": "none",
            "home": {"form": "vocabulary-role", "file": _FIXTURE_FILE, "owner": "package FixtureBatch2",
                     "name": "betaLinkVocabularyRole", "about": ["Alpha", "BetaOntologyDefinition"], "about_imports": {}},
            "relation": {"domain": "Alpha", "range": "Beta", "semantic_strength": None},
            "gates": [], "forward_obligations": [],
        },
        {
            "identity": "alphaLink", "semantic_kind": "relationship", "admission_class": "successor",
            "register": {"wave": None, "accounting": "w6-successor"}, "boundary": "none",
            "home": {"form": "vocabulary-role", "file": SUCCESSOR_FILE, "owner": _PKG,
                     "name": "alphaLinkVocabularyRole", "about": ["AlphaLink"], "about_imports": {}},
            "successor": {"records": ["alphaRecord"]},
            "gates": [], "forward_obligations": [],
        },
        {
            "identity": "oldAlphaLink", "semantic_kind": "relationship", "admission_class": "retired-name",
            "register": {"wave": "W6", "accounting": "retained"}, "boundary": "none",
            "home": {"form": "retirement-record", "file": SUCCESSOR_FILE, "owner": _PKG, "name": "oldAlpha"},
            "relation": {"domain": "Alpha", "range": "Alpha", "semantic_strength": None},
            "retired": {"successor": "alphaLink", "successor_carrier": "AlphaLink", "direction": "forward"},
            "gates": [{"gate": "decision-1", "resolved_by": ["docs/fixture.md#topic"]}],
            "forward_obligations": [],
        },
    ],
}


def _fixture(tmp_path, manifest=None, sysml=None, carriers=None):
    from de4sdv.semantic import kernel_vocabulary_projection as kernel_vocabulary

    root = tmp_path / "repo"
    files = {
        _FIXTURE_FILE: sysml if sysml is not None else _FIXTURE_SYSML,
        SUCCESSOR_FILE: carriers if carriers is not None else _FIXTURE_CARRIERS,
        kernel_vocabulary.ADMISSION_PATH: yaml.safe_dump(manifest if manifest is not None else _FIXTURE_MANIFEST, sort_keys=False),
    }
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root

def _build(root):
    from de4sdv.semantic import kernel_vocabulary_projection as kernel_vocabulary

    return kernel_vocabulary.build_outputs(root, kernel_vocabulary.load_document(root))


def _mutated(mutate):
    manifest = copy.deepcopy(_FIXTURE_MANIFEST)
    mutate({row["identity"]: row for row in manifest["admitted"]}, manifest)
    return manifest


def test_fixture_baseline_builds_and_is_comment_and_quote_inert(tmp_path):
    outputs = _build(_fixture(tmp_path))
    rows = {row["identity"]: row for row in outputs["projection_rows"]}
    assert set(rows) == {"Alpha", "Beta", "betaLink", "alphaLink", "oldAlphaLink"}
    assert rows["Alpha"]["definition"]["documentation"] == "Alpha is an exact fixture definition."
    assert rows["oldAlphaLink"]["retired"]["successor_navigation"] == "alphaLink"
    assert rows["oldAlphaLink"]["retired"]["refusal"] == "retired; use alphaLink"
    assert rows["alphaLink"]["successor"]["end_pairs"][0]["carrier"]["ends"] == [
        {"name": "source", "type": "Alpha"}, {"name": "target", "type": "Alpha"}]


_NEGATIVE_MANIFESTS = {
    "unknown key": lambda r, m: r["Alpha"].update({"sysml_mapping": {}}),
    "retired definition oracle": lambda r, m: r["Alpha"].update({"reviewed_definition": "Alpha is a different definition."}),
    "wrong doc index": lambda r, m: r["Alpha"]["home"].update({"index": 1}),
    "missing named doc": lambda r, m: r["Beta"]["home"].update({"name": "GammaOntologyDefinition"}),
    "wrong about targets": lambda r, m: r["betaLink"]["home"].update({"about": ["Alpha"]}),
    "unknown comment": lambda r, m: r["betaLink"]["home"].update({"name": "gammaLinkVocabularyRole"}),
    "successor record set": lambda r, m: r["alphaLink"]["successor"].update({"records": ["alphaRecord", "betaRecord"]}),
    "retired carrier": lambda r, m: r["oldAlphaLink"]["retired"].update({"successor_carrier": "BetaLink"}),
    "retired inverse without inverse": lambda r, m: r["oldAlphaLink"]["retired"].update({"direction": "inverse"}),
    "retirement record predicate": lambda r, m: r["oldAlphaLink"]["home"].update({"name": "oldBeta"}),
    "duplicate identity": lambda r, m: m["admitted"].append(copy.deepcopy(r["Alpha"])),
    "exception overlaps admitted": lambda r, m: m["exceptions"].append(
        {"identity": "Alpha", "accounting": "merged", "reason": "x"}),
    "decoy declaration in comment": lambda r, m: r["Alpha"]["grounding"]["kernel_mapping"].update(
        {"declaration": "part def Ghost"}),
    "gate without record fragment": lambda r, m: r["oldAlphaLink"]["gates"][0].update({"resolved_by": ["free text"]}),
    "gate qualified by a branch, not a release tag": lambda r, m: r["oldAlphaLink"]["gates"][0].update(
        {"resolved_by": ["main:docs/fixture.md#topic"]}),
    "ple row with runtime class": lambda r, m: r["betaLink"].update({"boundary": "ple-no-configurator-authority",
                                                                      "admission_class": "relationship-runtime",
                                                                      "mechanics": {"strategy": "dependency"}}),
    "retired name without retirement home": lambda r, m: r["oldAlphaLink"].update({"home": copy.deepcopy(r["betaLink"]["home"])}),
    "traversal claim key": lambda r, m: r["betaLink"].update({"traversal": True}),
    "method-admitted relationship": lambda r, m: r["betaLink"].update(
        {"register": {"wave": None, "accounting": "method-admitted"}}),
}


#: The refusal must come from the intended guard, not an incidental failure.
_NEGATIVE_REASONS = {
    "unknown key": "unknown keys",
    "retired definition oracle": "unknown keys",
    "wrong doc index": "anonymous documentation at index 1",
    "missing named doc": "named GammaOntologyDefinition",
    "wrong about targets": "annotates",
    "unknown comment": "exactly one comment gammaLinkVocabularyRole",
    "successor record set": "model successor records",
    "retired carrier": "no unique record over BetaLink",
    "retired inverse without inverse": "inverse retired name needs",
    "retirement record predicate": "retirement record oldBeta not found",
    "duplicate identity": "duplicate admitted identity",
    "exception overlaps admitted": "cannot also be admitted",
    "decoy declaration in comment": "part def Ghost not found",
    "gate without record fragment": "record fragments",
    "gate qualified by a branch, not a release tag": "record fragments",
    "ple row with runtime class": "PLE configuration rows stay vocabulary-only",
    "retired name without retirement home": "homed by a retirement record",
    "traversal claim key": "unknown keys",
    "method-admitted relationship": "a method-admitted row is a class definition",
}


def test_method_admitted_metadata_class_is_projected_without_a_comparison_claim(tmp_path):
    """A class a method pull request admits after the deletion (synthetic metadata
    definition) gets a metadata-definition profile and a row that never claims an
    authored-ontology comparison; a compared row keeps its parity label."""
    sysml = _FIXTURE_SYSML.replace(
        "  doc BetaOntologyDefinition",
        "  metadata def Gamma {\n    doc /* Gamma is a method-admitted fixture definition. */\n  }\n"
        "  doc BetaOntologyDefinition", 1)
    gamma = {
        "identity": "Gamma", "semantic_kind": "class", "admission_class": "definition",
        "register": {"wave": None, "accounting": "method-admitted"}, "boundary": "none",
        "home": {"form": "owned-doc", "file": _FIXTURE_FILE, "owner": "metadata def Gamma", "index": 0},
        "grounding": {"kernel_mapping": {"file": _FIXTURE_FILE, "declaration": "metadata def Gamma"},
                      "sub_class_of": None, "disjoint_with": []},
        "gates": [], "forward_obligations": [],
    }
    outputs = _build(_fixture(tmp_path, manifest=_mutated(lambda r, m: m["admitted"].append(gamma)), sysml=sysml))
    rows = {row["identity"]: row for row in outputs["projection_rows"]}
    profiles = {entry["for_concept"]: entry for entry in outputs["profile_entries"]}
    assert rows["Gamma"]["accounting"] == "method-admitted"
    assert rows["Gamma"]["definition"]["documentation"] == "Gamma is a method-admitted fixture definition."
    source = rows["Gamma"]["grounding"]["contract_source"]
    assert "no authored-ontology comparison exists" in source and "parity" not in source
    assert "closure/contract-equivalence.json" in rows["Alpha"]["grounding"]["contract_source"]
    assert profiles["Gamma"]["representation_class"] == "metadata-definition"
    assert profiles["Gamma"]["binding_contract_echo"]["api_metaclass"] == "MetadataDefinition"


def test_gate_records_archived_at_a_release_tag_are_tag_qualified(tmp_path):
    """A decision record that moved to a release tag is cited as
    ``<tag>:<path>#fragment`` (git's revision:path form)."""
    manifest = _mutated(lambda r, m: r["oldAlphaLink"]["gates"][0].update(
        {"resolved_by": ["release-2026-10-11:docs/fixture.md#topic"]}))
    rows = {row["identity"]: row for row in _build(_fixture(tmp_path, manifest=manifest))["projection_rows"]}
    assert rows["oldAlphaLink"]["retired"]["refusal"] == "retired; use alphaLink"


#: The release tag that archives the decision records the manifest cites.
ARCHIVE_TAG = "release-2026-10-11"


def _git(*args):
    import subprocess

    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)


def _tracked_files():
    return set(_git("ls-files").stdout.splitlines())


def _record_keys(path, text):
    """The fragment keys a cited record really has, or None for a row convention.

    The YAML decision records have real keys: approved-semantic-decisions.yaml
    keys its topics (``topics: {topic1: ...}``) and w6-transition-plan.yaml its
    entries by ``identity``. The Markdown records have no anchor of that name;
    their fragments are row conventions, so only the file is resolved:
    owner-decisions-2026-10.md ``#2026-10-05-7`` is row 7 of the 2026-10-05
    table and ``#wave-a-decision-9`` the Decision 9 row of the Wave A table;
    ADR 0020 ``#d1`` to ``#d4``, ``#d4-follow-up``, ``#decision-7`` and
    ``#decision-8`` name its numbered decision items.
    """
    if not path.endswith(".yaml"):
        return None
    document = yaml.safe_load(text)
    keys = set(document.get("topics") or {})
    keys |= {entry["identity"] for entry in document.get("entries") or ()
             if isinstance(entry, dict) and "identity" in entry}
    assert keys, f"{path}: a cited YAML record has neither topic keys nor identity rows"
    return keys


def _assert_record_resolves(ref, tracked):
    revision, _, located = ref.rpartition(":")
    path, _, fragment = located.partition("#")
    if revision:
        assert revision == ARCHIVE_TAG, f"{ref}: cite archived records at {ARCHIVE_TAG}"
        assert _git("rev-parse", "--verify", "--quiet", f"refs/tags/{ARCHIVE_TAG}").returncode == 0, (
            f"tag {ARCHIVE_TAG} is missing locally; run `git fetch origin tag {ARCHIVE_TAG}`")
        assert _git("cat-file", "-e", f"{revision}:{path}").returncode == 0, f"{ref}: no such file at {revision}"
        text = _git("show", f"{revision}:{path}").stdout
    else:
        assert path in tracked, f"{ref}: not a tracked file"
        text = (REPO_ROOT / path).read_text(encoding="utf-8")
    keys = _record_keys(path, text)
    if keys is not None:
        assert fragment in keys, f"{ref}: {path} has no {fragment!r}"


def test_every_gate_record_resolves_in_the_tree_or_at_its_release_tag():
    """An untagged gate record names a tracked file; a record archived at the
    release tag exists there (``git cat-file -e <tag>:<path>``), so no citation
    points at a deleted path. Where the fragment is a real key of the cited
    record, the key exists too."""
    tracked = _tracked_files()
    references = [ref for row in _rows().values() for gate in row["gates"] for ref in gate["resolved_by"]]
    assert references
    for ref in references:
        _assert_record_resolves(ref, tracked)


@pytest.mark.parametrize("ref,reason", [
    ("release-2026-10-11:docs/method-conformance/o4/no-such-record.yaml#topic99",
     "no such file at release-2026-10-11"),
    ("release-2026-10-11:docs/method-conformance/o4/approved-semantic-decisions.yaml#topic99",
     "has no 'topic99'"),
    ("release-2026-10-11:docs/method-conformance/o4/w6-transition-plan.yaml#noSuchIdentity",
     "has no 'noSuchIdentity'"),
    ("release-2099-01-01:docs/method-conformance/o4/approved-semantic-decisions.yaml#topic1",
     "cite archived records at release-2026-10-11"),
    ("docs/method-conformance/o4/approved-semantic-decisions.yaml#topic1", "not a tracked file"),
], ids=["missing-file-at-tag", "missing-topic-key", "missing-identity-row", "other-tag", "deleted-path-untagged"])
def test_unresolvable_gate_record_citations_are_caught(ref, reason):
    with pytest.raises(AssertionError, match=re.escape(reason)):
        _assert_record_resolves(ref, _tracked_files())


@pytest.mark.parametrize("case", sorted(_NEGATIVE_MANIFESTS))
def test_negative_manifest_mutations_are_refused(tmp_path, case):
    from de4sdv.semantic.kernel_vocabulary_projection import KernelVocabularyError

    root = _fixture(tmp_path, manifest=_mutated(_NEGATIVE_MANIFESTS[case]))
    with pytest.raises(KernelVocabularyError, match=_NEGATIVE_REASONS[case]):
        _build(root)


_NEGATIVE_MODELS = {
    "duplicate live declaration": ("sysml", lambda s: s.replace("  doc BetaOntologyDefinition",
                                                               "  part def Alpha { doc /* dup */ }\n  doc BetaOntologyDefinition")),
    "commented-out comment": ("sysml", lambda s: s.replace("  comment betaLinkVocabularyRole", "  // comment betaLinkVocabularyRole")
                                                 .replace("role of betaLink: domain Alpha, range Beta. */", "role */")),
    "nested named doc": ("sysml", lambda s: s.replace("  doc BetaOntologyDefinition /* Beta is a package-owned fixture definition. */\n", "")
                                         .replace("    attribute label", "    doc BetaOntologyDefinition /* Beta is a package-owned fixture definition. */\n    attribute label")),
    "record field twice": ("carriers", lambda s: s.replace('attribute :>> inverse = "";', 'attribute :>> inverse = "";\n    attribute :>> inverse = "";')),
    "record field missing": ("carriers", lambda s: s.replace('    attribute :>> inverse = "";\n', "")),
    "record field not literal": ("carriers", lambda s: s.replace('attribute :>> strength = "fixture";', "attribute :>> strength = fixture;")),
    "second record for predicate": ("carriers", lambda s: s.replace("  part oldAlpha", '''  part alphaRecordTwo : TraceRelationRecord {
    attribute :>> predicate = "alphaLink"; attribute :>> carrier = "AlphaLink"; attribute :>> mechanism = "m";
    attribute :>> strength = "s"; attribute :>> sourceClass = "Alpha"; attribute :>> targetClass = "Alpha";
    attribute :>> sourceUsage = "PartUsage"; attribute :>> targetUsage = "PartUsage"; attribute :>> inverse = "";
  }
  part oldAlpha''')),
    "carrier with one end": ("carriers", lambda s: s.replace("    end target : Alpha;\n", "")),
    "wrong successor version": ("carriers", lambda s: s.replace("de4sdv.relationship-successor/v1", "de4sdv.relationship-successor/v0")),
}


@pytest.mark.parametrize("case", sorted(_NEGATIVE_MODELS))
def test_negative_model_mutations_are_refused(tmp_path, case):
    from de4sdv.semantic.kernel_vocabulary_projection import KernelVocabularyError

    target, mutate = _NEGATIVE_MODELS[case]
    original = _FIXTURE_SYSML if target == "sysml" else _FIXTURE_CARRIERS
    mutated = mutate(original)
    assert mutated != original, case
    kwargs = {target: mutated}
    root = _fixture(tmp_path, **kwargs)
    with pytest.raises(KernelVocabularyError):
        _build(root)


def test_discriminator_pin_must_specialize_and_import_the_kernel_lineage(tmp_path):
    from de4sdv.semantic.kernel_vocabulary_projection import KernelVocabularyError

    contracts = "textual-notation-of-model/packages/features/fixture/contracts.sysml"
    sysml = _FIXTURE_SYSML.replace("  doc BetaOntologyDefinition",
                                   "  requirement def Lineage { doc /* lineage */ }\n  doc BetaOntologyDefinition")

    def with_discriminator(rows, manifest):
        rows["betaLink"]["admission_class"] = "relationship-runtime"
        rows["betaLink"]["mechanics"] = {"strategy": "dependency"}
        rows["betaLink"]["range_discriminator"] = {
            "kind": "type-lineage",
            "lineage": {"file": _FIXTURE_FILE, "declaration": "requirement def Lineage"},
            "closure": [{"file": contracts, "declaration": "requirement def Member"}],
        }

    manifest = _mutated(with_discriminator)
    good = "package Contracts {\n  private import DE4SDV_MethodContext::*;\n  requirement def Member :> Lineage { doc /* m */ }\n}\n"
    for body, ok in (
        (good, True),
        (good.replace(":> Lineage", ":> Other"), False),
        (good.replace("  private import DE4SDV_MethodContext::*;\n", ""), False),
        (good.replace("requirement def Member :> Lineage", "// requirement def Member :> Lineage\n  requirement def Member"), False),
    ):
        root = _fixture(tmp_path / str(len(body)) / ("ok" if ok else "bad"), manifest=manifest, sysml=sysml)
        (root / contracts).parent.mkdir(parents=True, exist_ok=True)
        (root / contracts).write_text(body, encoding="utf-8")
        if ok:
            row = {r["identity"]: r for r in _build(root)["projection_rows"]}["betaLink"]
            assert row["relation"]["range"]["discriminator"]["closure"][0]["declaration"] == "requirement def Member"
        else:
            with pytest.raises(KernelVocabularyError):
                _build(root)


# ---------------------------------------------------------------------------
# 7. Commit-independent current-source construction and strict live artifact gate
# ---------------------------------------------------------------------------


def test_generation_projects_current_synthetic_sources_without_git_binding(tmp_path):
    from de4sdv.semantic import kernel_vocabulary_projection as kernel_vocabulary

    root = _fixture(tmp_path)
    path = root / _FIXTURE_FILE
    path.write_text(path.read_text(encoding="utf-8").replace("Alpha is an exact fixture definition.", "Alpha meaning was edited."), encoding="utf-8")
    pair = kernel_vocabulary.build_artifact_pair(root)
    rows = {row["identity"]: row for row in pair["projection"]["rows"]}
    assert rows["Alpha"]["definition"]["documentation"] == "Alpha meaning was edited."
    assert "binding" not in pair["projection"] and "binding" not in pair["profile"]
    assert rows["oldAlphaLink"]["retired"]["refusal"] == "retired; use alphaLink"

def test_committed_artifacts_match_regeneration():
    from de4sdv.semantic import kernel_vocabulary_projection as kernel_vocabulary

    assert (REPO_ROOT / kernel_vocabulary.PROJECTION_PATH).is_file()
    assert (REPO_ROOT / kernel_vocabulary.PROFILE_PATH).is_file()
    assert kernel_vocabulary.run_check_errors(REPO_ROOT) == []

# This cleanup explicitly retires test_chain_verifier_requires_the_batch2_pair: its
# only subject was the removed live bound-input set. The verifier now checks
# frozen records only; frozen-binding tests remain owned by the integration lane.

# ---------------------------------------------------------------------------
# 8. Runtime independence and repository wiring
# ---------------------------------------------------------------------------


def test_kernel_vocabulary_machinery_is_never_imported_by_the_runtime_path():
    for relative in (
        "de4sdv/semantic/query.py", "de4sdv/semantic/traversal.py",
        "de4sdv/semantic/impact.py", "de4sdv/semantic/mcp_server.py", "de4sdv/semantic/api_binding.py",
        "de4sdv/semantic/kernel_binding_index.py",
        "de4sdv/semantic/deployment_runtime.py",
    ):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        for token in ("kernel_vocabulary_projection", "definition-batch2", "kernel-vocabulary"):
            assert token not in text, (relative, token)
    # The model-authority runtime reads the generated batch-2 pair as a data
    # layer; it never imports the generator or reads the admission manifest.
    for relative in ("de4sdv/semantic/model_authority_runtime.py",
                     "de4sdv/semantic/model_contract.py"):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        for token in ("kernel_vocabulary_projection", "kernel-vocabulary-admission"):
            assert token not in text, (relative, token)


def _passing_gate_mocks():
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_retired_semantic_authority import _passing_gate_mocks as shared

    return shared()


def test_check_repo_actually_invokes_the_kernel_vocabulary_gate():
    from unittest import mock

    from de4sdv.semantic import kernel_vocabulary_projection
    from scripts import check_repo

    calls = []
    mocks = _passing_gate_mocks()
    for m in mocks:
        m.start()
    try:
        with mock.patch.object(kernel_vocabulary_projection, "run_check_errors",
                               side_effect=lambda root: calls.append(root) or []):
            result = check_repo.main()
    finally:
        for m in mocks:
            m.stop()
    assert calls, "check_repo did not invoke the kernel-vocabulary gate"
    assert result == 0


def test_check_repo_fails_when_the_kernel_vocabulary_gate_fails():
    from unittest import mock

    from de4sdv.semantic import kernel_vocabulary_projection
    from scripts import check_repo

    mocks = _passing_gate_mocks()
    for m in mocks:
        m.start()
    try:
        with mock.patch.object(kernel_vocabulary_projection, "run_check_errors",
                               return_value=["sentinel kernel-vocabulary error"]):
            assert check_repo.main() == 1
    finally:
        for m in mocks:
            m.stop()
