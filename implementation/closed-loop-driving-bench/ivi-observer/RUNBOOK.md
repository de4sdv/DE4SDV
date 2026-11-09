# Runbook: the typed observation path on the aaos-build VM (option B)

For the orchestrator. Every step is a command, its expected output and a gate.
Times are nominal, from the precedents' own logs: the AEBS phase-10 plan
(`score-broker-path-bench/bench-plan.md`, S1) measured the clean SDV Core build at
1.5 h and the two-VM launch with ACL provisioning and clock setting at 1.0 h.

Option B: the S-CORE host sends the SOME/IP **struct** of ICD §3; SDV Core's broker
translates it in **REFLECTION** mode into the typed VSIDL message
`de4sdv.driving.v1.DrivingOperationalState`; the IVI app subscribes to that typed
topic. Option A (bytes carrier) is not this runbook; it is `fallback-a/`.

Path prefix in this document:

```
SLICE=$(git rev-parse --show-toplevel)/implementation/closed-loop-driving-bench/ivi-observer
BENCH=$(git rev-parse --show-toplevel)/implementation/score-broker-path-bench
```

Set once per shell on the VM:

```bash
export AOSP_TOP=$HOME/aosp
export PATH="$AOSP_TOP/out/host/linux-x86/bin:$PATH"
export ADB="$AOSP_TOP/out/host/linux-x86/bin/adb"
```

The whole slice is go/no-go in 2 days. The T+ column assumes day 1 starts at
08:00 UTC; the owner decides at **2026-11-11 08:30 UTC**.

| T+ | Step | Gate |
|---|---|---|
| 0:00 | 1 local checks, 2 freeze + disk | G0 |
| 0:20 | 3 **probe the AOSP tree** (read-only) | **G1** (and G1b before the build) |
| 0:45 | 4 S-CORE peer address | **G2** |
| 1:00 | 5 build the SDV Core image (long) | build ok |
| 2:40 | 6 launch both VMs | — |
| 3:00 | 7 core hop + payload hexdump | **G3** (T+6 h limit) |
| 3:45 | 8 build the app, 9 install + reboot | — |
| 4:15 | 10 clock | **G4** |
| 4:35 | 11 first receipt | **G5** (T+12 h limit) |
| 5:00 | 12 value checks, all 43 fields | **G6** (end of day 1) |
| day 2 | 13 screen recording, 14 judged run + pull, 15 teardown | evidence |

If a gate misses its limit, §16 says what is cut. Each gate names the artifact that
answers it; do not re-run a gate hopefully.

---

## 1. Local checks, off the VM (8 min)

```bash
cd "$SLICE"
python3 codec/someip_struct.py selftest
uv run --with grpcio-tools python tests/test_contract_and_encoding.py
(cd ../state-publisher && tests/run_tests.sh)  # generates tests/vectors/*.bin
python3 tests/decode_s1_vectors.py
bash -n scripts/*.sh
```

Expected: `CODEC SELFTEST PASSED`; `ALL LOCAL CHECKS PASSED (contract + encoding;
no AOSP, no runtime)`; `VECTOR CHECK PASSED: 16 vector(s) decoded, 16 compared,
688 field comparisons`; no `bash -n` output.

The vector check reads `../state-publisher/tests/vectors/`, which the publisher's
own `tests/run_tests.sh` generates (the directory is not committed). Run that first;
if it cannot run, the vector check prints `NOT CHECKED` and exits 2 — that is a
missing cross-check, not a pass: record it as such. If a vector disagrees, stop: the S-CORE encoder and this contract
disagree about the wire, and no VM time fixes that.

**G0: all of this passes.** If not, the artifacts are inconsistent with each other
and no VM time should be spent.

## 2. Freeze the tree and check the disk (12 min)

```bash
cd "$SLICE"
./scripts/stage_sdv_core_interop.sh check
./scripts/stage_ivi_observer.sh check
df -h /
cd "$AOSP_TOP" && repo manifest -r > "$SLICE/run/manifest-r.xml" && repo status | head -40
```

Expected: both `check: ok`, `mapping up to date (...)` from the generator check;
disk free **≥ 32 GB** (the AEBS floor and the clean build's ~30 GB peak; that bench
started with 19 GB once and had to prune the `android-cuttlefish` Bazel cache
first). Keep `manifest-r.xml`: it is the identity of both builds.

**G0 continues: do not build below 32 GB.** Prune first, with the owner's decision.

## 3. Probe the AOSP tree — the five facts option B rests on (25 min)

```bash
cd "$SLICE"
./scripts/probe_aosp_tree.sh | tee "$SLICE/run/aosp-tree-probe.txt"
echo "exit=$?"
```

It changes nothing, starts nothing, needs no build. Read its verdicts, not just its
exit code:

| Probe | What it decides | If it says BLOCKER |
|---|---|---|
| §1 `SomeIpPrimitive` values | `UINT32` and `FLOAT32` exist; whether `UINT64` does | no `FLOAT32`/`UINT32` → the struct cannot be expressed; stop (G1) |
| §2 `MessageTranslationMode` | `REFLECTION` is a mode of this release | no `REFLECTION` → option B has no translator; stop (G1) |
| §3 repeated-field handling | the translator touches repeated fields | no hit → read the code; if `repeated` is unsupported, option A (owner) |
| §4 string framing | the BOM/NUL convention, and whether the length covers it | a BOM-less reader means the S-CORE side would change; owner-level |
| §5 array length | bytes, not elements | elements would make 64 floats a length of 64; owner-level |
| §6 catalog registration | how a new publication type is registered, and whether `publisher { message: }` ever names a dotted type | sets `CATALOG_MODULE_KIND`; a dotted-name refusal is the bare-name variant of step 5 |
| §7 the mw::com frame | whether gatewayd drops the 4-byte prefix before SOME/IP | cannot be settled here if the gateway is another repo — G3 does it with a hexdump |

If the probe says `READ`, open the file and the lines it printed. Record what you
found in `run/aosp-tree-probe.txt`; the notes are evidence, and the next reader has
no VM.

**G1: no BLOCKER from the probe** — `UINT32`, `FLOAT32`, `REFLECTION` and a
`type_definition` consumer all exist. A BLOCKER here is an owner-level finding
before a single build hour is spent: record it and stop.

## 4. Read the S-CORE peer address and confirm the offer (15 min)

The core stack pins the S-CORE host's address on the VXLAN segment and accepts the
service only from it. On the S-CORE host (or from its console):

```bash
ip -brief addr show            # the VXLAN interface of the bench segment
ss -ltnp | grep 30510          # someipd listening on TCP 30510
```

```bash
export SCORE_SOMEIP_PEER=<address on 192.168.98.0/24 from the S-CORE host>
```

Do **not** accept the default (`192.168.98.1`) without this check: on the
three-host bench that address is the guest host, not the S-CORE host.

**G2: the S-CORE host listens on 30510, offers 0x4df0, and `SCORE_SOMEIP_PEER` is
its address on the segment.** Without it the guest can subscribe to nothing and
every later gate fails for the wrong reason.

## 5. Build the SDV Core image (1.5 h clean, 20–30 min incremental)

```bash
cd "$SLICE"
: "${SCORE_SOMEIP_PEER:?export it from step 4}"
./scripts/stage_sdv_core_interop.sh build
```

It stages the typed proto, the `SomeIpStruct` and the generated mapping into
`$SAMPLES/some_ip/catalog/de4sdv_driving/`, appends the catalog's
`proto_library`-style module (kind = `CATALOG_MODULE_KIND` from the probe), inserts
the broker's `publisher { message: "de4sdv.driving.v1.DrivingOperationalState" }`
at the anchor of an existing publisher entry, appends the broker publish ACL once,
renders `vsomeip_config.json` with the peer, checks the disk floor, runs
`lunch sdv_core_cf-cp2a-eng; m`, and writes `run/core-image-identity.txt` only if
the build passed.

Expected tail: `recorded the build identity in .../run/core-image-identity.txt`.
Read that file: manifest digest, `device/google/sdv` diff digest, and the hashes of
the five staged inputs at their destinations.

Three build-time failures and their one-line fixes, in order of likelihood:

| Symptom | Cause | Fix (and cost) |
|---|---|---|
| `vsidlc`/Soong cannot resolve `de4sdv.driving.v1.DrivingOperationalState` | the catalog module kind, or the bundle's proto srcs, do not include the new proto | re-run with `CATALOG_MODULE_KIND` set to what the probe printed; if the broker bundle compiles its own proto list, add the file there. +20–30 min |
| the broker rejects the dotted `message:` name in `broker.vsidl` | the parser wants a bare name in the declaration's package | change the one line to `message: "DrivingOperationalState"` (and note the package) and rebuild. +20–30 min |
| `vsidlc` rejects three `offered_event` blocks on one topic parameter | one topic per event is required | regenerate with three topic parameters (DESIGN §2); the app subscribes three times. +30–40 min |

**G1b (before the long part of the build): the catalog compiles the type and
`vsidlc` accepts the mapping.** `m de4sdv_driving_operational_state_proto` (or the
module name `m` chose) must succeed and the broker catalog must validate. Do not
start the 1.5 h image build on an unvalidated mapping.

## 6. Launch the two VMs (20 min, 30 with contingency)

```bash
cd "$BENCH"
./scripts/launch_two_vms.sh up
"$ADB" devices
```

Expected: `created de4sdv_core from sdv_core_cf (instance 2, config sdv_core_instance1)`,
then the same for `de4sdv_ivi`; `adb devices` shows `0.0.0.0:6521` and `:6522`.

```bash
"$ADB" -s 0.0.0.0:6521 shell getprop ro.boot.sdv.someip.enable   # true
"$ADB" -s 0.0.0.0:6521 shell getprop ro.boot.sdv.boot_mode       # unlocked
"$ADB" -s 0.0.0.0:6522 shell getprop ro.boot.sdv.instance_name   # instance2
```

## 7. Prove the core hop and the payload's first bytes (45 min)

```bash
"$ADB" -s 0.0.0.0:6521 shell "tcpdump -i any -n -c 40 'tcp port 30510' -w /data/local/tmp/someip.pcap" &
"$ADB" -s 0.0.0.0:6521 logcat -d | grep -iE "vsomeip|someip|broker" | tail -60
```

Expected, in this order: the stack loading the DE4SDV config, an SD offer/Subscribe
for `4df0.0001`, a `REMOTE SUBSCRIBE` to the S-CORE address, and the broker
creating the publication of `de4sdv-driving-operational-state`.

Then the payload itself — this is where option B is decided:

```bash
"$ADB" -s 0.0.0.0:6521 shell "tcpdump -i any -n -X 'tcp port 30510' | head -120"
```

| First payload bytes after the SOME/IP header | Meaning | Action |
|---|---|---|
| `00 00 00 02` | `schema_major = 2`: the struct starts at byte 0. **Expected.** | continue |
| `xx xx 00 00` with `xx xx` a little-endian length (e.g. `12 05 00 00`) | the mw::com envelope survived: the struct starts at byte 4 | record it and go to RISKS R1; the mapping is not wrong, the S-CORE gateway is |
| `08 01 ...` | protobuf: the S-CORE side is still sending option A | stop and report; the two sides are not the same contract |

Cross-check the size: a HEALTH struct is **234 bytes**, a VEHICLE_STATE **218**, a
full PLAN **1301** (frame +4 with the envelope). `python3 codec/someip_struct.py
sample --kind health --hex | wc -c` prints the reference frame for comparison.

**G3: the subscription is seen, the topic is published, and the payload starts with
the struct.** A missed G3 at T+6 h is an owner-level finding (ADR 0025 decision 4's
trigger: "a run in which the stack does not subscribe to the frame event"): record
the stack and broker logs and stop.

## 8. Build the observer app (10 min)

```bash
cd "$SLICE"
./scripts/stage_ivi_observer.sh build
```

The script copies the Soong modules into
`$AOSP_TOP/system/software_defined_vehicle/samples/de4sdv_driving_observer/{app,contract}`
(Soong only sees modules inside the tree), then `lunch sdv_ivi_cf-cp2a-eng; m
De4sdvDrivingStateObserver De4sdvDrivingStateRecordTest`.

Expected: `built .../out/target/product/sdv_ivi_cf/system/priv-app/De4sdvDrivingStateObserver/De4sdvDrivingStateObserver.apk`
and no Soong error. Run `De4sdvDrivingStateRecordTest` with the tree's java_test
runner; the same rules already ran offline (step 1).

This can run while the core image builds only if the tree is already built for
`sdv_ivi_cf`; otherwise run it here, after step 5.

## 9. Install: ACLs, APK, reboot (20 min)

```bash
./scripts/stage_ivi_observer.sh install
```

What it does, and why each piece is not optional:

1. `adb root` + `remount` on the IVI (eng/UNLOCKED; the relay precedent pushes to
   `/system`).
2. Pushes the subject ACL to
   `/product/etc/sdv_authz_acls/org.de4sdv.drivingstate/DrivingStateObserver.textproto`
   and the broker object policy to
   `/product/etc/sdv_authz_acls/com.android.sdv.someip/SomeIpBroker.textproto`.
   Both name `message: "de4sdv.driving.v1.DrivingOperationalState"`. The SD agent
   reads ACLs **only at its start** and exits if a second file names one subject, so
   the script refuses to continue on a duplicate.
3. Pushes the APK to `/system/priv-app/De4sdvDrivingStateObserver/`.
4. Reboots; PackageManager scans the APK, the SD agent reads the ACLs.
5. Prints `installed: package:/system/priv-app/...apk` and writes
   `run/ivi-observer-identity.txt` (APK sha256 host and guest, IVI fingerprint,
   both ACL digests, subject, topic, message).

If the image reads ACLs from `/system/etc/...` instead (PF-004), re-run with
`ACL_ROOT=/system/etc/sdv_authz_acls`; the duplicate check covers all four roots.

## 10. Clock the IVI (15 min)

```bash
cd "$BENCH"
export IVI_ADB=0.0.0.0:6522
./scripts/set_ivi_clock.sh allow
./scripts/set_ivi_clock.sh set
./scripts/set_ivi_clock.sh measure /tmp/ntp-start.pcap
```

Use `set`, not `setup` (`setup` also restarts the AEBS ingress and asserts a relay
`phase_start` that this bench does not have). Expected: chrony serves the IVI,
`auto_time` off, the clock stepped and re-measured, `offset` printed. The AEBS rule:
**a run whose offset plus its uncertainty is not below 20 ms is void** for
cross-host comparison.

**G4: offset + uncertainty < 20 ms.** Every cross-host number in the recording
depends on it; nothing on the path does.

## 11. Start the observer and get the first typed receipt (20 min)

```bash
cd "$SLICE"
./scripts/stage_ivi_observer.sh start
"$ADB" -s 0.0.0.0:6522 logcat -s DE4SDV_DRIVING_STATE | head -40
```

Expected lines: `lifecycle start ...`, `lifecycle config topic=...`,
`lifecycle config message=de4sdv.driving.v1.DrivingOperationalState`,
`lifecycle config translation=REFLECTION ...`, `lifecycle initComms ...`,
`subscribed topic=... message=...`, `lifecycle ready ...`, then
`seq=1 kind=HEALTH sequence=... publish_real=... mode=0(kStarting)`.

Read four things from the first receipt:

| Observation | Expected | If not |
|---|---|---|
| `kind` / `sequence` | HEALTH first, sequence 1, rising without gaps | a parse error instead → the gateway handed the app something else (R5) |
| strings | `producer=statePublisher` | `contract=producer_empty` or an empty producer → the string translation failed (R2) |
| arrays | a PLAN receipt with `points=64` and a non-zero `plan_x` | `points=0` → REFLECTION did not fill a repeated field (R2) |
| `all_defaults=1` | never | every kind field at its default → a `field_name` does not match the protobuf name (R2) |

**G5: a typed receipt with non-default fields.** If the app instead logs `error
reason=read: ...` or a protobuf parse exception, the gateway did not deliver the
typed message; that is R5, not an app bug. Do not spend the day on the Java path:
the fallback is the native C++ subscriber plus the loopback feed (RISKS R5, 2–3 h).

## 12. Prove the values are the published ones, all 43 fields (30 min)

```bash
./scripts/stage_ivi_observer.sh pull
python3 - <<'PY'
import json
recs=[json.loads(l) for l in open("run/observer.jsonl")]
samples=[r for r in recs if r.get("event")=="in.operational_state"]
plans=[r for r in samples if r["data"]["kind"]==1]
print(len(recs), "records;", len(samples), "receipts;", len(plans), "plans")
d=plans[0]["data"]
print({k:d[k] for k in ("plan_frame_index","plan_capture_ms","plan_sample_count","run_record")})
print("plan_x[0..2]", d["plan_x"][:3], "plan_y[-1]", d["plan_y"][-1])
print("clocks keys", len(d["clocks"]))
PY
```

Compare with `<run_dir>/score/statePublisher.jsonl` for the same `sequence`:

1. **Header**: `schema_major=2`, `schema_minor=0`, `kind`, `sequence`, `producer`.
2. **Times**: `publish_real_s`/`_ns`, `publish_mono_s`/`_ns` (exact integers);
   `plan_capture_ms` = frame × 100; `plan_production_mono_s`/`_ns`.
3. **Strings**: `plan_reference` = `<run_record>/<frameIndex>`, `run_record` 16 hex
   characters, `plan_producer` = `drivingAgent/inferPlan`, `mode_source`.
4. **Arrays**: all 64 elements of `plan_acceleration`, `plan_curvature`, `plan_x`,
   `plan_y`, element for element. A shift by one sample is a real ordering finding,
   not noise.
5. **HEALTH**: `mode`, `cause` (first stop cause latched), `cause_since_mono_s`/`_ns`,
   `last_plan_frame_index`, `last_plan_capture_ms`, `step_capture_ms`,
   `last_plan_production_mono_s`/`_ns`, `dropped_samples`, and on a refusal
   `checkpoint_expected_sha256`, `checkpoint_actual_sha256`, `refusal_reason`.

**G6: the observer's decoded values equal the publisher's, field for field.** This
is the gate the whole slice exists for; a run that only shows the topic arriving is
not it. A mismatch in a *string* or an *array* and nothing else is the broker's
translation (R2), not the publisher: say which field, with both lines in the report.

## 13. Record the screen (15 min)

```bash
./scripts/stage_ivi_observer.sh record 40
```

Expected: `run/ivi_screen.mp4` (~40 s) and `run/ivi_screen_logcat.txt`. Watch the
clip: the two clocks readable side by side (IVI real time and message publish real
time), the plan path drawn with its 10 m grid, health changing on a stop, the plan
frame and its capture time. Recorded on the guest, nothing retimed.

## 14. The judged run and the pull (30 min)

Start the S-CORE side's recorded run (out of this slice's scope), then:

```bash
./scripts/stage_ivi_observer.sh record 120        # optional second clip
./scripts/stage_ivi_observer.sh pull "$RUN_DIR/guest/observer.jsonl"
sha256sum "$RUN_DIR/guest/observer.jsonl" >> "$RUN_DIR/MANIFEST.sha256"
```

Expected: one record per receipt for the whole run, no `error` line after `ready`,
screen `receipts` equal to the file's `in.operational_state` lines. Copy
`run/aosp-tree-probe.txt` and `run/core-image-identity.txt` beside it: they are the
tree-specific evidence for G1/G1b.

## 15. Teardown (15 min)

```bash
cd "$SLICE"; ./scripts/stage_ivi_observer.sh remove
cd "$BENCH"; ./scripts/launch_two_vms.sh down
cd "$SLICE"; ./scripts/stage_sdv_core_interop.sh revert     # restores the AOSP tree
```

Keep `run/`: `aosp-tree-probe.txt`, `core-image-identity.txt`, `manifest-r.xml`,
`observer.jsonl`, `ivi_screen.mp4`, the logcat captures.

## 16. What is cut when a gate is late

| Gate | Limit | If missed |
|---|---|---|
| G0 | T+0.5 h | fix the artifacts; no VM time |
| G1 | T+1 h | a BLOCKER from the probe is an owner decision: option A (model amendment) or stop. Do not build. |
| G1b | T+2 h | the type does not resolve: fix `CATALOG_MODULE_KIND` / the dotted name once, then report with the `vsidlc` output |
| G2 | T+1.5 h | stop; the S-CORE side is not ready, no guest work can help |
| G3 | T+6 h | record the stack/broker logs and the payload hexdump, report to the owner (ADR 0025 decision 4's trigger) and stop the slice |
| G4 | T+5 h | run with the known offset, mark cross-host comparisons unscoped, keep going (a measurement rule, not a path rule) |
| G5 | T+12 h | if the message is not typed: RISKS R5 (native subscriber, 2–3 h). If it is typed but empty: R2, report with the broker log |
| G6 | end of day 1 | the path works but the values differ: report with both records, do not adjust one side |

## 17. Rollback

`stage_sdv_core_interop.sh revert` restores `broker.vsidl`, `someip_acl.textproto`,
the stack config and the catalog's `Android.bp` from `run/core-image-originals/`,
and removes the three staged files (and the catalog `Android.bp` if this script
created it); the core image then needs a rebuild to be clean.
`stage_ivi_observer.sh remove` deletes the two ACL files and the APK and reboots.
Nothing in this slice alters the IVI image, so the IVI returns to its image state by
itself.
