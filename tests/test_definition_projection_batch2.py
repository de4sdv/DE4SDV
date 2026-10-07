"""O4 definition-admission batch 2 — derived family, model homes, coverage.

Machine-locked here (fail-closed):

* the admitted set equals the derived family (retained register rows no other
  generated layer projects + unregistered ontology classes + W6 successors +
  the deprecated name of the merged validatesFitnessForUse row), and the
  exceptions are exactly the remaining non-retained identities;
* every retained register row and every authored-ontology identity has exactly
  one generated provider layer (or is a listed exception); the O3 13 are not
  re-admitted;
* the reviewed manifest fields equal the authored ontology (definition text,
  kernel mappings, ontology relations, domain/range/strength, mechanics) and
  the documentation locators equal ``kernel-definition-homes.json``;
* every register gate is resolved by an existing governance record fragment;
* the ``hasRelevantEvidenceContract`` closure is exactly the eight AEBS
  contracts across every model root;
* generated rows never carry O1 governance fields or a sysml_mapping, claim no
  traversal and no API identity; PLE rows claim no configurator authority;
* negative fixtures (synthetic SysML, never copies of model files) prove each
  model-home guard refuses.

The committed-artifact test is the Commit-B gate (red between the source
commit and the artifact commit by design).
"""
from __future__ import annotations

import copy
import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
O4 = "docs/method-conformance/o4/"
MANIFEST_PATH = O4 + "definition-admission-batch2.yaml"
ONTOLOGY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"
REGISTER_PATH = O4 + "o4-execution-register.json"
SUCCESSOR_FILE = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_relationship_carriers.sysml"

OTHER_LAYERS = {
    "o2-chain": [
        ("docs/method-conformance/o2/semantic-projection-v1.json", ("concepts",)),
        ("docs/method-conformance/o2/semantic-projection-v1.1.json", ("concepts", "predicates")),
        ("docs/method-conformance/o2/semantic-projection-v1.2.json", ("predicates",)),
    ],
    "definition-batch-1": [(O4 + "definition-projection.json", ("rows",))],
    "o2plus": [("docs/method-conformance/o2plus/semantic-projection-o2plus.json", ("rows",))],
    "vocabulary-carriers": [(O4 + "vocabulary-carriers-projection.json", ("rows",))],
}
W6_NEW_SUCCESSORS = {"hasValidationScenario", "hasRegulatorySource"}
MERGED_ALIASES = {"validatesFitnessForUse"}
EXPECTED_COUNTS = {
    "definition": 31,
    "external-reference": 4,
    "relationship-vocabulary": 12,
    "relationship-runtime": 2,
    "successor": 3,
    "deprecated-alias": 5,
}
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
O1_GOVERNANCE_FIELDS = (
    "authority_current", "authority_target", "evidence_state", "adoption_status",
    "transition_gate", "conditional_target", "disposition", "confidence", "stage",
    "unknowns", "required_evidence", "exact_fit_decision",
)


def _json(relative):
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def _manifest():
    return yaml.safe_load((REPO_ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))


def _ontology():
    return yaml.safe_load((REPO_ROOT / ONTOLOGY_PATH).read_text(encoding="utf-8"))


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
    from de4sdv.semantic import definition_projection_batch2 as b2

    return b2.build_outputs(REPO_ROOT, b2.load_document(REPO_ROOT))


# ---------------------------------------------------------------------------
# 1. Family, exceptions and complete coverage
# ---------------------------------------------------------------------------


def test_admitted_set_is_exactly_the_derived_family():
    from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

    register = _register()
    ontology = _ontology()
    other = set().union(*_layer_identities().values())
    retained = {i for i, r in register.items() if r["accounting_status"] == "retained" and not r["o3_complete"]}
    unregistered = set(ontology["classes"]) - set(register)
    family = (retained - other) | unregistered | W6_NEW_SUCCESSORS | MERGED_ALIASES
    rows = _rows()
    assert set(rows) == family
    assert len(rows) == 57 == len(_manifest()["admitted"])
    assert len(retained - other) == 42 and len(unregistered) == 12
    assert not set(rows) & set(MIGRATED_IDENTITIES)
    assert not set(rows) & other
    counts = {}
    for row in rows.values():
        counts[row["admission_class"]] = counts.get(row["admission_class"], 0) + 1
    assert counts == EXPECTED_COUNTS
    # The new successors are neither register rows nor authored identities.
    assert not W6_NEW_SUCCESSORS & (set(register) | set(ontology["relationships"]))
    assert register["validatesFitnessForUse"]["accounting_status"] == "merged"


def test_every_retained_row_and_ontology_identity_has_exactly_one_provider():
    register = _register()
    ontology = _ontology()
    layers = _layer_identities()
    layers["definition-batch-2"] = set(_rows())
    exceptions = {entry["identity"]: entry for entry in _manifest()["exceptions"]}
    universe = set(register) | set(ontology["classes"]) | set(ontology["relationships"])
    providers = {identity: [name for name, ids in layers.items() if identity in ids] for identity in universe}
    duplicates = {i: p for i, p in providers.items() if len(p) > 1}
    assert duplicates == {}
    uncovered = {i for i, p in providers.items() if not p}
    assert uncovered == set(exceptions)
    # No retained row is an exception: every retained row is model-projected.
    assert all(entry["accounting"] != "retained" for entry in exceptions.values())
    for identity, entry in exceptions.items():
        assert register[identity]["accounting_status"] == entry["accounting"]
    assert set(exceptions) == {"IncrementTraceabilityShell", "derivesNeedFromConcern"}
    retained = {i for i, r in register.items() if r["accounting_status"] == "retained"}
    assert retained <= set().union(*layers.values())


def test_projection_scope_echoes_the_owner_visible_exceptions():
    from de4sdv.semantic.definition_projection_batch2 import PROJECTION_PATH

    committed = _json(PROJECTION_PATH)
    assert committed["scope"]["exceptions"] == sorted(
        _manifest()["exceptions"], key=lambda entry: entry["identity"]
    )
    assert committed["scope"]["admitted"] == sorted(_rows())


# ---------------------------------------------------------------------------
# 2. Reviewed manifest fields equal the authored ontology and the homes inventory
# ---------------------------------------------------------------------------


def test_reviewed_fields_equal_the_authored_ontology():
    ontology = _ontology()
    for identity, row in _rows().items():
        if row["semantic_kind"] == "class":
            spec = ontology["classes"][identity]
            assert row["reviewed_definition"] == " ".join(spec["definition"].split()), identity
            grounding = row["grounding"]
            assert grounding["kernel_mapping"] == spec["kernel"], identity
            assert grounding["sub_class_of"] == spec.get("subClassOf"), identity
            assert grounding["disjoint_with"] == spec.get("disjointWith", []), identity
            continue
        spec = ontology["relationships"].get(identity)
        if spec is None:
            assert identity in W6_NEW_SUCCESSORS
            continue
        if row["admission_class"] == "successor":
            continue
        mapping = spec.get("sysml_mapping") or {}
        assert row["relation"] == {
            "domain": spec["domain"], "range": spec["range"],
            "semantic_strength": mapping.get("semantic_strength"),
        }, identity
        if row["home"]["form"] in ("owned-doc", "named-doc"):
            assert row["reviewed_definition"] == " ".join(spec["definition"].split()), identity
        else:
            assert row["reviewed_definition"] is None and not spec.get("definition"), identity
        if "mechanics" in row:
            assert row["mechanics"] == {k: v for k, v in mapping.items() if k != "semantic_strength"}, identity
        elif mapping and row["admission_class"] != "deprecated-alias":
            pytest.fail(f"{identity}: an authored mapping must be carried as mechanics")
    # Every authored executable mapping outside the O3 13 is accounted:
    # runtime-mapped, external reference, or the deprecated realizedBy alias.
    mapped = {name for name, spec in ontology["relationships"].items() if spec.get("sysml_mapping")}
    rows = _rows()
    in_batch = {name for name in mapped if name in rows}
    assert in_batch == {"specifiesFunction", "hasRelevantEvidenceContract", "hasEvidence", "realizedBy"}
    assert rows["realizedBy"]["admission_class"] == "deprecated-alias"


def test_documentation_homes_equal_the_kernel_definition_homes_inventory():
    homes = {row["identity"]: row for row in _json(O4 + "kernel-definition-homes.json")["definitions"]}
    for identity, row in _rows().items():
        home = row["home"]
        if home["form"] not in ("owned-doc", "named-doc"):
            assert identity not in homes, identity
            continue
        recorded = homes[identity]
        assert (home["file"], home["owner"], home.get("name"), home["index"]) == (
            recorded["file"], recorded["declaration"], recorded["documentation_name"],
            recorded["documentation_index"],
        ), identity
        assert (home["form"] == "named-doc") == bool(recorded["documentation_name"]), identity


def test_successors_and_aliases_follow_the_w6_transition_plan():
    plan = {entry["identity"]: entry for entry in yaml.safe_load(
        (REPO_ROOT / (O4 + "w6-transition-plan.yaml")).read_text(encoding="utf-8"))["entries"]}
    rows = _rows()
    for identity in ("realizedBy", "deployedTo", "validatedBy", "constrainedBy"):
        assert rows[identity]["alias"]["successor"] == plan[identity]["successor"], identity
    assert plan["specifiesFunction"]["successor"] is None
    assert rows["specifiesFunction"]["admission_class"] == "relationship-runtime"
    assert {row["alias"]["successor"] for row in rows.values() if "alias" in row} <= {
        identity for identity, row in rows.items() if row["admission_class"] == "successor"
    }
    register = _register()
    assert register["validatesFitnessForUse"]["merge_into"] == "validatedBy"
    assert rows["validatesFitnessForUse"]["alias"]["direction"] == "inverse"
    # The model retirement record refuses an alias reading for constrainedBy.
    assert rows["constrainedBy"]["alias"]["answer_mode"] == "documentation-only"
    assert {i for i, r in rows.items() if "alias" in r and r["alias"]["answer_mode"] == "documentation-only"} == {"constrainedBy"}
    # The authored allocatedTo signature is the second successor end pair.
    ontology = _ontology()
    old = ontology["relationships"]["allocatedTo"]
    projected = {row["identity"]: row for row in _outputs()["projection_rows"]}
    pair = projected["allocatedTo"]["successor"]["end_pairs"][1]
    assert (pair["source_class"], pair["target_class"]) == (old["domain"], old["range"])


# ---------------------------------------------------------------------------
# 3. Gate resolution references resolve to governance record fragments
# ---------------------------------------------------------------------------

_ADR = "docs/architecture-decisions/0020-give-ontology-definitions-model-resident-kernel-homes.md"
_OWNER = O4 + "owner-decisions-2026-10.md"
_FRAGMENT_PHRASES = {
    (_ADR, "d1"): "**D1 — architecture umbrella terms.**",
    (_ADR, "d2"): "**D2 — acceptance criterion.**",
    (_ADR, "d3"): "**D3 — evaluation exclusions.**",
    (_ADR, "d4"): "**D4 — evidence contract.**",
    (_ADR, "d4-follow-up"): "**D4 follow-up (2026-10-06).**",
    (_ADR, "decision-7"): "**Decision 7 — feature/common-capability disjointness.**",
    (_ADR, "decision-8"): "**Decision 8 — canonical architecture.**",
    (_OWNER, "2026-10-05-7"): "| 7 | Feature/common-capability disjointness (open decision 14) |",
    (_OWNER, "2026-10-05-8"): "| 8 | Canonical architecture source (open decision 10) |",
    (_OWNER, "wave-a-decision-9"): "| Decision 9 — product-line configurator authority |",
}
_DECISION_FOR_FRAGMENT = {
    (_ADR, "d1"): "decision-5", (_ADR, "d2"): "decision-6", (_ADR, "d3"): "decision-7",
    (_ADR, "decision-7"): "decision-14", (_ADR, "decision-8"): "decision-10",
    (_OWNER, "2026-10-05-7"): "decision-14", (_OWNER, "2026-10-05-8"): "decision-10",
    (_OWNER, "wave-a-decision-9"): "decision-9",
}


def _resolve_reference(reference):
    path, _, fragment = reference.partition("#")
    assert ".." not in Path(path).parts and path.startswith("docs/")
    target = REPO_ROOT / path
    assert target.is_file(), reference
    if path.endswith("approved-semantic-decisions.yaml"):
        topics = yaml.safe_load(target.read_text(encoding="utf-8"))["topics"]
        assert fragment in topics, reference
        return set(topics[fragment]["decisions"])
    if path.endswith("w6-transition-plan.yaml"):
        entries = {e["identity"]: e for e in yaml.safe_load(target.read_text(encoding="utf-8"))["entries"]}
        assert fragment in entries, reference
        return set(entries[fragment]["authorization"]["decisions"])
    phrase = _FRAGMENT_PHRASES.get((path, fragment))
    assert phrase, f"unknown record fragment {reference}"
    assert phrase in target.read_text(encoding="utf-8"), reference
    decision = _DECISION_FOR_FRAGMENT.get((path, fragment))
    return {decision} if decision else set()


def test_every_register_gate_is_resolved_by_an_existing_record():
    register = _register()
    for identity, row in _rows().items():
        reg = register.get(identity)
        expected = set()
        if reg is not None and reg["accounting_status"] == "retained":
            expected = set(reg["gate_decisions"]) | ({"row-blocker"} if reg["blockers"] else set())
        elif reg is not None:  # the merged alias keeps its own blocker resolution
            expected = {"row-blocker"} if reg["blockers"] else set()
        assert {gate["gate"] for gate in row["gates"]} == expected, identity
        for gate in row["gates"]:
            named = set()
            for reference in gate["resolved_by"]:
                named |= _resolve_reference(reference)
            if gate["gate"] != "row-blocker":
                assert gate["gate"] in named, (identity, gate)


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


def test_evidence_contract_closure_is_exactly_the_eight_aebs_contracts_repo_wide():
    """Population test: no other model definition specializes EvidenceContract."""
    from de4sdv.semantic.definition_projection_batch2 import _Source

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
    assert {(p["file"], p["declaration"]) for p in row["range_discriminator"]["closure"]} == EC_CLOSURE
    projected = {r["identity"]: r for r in _outputs()["projection_rows"]}["hasRelevantEvidenceContract"]
    disc = projected["relation"]["range"]["discriminator"]
    assert disc["kind"] == "type-lineage"
    assert disc["lineage"]["declaration"] == "requirement def EvidenceContract"
    assert len(disc["closure"]) == 8
    assert "prefix" in disc["rule"] and "never by name" in disc["rule"]


# ---------------------------------------------------------------------------
# 5. Generated rows
# ---------------------------------------------------------------------------


def test_generated_rows_carry_no_governance_fields_or_executable_claims():
    from de4sdv.semantic.definition_projection_batch2 import PROFILE_SCHEMA, SUPPORT

    outputs = _outputs()
    rows = _rows()
    assert len(outputs["projection_rows"]) == len(outputs["profile_entries"]) == 57
    for row in outputs["projection_rows"]:
        serialized = json.dumps(row)
        for field in O1_GOVERNANCE_FIELDS + ("sysml_mapping", "gates", "forward_obligations"):
            assert f'"{field}"' not in serialized, (row["identity"], field)
        assert row["traversal"] is False and row["api_identity"] == "unclaimed"
        assert row["support"] == SUPPORT[row["admission_class"]]
        observation = row["definition"]["documentation_observation"]
        if rows[row["identity"]]["home"]["form"] in ("owned-doc", "named-doc"):
            assert observation == "normalized-exact", row["identity"]
        assert row["definition"]["documentation"].strip(), row["identity"]
    for entry in outputs["profile_entries"]:
        assert entry["profile_identity"] == f"{PROFILE_SCHEMA}#{entry['for_concept']}"
        serialized = json.dumps(entry)
        for field in O1_GOVERNANCE_FIELDS + ("sysml_mapping",):
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
_FIXTURE_CARRIERS = '''package DE4SDV_RelationshipSuccessor {
  connection def AlphaLink {
    end source : Alpha;
    end target : Alpha;
  }
  comment alphaLinkVocabularyRole about AlphaLink /* Successor definition for alphaLink. */
  part version : SuccessorVersionRecord {
    attribute :>> version = "de4sdv.relationship-successor/v1";
    attribute :>> supersedes = "oldAlphaLink";
  }
  part alphaRecord : SuccessorRelationRecord {
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
  part oldAlpha : SuccessorRetirementRecord {
    attribute :>> predicate = "oldAlphaLink";
    attribute :>> reason = "Retired; alphaLink is the successor.";
  }
}
'''
_PKG = "package DE4SDV_RelationshipSuccessor"
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
            "reviewed_definition": "Alpha is an exact fixture definition.",
            "grounding": {"kernel_mapping": {"file": _FIXTURE_FILE, "declaration": "part def Alpha"},
                          "sub_class_of": None, "disjoint_with": []},
            "gates": [], "forward_obligations": [],
        },
        {
            "identity": "Beta", "semantic_kind": "class", "admission_class": "definition",
            "register": {"wave": None, "accounting": "unregistered"}, "boundary": "native-grounding",
            "home": {"form": "named-doc", "file": _FIXTURE_FILE, "owner": "package FixtureBatch2",
                     "name": "BetaOntologyDefinition", "index": 0},
            "reviewed_definition": "Beta is a package-owned fixture definition.",
            "grounding": {"kernel_mapping": {"native": "fixture native"}, "sub_class_of": "Alpha", "disjoint_with": []},
            "gates": [], "forward_obligations": [],
        },
        {
            "identity": "betaLink", "semantic_kind": "relationship", "admission_class": "relationship-vocabulary",
            "register": {"wave": "W4", "accounting": "retained"}, "boundary": "none",
            "home": {"form": "vocabulary-role", "file": _FIXTURE_FILE, "owner": "package FixtureBatch2",
                     "name": "betaLinkVocabularyRole", "about": ["Alpha", "BetaOntologyDefinition"], "about_imports": {}},
            "reviewed_definition": None,
            "relation": {"domain": "Alpha", "range": "Beta", "semantic_strength": None},
            "gates": [], "forward_obligations": [],
        },
        {
            "identity": "alphaLink", "semantic_kind": "relationship", "admission_class": "successor",
            "register": {"wave": None, "accounting": "w6-successor"}, "boundary": "none",
            "home": {"form": "vocabulary-role", "file": SUCCESSOR_FILE, "owner": _PKG,
                     "name": "alphaLinkVocabularyRole", "about": ["AlphaLink"], "about_imports": {}},
            "reviewed_definition": None, "successor": {"records": ["alphaRecord"]},
            "gates": [], "forward_obligations": [],
        },
        {
            "identity": "oldAlphaLink", "semantic_kind": "relationship", "admission_class": "deprecated-alias",
            "register": {"wave": "W6", "accounting": "retained"}, "boundary": "none",
            "home": {"form": "retirement-record", "file": SUCCESSOR_FILE, "owner": _PKG, "name": "oldAlpha"},
            "reviewed_definition": None,
            "relation": {"domain": "Alpha", "range": "Alpha", "semantic_strength": None},
            "alias": {"successor": "alphaLink", "successor_carrier": "AlphaLink", "direction": "forward",
                      "answer_mode": "successor-facts"},
            "gates": [{"gate": "decision-1", "resolved_by": ["docs/fixture.md#topic"]}],
            "forward_obligations": [],
        },
    ],
}
_PROGRAM_FILES = (
    "de4sdv/semantic/authority_inventory.py",
    "de4sdv/semantic/projection_o2p.py",
)


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def _fixture(tmp_path, manifest=None, sysml=None, carriers=None, commit=False):
    from de4sdv.semantic import definition_projection_batch2 as b2

    root = tmp_path / "repo"
    files = {
        _FIXTURE_FILE: sysml if sysml is not None else _FIXTURE_SYSML,
        SUCCESSOR_FILE: carriers if carriers is not None else _FIXTURE_CARRIERS,
        b2.ADMISSION_PATH: yaml.safe_dump(manifest if manifest is not None else _FIXTURE_MANIFEST, sort_keys=False),
        b2.DESIGN_PATH: "# fixture design\n",
        b2.MODULE_PATH: "# bound module stand-in\n",
        b2.GENERATOR_PATH: "# bound generator stand-in\n",
    }
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for relative in _PROGRAM_FILES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO_ROOT / relative).read_bytes())
    if commit:
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "review@example.invalid")
        _git(root, "config", "user.name", "review")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "batch-2 fixture inputs")
    return root


def _build(root):
    from de4sdv.semantic import definition_projection_batch2 as b2

    return b2.build_outputs(root, b2.load_document(root))


def _mutated(mutate):
    manifest = copy.deepcopy(_FIXTURE_MANIFEST)
    mutate({row["identity"]: row for row in manifest["admitted"]}, manifest)
    return manifest


def test_fixture_baseline_builds_and_is_comment_and_quote_inert(tmp_path):
    outputs = _build(_fixture(tmp_path))
    rows = {row["identity"]: row for row in outputs["projection_rows"]}
    assert set(rows) == {"Alpha", "Beta", "betaLink", "alphaLink", "oldAlphaLink"}
    assert rows["Alpha"]["definition"]["documentation"] == "Alpha is an exact fixture definition."
    assert rows["oldAlphaLink"]["alias"]["successor_navigation"] == "alphaLink"
    assert rows["alphaLink"]["successor"]["end_pairs"][0]["carrier"]["ends"] == [
        {"name": "source", "type": "Alpha"}, {"name": "target", "type": "Alpha"}]


_NEGATIVE_MANIFESTS = {
    "unknown key": lambda r, m: r["Alpha"].update({"sysml_mapping": {}}),
    "documentation differs": lambda r, m: r["Alpha"].update({"reviewed_definition": "Alpha is a different definition."}),
    "wrong doc index": lambda r, m: r["Alpha"]["home"].update({"index": 1}),
    "missing named doc": lambda r, m: r["Beta"]["home"].update({"name": "GammaOntologyDefinition"}),
    "wrong about targets": lambda r, m: r["betaLink"]["home"].update({"about": ["Alpha"]}),
    "unknown comment": lambda r, m: r["betaLink"]["home"].update({"name": "gammaLinkVocabularyRole"}),
    "successor record set": lambda r, m: r["alphaLink"]["successor"].update({"records": ["alphaRecord", "betaRecord"]}),
    "alias carrier": lambda r, m: r["oldAlphaLink"]["alias"].update({"successor_carrier": "BetaLink"}),
    "alias inverse without inverse": lambda r, m: r["oldAlphaLink"]["alias"].update({"direction": "inverse"}),
    "retirement record predicate": lambda r, m: r["oldAlphaLink"]["home"].update({"name": "oldBeta"}),
    "duplicate identity": lambda r, m: m["admitted"].append(copy.deepcopy(r["Alpha"])),
    "exception overlaps admitted": lambda r, m: m["exceptions"].append(
        {"identity": "Alpha", "accounting": "merged", "reason": "x"}),
    "decoy declaration in comment": lambda r, m: r["Alpha"]["grounding"]["kernel_mapping"].update(
        {"declaration": "part def Ghost"}),
    "gate without record fragment": lambda r, m: r["oldAlphaLink"]["gates"][0].update({"resolved_by": ["free text"]}),
    "ple row with runtime class": lambda r, m: r["betaLink"].update({"boundary": "ple-no-configurator-authority",
                                                                      "admission_class": "relationship-runtime",
                                                                      "mechanics": {"strategy": "dependency"}}),
    "alias without retirement home": lambda r, m: r["oldAlphaLink"].update({"home": copy.deepcopy(r["betaLink"]["home"])}),
    "traversal claim key": lambda r, m: r["betaLink"].update({"traversal": True}),
}


#: The refusal must come from the intended guard, not an incidental failure.
_NEGATIVE_REASONS = {
    "unknown key": "unknown keys",
    "documentation differs": "reviewed definition differ",
    "wrong doc index": "anonymous documentation at index 1",
    "missing named doc": "named GammaOntologyDefinition",
    "wrong about targets": "annotates",
    "unknown comment": "exactly one comment gammaLinkVocabularyRole",
    "successor record set": "model successor records",
    "alias carrier": "no unique record over BetaLink",
    "alias inverse without inverse": "inverse alias needs",
    "retirement record predicate": "retirement record oldBeta not found",
    "duplicate identity": "duplicate admitted identity",
    "exception overlaps admitted": "cannot also be admitted",
    "decoy declaration in comment": "part def Ghost not found",
    "gate without record fragment": "record fragments",
    "ple row with runtime class": "PLE configuration rows stay vocabulary-only",
    "alias without retirement home": "homed by a retirement record",
    "traversal claim key": "unknown keys",
}


@pytest.mark.parametrize("case", sorted(_NEGATIVE_MANIFESTS))
def test_negative_manifest_mutations_are_refused(tmp_path, case):
    from de4sdv.semantic.definition_projection_batch2 import DefinitionBatch2Error

    root = _fixture(tmp_path, manifest=_mutated(_NEGATIVE_MANIFESTS[case]))
    with pytest.raises(DefinitionBatch2Error, match=_NEGATIVE_REASONS[case]):
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
    "second record for predicate": ("carriers", lambda s: s.replace("  part oldAlpha", '''  part alphaRecordTwo : SuccessorRelationRecord {
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
    from de4sdv.semantic.definition_projection_batch2 import DefinitionBatch2Error

    target, mutate = _NEGATIVE_MODELS[case]
    original = _FIXTURE_SYSML if target == "sysml" else _FIXTURE_CARRIERS
    mutated = mutate(original)
    assert mutated != original, case
    kwargs = {target: mutated}
    root = _fixture(tmp_path, **kwargs)
    with pytest.raises(DefinitionBatch2Error):
        _build(root)


def test_discriminator_pin_must_specialize_and_import_the_kernel_lineage(tmp_path):
    from de4sdv.semantic.definition_projection_batch2 import DefinitionBatch2Error

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
            with pytest.raises(DefinitionBatch2Error):
                _build(root)


# ---------------------------------------------------------------------------
# 7. Binding (two-commit pattern) and the Commit-B gate
# ---------------------------------------------------------------------------


def test_generation_binds_committed_inputs_and_refuses_uncommitted_edits(tmp_path):
    from de4sdv.semantic import definition_projection_batch2 as b2
    from de4sdv.semantic.projection_o2p import canonical_json

    root = _fixture(tmp_path, commit=True)
    revision = _git(root, "rev-parse", "HEAD")
    artifacts = b2.build_artifact_pair(root, source_revision=revision)
    binding = artifacts["projection"]["binding"]
    assert binding["source_revision"] == revision
    assert binding["generation_software"]["program_inputs"] == [
        b2.MODULE_PATH, b2.GENERATOR_PATH, b2.AUTHORITY_INVENTORY_PATH, b2.PROJECTION_O2P_PATH]
    assert set(binding["bound_inputs"]) == {
        b2.ADMISSION_PATH, b2.DESIGN_PATH, b2.MODULE_PATH, b2.GENERATOR_PATH,
        b2.AUTHORITY_INVENTORY_PATH, b2.PROJECTION_O2P_PATH, _FIXTURE_FILE, SUCCESSOR_FILE}
    for key, relative in (("projection", b2.PROJECTION_PATH), ("profile", b2.PROFILE_PATH)):
        (root / relative).write_text(canonical_json(artifacts[key]), encoding="utf-8")
    assert b2.run_check_errors(root) == []
    for relative in (_FIXTURE_FILE, b2.AUTHORITY_INVENTORY_PATH, b2.MODULE_PATH):
        path = root / relative
        original = path.read_text(encoding="utf-8")
        path.write_text(original + "\n// uncommitted probe\n", encoding="utf-8")
        with pytest.raises(b2.DefinitionBatch2Error, match=re.escape(relative)):
            b2.build_artifact_pair(root, source_revision=revision)
        errors = b2.run_check_errors(root)
        assert errors and any(relative in error for error in errors), errors
        path.write_text(original, encoding="utf-8")
    assert b2.run_check_errors(root) == []


def test_committed_artifacts_match_regeneration():
    from de4sdv.semantic import definition_projection_batch2 as b2
    from de4sdv.semantic.authority_inventory import validate_source_binding
    from de4sdv.semantic.projection_o2p import canonical_json

    projection_path = REPO_ROOT / b2.PROJECTION_PATH
    assert projection_path.is_file(), "Commit-B gate: the batch-2 pair is published in the artifact commit"
    committed = json.loads(projection_path.read_text(encoding="utf-8"))
    assert validate_source_binding(REPO_ROOT, committed["binding"]) == []
    artifacts = b2.build_artifact_pair(REPO_ROOT, source_revision=committed["binding"]["source_revision"])
    assert canonical_json(artifacts["projection"]) == projection_path.read_text(encoding="utf-8")
    assert canonical_json(artifacts["profile"]) == (REPO_ROOT / b2.PROFILE_PATH).read_text(encoding="utf-8")
    assert b2.run_check_errors(REPO_ROOT) == []


def test_chain_verifier_requires_the_batch2_pair():
    from de4sdv.semantic import definition_projection_batch2 as b2
    from scripts import verify_generated_chain

    expected = verify_generated_chain._expected_inputs(REPO_ROOT)
    for relative in (b2.PROJECTION_PATH, b2.PROFILE_PATH):
        assert relative in expected
        assert b2.EXTERNAL_REFERENCE_PROFILE_PATH in expected[relative]
        assert SUCCESSOR_FILE in expected[relative]


# ---------------------------------------------------------------------------
# 8. Runtime independence and repository wiring
# ---------------------------------------------------------------------------


def test_batch2_machinery_is_never_imported_by_the_runtime_path():
    for relative in (
        "de4sdv/semantic/query.py", "de4sdv/semantic/runtime.py", "de4sdv/semantic/traversal.py",
        "de4sdv/semantic/impact.py", "de4sdv/semantic/mcp_server.py", "de4sdv/semantic/api_binding.py",
        "de4sdv/semantic/kernel_binding_index.py", "de4sdv/semantic/o3_bundle.py",
        "de4sdv/semantic/authority_selection.py", "de4sdv/semantic/composition_construction.py",
    ):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        for token in ("definition_projection_batch2", "definition-batch2", "definition-admission-batch2"):
            assert token not in text, (relative, token)


def _passing_gate_mocks():
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_o4_consumer_ledger import _passing_gate_mocks as shared

    return shared()


def test_check_repo_actually_invokes_the_batch2_gate():
    from unittest import mock

    from de4sdv.semantic import definition_projection_batch2
    from scripts import check_repo

    calls = []
    mocks = _passing_gate_mocks()
    for m in mocks:
        m.start()
    try:
        with mock.patch.object(definition_projection_batch2, "run_check_errors",
                               side_effect=lambda root: calls.append(root) or []):
            result = check_repo.main()
    finally:
        for m in mocks:
            m.stop()
    assert calls, "check_repo did not invoke the batch-2 gate"
    assert result == 0


def test_check_repo_fails_when_the_batch2_gate_fails():
    from unittest import mock

    from de4sdv.semantic import definition_projection_batch2
    from scripts import check_repo

    mocks = _passing_gate_mocks()
    for m in mocks:
        m.start()
    try:
        with mock.patch.object(definition_projection_batch2, "run_check_errors",
                               return_value=["sentinel batch-2 error"]):
            assert check_repo.main() == 1
    finally:
        for m in mocks:
            m.stop()
