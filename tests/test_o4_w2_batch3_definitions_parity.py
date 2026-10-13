"""Historical definition records and current model boundaries.

This cleanup retires current-documentation equality with copied or frozen definitions.
Live checks retain owned nonempty documentation, structure and claim boundaries.
Inventory/decision parity fields below describe frozen historical evidence only;
they are not recomputed from, or imposed on, current model wording.
"""

from __future__ import annotations

import re
from pathlib import Path


from model_contract_fixtures import owned_definition_documentation
from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES as MIGRATED_IDENTITIES

REPO = Path(__file__).resolve().parents[1]
MODEL_PATH = (
    REPO / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml"
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


def test_enum_has_owned_documentation_and_recorded_parity() -> None:
    # This cleanup retired enum prose parity; retain owned documentation and the record.
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    assert owned_definition_documentation(file_text, "enum def SignalMappingDisposition").strip()


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
