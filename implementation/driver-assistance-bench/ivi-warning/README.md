# Warning request on the guests (INC-DRIVING-002)

Status: draft, not yet validated. Nothing in this folder has run on a guest or on the bench yet.

## The problem

The candidate's planner decides that the driver should be warned of a collision. That decision has to
reach an app on the AAOS SDV IVI VM, which shows the warning and starts a sound. The bench allots 0.1 s
of wall-clock time to the path, from the publisher's send to the app's receipt (REQ-DRIVING-042;
MAP-DRIVING-DA-WARNING-REQUEST). The path crosses three processes on the S-CORE host, a VXLAN segment
and two VMs. Each crossing is configured by ids and names in a different file, and one wrong id
anywhere fails silently.

This folder holds the guests' contract of the warning request and the files that carry it from
SOME/IP to the Data Tunnel. The S-CORE host's files are in [`../score-path/config/`](../score-path/config/).
Every id comes from [`../interfaces/service_ids.json`](../interfaces/service_ids.json), the
machine-readable copy of [`../interfaces/ICD.md`](../interfaces/ICD.md), and the tests hold each
file to it.

## The path, hop by hop

The hops are those of the model's mapping MAP-DRIVING-DA-WARNING-REQUEST and its connections in
`driver_assistance_physical_software_realization.sysml`.

| # | Hop | Model element | Config file | Ids |
|---|---|---|---|---|
| 1 | Publisher | `SCOREWarningRequestPublisher.warningRequestOut` | the candidate's mw::com manifest (another lane); bytes from `EncodeWarningRequestSomeip` in [`payloads.h`](../interfaces/include/de4sdv/driver_assistance/payloads.h) | event `warning_request`, 8 bytes, big-endian, no prefix |
| 2 | mw::com (LoLa, shared memory) | `warningRequestOverSCORECommunication` | [`mw_com_config_gatewayd_warning.json`](../score-path/config/mw_com_config_gatewayd_warning.json) | `de4sdv/driver_assistance/warning_request`, service id 7412 |
| 3 | gatewayd to someipd (the gateway's IPC) | `warningRequestOverGatewayIPC` | [`someip_gateway_config_warning.json`](../score-path/config/someip_gateway_config_warning.json), [`mw_com_config_someipd_warning.json`](../score-path/config/mw_com_config_someipd_warning.json) | gateway service 0x4df1, event 0x8001, eventgroup 1 |
| 4 | SOME/IP over the VXLAN segment | `warningRequestOverSOMEIPAcrossVXLANSegment` | [`vsomeip_someipd_warning.json`](../score-path/config/vsomeip_someipd_warning.json) | 0x4df1/0x0001, reliable TCP 30511, offered at 192.168.98.1 |
| 5 | SDV Core interop (vsomeip stack and SOME/IP broker) | `DriverAssistanceSDVCoreGuest.someIpIn`, `warningRequestTopicPublishedByBroker` | [`interop/vsomeip_config.json`](interop/vsomeip_config.json), [`interop/someip_type_definition.textproto`](interop/someip_type_definition.textproto), [`interop/de4sdv_driving_collision_warning_request.vsidl`](interop/de4sdv_driving_collision_warning_request.vsidl), [`interop/de4sdv_driving_collision_warning_request_bundle.vsidl`](interop/de4sdv_driving_collision_warning_request_bundle.vsidl), [`interop/broker_acl_append.textproto`](interop/broker_acl_append.textproto) | REFLECTION into `de4sdv.driving.v1.CollisionWarningRequest` |
| 6 | Data Tunnel, SDV Core VM to IVI VM | `warningRequestTopicOverDataTunnelAcrossVMs` | [`contract/de4sdv_driving_collision_warning_request.proto`](contract/de4sdv_driving_collision_warning_request.proto), [`interop/acl/ivi_broker_object_policy.textproto`](interop/acl/ivi_broker_object_policy.textproto) | unit `de4sdv-driving-warning-request` |
| 7 | SDV Gateway on the IVI VM | `warningRequestThroughSDVGateway` | [`interop/acl/ivi_warning_subscriber.textproto`](interop/acl/ivi_warning_subscriber.textproto) | subject `org.de4sdv.collisionwarning` / `CollisionWarningPresentation` |
| 8 | App | `CollisionWarningPresentationApplication.warningRequestIn` | the IVI app (B10, not in this folder) | subscribes to the unit by name |

The values stay the same on every hop: `requested` is 0 or 1 and `issue_time_sim_ms` is the capture
simulation time in whole milliseconds. The broker fills the protobuf fields by name, so the field
names of the struct and of the message are the same.

## What is in this folder

- `contract/`: the typed Data Tunnel message, a VSIDL publication. The model types `requested` by
  `Vehicle_ADAS_AEBS_DriverWarning_IsActive`, a boolean; the ICD carries it as UINT32 0 or 1.
- `interop/`: the files of hops 5 to 7. The mapping is generated:
  `python3 scripts/gen_someip_vsidl.py` (write) or `--check` (stale check). The stack config holds
  0x4dee and 0x4df0 exactly as the closed-loop driving bench's
  [`vsomeip_config.json`](../../closed-loop-driving-bench/ivi-observer/interop/vsomeip_config.json)
  does, with 0x4df1 added; its provider is `__SCORE_SOMEIP_PEER__` until staging renders it.
- `scripts/stage_sdv_core_interop.sh`: `check`, `render <file>`, `stage`, `validate` (the catalog
  build G1b and a decode of the generated SOME/IP config) and `revert`. It needs `AOSP_TOP` and
  `SCORE_SOMEIP_PEER`, the S-CORE host's address on the segment (192.168.98.1 in the model). The
  render refuses a stack config without 0x4dee, 0x4df0 and 0x4df1, and any change to a service the
  tree already carries. It builds no image.
- `scripts/decode_warning_payload.py --hex <payload>`: decodes a SOME/IP payload by the type
  definition and refuses leftover bytes, such as a 4-byte prefix in front of the struct.

## In the guest rebuild

The staging fits the incremental guest build (B12) of `phase10/aaos-build/` as a step after S6
(INC-MW-011) and S7 (INC-DRIVING-001):

```bash
SCORE_SOMEIP_PEER=192.168.98.1 AOSP_TOP=~/aosp ivi-warning/scripts/stage_sdv_core_interop.sh validate
```

Two traps for that recipe:

- `build_guests.sh core` runs the closed-loop bench's `stage_sdv_core_interop.sh build`, which
  stages S7 again and writes its own stack config with 0x4dee and 0x4df0 only. Run on a scratch copy
  of the INC-DRIVING-001 tree's files, that dropped 0x4df1. Stage this folder after it and build the
  image with a plain `m`, or re-stage this folder and rebuild.
- `stage_overlays.sh --gates` compares `broker.vsidl`, `someip_acl.textproto` and the stack config
  with the INC-DRIVING-001 digests. After this staging they differ by design; the gate needs the new
  digests.

The IVI broker object policy is installed at the same path as the earlier increments' policies. If
another increment's subscriber must work on the same IVI VM, merge the blocks into one file.

## Tests

`tests/` runs in the `driver-assistance-bench (INC-DRIVING-002)` suite of
`tools/run_bench_unit_tests.py`:

- `test_warning_path_ids.py`: the ids are equal in `service_ids.json`, the gateway config, the
  mw::com manifests, someipd's vsomeip config, the SDV Core stack config and the mapping;
- `test_warning_contract.py`: the message's field names and numbers equal the type definition and
  the ICD; the mapping is not stale; the ACLs name the same message, unit and subject;
- `test_warning_golden_bytes.py`: a C++ program built against `payloads.h` prints the encoder's
  bytes for six vectors; the guest's type definition decodes them to the values computed in Python
  with `decimal` and `struct`; a prefixed payload is refused;
- `test_warning_staging.py`: the render keeps 0x4dee and 0x4df0; stage and revert on a synthetic tree.

## What the local tests cannot show

These need the phase 10 probe of the guests, and for hops 1 and 2 the probe of the S-CORE path:

- that the candidate's manifest and gatewayd's agree at run time, and that gatewayd subscribes to the
  event (the probe of the S-CORE path);
- that the first bytes of each SOME/IP payload on the VXLAN segment are `00 00 00 0x`, the struct
  itself, with no prefix;
- the ACLs on the real guests: the broker publishes the unit with no `someip_broker_agent` error, the
  IVI SD agent loads the subject grant and the object policy, and whether the guests ran enforcing
  or permissive;
- the timing: 0.1 s from the publisher's send to the app's receipt, measured across the S-CORE
  host's clock and the IVI VM's free-running clock with a stated bound;
- the app: its receipt, the first displayed frame with the warning and the start of the sound.
