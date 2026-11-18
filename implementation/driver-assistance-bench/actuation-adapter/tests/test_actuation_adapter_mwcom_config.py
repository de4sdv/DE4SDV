"""The adapter's mw::com configuration names the driving-command event as ICD.md fixes it.

The service id, the instance specifier and the event name are read from the mw::com table of
interfaces/ICD.md (MAP-DRIVING-DA-COMMAND's row), not copied into this test, so a change on either
side fails here. The service type name, the event id, the instance id, the binding, the slots and the
subscriber count are not in the ICD: they are the lead's choices, pending the B6 manifests, pinned here
as such; the slot count is read from the INC-DRIVING-001 kit's driving command event (7404).
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


def test_the_values_the_icd_leaves_open_are_the_leads_pending_b6() -> None:
    # Not in ICD.md: the lead's decision, the warning request's pattern (service type name, event id 1,
    # instance 1, SHM, one subscriber, the adapter), pending the B6 manifests.
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    service = config["serviceTypes"][0]
    assert service["serviceTypeName"] == "/de4sdv/driver_assistance/DrivingCommand"
    assert [b["binding"] for b in service["bindings"]] == ["SHM"]
    assert [e["eventId"] for e in service["bindings"][0]["events"]] == [1]
    instances = config["serviceInstances"][0]["instances"]
    assert [(i["instanceId"], i["binding"]) for i in instances] == [(1, "SHM")]
    assert [e["maxSubscribers"] for e in instances[0]["events"]] == [1]


def kit_command_slots() -> set[int]:
    """numberOfSampleSlots of INC-DRIVING-001's driving command event (service 7404), in every kit file."""
    kit = ADAPTER.parent.parent / "closed-loop-driving-bench"
    slots = set()
    for path in sorted(kit.glob("*/mw_com_config_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        names = {s["serviceTypeName"] for s in data["serviceTypes"]
                 if any(b["serviceId"] == 7404 for b in s["bindings"])}
        for instance in data["serviceInstances"]:
            if instance["serviceTypeName"] in names:
                slots.update(e["numberOfSampleSlots"] for i in instance["instances"] for e in i["events"])
    return slots


def test_the_slot_count_is_that_of_the_inc_driving_001_command_event() -> None:
    # 7404 is the closest entry of 7401-7406: the same kind of event (one driving command per plan,
    # from the planner's process to the actuation adapter).
    slots = kit_command_slots()
    assert len(slots) == 1, slots
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    events = config["serviceInstances"][0]["instances"][0]["events"]
    assert [e["numberOfSampleSlots"] for e in events] == sorted(slots)


def test_main_subscribes_to_the_icd_specifier_and_event() -> None:
    row = icd_command_row()
    main = (ADAPTER / "actuation_adapter_main.cpp").read_text(encoding="utf-8")
    specifier = re.search(r'kDrivingCommandSpecifier = "([^"]+)";', main)
    assert specifier and specifier.group(1) == row["specifier"]
    event = re.search(r'Event<DrivingCommandEventPayload> (\w+)\{\*this,\s*"([^"]+)"\};', main)
    assert event and event.group(1) == row["event"] and event.group(2) == row["event"]
