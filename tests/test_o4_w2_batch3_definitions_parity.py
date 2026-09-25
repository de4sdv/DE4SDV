"""O4 W2 batch 3 — definitions-parity batch (three signal-mapping rows).

Batch scope (exactly three retained, ungated ``MODEL_AUTHORITY_PARITY`` rows
grounded in ``de4sdv_method_process.sysml``):

* ``SignalMappingDisposition`` — parity closed **normalized-exact**: the
  enum-level doc now carries the reviewed definition text verbatim; the
  literal set and literal docs are unchanged.
* ``LogicalToSoftwareSignalMappingRecord`` — parity closed by an explicit
  **reviewed-equivalence** record: the model doc carries the reviewed
  strengthened control-record wording (a reviewed documented superset of the
  YAML comparison-source definition); the record must not become a second
  authority for external contract facts, and the string-vs-reference
  endpoint-field representation stays unresolved by design.
* ``SystemToSoftwareSignalMappingCandidate`` — parity closed by an explicit
  **reviewed-equivalence** record: the model doc carries the reviewed
  non-claiming allocation semantics plus the reviewed specialization-payload
  delta; no ``realizedBy -> allocatedToArchitecture`` redesign is implemented
  or pre-empted.

Lifecycle: stage ``o4-w2 batch 3 (definitions parity)``; remaining obligation
``O2 admission / generated Semantic Projection from the reviewed model
representation``; no O3 transition/admission obligation; ``authority_current``
remains ``legacy-yaml``; no closure evidence; no authority cutover.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from de4sdv.semantic.authority_inventory import doc_text_observation
from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

REPO = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO / "docs/method-conformance/o1/semantic-authority-inventory.json"
DECISIONS_PATH = REPO / "docs/method-conformance/o1/authority-review-decisions.yaml"
ONTOLOGY_PATH = REPO / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
REGISTER_PATH = REPO / "docs/method-conformance/o4/o4-execution-register.json"
MODEL_PATH = (
    REPO / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml"
)

PILOT_ROWS: dict[str, str] = {
    "SignalMappingDisposition": "enum def SignalMappingDisposition",
    "LogicalToSoftwareSignalMappingRecord": "item def LogicalToSoftwareSignalMappingRecord",
    "SystemToSoftwareSignalMappingCandidate": "allocation def SystemToSoftwareSignalMappingCandidate",
}

REVIEWED_DEFINITIONS: dict[str, str] = {
    "SignalMappingDisposition": (
        "The disposition of a logical-to-software signal mapping "
        "(mapped, candidate, deferred, or notApplicable)."
    ),
    "LogicalToSoftwareSignalMappingRecord": (
        "A control record for a logical or semantic information item crossing "
        "into a software, service, topic, API, or physical boundary; preserves "
        "trace and review obligations without claiming runtime interoperability."
    ),
    "SystemToSoftwareSignalMappingCandidate": (
        "A reusable non-claiming allocation relationship from a logical/function "
        "signal responsibility to a concrete software or adapter signal endpoint; "
        "the allocation alone never proves field identity or runtime "
        "interoperability."
    ),
}

# later-batch convention (definition admission batch 1): the O2-admission
# obligation of these rows is discharged by the generated definition
# projection/profile pair; the remaining forward obligation is the runtime
# one (support stays vocabulary-only).
REMAINING_OBLIGATION = [
    "runtime-queryable support (post-migration) requires exact-revision traversal evidence; support remains vocabulary-only",
]
# later-batch convention: re-stated at the current treatment stage.
TREATED_STAGE = "o4 definition admission batch 1 (projection + profile)"
EQUIVALENCE_ROWS = (
    "LogicalToSoftwareSignalMappingRecord",
    "SystemToSoftwareSignalMappingCandidate",
)

#: The record's attribute surface pinned unchanged (endpoint fields remain
#: string-typed; the string-vs-reference question stays unresolved).
RECORD_ATTRIBUTES = (
    "mappingId",
    "semanticSource",
    "softwareContractArtifact",
    "softwareContractMessage",
    "softwareContractField",
    "adapterEndpoints",
    "direction",
    "dataTypeAndUnit",
    "timingQualityAndState",
    "transformationRule",
    "disposition",
    "owner",
    "nextAction",
    "evidenceOrGap",
)


def _inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _decisions() -> dict:
    return yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8"))["entries"]


def _entries(inventory: dict, identities=None) -> dict:
    entries = {entry["identity"]: entry for entry in inventory["entries"]}
    if identities is None:
        return entries
    return {identity: entries[identity] for identity in identities}


def _declaration_block(text: str, declaration: str) -> list[str]:
    lines = text.splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.strip() == f"{declaration} {{"
    )
    base_indent = len(lines[start]) - len(lines[start].lstrip())
    block = [lines[start]]
    for line in lines[start + 1 :]:
        block.append(line)
        if line.strip() == "}" and (len(line) - len(line.lstrip())) == base_indent:
            break
    return block


def _flat(text: str) -> str:
    """Whitespace-collapsed block text with comment decoration removed."""
    return " ".join(text.replace("*", " ").split())


def test_exact_three_row_scope() -> None:
    inventory = _inventory()
    entries = _entries(inventory, PILOT_ROWS)
    assert len(entries) == 3
    register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    rows = {row["identity"]: row for row in register["rows"]}
    for identity in PILOT_ROWS:
        assert entries[identity]["observed"]["file"].endswith(
            "de4sdv_method_process.sysml"
        ), identity
        row = rows[identity]
        assert row["membership"] == "o4-target", identity
        assert row["base_wave"] == "W2", identity
        assert row["gate_wave"] is None, identity
        assert row["migration_class"] == "MODEL_AUTHORITY_PARITY", identity


def test_enum_level_doc_is_normalized_exact() -> None:
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    ontology = yaml.safe_load(ONTOLOGY_PATH.read_text(encoding="utf-8"))["classes"]
    definition = ontology["SignalMappingDisposition"]["definition"]
    assert definition == REVIEWED_DEFINITIONS["SignalMappingDisposition"]
    observation = doc_text_observation(
        file_text, "enum def SignalMappingDisposition", definition
    )
    assert observation == "normalized-exact"
    reviewed = _entries(_inventory(), ["SignalMappingDisposition"])[
        "SignalMappingDisposition"
    ]["reviewed"]
    assert reviewed["semantic_text_equivalence"] is None
    assert reviewed["stage"] == TREATED_STAGE
    assert reviewed["required_evidence"] == REMAINING_OBLIGATION
    assert "parity complete (o4-w2 batch 3)" in reviewed["exact_fit_decision"]


def test_reviewed_equivalence_rows_record_their_equivalence() -> None:
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    ontology = yaml.safe_load(ONTOLOGY_PATH.read_text(encoding="utf-8"))["classes"]
    entries = _entries(_inventory(), EQUIVALENCE_ROWS)
    for identity in EQUIVALENCE_ROWS:
        declaration = PILOT_ROWS[identity]
        definition = ontology[identity]["definition"]
        assert definition == REVIEWED_DEFINITIONS[identity]
        observation = doc_text_observation(file_text, declaration, definition)
        assert observation == "differs", identity
        reviewed = entries[identity]["reviewed"]
        assert reviewed["semantic_text_equivalence"] == "reviewed-equivalent", identity
        assert reviewed["stage"] == TREATED_STAGE, identity
        assert reviewed["required_evidence"] == REMAINING_OBLIGATION, identity
        assert reviewed["exact_fit_decision"].startswith("reviewed-equivalence:"), identity
        assert "not a divergence" in reviewed["exact_fit_decision"], identity


def test_lifecycle_evidence_is_o4_o2_only() -> None:
    inventory = _inventory()
    for identity, entry in _entries(inventory, PILOT_ROWS).items():
        evidence = entry["reviewed"]["required_evidence"]
        assert not any("O3" in item for item in evidence), identity
        # later-batch convention (definition admission batch 1): the O2-admission
        # obligation was discharged by the generated projection/profile pair; the
        # forward obligation is the runtime note.
        assert evidence == REMAINING_OBLIGATION, identity
    assert len(MIGRATED_IDENTITIES) == 13
    assert set(PILOT_ROWS).isdisjoint(set(MIGRATED_IDENTITIES))


def test_legacy_yaml_authority_remains_current() -> None:
    inventory = _inventory()
    for identity, entry in _entries(inventory, PILOT_ROWS).items():
        reviewed = entry["reviewed"]
        assert reviewed["authority_current"] == "legacy-yaml", identity
        assert reviewed["authority_target"] == "model-authoritative", identity
        assert reviewed["evidence_state"] == "repository-evidenced", identity
        assert reviewed["conditional_target"] is False, identity
        assert reviewed["closure_evidence_ref"] is None, identity
        assert reviewed["adoption_status"] == "not-applicable", identity


def test_decisions_source_records_the_closed_parity() -> None:
    entries = _decisions()
    for identity in PILOT_ROWS:
        reviewed = entries[identity]
        assert reviewed["stage"] == TREATED_STAGE, identity
        assert reviewed["required_evidence"] == REMAINING_OBLIGATION, identity
    assert entries["SignalMappingDisposition"]["semantic_text_equivalence"] is None
    for identity in EQUIVALENCE_ROWS:
        assert (
            entries[identity]["semantic_text_equivalence"] == "reviewed-equivalent"
        ), identity


def test_enum_literal_set_unchanged() -> None:
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    block = _declaration_block(file_text, "enum def SignalMappingDisposition")
    literals = [
        line.strip().split(" ")[0]
        for line in block[1:-1]
        if re.match(r"^\s{4}[A-Za-z_][A-Za-z0-9_]*\s*\{", line)
    ]
    assert literals == ["mapped", "candidate", "deferred", "notApplicable"]
    # The enum-level doc exists (leading doc statement at direct depth).
    direct_docs = [
        line
        for line in block[1:-1]
        if line.strip().startswith("doc /*") and len(line) - len(line.lstrip()) == 4
    ]
    assert len(direct_docs) == 1
    assert "The disposition of a logical-to-software signal mapping" in direct_docs[0]


def test_record_boundaries_hold() -> None:
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    block = _declaration_block(file_text, "item def LogicalToSoftwareSignalMappingRecord")
    attribute_lines = [
        line.strip() for line in block if line.strip().startswith("attribute ")
    ]
    assert len(attribute_lines) == len(RECORD_ATTRIBUTES)
    for name, line in zip(RECORD_ATTRIBUTES, attribute_lines):
        assert line.startswith(f"attribute {name} :"), name
    # Endpoint-field representation stays unresolved: string-typed, unchanged.
    assert "attribute adapterEndpoints : ScalarValues::String;" in attribute_lines
    assert "attribute softwareContractArtifact : ScalarValues::String;" in attribute_lines
    # Not a second authority for external contract facts.
    joined = _flat(" ".join(block))
    assert "authoritative external artifacts" in joined
    note = _entries(_inventory(), ["LogicalToSoftwareSignalMappingRecord"])[
        "LogicalToSoftwareSignalMappingRecord"
    ]["reviewed"]["note"]
    assert "must not become a second authority" in note
    assert "stays unresolved by design" in note


def test_candidate_boundaries_hold() -> None:
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    assert "allocation def SystemToSoftwareSignalMappingCandidate {" in file_text
    block = _declaration_block(
        file_text, "allocation def SystemToSoftwareSignalMappingCandidate"
    )
    inner = [line for line in block[1:-1] if line.strip()]
    assert all(line.strip().startswith(("doc /*", "*")) for line in inner)
    joined = _flat(" ".join(block))
    assert "never proves field identity or runtime interoperability" in joined
    assert "allocatedToArchitecture" not in file_text
    note = _entries(_inventory(), ["SystemToSoftwareSignalMappingCandidate"])[
        "SystemToSoftwareSignalMappingCandidate"
    ]["reviewed"]["note"]
    assert "not implemented or pre-empted" in note


def test_unrelated_w2_rows_are_untouched() -> None:
    inventory = _inventory()
    entries = _entries(inventory)
    for identity in ("EngineeringIncrement", "FeatureIncrement", "NeedsRequirementsIncrement"):
        assert entries[identity]["observed"]["doc_text_observation"] == (
            "normalized-exact"
        ), identity
        # later-batch convention (definition admission batch 1): prior rows now
        # carry the shared admission stage.
        assert entries[identity]["reviewed"]["stage"] == TREATED_STAGE, identity
    for identity in (
        "IncrementEngineeringQuestion",
        "IncrementLifecycleDecision",
        "SystemLayer",
        "ProblemStatement",
        "Assumption",
        "Gap",
    ):
        # later-batch convention (definition admission batch 1): prior rows now
        # carry the shared admission stage.
        assert entries[identity]["reviewed"]["stage"] == TREATED_STAGE, identity
    assert entries["DerivesFromNeed"]["reviewed"]["semantic_text_equivalence"] == (
        "review-required"
    )
    assert entries["IncrementSize"]["reviewed"]["disposition"] == "keep-as-is"
