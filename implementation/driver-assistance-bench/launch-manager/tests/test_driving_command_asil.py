"""The driving command's mw::com deployment is ASIL B in every manifest that names it, provider and consumer.

The supervision decision of 2026-11-18 puts the driving command (MAP-DRIVING-DA-COMMAND,
de4sdv/driver_assistance/driving_command) on an ASIL B deployment of S-CORE Communication. At Communication v0.6.0
(the bench's pin), the schema of mw_com_config.json says: an instance at asil-level B needs the process's global
asil-level set to B as well, on the provider's side (it then serves QM and ASIL B consumers) and on the consumer's
(it then needs an ASIL B provider). This deployment is S-CORE's mechanism, not a safety claim: VisionPilot and its GPU
libraries are not developed or qualified to ASIL B.

The manifests are discovered: every JSON file under the bench whose serviceInstances name the specifier. The S-CORE
host's manifests must also agree on the ids of each event they share, and use distinct application ids, since all
the host's processes run under one uid (launch-manager/README.md).
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
COMMAND = "de4sdv/driver_assistance/driving_command"

# The S-CORE host's manifests, by process.
HOST_MANIFESTS = {
    "vision_pilot": BENCH / "score-path" / "config" / "mw_com_config_vision_pilot.json",
    "actuation_adapter": BENCH / "actuation-adapter" / "mw_com_config_actuation_adapter.json",
    "gatewayd": BENCH / "score-path" / "config" / "mw_com_config_gatewayd_warning.json",
    "someipd": BENCH / "score-path" / "config" / "mw_com_config_someipd_warning.json",
}
# The p10-1/p10-3 test publisher of the warning request runs in the candidate's place (never beside it) and takes the
# candidate's global ASIL B, so that gatewayd (QM) receives from an ASIL B process as it will from the candidate. It
# names no ASIL B instance and not the command (ivi-warning/injector/README.md).
STAND_IN_FOR_THE_CANDIDATE = BENCH / "ivi-warning" / "injector" / "mw_com_config_warning_injector.json"


def manifests() -> list[Path]:
    out = []
    for path in sorted(BENCH.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("serviceInstances"), list):
            out.append(path)
    return out


def naming_the_command() -> list[Path]:
    return [p for p in manifests()
            if any(i.get("instanceSpecifier") == COMMAND
                   for i in json.loads(p.read_text(encoding="utf-8"))["serviceInstances"])]


def test_discovery_finds_the_provider_and_the_consumer() -> None:
    found = naming_the_command()
    assert found == sorted([HOST_MANIFESTS["vision_pilot"], HOST_MANIFESTS["actuation_adapter"]]), found


def test_the_command_is_asil_b_with_a_global_asil_b() -> None:
    for path in naming_the_command():
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = [i for i in data["serviceInstances"] if i["instanceSpecifier"] == COMMAND]
        assert len(entries) == 1, path
        levels = [instance["asil-level"] for instance in entries[0]["instances"]]
        assert levels == ["B"], (path, levels)
        assert data["global"]["asil-level"] == "B", path


def test_only_the_command_is_asil_b() -> None:
    """The warning request and the candidate record stay QM: the decision names the driving command only."""
    for path in manifests():
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["serviceInstances"]:
            for instance in entry["instances"]:
                if instance.get("asil-level") == "B":
                    assert entry["instanceSpecifier"] == COMMAND, (path, entry["instanceSpecifier"])
        if data.get("global", {}).get("asil-level") == "B":
            assert path in naming_the_command() or path == STAND_IN_FOR_THE_CANDIDATE, path


def test_the_stand_in_for_the_candidate_has_its_warning_instance_and_its_global_asil_b() -> None:
    stand_in = json.loads(STAND_IN_FOR_THE_CANDIDATE.read_text(encoding="utf-8"))
    candidate = json.loads(HOST_MANIFESTS["vision_pilot"].read_text(encoding="utf-8"))
    warning = "de4sdv/driver_assistance/warning_request"
    assert [e["instanceSpecifier"] for e in stand_in["serviceInstances"]] == [warning]
    assert stand_in["global"]["asil-level"] == candidate["global"]["asil-level"] == "B"
    assert _events(STAND_IN_FOR_THE_CANDIDATE)[warning] == _events(HOST_MANIFESTS["vision_pilot"])[warning]
    assert all(i["asil-level"] == "QM" for e in stand_in["serviceInstances"] for i in e["instances"])


def _events(path: Path) -> dict[str, tuple]:
    """Per instance specifier: (service type, service id, event ids, instance ids, slots, subscribers)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    types = {t["serviceTypeName"]: t for t in data["serviceTypes"]}
    out = {}
    for entry in data["serviceInstances"]:
        service = types[entry["serviceTypeName"]]
        binding = service["bindings"][0]
        out[entry["instanceSpecifier"]] = (
            entry["serviceTypeName"], binding["serviceId"],
            tuple(sorted((e["eventName"], e["eventId"]) for e in binding.get("events", []))),
            tuple(i["instanceId"] for i in entry["instances"]),
            tuple((e["eventName"], e.get("numberOfSampleSlots"), e.get("maxSubscribers"))
                  for i in entry["instances"] for e in i.get("events", [])),
        )
    return out


def test_the_host_manifests_agree_on_every_shared_event() -> None:
    by_process = {name: _events(path) for name, path in HOST_MANIFESTS.items()}
    shared = 0
    names = sorted(by_process)
    for a in names:
        for b in names:
            if a >= b:
                continue
            for specifier in set(by_process[a]) & set(by_process[b]):
                assert by_process[a][specifier] == by_process[b][specifier], (a, b, specifier)
                shared += 1
    # the command (candidate, adapter), the warning request (candidate, gatewayd), SomeipdService (gatewayd, someipd)
    assert shared == 3


def test_the_host_processes_have_distinct_application_ids() -> None:
    ids = {name: json.loads(path.read_text(encoding="utf-8"))["global"]["applicationID"]
           for name, path in HOST_MANIFESTS.items()}
    assert len(set(ids.values())) == len(ids), ids
