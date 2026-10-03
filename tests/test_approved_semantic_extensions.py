"""Approved extensions are accounted model vocabulary, never closure claims."""
import json
from pathlib import Path
import re

import pytest

from de4sdv.semantic import authority_inventory as ai
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

ROOT = Path(__file__).resolve().parents[1]
MODEL = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_scoped_assurance.sysml"
ASSURANCE_RECORDS = (
    "EvidenceSupportCitation",
    "ScopedVVActivityRecord",
    "ScopedEvidenceAdequacyAssessment",
)
TRACE_RECORDS = ("ApprovedTraceMethod", "IncrementTraceObligations")
TRACE_MODEL = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_traces.sysml"
RELATIONSHIP_MODEL = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_relationship_carriers.sysml"
RELATIONSHIP_EXTENSIONS = {
    "AllocatableFunction": "action def AllocatableFunction",
    "LogicalAllocationElement": "part def LogicalAllocationElement",
    "PhysicalAllocationElement": "part def PhysicalAllocationElement",
    "ValidationPlanningScenario": "part def ValidationPlanningScenario",
    "RegulatorySource": "part def ControlledRegulatorySource",
    "ValidationPlanningAssociation": "connection def ValidationPlanningAssociation",
    "RegulatorySourceAssociation": "connection def RegulatorySourceAssociation",
}
EXTENSIONS = ASSURANCE_RECORDS + TRACE_RECORDS + tuple(RELATIONSHIP_EXTENSIONS)


@pytest.mark.parametrize("identity", ASSURANCE_RECORDS)
def test_assurance_extension_has_exact_model_mapping_and_no_closure_promotion(identity):
    contract = KernelContract.load(ROOT / ai.ONTOLOGY_PATH)
    assert contract.classes[identity]["kernel"] == {
        "file": MODEL, "declaration": f"item def {identity}"}
    decisions = ai.load_reviewed_decisions(ROOT / ai.DECISIONS_PATH)
    observed = ai.observed_entries(ROOT, contract, decisions)
    assert observed[identity]["observed"]["doc_text_observation"] == "normalized-exact"
    reviewed = decisions["entries"][identity]
    assert reviewed["evidence_state"] == "proposed"
    assert reviewed["adoption_status"] == "not-applicable"
    assert reviewed["closure_evidence_ref"] is None
    assert reviewed["transition_gate"]
    assert reviewed["semantic_text_equivalence"] is None
    assert identity not in MIGRATED_IDENTITIES


def test_historical_o4_review_population_is_not_silently_expanded():
    review = json.loads((ROOT / "docs/method-conformance/o4/ontology-review/integrated-review.json").read_text())
    rows = review["rows"]
    assert len(rows) == len({r["identity"] for r in rows}) == 93
    assert set(EXTENSIONS).isdisjoint(r["identity"] for r in rows)
    assert {r["identity"] for r in rows if r["o3_protected"]} == set(MIGRATED_IDENTITIES)


def test_integrated_inventory_accounts_for_all_new_records_without_waiving_coverage():
    contract = KernelContract.load(ROOT / ai.ONTOLOGY_PATH)
    decisions = ai.load_reviewed_decisions(ROOT / ai.DECISIONS_PATH)
    observed = ai.observed_entries(ROOT, contract, decisions)
    assert set(observed) == set(decisions["entries"])
    assert not ai.validate_inventory(
        observed, decisions, ai.load_closure_records(ROOT / ai.CLOSURE_PATH),
        ai.strategy_accounting(ROOT, contract, decisions))


@pytest.mark.parametrize("identity,declaration", RELATIONSHIP_EXTENSIONS.items())
def test_relationship_extension_is_ingestable_but_not_promoted(identity, declaration):
    contract = KernelContract.load(ROOT / ai.ONTOLOGY_PATH)
    assert identity in contract.classes
    assert contract.classes[identity]["kernel"] == {
        "file": RELATIONSHIP_MODEL, "declaration": declaration}
    decisions = ai.load_reviewed_decisions(ROOT / ai.DECISIONS_PATH)
    row = decisions["entries"][identity]
    assert row["evidence_state"] == "proposed"
    assert row["closure_evidence_ref"] is None
    assert row["transition_gate"]
    assert row["semantic_text_equivalence"] is None
    observed = ai.observed_entries(ROOT, contract, decisions)
    assert observed[identity]["observed"]["doc_text_observation"] == "normalized-exact"
    assert identity not in MIGRATED_IDENTITIES


@pytest.mark.parametrize("identity,native", [
    ("Function", "SysML v2 action/state/behavior definitions in functional-architecture slices"),
    ("LogicalElement", "part def elements in logical-architecture slices"),
    ("PhysicalElement", "part def elements in physical/software realization slices"),
    ("ValidationScenario", "Scenario parts with bounded validation outcomes (for example passBoundedValidation)"),
])
def test_successor_extension_does_not_rewrite_predecessor_mapping(identity, native):
    contract = KernelContract.load(ROOT / ai.ONTOLOGY_PATH)
    assert contract.classes[identity]["kernel"] == {"native": native}


def test_all_successor_pins_can_route_from_real_ontology_mapping_names():
    """Synthetic binding metadata proves wiring, not licensed ingestion/readback."""
    from types import SimpleNamespace
    from de4sdv.sysml_api.revisions import KernelElementBinding
    from de4sdv.semantic.relationship_successor_contract import generate_contract
    from de4sdv.semantic.relationship_successor import route_successor_bindings

    ontology = KernelContract.load(ROOT / ai.ONTOLOGY_PATH)
    profile = generate_contract(ROOT)
    pins = {**profile["classes"], **profile["carriers"]}
    bindings = []
    for pin in pins.values():
        matches = [name for name, row in ontology.classes.items() if row.get("kernel") == pin]
        assert len(matches) == 1, pin
        name = matches[0]
        bindings.append(KernelElementBinding(name, "synthetic-fixture-" + name,
            pin["file"], pin["declaration"]))
    supplied = SimpleNamespace(kernel_bindings=tuple(bindings))
    original = supplied.kernel_bindings
    index, routes = route_successor_bindings(profile, supplied)
    assert supplied.kernel_bindings == original
    assert {row.ontology_class for row in index.bindings} == set(pins)
    assert {row["profile_class"] for row in routes} == set(pins)
    actual = {row["profile_class"]: row["ingestion_class"] for row in routes}
    assert actual == {
        "Need": "Need", "Requirement": "Requirement",
        "Function": "AllocatableFunction", "LogicalElement": "LogicalAllocationElement",
        "PhysicalElement": "PhysicalAllocationElement",
        "ValidationScenario": "ValidationPlanningScenario", "RegulatorySource": "RegulatorySource",
        "hasValidationScenario": "ValidationPlanningAssociation",
        "hasRegulatorySource": "RegulatorySourceAssociation",
    }


@pytest.mark.parametrize("identity", TRACE_RECORDS)
def test_trace_extension_has_exact_model_mapping_without_runtime_admission(identity):
    contract = KernelContract.load(ROOT / ai.ONTOLOGY_PATH)
    assert contract.classes[identity]["kernel"] == {
        "file": TRACE_MODEL, "declaration": f"part def {identity}"}
    decisions = ai.load_reviewed_decisions(ROOT / ai.DECISIONS_PATH)
    observed = ai.observed_entries(ROOT, contract, decisions)
    assert observed[identity]["observed"]["doc_text_observation"] == "normalized-exact"
    row = decisions["entries"][identity]
    assert row["evidence_state"] == "proposed"
    assert row["closure_evidence_ref"] is None
    assert row["transition_gate"]
    assert row["semantic_text_equivalence"] is None
    assert identity not in MIGRATED_IDENTITIES


@pytest.mark.parametrize("identity", ("TraceLink", "RequiredTraceChain", "IncrementTraceabilityShell"))
def test_historical_trace_identity_is_retained_but_not_a_successor_witness(identity):
    contract = KernelContract.load(ROOT / ai.ONTOLOGY_PATH)
    mapping = contract.classes[identity]["kernel"]
    assert set(mapping) == {"external"}
    assert "Historical pre-Topic-5" in mapping["external"]
    row = ai.load_reviewed_decisions(ROOT / ai.DECISIONS_PATH)["entries"][identity]
    assert row["authority_current"] == "legacy-yaml"
    assert row["evidence_state"] == "repository-evidenced"
    assert row["closure_evidence_ref"] is None
    assert row["semantic_text_equivalence"] is None
    assert any("whole-consumer migration" in text for text in row["required_evidence"])


def test_reusable_stakeholder_roles_and_relationship_carrier_are_not_authority_grants():
    prefix = "textual-notation-of-model/packages/methods/de4sdv/"
    text = (ROOT / prefix / "de4sdv_stakeholders.sysml").read_text()
    code = re.sub(r"/\*.*?\*/|//[^\n]*", " ", text, flags=re.S)
    roles = {
        "SafetyExpert", "SecurityExpert", "SystemArchitect", "SoftwareDeveloper",
        "HardwareDeveloper", "Maintainer", "Supplier", "ProjectManager",
        "RoadUser", "VehicleOccupant", "SystemsEngineer", "ProductLineEngineer",
        "ComplianceEngineer", "VerificationEngineer", "OpenSourceReviewer",
    }
    declarations = re.findall(r"\bpart def (\w+)\s*:>\s*Stakeholder\b", code)
    assert set(declarations) == roles
    assert len(declarations) == len(roles)
    assert not re.search(r"\bindividual\s+(?:part|item)\s+def\b", code)
    contract = KernelContract.load(ROOT / ai.ONTOLOGY_PATH)
    assert contract.relationships["hasStakeholder"]["domain"] == "EngineeringIncrement"
    assert contract.relationships["hasStakeholder"]["range"] == "Stakeholder"
    assert "sysml_mapping" not in contract.relationships["hasStakeholder"]
    kernel = ai.kernel_accounting(ROOT, contract)
    assert kernel.governed_declarations == kernel.mapped_in_directory + kernel.exclusions


def _constructor_record(name, kind, **values):
    """Small synthetic construction input, never a real-model fixture."""
    fields = "\n".join(f"    attribute :>> {key} = {json.dumps(value)};"
                       for key, value in values.items())
    return f"  part {name} : {kind} {{\n{fields}\n  }}\n"


@pytest.fixture
def successor_constructor_parts():
    return {
        "source": "  part def LeftRoot {}\n",
        "target": "  part def RightRoot {}\n",
        "carrier": ("  connection def SyntheticCarrier {\n"
                    "    end source : LeftRoot;\n    end target : RightRoot;\n  }\n"),
        "version": _constructor_record("version", "SuccessorVersionRecord",
            version="synthetic/v1", supersedes="synthetic/previous"),
        "source_record": _constructor_record("leftPin", "SuccessorClassRecord",
            identity="Left", sourceFile=RELATIONSHIP_MODEL, declaration="part def LeftRoot"),
        "target_record": _constructor_record("rightPin", "SuccessorClassRecord",
            identity="Right", sourceFile=RELATIONSHIP_MODEL, declaration="part def RightRoot"),
        "relation": _constructor_record("relationship", "SuccessorRelationRecord",
            predicate="syntheticRelation", carrier="SyntheticCarrier", mechanism="typed-connection",
            strength="planning", sourceClass="Left", targetClass="Right",
            sourceUsage="PartUsage", targetUsage="PartUsage", inverse=""),
    }


def _constructor_model(parts):
    return "package DE4SDV_RelationshipSuccessor {\n" + "".join(parts.values()) + "}\n"


def _synthetic_constructor(monkeypatch, sources):
    """Overlay synthetic sources; unrelated program digests are not under test."""
    from de4sdv.semantic import relationship_successor_contract as construction
    original_text, original_bytes = Path.read_text, Path.read_bytes
    overlays = {ROOT / path: text for path, text in sources.items()}

    def read_text(path, *args, **kwargs):
        return overlays[path] if path in overlays else original_text(path, *args, **kwargs)

    def read_bytes(path, *args, **kwargs):
        return overlays[path].encode() if path in overlays else original_bytes(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(construction, "PROGRAM_INPUTS", ())
        scoped.setattr(Path, "read_text", read_text)
        scoped.setattr(Path, "read_bytes", read_bytes)
        return construction.generate_contract(ROOT)


@pytest.mark.parametrize("fragment", ["version", "carrier", "source", "target"])
def test_successor_constructor_rejects_foreign_owner(monkeypatch, successor_constructor_parts, fragment):
    parts = successor_constructor_parts
    baseline = _synthetic_constructor(monkeypatch, {RELATIONSHIP_MODEL: _constructor_model(parts)})
    assert baseline["schema"] == "synthetic/v1"
    assert baseline["carriers"]["syntheticRelation"]["declaration"] == "connection def SyntheticCarrier"
    parts[fragment] = "  part def ForeignOwner {\n" + parts[fragment] + "  }\n"
    with pytest.raises(ValueError):
        _synthetic_constructor(monkeypatch, {RELATIONSHIP_MODEL: _constructor_model(parts)})


def test_successor_constructor_package_prefix_is_not_governed_identity(monkeypatch, successor_constructor_parts):
    parts = {"version": successor_constructor_parts["version"]}
    model = _constructor_model(parts)
    assert _synthetic_constructor(monkeypatch, {RELATIONSHIP_MODEL: model})["schema"] == "synthetic/v1"
    model = model.replace("package DE4SDV_RelationshipSuccessor {",
                          "package DE4SDV_RelationshipSuccessor::Foreign {")
    with pytest.raises(ValueError, match="missing governed successor package"):
        _synthetic_constructor(monkeypatch, {RELATIONSHIP_MODEL: model})


@pytest.fixture
def successor_qualified_sources(successor_constructor_parts):
    parts = successor_constructor_parts
    parts["source"] = parts["target"] = ""
    parts["source_record"] = _constructor_record("leftPin", "SuccessorClassRecord",
        identity="Left", sourceFile="pins/source.sysml", declaration="part def SourceRoot")
    parts["target_record"] = _constructor_record("rightPin", "SuccessorClassRecord",
        identity="Right", sourceFile="pins/target.sysml", declaration="part def TargetRoot")
    parts["carrier"] = ("  connection def SyntheticCarrier {\n"
        "    end source : CanonicalSource::SourceRoot;\n"
        "    end target : CanonicalTarget::TargetRoot;\n  }\n")
    return {
        RELATIONSHIP_MODEL: _constructor_model(parts),
        "pins/source.sysml": "package CanonicalSource {\n  part def SourceRoot {}\n}\n",
        "pins/target.sysml": "package CanonicalTarget {\n  part def TargetRoot {}\n}\n",
        "pins/foreign.sysml": "package Foreign {\n  part def TargetRoot {}\n}\n",
    }


@pytest.mark.parametrize("target_type", ["Foreign::TargetRoot", "Missing::TargetRoot"])
def test_successor_constructor_rejects_foreign_qualified_pin(monkeypatch, successor_qualified_sources, target_type):
    sources = successor_qualified_sources
    baseline = _synthetic_constructor(monkeypatch, sources)
    assert baseline["classes"]["Right"] == {
        "file": "pins/target.sysml", "declaration": "part def TargetRoot"}
    assert "pins/foreign.sysml" not in baseline["bound_inputs"]
    sources[RELATIONSHIP_MODEL] = sources[RELATIONSHIP_MODEL].replace(
        "CanonicalTarget::TargetRoot", target_type)
    with pytest.raises(ValueError, match="carrier endpoint pin mismatch"):
        _synthetic_constructor(monkeypatch, sources)


@pytest.mark.parametrize("fragment", ["version", "carrier"])
def test_successor_constructor_refuses_live_duplicate_outside_package(monkeypatch, successor_constructor_parts, fragment):
    parts = successor_constructor_parts
    model = _constructor_model(parts) + "package Foreign {\n" + parts[fragment] + "}\n"
    with pytest.raises(ValueError, match="ambiguous live declaration"):
        _synthetic_constructor(monkeypatch, {RELATIONSHIP_MODEL: model})


@pytest.mark.parametrize("mode", ["no_import", "comment_import", "nested_import", "local_shadow"])
def test_successor_constructor_bare_type_requires_canonical_scope(monkeypatch, successor_qualified_sources, mode):
    sources = successor_qualified_sources
    model = sources[RELATIONSHIP_MODEL].replace("CanonicalTarget::TargetRoot", "TargetRoot")
    imported = model.replace("{\n", "{\n  private import CanonicalTarget::*;\n", 1)
    assert _synthetic_constructor(monkeypatch, {**sources, RELATIONSHIP_MODEL: imported})["classes"]["Right"]["file"] == "pins/target.sysml"
    if mode == "comment_import":
        model = model.replace("{\n", "{\n  /* private import CanonicalTarget::*; */\n", 1)
    elif mode == "nested_import":
        model = model.replace("{\n", "{\n  part def ForeignOwner { private import CanonicalTarget::*; }\n", 1)
    elif mode == "local_shadow":
        model = imported.replace("{\n", "{\n  part def TargetRoot {}\n", 1)
    sources[RELATIONSHIP_MODEL] = model
    with pytest.raises(ValueError, match="carrier endpoint pin mismatch"):
        _synthetic_constructor(monkeypatch, sources)


def test_successor_constructor_refuses_competing_known_imported_homonym(monkeypatch, successor_qualified_sources):
    """R4-adj: two known pinned homonyms in direct import scope make a bare end ambiguous."""
    sources = successor_qualified_sources
    foreign_pin = _constructor_record("foreignPin", "SuccessorClassRecord",
        identity="ForeignRight", sourceFile="pins/foreign.sysml", declaration="part def TargetRoot")
    competing = sources[RELATIONSHIP_MODEL].replace(
        "{\n", "{\n  private import CanonicalTarget::*;\n  private import Foreign::*;\n" + foreign_pin, 1)
    # Both pinned definitions are known and imported; the qualified spelling still admits.
    qualified = _synthetic_constructor(monkeypatch, {**sources, RELATIONSHIP_MODEL: competing})
    assert qualified["classes"]["Right"] == {
        "file": "pins/target.sysml", "declaration": "part def TargetRoot"}
    assert qualified["classes"]["ForeignRight"] == {
        "file": "pins/foreign.sysml", "declaration": "part def TargetRoot"}
    # The supported bare spelling cannot uniquely identify the canonical pin: refuse it.
    bare = competing.replace("CanonicalTarget::TargetRoot", "TargetRoot")
    with pytest.raises(ValueError, match="carrier endpoint pin mismatch"):
        _synthetic_constructor(monkeypatch, {**sources, RELATIONSHIP_MODEL: bare})


def test_successor_constructor_bare_type_uniqueness_is_bounded_to_known_imports(
        monkeypatch, successor_qualified_sources):
    """R4-adj boundary: only known pins visible by direct import can compete."""
    sources = successor_qualified_sources
    foreign_pin = _constructor_record("foreignPin", "SuccessorClassRecord",
        identity="ForeignRight", sourceFile="pins/foreign.sysml", declaration="part def TargetRoot")
    # The competing pin is known but its package is not imported: the bare end stays canonical.
    model = sources[RELATIONSHIP_MODEL].replace(
        "{\n", "{\n  private import CanonicalTarget::*;\n" + foreign_pin, 1)
    model = model.replace("CanonicalTarget::TargetRoot", "TargetRoot")
    assert _synthetic_constructor(monkeypatch, {**sources, RELATIONSHIP_MODEL: model})["classes"]["Right"] == {
        "file": "pins/target.sysml", "declaration": "part def TargetRoot"}
    # The competing package is imported but no competing pin is known: bounded, no resolver.
    model = sources[RELATIONSHIP_MODEL].replace(
        "{\n", "{\n  private import CanonicalTarget::*;\n  private import Foreign::*;\n", 1)
    model = model.replace("CanonicalTarget::TargetRoot", "TargetRoot")
    assert _synthetic_constructor(monkeypatch, {**sources, RELATIONSHIP_MODEL: model})["classes"]["Right"] == {
        "file": "pins/target.sysml", "declaration": "part def TargetRoot"}


@pytest.mark.parametrize("qualified", [True, False])
def test_successor_constructor_known_qualified_identity_cannot_choose_between_files(
        monkeypatch, successor_qualified_sources, qualified):
    sources = successor_qualified_sources
    sources["pins/foreign.sysml"] = sources["pins/target.sysml"]
    competing_pin = _constructor_record("foreignPin", "SuccessorClassRecord",
        identity="ForeignRight", sourceFile="pins/foreign.sysml", declaration="part def TargetRoot")
    model = sources[RELATIONSHIP_MODEL].replace(
        "{\n", "{\n  private import CanonicalTarget::*;\n" + competing_pin, 1)
    if not qualified:
        model = model.replace("CanonicalTarget::TargetRoot", "TargetRoot")
    with pytest.raises(ValueError, match="carrier endpoint pin mismatch"):
        _synthetic_constructor(monkeypatch, {**sources, RELATIONSHIP_MODEL: model})


def test_successor_constructor_local_bare_identity_cannot_choose_between_files(
        monkeypatch, successor_constructor_parts):
    model = _constructor_model(successor_constructor_parts)
    competing_pin = _constructor_record("foreignPin", "SuccessorClassRecord",
        identity="ForeignLeft", sourceFile="pins/foreign.sysml", declaration="part def LeftRoot")
    model = model.replace("{\n", "{\n" + competing_pin, 1)
    sources = {RELATIONSHIP_MODEL: model,
               "pins/foreign.sysml": "package DE4SDV_RelationshipSuccessor {\n  part def LeftRoot {}\n}"}
    with pytest.raises(ValueError, match="carrier endpoint pin mismatch"):
        _synthetic_constructor(monkeypatch, sources)
