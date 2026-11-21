"""service_ids.json is the machine-readable copy of the ids that ICD.md proposes.

Every value in ICD.md's tables, and the sentence that keeps 0x4dee and 0x4df0, must equal
service_ids.json. The configs of the warning path read their ids from service_ids.json
(ivi-warning/tests hold them to it), so a drift between the two documents fails here first.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

INTERFACES = Path(__file__).resolve().parent.parent
ICD = INTERFACES / "ICD.md"
IDS = INTERFACES / "service_ids.json"
HEADER = INTERFACES / "include" / "de4sdv" / "driver_assistance" / "payloads.h"


def _ids() -> dict:
    return json.loads(IDS.read_text(encoding="utf-8"))


def _tables(markdown: str) -> list[tuple[list[str], list[list[str]]]]:
    """Every pipe table of the document as (header cells, body rows)."""
    tables: list[tuple[list[str], list[list[str]]]] = []
    block: list[str] = []
    for line in markdown.splitlines() + [""]:
        if line.startswith("|"):
            block.append(line)
            continue
        if len(block) >= 2:
            cells = [[c.strip() for c in row.strip().strip("|").split("|")] for row in block]
            assert set("".join(cells[1])) <= set("-: "), f"not a table separator: {block[1]}"
            tables.append((cells[0], cells[2:]))
        block = []
    return tables


def _table(header_first: str) -> list[list[str]]:
    found = [rows for header, rows in _tables(ICD.read_text(encoding="utf-8")) if header[0] == header_first]
    assert len(found) == 1, f"{len(found)} tables of ICD.md start with the column {header_first!r}"
    return found[0]


def _code(cell: str) -> str:
    match = re.fullmatch(r"`([^`]+)`", cell)
    assert match, f"not one code span: {cell!r}"
    return match.group(1)


def test_mw_com_events_table_equals_service_ids() -> None:
    rows = _table("Mapping")
    events = _ids()["icd"]["mw_com_events"]
    assert len(rows) == len(events) == 3
    for row, event in zip(rows, events):
        mapping, name, specifier, service_id = row[:4]
        assert mapping == event["mapping"]
        assert _code(name) == event["event"]
        assert _code(specifier) == event["instance_specifier"]
        assert int(service_id) == event["service_id"]


def test_someip_table_equals_service_ids() -> None:
    icd = _ids()["icd"]
    someip = icd["someip_warning_request"]
    tunnel = icd["data_tunnel"]
    fields = "; ".join(f"{f['type']} {f['name']} = {f['number']}" for f in tunnel["fields"])
    expected = {
        "Service, instance": f"{someip['service_id']}, {someip['instance_id']}",
        "Eventgroup, event": f"{someip['eventgroup_id']}, {someip['event_id']}",
        "Transport": f"{someip['transport']}, {someip['protocol']} {someip['port']}",
        "Data Tunnel message": f"`{tunnel['message']} {{ {fields}; }}`",
        "Service unit": f"`{tunnel['service_unit']}`",
    }
    rows = {item: value for item, value in _table("Item")}
    assert rows == expected


def test_warning_bytes_table_equals_service_ids() -> None:
    rows = _table("Offset")
    payload = _ids()["icd"]["warning_request_someip_payload"]
    assert len(rows) == len(payload["fields"])
    for (offset, field, kind), expected in zip(rows, payload["fields"]):
        assert int(offset) == expected["offset"]
        assert _code(field) == expected["name"]
        assert kind.split(",")[0] == expected["type"]
    last = payload["fields"][-1]
    assert payload["size"] == last["offset"] + 4
    text = ICD.read_text(encoding="utf-8")
    assert "The bytes are a proposal: big-endian, with no length field." in text
    assert payload["byte_order"] == "big-endian"
    assert payload["length_field"] == "none"


def test_kept_services_sentence_equals_service_ids() -> None:
    kept = _ids()["icd"]["someip_kept"]
    text = ICD.read_text(encoding="utf-8")
    sentence = re.search(
        r"^(0x[0-9a-f]{4}) on TCP (\d+) and (0x[0-9a-f]{4}) on TCP (\d+) belong to the closed-loop driving bench"
        r" and stay as they are\.$",
        text,
        re.M,
    )
    assert sentence, "the sentence that keeps the closed-loop driving bench's services is gone"
    found = [(sentence.group(1), int(sentence.group(2))), (sentence.group(3), int(sentence.group(4)))]
    assert found == [(k["service_id"], k["port"]) for k in kept]
    assert all(k["status"] == "kept" for k in kept)


def test_icd_points_to_service_ids() -> None:
    assert "[`service_ids.json`](service_ids.json)" in ICD.read_text(encoding="utf-8")


def test_payload_header_agrees_with_service_ids() -> None:
    header = HEADER.read_text(encoding="utf-8")
    someip = _ids()["icd"]["someip_warning_request"]
    size = re.search(r"kWarningRequestSomeipSize = (\d+);", header)
    assert size and int(size.group(1)) == _ids()["icd"]["warning_request_someip_payload"]["size"]
    assert f"service {someip['service_id']}, event {someip['event_id']}" in header


@pytest.mark.parametrize("section", ["icd", "lane_choices"])
def test_every_value_has_a_status(section: str) -> None:
    assert _ids()[section]["status"], f"{section} has no status"
