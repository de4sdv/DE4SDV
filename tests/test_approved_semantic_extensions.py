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
