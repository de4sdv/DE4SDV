# Driver-assistance bench: interface control (INC-DRIVING-002)

Status: draft, not yet validated. No message below has run on the bench yet.

The SysML model is the authority. These are the signal mappings of
`textual-notation-of-model/packages/features/driving/driver_assistance_physical_software_realization.sysml`
that the bench implements. Where the model leaves a value open, this document gives the bench's
**proposal**. Proposals are fixed for implementation, but none is model content until the phase 10b pull
request types it.

## mw::com events (S-CORE host)

| Mapping | Event | Instance specifier | Service id | Payload | Status |
|---|---|---|---|---|---|
| MAP-DRIVING-DA-COMMAND | `driving_command` | `de4sdv/driver_assistance/driving_command` | 7411 | `DrivingCommandEventPayload` (24 bytes) | fields: model; ids and layout: proposal |
| MAP-DRIVING-DA-WARNING-REQUEST | `warning_request` | `de4sdv/driver_assistance/warning_request` | 7412 | the 8 SOME/IP bytes below, as they are | fields: model; ids and bytes: proposal |
| MAP-DRIVING-DA-CANDIDATE-RECORD | `candidate_record` | `de4sdv/driver_assistance/candidate_record` | 7413 | `CandidateRecordEventPayload` (368 bytes), re-published every 1 s for the whole run | fields: model; event form: proposal |

The headers are in `include/de4sdv/driver_assistance/payloads.h`. Service ids 7401 to 7406 belong to the
closed-loop driving bench.

### Driving command

The fields come from the model:

- `acceleration`: float, m/s², negative decelerates.
- `steeringAngle`: float, degrees, positive to the left. It is `-steering[1] * 180 / pi`.
- `issueTime`: double, simulation seconds. It is the capture time of the frame the command was computed
  from.
- `sequenceCount`: uint32, counting from 1 in each run.
- `checkValue`: uint32.

The candidate sends no command before the candidate record has arrived.

The check value is a proposal. It is the CRC32 of IEEE 802.3 (zlib's `crc32`) over the little-endian bytes of
`acceleration`, `steeringAngle`, `issueTime` and `sequenceCount`, in this order, 20 bytes in all. The model
says only that the check value is a 32-bit CRC over the other fields.

### Warning request

The fields come from the model:

- `requested`: true when the plan's warnings hold FCW or AEB.
- `issueTime`: the capture simulation time of the frame the plan was computed from.

There is one event per plan. A request starts with the first true event after a false one.

The bytes are a proposal: big-endian, with no length field.

| Offset | Field | Type |
|---|---|---|
| 0 | `requested` | UINT32, 0 or 1 |
| 4 | `issue_time_sim_ms` | UINT32, the issue time rounded to whole milliseconds |

The 0.05 s step makes every issue time a whole number of milliseconds. The candidate's mw::com event carries
these 8 bytes with no prefix, and gatewayd copies them unread.

## SOME/IP and the AAOS SDV (proposal)

| Item | Value |
|---|---|
| Service, instance | 0x4df1, 0x0001 |
| Eventgroup, event | 0x0001, 0x8001 |
| Transport | reliable, TCP 30511 |
| Data Tunnel message | `de4sdv.driving.v1.CollisionWarningRequest { uint32 requested = 1; uint32 issue_time_sim_ms = 2; }` |
| Service unit | `de4sdv-driving-warning-request` |

0x4dee on TCP 30509 and 0x4df0 on TCP 30510 belong to the closed-loop driving bench and stay as they are.

## Timing (model)

REQ-DRIVING-042 allots 0.2 s of wall-clock time from the request to each mode of the warning:

- 0.1 s for the path, from the publisher's send to the receipt by the warning presentation on the IVI VM;
- 0.1 s for the presentation, from the receipt to the first displayed frame with the warning and to the start
  of the sound.

The actuation adapter rejects a command whose issue time is more than 0.1 s of simulation time older than the
newest world time. It also rejects a command it detects as lost, repeated or corrupted, and applies nothing in
its place.
