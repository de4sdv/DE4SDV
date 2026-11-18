"""The ids of the warning path are equal in every config that carries them.

LoLa, gatewayd and vsomeip connect by ids and names, so a swapped id passes each component's own
checks and fails only on the bench. This test reads every id from interfaces/service_ids.json and
holds each config of the path to it:

- score-path/config: gatewayd's SOME/IP gateway config, the mw::com manifests of gatewayd and
  someipd, and someipd's vsomeip config (the S-CORE host);
- ivi-warning/interop: the SDV Core stack config and the VSIDL mapping (the guests).

MAP-DRIVING-DA-WARNING-REQUEST: the publisher's mw::com event, gatewayd to someipd over the
gateway's IPC, SOME/IP over the VXLAN segment into the SOME/IP interop of SDV Core, the Data
Tunnel topic to the SDV Gateway on the IVI VM.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BENCH = Path(__file__).resolve().parents[2]
IDS = json.loads((BENCH / "interfaces" / "service_ids.json").read_text(encoding="utf-8"))
ICD = IDS["icd"]
LANE = IDS["lane_choices"]
SCORE = BENCH / "score-path" / "config"
GATEWAY = SCORE / "someip_gateway_config_warning.json"
GATEWAYD_MW_COM = SCORE / "mw_com_config_gatewayd_warning.json"
SOMEIPD_MW_COM = SCORE / "mw_com_config_someipd_warning.json"
SOMEIPD_VSOMEIP = SCORE / "vsomeip_someipd_warning.json"
GUEST_VSOMEIP = BENCH / "ivi-warning" / "interop" / "vsomeip_config.json"
MAPPING = BENCH / "ivi-warning" / "interop" / "de4sdv_driving_collision_warning_request.vsidl"
PEER_PLACEHOLDER = "__SCORE_SOMEIP_PEER__"

WARNING = next(e for e in ICD["mw_com_events"] if e["mapping"] == "MAP-DRIVING-DA-WARNING-REQUEST")
SOMEIP = ICD["someip_warning_request"]
SERVICE_ID = int(SOMEIP["service_id"], 16)
INSTANCE_ID = int(SOMEIP["instance_id"], 16)
EVENTGROUP = int(SOMEIP["eventgroup_id"], 16)
EVENT = int(SOMEIP["event_id"], 16)
SOMEIPD_SERVICE = "/score/someip/SomeipdService"
# gatewayd subscribes each event with someip::kMaxSampleCount = 10 samples (the INC-DRIVING-001
# kit's reading of the gateway at d9eac670); LoLa refuses a subscription above the slot count.
GATEWAYD_SUBSCRIBED_SAMPLES = 10
# Ids of the closed-loop driving bench that must not enter the warning path's S-CORE configs.
CLOSED_LOOP_IDS = ("7406", "19952", "0x4df0", "30510", "operational_state")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gateway_config_carries_the_warning_service_only() -> None:
    config = _json(GATEWAY)
    assert len(config["service_types"]) == 1
    service = config["service_types"][0]
    gateway = LANE["gateway"]
    assert service["service_id"] == SERVICE_ID
    assert service["service_type_name"] == gateway["service_type_name"]
    assert (service["service_version_major"], service["service_version_minor"]) == (
        gateway["service_version_major"], gateway["service_version_minor"])
    assert len(service["events"]) == 1
    event = service["events"][0]
    # gatewayd finds the mw::com event by this name.
    assert event["event_name"] == WARNING["event"]
    assert event["event_id"] == EVENT
    assert event["eventgroup_ids"] == [EVENTGROUP]
    assert event["serialization_config_type"] == gateway["serialization_config_type"] == "NullSerializerConfig"
    size = event["serialization_config"]["max_message_size"]
    assert size == gateway["max_message_size"]
    assert size >= ICD["warning_request_someip_payload"]["size"]
    assert LANE["mw_com_warning_request"]["sample_type"] == f"PreSerializedData<{size}>"
    assert service["local_service_instances"] == [
        {"instance_specifier": WARNING["instance_specifier"], "instance_id": INSTANCE_ID}]
    assert "remote_service_instances" not in service


def test_gatewayd_manifest_consumes_the_warning_event() -> None:
    manifest = _json(GATEWAYD_MW_COM)
    lane = LANE["mw_com_warning_request"]
    types = {t["serviceTypeName"]: t for t in manifest["serviceTypes"]}
    assert set(types) == {lane["service_type_name"], SOMEIPD_SERVICE}
    (binding,) = types[lane["service_type_name"]]["bindings"]
    assert binding["binding"] == lane["binding"]
    assert binding["serviceId"] == WARNING["service_id"]
    assert binding["events"] == [{"eventName": WARNING["event"], "eventId": lane["event_id"]}]

    instances = {i["instanceSpecifier"]: i for i in manifest["serviceInstances"]}
    assert set(instances) == {WARNING["instance_specifier"], "someipd/daemon"}
    warning = instances[WARNING["instance_specifier"]]
    assert warning["serviceTypeName"] == lane["service_type_name"]
    (instance,) = warning["instances"]
    assert instance["instanceId"] == lane["instance_id"]
    assert instance["binding"] == lane["binding"]
    (event,) = instance["events"]
    assert event["eventName"] == WARNING["event"]
    assert event["numberOfSampleSlots"] == lane["number_of_sample_slots"] >= GATEWAYD_SUBSCRIBED_SAMPLES
    assert event["maxSubscribers"] == lane["max_subscribers"]
    assert manifest["global"]["applicationID"] == LANE["gateway"]["gatewayd_application_id"]


def test_someipd_manifest_and_the_daemon_link_agree() -> None:
    gatewayd = _json(GATEWAYD_MW_COM)
    someipd = _json(SOMEIPD_MW_COM)
    assert [t["serviceTypeName"] for t in someipd["serviceTypes"]] == [SOMEIPD_SERVICE]
    # The gateway's own IPC between the daemons: the same deployment in both copies.
    for key, name in (("serviceTypes", "serviceTypeName"), ("serviceInstances", "serviceTypeName")):
        mine = [e for e in gatewayd[key] if e[name] == SOMEIPD_SERVICE]
        assert mine == someipd[key]
    assert someipd["global"]["applicationID"] == LANE["gateway"]["someipd_application_id"]
    assert gatewayd["global"]["applicationID"] != someipd["global"]["applicationID"]


def test_someipd_vsomeip_offers_the_warning_service_at_the_score_address() -> None:
    config = _json(SOMEIPD_VSOMEIP)
    vsomeip = LANE["someipd_vsomeip"]
    assert config["unicast"] == vsomeip["unicast"] == "192.168.98.1"  # the model: the S-CORE host's address
    assert config["netmask"] == vsomeip["netmask"]
    assert config["network"] == vsomeip["network"]
    assert config["applications"] == [vsomeip["application"]]
    assert config["routing"] == vsomeip["application"]["name"]
    (service,) = config["services"]
    assert int(service["service"], 16) == SERVICE_ID
    assert int(service["instance"], 16) == INSTANCE_ID
    assert int(service["reliable"]) == SOMEIP["port"]
    assert "unreliable" not in service
    assert service["events"] == [{"event": SOMEIP["event_id"], "is_field": "false", "is_reliable": "true"}]
    assert service["eventgroups"] == [{"eventgroup": SOMEIP["eventgroup_id"], "events": [SOMEIP["event_id"]]}]


def test_sdv_core_stack_config_consumes_the_warning_service_from_the_score_side() -> None:
    config = _json(GUEST_VSOMEIP)
    services = {int(s["service"], 16): s for s in config["services"]}
    service = services[SERVICE_ID]
    assert int(service["instance"], 16) == INSTANCE_ID
    assert service["unicast"] == PEER_PLACEHOLDER  # rendered at staging with SCORE_SOMEIP_PEER
    assert int(service["reliable"]["port"]) == SOMEIP["port"]
    assert service["events"] == [{"event": SOMEIP["event_id"], "is_field": "false", "is_reliable": "true"}]
    assert service["eventgroups"] == [{"eventgroup": SOMEIP["eventgroup_id"], "events": [SOMEIP["event_id"]]}]
    assert {"service": SOMEIP["service_id"], "instance": SOMEIP["instance_id"]} in config["secure-services"]
    port = str(SOMEIP["port"])
    assert {"address": PEER_PLACEHOLDER,
            "reliable": [{"first": port, "last": port, "type": "secure"}]} in config["acceptances"]
    for kept in ICD["someip_kept"]:
        assert int(services[int(kept["service_id"], 16)]["reliable"]["port"]) == kept["port"]
    # Both ends of the SOME/IP link run service discovery on the same group and port.
    someipd = _json(SOMEIPD_VSOMEIP)["service-discovery"]
    guest = config["service-discovery"]
    for key in ("enable", "multicast", "port", "protocol"):
        assert guest[key] == someipd[key], key


def test_vsidl_mapping_carries_the_ids() -> None:
    mapping = MAPPING.read_text(encoding="utf-8")
    assert re.findall(r"someip_service_id: (0x[0-9a-f]{4})", mapping) == [SOMEIP["service_id"]]
    assert re.findall(r"instance_id: (0x[0-9a-f]{4})", mapping) == [SOMEIP["instance_id"]]
    assert re.findall(r"group_id: (0x[0-9a-f]{4})", mapping) == [SOMEIP["eventgroup_id"]]
    assert re.findall(r"event_id: (0x[0-9a-f]{4})", mapping) == [SOMEIP["event_id"]]


def test_no_closed_loop_driving_service_in_the_score_configs() -> None:
    for path in (GATEWAY, GATEWAYD_MW_COM, SOMEIPD_MW_COM, SOMEIPD_VSOMEIP):
        text = path.read_text(encoding="utf-8")
        for token in CLOSED_LOOP_IDS:
            assert re.search(rf"\b{re.escape(token)}\b", text) is None, f"{path.name} names {token}"
