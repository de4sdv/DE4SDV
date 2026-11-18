"""The adapter's mw::com configuration names the driving-command event as ICD.md fixes it.

The service id, the instance specifier and the event name are read from the mw::com table of
interfaces/ICD.md (MAP-DRIVING-DA-COMMAND's row), not copied into this test, so a change on either
side fails here. The event id, the instance id, the slots and the subscriber count are not in the ICD;
the test pins only that the adapter's configuration is a consumer of that one service.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
ICD = ADAPTER.parent / "interfaces" / "ICD.md"
CONFIG = ADAPTER / "mw_com_config_actuation_adapter.json"


def icd_command_row() -> dict[str, str]:
    for line in ICD.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == "MAP-DRIVING-DA-COMMAND":
            return {
                "event": cells[1].strip("`"),
                "specifier": cells[2].strip("`"),
                "service_id": cells[3],
                "payload": cells[4],
            }
    raise AssertionError("ICD.md has no MAP-DRIVING-DA-COMMAND row")


def test_the_icd_row_is_read() -> None:
    row = icd_command_row()
    assert re.fullmatch(r"\d+", row["service_id"]), row
    assert "DrivingCommandEventPayload" in row["payload"], row


def test_the_configuration_names_the_icd_service_event_and_specifier() -> None:
    row = icd_command_row()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert len(config["serviceTypes"]) == 1
    service = config["serviceTypes"][0]
    bindings = service["bindings"]
    assert [binding["serviceId"] for binding in bindings] == [int(row["service_id"])]
    assert [event["eventName"] for event in bindings[0]["events"]] == [row["event"]]
    instances = config["serviceInstances"]
    assert [instance["instanceSpecifier"] for instance in instances] == [row["specifier"]]
    assert instances[0]["serviceTypeName"] == service["serviceTypeName"]
    assert [event["eventName"] for event in instances[0]["instances"][0]["events"]] == [row["event"]]
