"""Historical definition records and current model boundaries.

This cleanup retires current-documentation equality with copied or frozen definitions.
Live checks retain owned nonempty documentation, structure and claim boundaries.
Inventory/decision parity fields below describe frozen historical evidence only;
they are not recomputed from, or imposed on, current model wording.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from model_contract_fixtures import owned_definition_documentation
from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES as MIGRATED_IDENTITIES

REPO = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO / "docs/method-conformance/o1/semantic-authority-inventory.json"
DECISIONS_PATH = REPO / "docs/method-conformance/o1/authority-review-decisions.yaml"
REGISTER_PATH = REPO / "docs/method-conformance/o4/o4-execution-register.json"
MODEL_PATH = (
    REPO / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml"
)

PILOT_ROWS: dict[str, str] = {
    "SignalMappingDisposition": "enum def SignalMappingDisposition",
    "LogicalToSoftwareSignalMappingRecord": "item def LogicalToSoftwareSignalMappingRecord",
    "SystemToSoftwareSignalMappingCandidate": "allocation def SystemToSoftwareSignalMappingCandidate",
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


def test_enum_has_owned_documentation_and_recorded_parity() -> None:
    # This cleanup retired enum prose parity; retain owned documentation and the record.
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    assert owned_definition_documentation(file_text, "enum def SignalMappingDisposition").strip()
    reviewed = _entries(_inventory(), ["SignalMappingDisposition"])[
        "SignalMappingDisposition"
    ]["reviewed"]
    assert reviewed["semantic_text_equivalence"] is None
    assert reviewed["stage"] == TREATED_STAGE
    assert reviewed["required_evidence"] == REMAINING_OBLIGATION
    assert "parity complete (o4-w2 batch 3)" in reviewed["exact_fit_decision"]


def test_reviewed_equivalence_rows_record_their_equivalence() -> None:
    # This cleanup retired current-vs-copied "differs"; these are recorded review outcomes.
    entries = _entries(_inventory(), EQUIVALENCE_ROWS)
    for identity in EQUIVALENCE_ROWS:
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
    # This cleanup retires the copied enum-definition phrase, not its documentation home.
    assert owned_definition_documentation(file_text, "enum def SignalMappingDisposition").strip()


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
    inner = "\n".join(block[1:-1])
    # Named Documentation is still documentation, not implemented endpoints or
    # allocations. Strip only complete doc statements (including a visibility
    # prefix such as ``private doc``), then reject all code.
    doc_statement = r"(?:\b(?:public|private|protected)\s+)?\bdoc(?:\s+[A-Za-z_]\w*)?\s*/\*.*?\*/"
    assert not re.sub(doc_statement, "", inner, flags=re.S).strip()
    for code in ("end source : Anything;", "attribute implemented : Boolean;"):
        assert re.sub(doc_statement, "", inner + "\n" + code, flags=re.S).strip()
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
