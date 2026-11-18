# S-CORE path config of the warning request (INC-DRIVING-002)

Status: draft, not yet validated. None of these files has run on the S-CORE host yet.

## The problem

The candidate publishes its warning request on an mw::com event. gatewayd must find that event,
hand it to someipd, and someipd must offer it on SOME/IP to the SDV Core VM on the VXLAN segment
(MAP-DRIVING-DA-WARNING-REQUEST). LoLa, gatewayd and vsomeip connect by ids and names, so each file
here has to agree with the candidate's manifest and with the guest's stack config.

These files are taken from the INC-DRIVING-001 kit's driving configs, with the warning's ids from
[`../../interfaces/service_ids.json`](../../interfaces/service_ids.json). No INC-DRIVING-001 service
is in them.

| File | Read by | Content |
|---|---|---|
| [`someip_gateway_config_warning.json`](someip_gateway_config_warning.json) | gatewayd (`-c`, as the compiled `.bin`) | service type 0x4df1, event `warning_request` 0x8001 in eventgroup 1, null serializer of 2048 bytes, local instance `de4sdv/driver_assistance/warning_request` |
| [`gateway_overlay.BUILD.bazel`](gateway_overlay.BUILD.bazel) | Bazel, as `BUILD.bazel` of an overlay package in the gateway workspace | compiles the gateway config to `someip_gateway_config_warning.bin` |
| [`mw_com_config_gatewayd_warning.json`](mw_com_config_gatewayd_warning.json) | gatewayd (`-s`) | service id 7412 on SHM, event id 1, 20 slots, one subscriber; SomeipdService 6400; application id 3410 |
| [`mw_com_config_someipd_warning.json`](mw_com_config_someipd_warning.json) | someipd (`-s`) | SomeipdService 6400; application id 3411 |
| [`vsomeip_someipd_warning.json`](vsomeip_someipd_warning.json) | someipd (`VSOMEIP_CONFIGURATION`) | 0x4df1/0x0001 on reliable TCP 30511 at 192.168.98.1 (the model's S-CORE address), SD on 224.0.0.0:30490 |

## What the other lanes must match

- The candidate's mw::com manifest: service type `/de4sdv/driver_assistance/WarningRequest`, service
  id 7412, event `warning_request` with id 1, instance 1, 20 slots, one subscriber, and the sample
  type `PreSerializedData<2048>` with `size` = 8 and the bytes of `EncodeWarningRequestSomeip`.
  gatewayd copies `data[0..size)` unread, so nothing may stand in front of the struct.
- The Launch Manager config: application ids 3410 and 3411 must not be used by another process on
  the host.

These values are in the `lane_choices` section of `service_ids.json`. ICD.md does not fix them.

The hop-by-hop path and what the bench must still show are in
[`../../ivi-warning/README.md`](../../ivi-warning/README.md).
