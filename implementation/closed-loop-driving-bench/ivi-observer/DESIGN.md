# Typed observation path: design (INC-DRIVING-001 slice 10b), option B

Status: **design + artifacts + local checks, nothing run on a VM.** The owner
chose the typed path for phase 8 on 2026-11-09 and timeboxed it to
2026-11-11 08:30 UTC. This directory holds what the runbook needs; no AOSP tree,
no guest VM and no S-CORE host was reachable from where it was written.

Authority: the model
(`textual-notation-of-model/packages/features/driving/closed_loop_driving_physical_software_realization.sysml`,
MAP-DRIVING-OPERATIONAL-STATE, GAP-DRIVING-006) and `interfaces/ICD.md` v2 sections
3 and 6. Where this design departs from either, the section says so.

Revision note: this design was first written as **option A** (S-CORE publishes
protobuf, the broker forwards it as bytes, the app decodes). The S1–S5 review
rejected that recommendation: the premise for
rejecting option B was false (the S-CORE publisher is this slice's own code, not a
running foreign slice), and MAP-DRIVING-OPERATIONAL-STATE says the interop maps the
events onto **one typed VSIDL message**. Option A is kept, unchanged, in
`fallback-a/` as the first fallback; it needs a model amendment and the owner's
word.

## 1. The chain, hop by hop

```
statePublisher (S-CORE host, mw::com event 7406, PreSerializedData<2048>)
  → gatewayd → someipd            SOME/IP service 0x4df0, instance 0x0001,
                                   events 0x8001/0x8002/0x8003, eventgroup 0x0001,
                                   TCP 30510, reliable, payload = the §3 struct
  → VXLAN segment                 S-CORE host address = SCORE_SOMEIP_PEER
  → SDV Core VM 192.168.98.3      SOME/IP stack (vsomeip 3.1.37.1, AOSP copy)
  → SOME/IP broker                message_translation_mode: REFLECTION,
                                   type_definition = 43-field SomeIpStruct
  → Data Tunnel topic             de4sdv-driving-operational-state,
                                   type de4sdv.driving.v1.DrivingOperationalState
  → SDV Gateway on IVI            cross-VM subscription (ACL on both sides)
  → IVI observer app              typed message → JSONL + screen
```

| Hop | Observation point | What proves it moved |
|---|---|---|
| publisher → someipd | `<run_dir>/score/statePublisher.jsonl`, gatewayd/someipd logcat | `out.operational_state` per event (ICD §2/§6) |
| someipd → guest, TCP 30510 | `tcpdump` on the SDV Core VM and on the host | SYN/subscribe, then event payloads; the first 4 bytes of the payload are `00 00 00 02` (schema_major = 2) if the struct starts at byte 0 |
| stack → broker → topic | broker logcat (`SomeIpBroker`), `sdv_authz` | the mapping loaded, the publication created, the topic named |
| broker → topic | the topic's content on the guest | typed fields, not bytes: a wrong `field_name` leaves its field at the default |
| topic → SDV Gateway → IVI | IVI `logcat` of the observer, the SDV Gateway's own log | subscription created; `ready` and receipts |
| observer | `<run_dir>/guest/observer.jsonl`, the screen, the recording | one record per receipt: the 43 fields, both clocks, the IVI receipt stamp |

Every hop has its own log, so a failure is localized by the first hop whose log
stops (§8).

## 2. Why one topic and three events

The ICD fixes three events that carry one message, told apart by `kind`. The
mapping sends all three to **one** topic parameter
(`de4sdv-driving-operational-state`), so the observer has one subscription, one
ACL pair and one loss counter instead of three of each. Ordering inside a kind is
the publisher's `sequence`; the interleaving across kinds carries no meaning and
is not used.

Fallback if vsidlc refuses three offered events on one topic parameter: three
topic parameters (keys 1/2/3) and three subscriptions in the app; the generator's
header names the edit, and it costs about 30 minutes on the VM.

## 3. The contract on the wire

Three artifacts, one table (`codec/icd_table.py`, copied by hand from ICD §3):

| Artifact | What it is | Held to the table by |
|---|---|---|
| `contract/de4sdv_driving_operational_state.proto` | the typed VSIDL message: proto3, 43 fields, numbers 1..43, `uint32`/`float`/`string`/`repeated float` | the contract test (name, number, type, order, no `bytes`, no enum) |
| `interop/someip_type_definition.textproto` | the `SomeIpStruct`: 43 `field` entries, `length_field_size: ZERO` | the same test, field by field |
| `interop/de4sdv_driving_operational_state.vsidl` | the mapping, **generated** from the two above | `gen_someip_vsidl.py --check` in the test and in `stage_sdv_core_interop.sh check` |

Encoding (ICD §3, AOSP "Write a SOME/IP type definition"): a struct in field
order, no struct length field, big-endian. `u32` is `UINT32`, `f32` is `FLOAT32`,
`str` is `someip_string { UTF_8, length_field_size: FOUR }` with the AUTOSAR body
(`EF BB BF` + UTF8 + `00`, the length covering all of it), `f32[]` is
`someip_array { length_field_size: FOUR, array_type { FLOAT32 } }` with the length
in **bytes**. The broker matches struct fields to protobuf fields **by name**
(REFLECTION), which is why the three artifacts share one list of names and one
order.

Sizes, from the codec (all under the S-CORE `PreSerializedData<2048>` bound):

| Kind | Struct | Frame (mw::com envelope + 4) |
|---|---|---|
| PLAN, 64 points, four arrays | 1301 B | 1305 B |
| VEHICLE_STATE | 218 B | 222 B |
| HEALTH | 234 B | 238 B |

Times are `_s`/`_ns` UINT32 pairs and `_ms` UINT32, so no 64-bit primitive is
needed. That was an ICD decision (O1's note) and it is also a hedge: the
documentation lists `UINT8/16/32, INT32, FLOAT32, BOOL` and nothing wider, and
`scripts/probe_aosp_tree.sh` greps the shipped enum to say whether `UINT64` exists
at all. If it does, nothing here changes.

### Why the three events carry one definition three times

A VSIDL mapping file has no aliasing: each `offered_event` needs its own
`type_definition`. The generator emits the same block three times, and the test
asserts the three blocks are byte-identical, so "one definition reused" is a
property the tooling guarantees and checks, not one the format can express.

## 4. The observer

One process, one subscriber, one screen. It publishes nothing, offers nothing and
calls nothing (REQ-DRIVING-018, -019).

- **Subscription** (`TypedStateSubscriber`): subject
  `org.de4sdv.drivingstate` / `DrivingStateObserver`, topic
  `de4sdv-driving-operational-state`, message
  `de4sdv.driving.v1.DrivingOperationalState`, parser = the generated class. The
  platform parses the protobuf; the app reads fields. **No bytes, no framing, no
  decode step.** Polls every 100 ms and on the gateway's data-available
  notification; reads up to 16 per batch; retries the connection every 5 s instead
  of dying (the bench reboots and restarts the gateway).
- **Contract checks** (`MessageMapper`): `schema_major == 2`, `kind in 1..3`,
  non-empty `producer`; and one diagnostic that protobuf cannot express — if every
  field of the message's kind is still at its default, the record and the screen
  say `all_defaults`, because the likeliest cause is a `field_name` that does not
  match the protobuf field name and the translation silently filled nothing.
- **Record** (`StateRecord`): one JSONL line per receipt, the ICD §6 envelope
  (`t_mono_ns`, `t_real_ns`, `host`, `component`, `event`, `seq`, `data`). `data`
  is the message, field for field, in ICD order and with ICD names, plus a
  sibling `clocks` object naming each time field's clock (C9) and two display-only
  names (`kind_name`, `mode_name`, `cause_name`). `t_real_ns` is the IVI's own
  receipt stamp at millisecond granularity (`System.currentTimeMillis() * 1e6`);
  the image's Java API has no nanosecond realtime read. No latency is computed in
  the app (ICD §6).
- **Screen** (`ObserverView`, `PlanPathView`): the two clocks side by side — *IVI
  real time at receipt* and *message publish real time* — then health (mode and
  cause with their names, when the stop began, its source), the vehicle state,
  the newest plan with its frame index and image capture time, and the plan's path
  (`plan_x`/`plan_y`, vehicle frame, x forward and y left, 10 m grid, ego at the
  origin). Stamps are formatted, never differenced.
- **Screen recording**: `screenrecord` on the guest, 40 s, pulled
  (`stage_ivi_observer.sh record`).

The app is pushed, not built into the IVI image (DESIGN §5 of the previous
revision still holds: the AEBS app proved Java gateway subscription on this image
family). If the pushed app cannot bind the gateway, SELinux is the cause and
`sepolicy/README.md` names the capture and the fix.

## 5. Proven, assumed, and what would refute it

| Claim | Status | Evidence / the check that settles it |
|---|---|---|
| The SOME/IP broker translates a `SomeIpStruct` in REFLECTION mode into a typed protobuf message, matching fields by name | **documented** | AOSP "Write a SOME/IP mapping file" (event example uses `message_translation_mode: REFLECTION`) and "Write a SOME/IP type definition" (field_name "must exactly match") |
| `SomeIpPrimitive` has `UINT32` and `FLOAT32`; a struct declares `length_field_size: ZERO` | **documented** | same page; `probe_aosp_tree.sh` §1 confirms on the shipped tree |
| The broker fills a **repeated** float field from a length-prefixed FLOAT32 array, and reads strings with the BOM/NUL convention | **assumed** | the page states the mapping table but not this code path; probe §3/§4/§5 prints the code; gate G5 catches an empty array or an all-default message, G6 the subtler string faults |
| The S-CORE encoder writes exactly this struct, BOM and byte-lengths included | **proven against vectors** | 16 frames from `state-publisher/tests/vectors/*.bin` (generated by that side's `tests/run_tests.sh`; not committed), decoded by `tests/decode_s1_vectors.py`: 688 field comparisons, no disagreement |
| The SOME/IP payload is the struct alone, not the mw::com frame with its 4-byte prefix | **assumed** | ICD §3 says so; the vectors carry the envelope (ICD §2), so gatewayd must drop it; gate G3 hexdumps the first event payload |
| A new protobuf type enters the SDV catalog through a `proto_library` in the catalog's `Android.bp`, and `vsidlc` resolves it for `broker.vsidl` | **assumed** | no offline tree; probe §6 prints the tree's own registration and module kinds; a wrong module kind is a build-time failure, not a silent one |
| A dotted message name in `broker.vsidl`'s `publisher` entry resolves across packages | **assumed** | the AEBS precedent used a same-package name; probe §6 prints whether any tree entry is dotted; the bare-name variant is a one-line change plus a rebuild |
| A Java app on this image subscribes through `google.sdv.gateway.client` and draws typed messages | **proven** | INC-AEBS-010 `GatewayFrameSubscriber` + `MainActivity`, runtime-verified (PF-004) |
| An app pushed into `/system/priv-app` may bind the SDV Gateway | **assumed** | the AEBS app was an image module; G5 (`initComms` + `avc: denied`) decides |
| The SDV Gateway hands the app the broker's protobuf message ready to parse | **assumed** | the Java client parses into the generated class; a parse failure surfaces as a read error at G5 |

## 6. Option A, kept as the first fallback

`fallback-a/` holds the rejected design unchanged: the carrier
`De4sdvDrivingOperationalStateFrame { bytes data = 1 }`, the `INTERPRET_AS_BYTES`
mapping, the `SlotFramer`, the bytes decoder and its test. It is the fallback **if
and only if** the probe finds the broker cannot reflect a repeated float or a
BOM-prefixed string, or a gate proves the translation does not happen.

Taking it needs a model amendment: the topic's type would be a bytes carrier, not
`DrivingOperationalState`, which is what MAP-DRIVING-OPERATIONAL-STATE states. That
is the owner's decision, not the implementer's, and the amendment is named in
`fallback-a/README.md`.

The second fallback stays as the review recorded it: the P4 path, as a deviation
from the no-relay rule.

## 7. Local validation (run these before spending VM time)

```bash
python3 codec/someip_struct.py selftest
uv run --with grpcio-tools python tests/test_contract_and_encoding.py
python3 tests/decode_s1_vectors.py
bash -n scripts/*.sh
```

Results of the last run are in §7.1; the test prints what it checked and fails on
drift rather than warning. It proves nothing about the runtime.

### 7.1 What was run, and what it returned

```
$ python3 codec/someip_struct.py selftest
PLAN            1301 B  consumed  1301  first bytes 00 00 00 02 00 00 00 00 ...  round trip ok
VEHICLE_STATE    218 B  consumed   218  first bytes 00 00 00 02 00 00 00 00 ...  round trip ok
HEALTH           234 B  consumed   234  first bytes 00 00 00 02 00 00 00 00 ...  round trip ok
CODEC SELFTEST PASSED

$ uv run --with grpcio-tools python tests/test_contract_and_encoding.py
contract: ok (43 fields, numbers 1..43, uint32/float/string/repeated float, no bytes)
someip struct: ok (43 fields x 3 events, identical, REFLECTION, no struct length, not stale)
codec: ok (big-endian, BOM in the length, arrays in bytes, 3 kinds 1301/218/234 B, malformed rejected)
agreement: ok (the codec and the protobuf message hold the same 43 values per kind)
artifacts agree: ok (mapping, bundle, ACLs, stack, the app, the record, the ICD)
ALL LOCAL CHECKS PASSED (contract + encoding; no AOSP, no runtime)

$ python3 tests/decode_s1_vectors.py | tail -1
VECTOR CHECK PASSED: 16 vector(s) decoded, 16 compared, 688 field comparisons
```

The vector check is the one cross-implementation number: the frames are the
S-CORE side's, the decoder is `codec/someip_struct.py`, written from the ICD table
and the type definition, and every one of the 43 fields agrees on all 16 frames. The
vectors are generated, not committed (`../state-publisher/tests/run_tests.sh`), so a
later session must regenerate them before quoting this number again; with the
directory absent the script says `NOT CHECKED` and exits 2, and this paragraph is
then the record of the run that did happen (2026-11-09, 10:46 UTC).
Two caveats, stated rather than glossed: `expected.json` was produced by the S-CORE
side's own decoder from the same frames, so this is decoder-to-decoder agreement
(their intent checks are in `tests/test_publisher_core.cpp`); and it says nothing
about the broker.

### 7.2 The scripts, against a synthetic tree

The AOSP tree is not here, so the scripts were exercised against a fixture that
mimics the layout they expect (`system/software_defined_vehicle/samples/some_ip/…`
with a `someip_types.proto`, a catalog `Android.bp`, an `agent/broker.vsidl`, a
`config/broker_apex/someip_acl.textproto` and a stack `vsomeip_config.json`). It
proves the scripts' quoting, insertion, backup and revert, not the AOSP layout:

```
$ AOSP_TOP=<fixture> ./scripts/probe_aosp_tree.sh | tail -2
7 checks, 0 blocker(s)

$ AOSP_TOP=<fixture> ./scripts/stage_sdv_core_interop.sh check
check: ok
$ AOSP_TOP=<fixture> SCORE_SOMEIP_PEER=10.0.0.9 ./scripts/stage_sdv_core_interop.sh stage
catalog module de4sdv_driving_operational_state_proto appended ...
appended the broker publish ACL
broker.vsidl publisher inserted: de4sdv.driving.v1.DrivingOperationalState
stack config rendered with SCORE_SOMEIP_PEER=10.0.0.9
$ AOSP_TOP=<fixture> ./scripts/stage_sdv_core_interop.sh revert
tree_identical_after_revert=yes
```

`bash -n scripts/*.sh` is clean. The Java has no compiler on this host; all seven
files were parsed with `javalang` (syntax only, no types) and the compiler is the
AOSP build at RUNBOOK step 8 — that is stated rather than implied by a green test.

## 8. Localizing a failure

| First hop without evidence | Likely cause | Check |
|---|---|---|
| someipd → guest | peer address, VXLAN, firewall, event ids | `tcpdump -i any port 30510` both ends; SD offers on 30490 |
| payload looks shifted | the mw::com 4-byte prefix was not dropped | the first 4 payload bytes are `00 00 00 02`; if they are a little-endian length, the struct starts at byte 4 and the mapping cannot be right |
| stack → broker | mapping not loaded, type not registered, stack config not applied | broker logcat, `vsidlc` output, the catalog's `Android.bp`, `vsomeip_config.json` in the image |
| broker → topic | ACL denies the publication, or the name does not match | broker logcat; the topic name in the ACL vs the parameterization |
| broker translates nothing | a `field_name` differs from the protobuf field, or REFLECTION cannot fill a repeated field | the record's `all_defaults` flag, empty strings where the S-CORE log has text, empty arrays where the log has 64 points |
| gateway → IVI | missing/duplicated ACL, SD agent restarted only at boot | `initComms`, `NOT_FOUND`, the ACL file list |
| values | the S-CORE side sends something else | compare all 43 fields with `statePublisher.jsonl` (G6) |

## 9. Effort

| Work | Nominal | Basis |
|---|---|---|
| this directory, offline (design, contract, generator, codec, tests, fallbacks) | 8 h | done |
| SDV Core: freeze, **probe**, stage, build, identity | 2.0 h | AEBS S1: 0.25 h prep + 1.5 h clean build; the probe is new, 0.25 h |
| two-VM launch, boot assertions | 0.5 h | AEBS S1: 1.0 h split here |
| core hop checks incl. the payload hexdump (G3) | 0.75 h | AEBS S1 smoke block |
| IVI: build app, ACLs, push, reboot, identity | 0.5 h | relay stage 0.5 h |
| clock (G4) | 0.25 h | AEBS S1 |
| observer bring-up to a decoded receipt (G5) | 1.0 h | no precedent; two reboot cycles budgeted |
| value checks, all 43 fields (G6) | 0.75 h | new: strings and arrays, not just numbers |
| screen recording, judged run, pull | 1.0 h | AEBS S2 0.5 h + pull 0.4 h |
| teardown and revert | 0.25 h | AEBS S3 0.4 h |
| **total on the VM** | **7.0 h** | **~10 h with contingency** |

Option B costs about 1.5 h more than A on the VM (the probe, the catalog
registration, the slower value check) and 2 h more offline (generator, codec,
cross-check). It does not change the two builds. The 2-day timebox holds with
**one** fallback inside it; it does not hold with two.

## 10. What this design does not claim

No runtime evidence of record. No case of record is closed. Nothing here says the
AAOS SDV reference stack, the SOME/IP broker or the SDV Gateway conforms to any
specification, and no safety or cybersecurity statement is made. The HMI stays an
informational display. The bench runs UNLOCKED; results do not carry over to
LOCKED.
