# Typed observation path: design (INC-DRIVING-001 slice 10b), option B

Status: **built and run on the bench, on a permissive IVI guest.** The owner
chose the typed path for phase 8 on 2026-11-09. The design was first written
before any run (no AOSP tree, no guest VM and no S-CORE host was reachable from
where it was written) and revised with what the bring-up found. The path then
ran in six recorded runs of 2026-11-10 (`RUNBOOK.md`, `RISKS.md`); section 5
says which of its assumptions those runs settled. No run was made under
enforcing (`sepolicy/README.md`).

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
  → Data Tunnel service units     de4sdv-driving-operational-state-plan (0x8001),
                                   -vehicle-state (0x8002), -health (0x8003),
                                   one type de4sdv.driving.v1.DrivingOperationalState
  → SDV Gateway on IVI            cross-VM subscription (ACL on both sides)
  → IVI observer app              typed message → JSONL + screen
```

| Hop | Observation point | What proves it moved |
|---|---|---|
| publisher → someipd | `<run_dir>/score/statePublisher.jsonl`, gatewayd/someipd logcat | `out.operational_state` per event (ICD §2/§6) |
| someipd → guest, TCP 30510 | `tcpdump` on the SDV Core VM and on the host | SYN/subscribe, then event payloads; the first 4 bytes of the payload are `00 00 00 02` (schema_major = 2) if the struct starts at byte 0 |
| stack → broker → units | broker logcat (`someip_broker_agent`), `sdv_authz` | the mapping loaded, one publisher created per unit |
| broker → units | the units' content on the guest | typed fields, not bytes: a wrong `field_name` leaves its field at the default |
| units → SDV Gateway → IVI | IVI `logcat` of the observer, the SDV Gateway's own log | three subscriptions created; `ready` and receipts of all three kinds |
| observer | `<run_dir>/guest/observer.jsonl`, the screen, the recording | one record per receipt: the 43 fields, both clocks, the IVI receipt stamp |

Every hop has its own log, so a failure is localized by the first hop whose log
stops (§8).

## 2. Why three service units of one type

The ICD fixes three events that carry one message, told apart by `kind`. The
mapping gives each event its own `instance_impl` and its own service unit, all of
the one type `de4sdv.driving.v1.DrivingOperationalState`:

| Event | Mapping key | Service unit |
|---|---|---|
| 0x8001 plan | 0 | `de4sdv-driving-operational-state-plan` |
| 0x8002 vehicle_state | 1 | `de4sdv-driving-operational-state-vehicle-state` |
| 0x8003 health | 2 | `de4sdv-driving-operational-state-health` |

Why not one unit: an `instance_impl` holds one interface (`interface_type` is a
oneof in the platform's SOME/IP mapping proto), the broker creates one SDV publisher
per offered event, and the publication model of the type is `SINGLE_PUB`, under
which each channel has one publisher. One unit fed by three broker publishers would
contradict that; three units of one type follow it. The model allows it:
MAP-DRIVING-OPERATIONAL-STATE maps the three events onto one VSIDL message and
leaves the split into topics to this contract. The one-unit form is kept in
`interop/variants/` for an owner decision only, with no IVI side.

The observer has one gateway client (the JNI keeps one per process), three
subscriptions by name on it, one ACL pair that names the three units, and one
merged state. Ordering inside a kind is the publisher's `sequence`, one per unit;
the interleaving across kinds carries no meaning and is not used.

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

| Kind | Struct (the SOME/IP payload) | Library frame (+4, the vectors; not sent) |
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
  `org.de4sdv.drivingstate` / `DrivingStateObserver`, the three units
  `de4sdv-driving-operational-state-plan`, `-vehicle-state` and `-health`, message
  `de4sdv.driving.v1.DrivingOperationalState`, parser = the generated class
  (`DrivingOperationalState.parser()`, varint-delimited, as the platform's own
  `Subscriber` parses). The broker translated the struct; the app reads fields. **No
  bytes field, no framing of our own, no SOME/IP decode step.** Each unit is found
  **by name** (`com.android.sdv.someip` / `SomeIpBroker` / the unit name, any VM), as
  the proven native relay and the platform's SOME/IP sample do, not by unit type; a
  by-name address is (VM, package, bundle, unit) and carries no message name. All
  three subscriptions live on one client and feed one state; a receipt whose `kind`
  is not its unit's is kept and also reported as an error (a crossed unit key in the
  mapping). The link is `SUBSCRIBED` only when all three units are. Polls every
  100 ms and on the
  gateway's data-available notification; reads up to 16 per batch; `DATA_LOSS` is
  counted, not a reconnect; every gateway failure is shown with its status; retries
  every 5 s after closing the client (the JNI keeps one client per process).
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
- **Screen** (`ObserverView`, drawing only; content in `ScreenModel`, layout in
  `ScreenLayout`, projection in `PlanGeometry`, plan numbers in `PlanKinematics`, all
  Android-free and pinned by JVM tests): the plan's path (`plan_x`/`plan_y`, vehicle
  frame, x forward up and y left left, one scale for both axes, a metric grid whose
  spacing is printed, ego at the origin, larger dots at whole seconds); mode and cause
  (the only colour authority, always with text); speed in m/s and km/h and the plan's
  speed at +1 s, +3 s and the horizon (the plan's acceleration integrated from the
  current speed, labelled as such); the plan's frame, sample count, +1 s point and
  first-second mean curvature (a number, no steering word); IVI real time now and the
  newest message's publish real time; identity and counters; one provenance line.
  The receipt lag and the plan age are shown as **display-only** differences of two
  clocks (IVI vs S-CORE real time), labelled so; the record stays stamps only (ICD §6,
  no computed latencies). STALE after 1.0 s without a receipt greys the state and
  clears the path. The layout is one 1080 x 600 reference; `ScreenLayout.place`
  scales and centres it inside the part of the view the system bars leave free (the
  IVI's window is edge to edge, so the bars otherwise cover the header and the
  footer). A start with `--ez immersive true` asks for hidden bars; with zero insets
  the reference fills the display 1:1.
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
| The broker fills a **repeated** float field from a length-prefixed FLOAT32 array, and reads strings with the BOM/NUL convention | **shown in the recorded runs** | the page states the mapping table but not this code path; probe §3/§4/§5 prints the code; gate G5 catches an empty array or an all-default message, G6 the subtler string faults. Settled by G6: in the two closed-loop runs every field the app received, arrays and strings included, equals the publisher's |
| The S-CORE encoder writes exactly this struct, BOM and byte-lengths included | **proven against vectors** | 16 frames in `state-publisher/tests/vectors/*.bin` (committed; that side's `tests/run_tests.sh` regenerates them byte-identically), decoded by `tests/decode_s1_vectors.py`: 688 field comparisons, no disagreement |
| The SOME/IP payload is the struct alone, not the library frame with its 4-byte prefix | **shown in the recorded runs** | gatewayd copies `data[0..size)` of the sample onto the payload unread, so the publisher shell sends the frame from byte 4 with `size` = the message length (ICD §2, A33); gate G3 hexdumps the first event payload (`00 00 00 02`). On the wire the event payloads start with `00 00 00 02`, and the broker decoded them |
| A new protobuf type enters the SDV catalog as plain files in a subdirectory the catalog's `Android.bp` globs (`**/*.proto`, `**/*.vsidl`), carries the pdk29 publication annotations, and `vsidlc` resolves it for `broker.vsidl` | **checked at G1b** | probe §6 prints the globs; `stage_sdv_core_interop.sh validate` builds the catalog modules and decodes the generated `someip-config.binpb` before the image build |
| The runtime accepts three service units of one `SINGLE_PUB` type, one broker publisher each | **shown in the recorded runs** | the language and mapping rules allow it; the runtime rule is in `sdv_comms`, not in the AOSP source read here; the broker's start log and the app's three `subscribed unit=` lines decide (RISKS R4). The app subscribed to all three units in all six runs |
| A dotted message name in `broker.vsidl`'s `publisher` entry resolves across packages | **assumed** | the AEBS precedent used a same-package name; probe §6 prints whether any tree entry is dotted; the bare-name variant is a one-line change plus a rebuild |
| A Java app on this image subscribes through `google.sdv.gateway.client` and draws typed messages | **proven** | INC-AEBS-010 `GatewayFrameSubscriber` + `MainActivity`, runtime-verified (PF-004) |
| An app pushed into `/vendor/priv-app` may bind the SDV Gateway | **shown on a permissive guest only** | the AEBS app was an image module in the same partition with the same module shape; G5 (`initComms` + `avc: denied`) decides. The app bound the gateway in all six runs, each on a permissive guest; under enforcing this is open (`sepolicy/README.md`, RISKS R5) |
| The SDV Gateway hands the app the broker's protobuf message ready to parse | **shown in the recorded runs** | the Java client parses into the generated class; a parse failure surfaces as a read error at G5. The app received and parsed the messages in all six runs; in the two closed-loop runs every receipt equals the publisher's record (G6) |

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
(cd ../state-publisher && tests/run_tests.sh)      # regenerates the vectors byte-identically
python3 tests/decode_s1_vectors.py
uv run --with grpcio-tools python tests/test_contract_and_encoding.py
python3 scripts/gen_someip_vsidl.py --check
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

$ VSIDL_PROTO_ROOT=<tree>/vsidl/language/src/protos python tests/test_contract_and_encoding.py
contract: compiled as is, with sdv/vsidl/v1/annotations.proto from <tree>/vsidl/language/src/protos
contract: ok (43 fields, numbers 1..43, uint32/float/string/repeated float, no bytes)
annotations: ok (SINGLE_PUB, message_count 32, 8 strings with a max size, 4 repeated fields with a max count; as text and through the descriptor)
someip struct: ok (43 fields x 3 events, identical, REFLECTION, no struct length, one instance_impl and one unit per event, not stale)
codec: ok (big-endian, BOM in the length, arrays in bytes, 3 kinds 1301/218/234 B, malformed rejected)
agreement: ok (the codec and the protobuf message hold the same 43 values per kind)
artifacts agree: ok (mapping, bundle, ACLs, stack, the app, the record, the ICD; three units)
ALL LOCAL CHECKS PASSED (contract + encoding; no AOSP, no runtime)

$ python3 tests/decode_s1_vectors.py | tail -1
VECTOR CHECK PASSED: 16 vector(s) decoded, 16 compared, 688 field comparisons
```

The vector check is the one cross-implementation number: the frames are the
S-CORE side's, the decoder is `codec/someip_struct.py`, written from the ICD table
and the type definition, and every one of the 43 fields agrees on all 16 frames. The
vectors are committed, and `../state-publisher/tests/run_tests.sh` regenerated all
18 vector files byte-identically on 2026-11-10; with the directory absent the script
says `NOT CHECKED` and exits 2. The same 16 frames, taken from byte 4 as the
publisher shell sends them, also pass a re-implementation of the broker's REFLECTION
rules for this type (688 field comparisons, no disagreement; with the 4-byte prefix
left on, every frame fails as the broker would, `Unknown BOM for string`).
Two caveats, stated rather than glossed: `expected.json` was produced by the S-CORE
side's own decoder from the same frames, so this is decoder-to-decoder agreement
(their intent checks are in `tests/test_publisher_core.cpp`); and it says nothing
about the broker.

### 7.2 The scripts, against a copy of the pulled AOSP subset

The full AOSP tree is not here. The scripts' AOSP-free modes ran against a copy of
the pulled `system/software_defined_vehicle` subset (never the subset itself), on
2026-11-10. It proves the scripts' checks, insertion, rendering, backup and revert
on the real layout, not a build:

```
$ AOSP_TOP=<copy> ./scripts/probe_aosp_tree.sh | tail -1
7 checks, 0 blocker(s)
$ AOSP_TOP=<copy> ./scripts/stage_sdv_core_interop.sh check
check: ok (variant: three, units: de4sdv-driving-operational-state-plan de4sdv-driving-operational-state-vehicle-state de4sdv-driving-operational-state-health)
$ AOSP_TOP=<copy> ./scripts/stage_sdv_core_interop.sh stage          # no SCORE_SOMEIP_PEER
ERROR: export SCORE_SOMEIP_PEER (the S-CORE host's VXLAN address, RUNBOOK step 4); nothing staged
$ AOSP_TOP=<copy> SCORE_SOMEIP_PEER=192.168.98.1 ./scripts/stage_sdv_core_interop.sh stage
appended the broker publish ACL (three unit variant)
broker.vsidl publisher inserted: de4sdv.driving.v1.DrivingOperationalState
stack config rendered: services ['0x4dee', '0x4df0'], 0x4df0 provider 192.168.98.1
(a second run: "already present" for each unit and the publisher; one acceptance
entry for 192.168.98.1 with ports 30509 and 30510)
$ AOSP_TOP=<copy> ./scripts/stage_ivi_observer.sh check
check: ok (artifacts agree; nothing touched)
$ AOSP_TOP=<copy> ./scripts/stage_ivi_observer.sh stage && ... unstage
(42 Gateway client sources staged; protoc lite accepts the staged contract with the module's include path)
$ AOSP_TOP=<copy> ./scripts/stage_sdv_core_interop.sh revert
tree_identical_after_revert=yes
```

`bash -n` is clean on every script. The app was compiled with `javac -Xlint:all`
(JDK 21, `--release 17`) against the tree's own Gateway Java client sources,
protobuf-javalite 3.25.5 and compile-time stubs of the Android and gRPC classes,
with the contract generated by protoc 3.25.5 in lite mode from the annotated proto:
no warning, no error, and all 47 JVM tests pass (the 39 of the on-tree test module
plus the subscriber's 8). The AOSP build at RUNBOOK step 8 is still the real
compiler.

## 8. Localizing a failure

| First hop without evidence | Likely cause | Check |
|---|---|---|
| someipd → guest | peer address, VXLAN, firewall, event ids | `tcpdump -i any port 30510` both ends; SD offers on 30490 |
| payload looks shifted | an unpatched publisher shell sends the library frame with its 4-byte prefix | the first 4 payload bytes are `00 00 00 02`; if they are a little-endian length, the struct starts at byte 4 and the broker rejects every event (`Unknown BOM for string`) |
| stack → broker | mapping not loaded, type not registered, stack config not applied | broker logcat, `run/g1b-build.log`, `run/someip-config.decoded.txt`, `vsomeip_config.json` in the image |
| broker → units | ACL denies the publication, or a unit name does not match | broker logcat (`Failed to create publisher with service_unit_name`); the unit names in the broker ACL vs the mapping's service-unit keys |
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
