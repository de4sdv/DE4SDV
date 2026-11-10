# IVI observer: the typed observation path (slice 10b), option B

The guest end of INC-DRIVING-001's observation path, typed end to end: the S-CORE
host publishes the driving operational state as a **SOME/IP struct** (ICD v2 §3);
SDV Core's SOME/IP broker translates it in **REFLECTION** mode into the typed VSIDL
message `de4sdv.driving.v1.DrivingOperationalState`, published on three service
units of that type, one per event (`de4sdv-driving-operational-state-plan`,
`-vehicle-state`, `-health`); one Android app on the IVI VM subscribes to the three
units through the SDV Gateway, shows mode, cause, speed,
the plan's path and the two clocks, and logs every receipt as JSONL (ICD §6). No
DE4SDV relay on the guest.

**Status: design, artifacts and local checks; nothing run on a VM.** The
orchestrator executes `RUNBOOK.md` on the aaos-build VM. Decision point
2026-11-11 08:30 UTC.

Option A (S-CORE sends protobuf, the broker forwards bytes, the app decodes) is
rejected as the primary design and kept in `fallback-a/`; it would need a model
amendment and the owner's word.

## Read in this order

| File | What it answers |
|---|---|
| `DESIGN.md` | the chain hop by hop; the contract on the wire (§3); **proven vs assumed** (§5); option A as fallback (§6); what was actually run (§7.1) |
| `RUNBOOK.md` | numbered steps, the AOSP-tree probe first, gates G0–G6 with T+ limits, the payload hexdump that decides B, rollback |
| `RISKS.md` | thirteen risks by likelihood, each with the check that catches it early |
| `fallback-a/README.md` | what option A is, why it was rejected, and the amendment it needs |
| `sepolicy/README.md` | why no new policy is expected and the two fixes when one is |

## Artifacts

| Path | Role | Read by |
|---|---|---|
| `contract/de4sdv_driving_operational_state.proto` | the typed VSIDL message: proto3, 43 fields, numbers 1..43, `uint32`/`float`/`string`/`repeated float` | `vsidlc`, the broker, the app's generated parser |
| `interop/someip_type_definition.textproto` | the `SomeIpStruct`: 43 fields in ICD order, no struct length, AUTOSAR strings, byte-length arrays | the generator, the broker, review |
| `interop/de4sdv_driving_operational_state.vsidl` | the mapping: 0x4df0/0x0001, events 0x8001–0x8003, eventgroup 1, one `instance_impl` and one service unit per event (unit type `de4sdv.driving.v1.DrivingOperationalState`), `REFLECTION` + the struct on each event — **generated** | `vsidlc`, the broker |
| `interop/variants/` | the one-unit form of the mapping and the broker ACL, for an owner decision only (no IVI side) | `MAPPING_VARIANT=one` |
| `scripts/gen_someip_vsidl.py` | emits the mapping from the type definition (three identical blocks; textproto cannot alias) | the test, `stage_sdv_core_interop.sh check` |
| `interop/de4sdv_driving_operational_state_bundle.vsidl` | the broker's `publisher` declaration (inserted into the platform `broker.vsidl`) | the SDV Core build |
| `interop/vsomeip_config.json` | the core stack: service, port 30510, peer pinned and secure | the core image's stack |
| `interop/broker_acl_append.textproto` | the broker may publish the three units with the typed message | the core image's broker APEX |
| `interop/acl/ivi_observer_subscriber.textproto` | the observer's subject grant | the IVI SD agent (at boot) |
| `interop/acl/ivi_broker_object_policy.textproto` | the broker's object policy on the IVI (cross-VM read) | the IVI SD agent (at boot) |
| `app/` | the observer: typed subscriber of the three units, mapper, record writer, screen (drawing, model, layout, plan geometry and numbers), JVM tests | `m De4sdvDrivingStateObserver De4sdvDrivingStateObserverTests` |
| `codec/icd_table.py` | the 43-field table, hand-copied from ICD §3 — the single source the artifacts are held to | the tests, the generator, the codec |
| `codec/someip_struct.py` | the **independent** encoder/decoder of the §3 struct (no C++ read), with a CLI | the tests, the VM gates, the vector check |
| `scripts/probe_aosp_tree.sh` | read-only probe of the facts option B rests on (7 checks) | the VM, before any build |
| `scripts/stage_sdv_core_interop.sh` | check/stage/validate (G1b)/build/revert the SDV Core overlay | the VM |
| `scripts/stage_ivi_observer.sh` | check/stage/build/install/start/verify/record/pull/remove/unstage the IVI side | the VM |
| `tests/test_contract_and_encoding.py` | contract + struct + codec + protobuf agreement | any host with `uv` |
| `tests/decode_s1_vectors.py` | decodes the S-CORE side's wire vectors with the independent codec | after the publisher's vectors exist |

## Local validation (run this before spending VM time)

```bash
python3 codec/someip_struct.py selftest
(cd ../state-publisher && tests/run_tests.sh)
python3 tests/decode_s1_vectors.py
uv run --with grpcio-tools python tests/test_contract_and_encoding.py
bash -n scripts/*.sh
```

Last run (2026-11-10): the codec round-trips all three kinds (PLAN 1301 B,
VEHICLE_STATE 218 B, HEALTH 234 B); the publisher's tests pass and regenerate the
committed vectors byte-identically; the vector check decoded 16 S-CORE frames and
compared **688 fields with no disagreement**; the contract test prints six `ok`
lines and `ALL LOCAL CHECKS PASSED (contract + encoding; no AOSP, no runtime)`. It
proves nothing about the broker, the gateway or the guest.

## The decision the owner may still have to make

Option B depends on one unproven fact: that the shipped broker's REFLECTION
translator fills a `repeated float` field and reads the AUTOSAR string framing. The
documentation says the vocabulary exists; it does not show that code path. The probe
reads it before the build, and gate G6 catches it field by field. If it fails, the
first fallback is option A (`fallback-a/`), which changes the topic's type from
`DrivingOperationalState` to a bytes carrier — a model amendment, not an
implementer's choice — and the timebox no longer holds.
