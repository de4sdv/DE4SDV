# Runbook: the typed observation path on the aaos-build VM (option B)

Every step is a command, its expected output and a gate.
Times are nominal, from the precedents' own logs: the AEBS phase-10 plan
(`score-broker-path-bench/bench-plan.md`, S1) measured the clean SDV Core build at
1.5 h and the two-VM launch with ACL provisioning and clock setting at 1.0 h.

Option B: the S-CORE host sends the SOME/IP **struct** of ICD §3; SDV Core's broker
translates it in **REFLECTION** mode into the typed VSIDL message
`de4sdv.driving.v1.DrivingOperationalState` and publishes it on three service units of
that one type, one per event: `de4sdv-driving-operational-state-plan` (0x8001),
`de4sdv-driving-operational-state-vehicle-state` (0x8002) and
`de4sdv-driving-operational-state-health` (0x8003). The IVI app subscribes to the
three units by name and merges them into one state. Option A (bytes carrier) is not
this runbook; it is `fallback-a/`.

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

The plan was sized for two days. The T+ column gives nominal times from the
start of day 1.

| T+ | Step | Gate |
|---|---|---|
| 0:00 | 1 local checks, 2 freeze + disk | G0 |
| 0:20 | 3 **probe the AOSP tree** (read-only) | **G1** |
| 0:45 | 4 S-CORE peer address | **G2** |
| 1:00 | 5 stage, validate, build the SDV Core image (long) | **G1b**, then build ok |
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
(cd ../state-publisher && tests/run_tests.sh)            # regenerates tests/vectors/*.bin
git status --short ../state-publisher/tests/vectors      # prints nothing
python3 tests/decode_s1_vectors.py
uv run --with grpcio-tools python tests/test_contract_and_encoding.py
python3 scripts/gen_someip_vsidl.py --check
bash -n scripts/*.sh
bash tests/test_stage_ivi_build_variant.sh
```

Expected: `CODEC SELFTEST PASSED`; `all tests passed`; no `git status` output;
`VECTOR CHECK PASSED: 16 vector(s) decoded, 16 compared, 688 field comparisons`;
`ALL LOCAL CHECKS PASSED (contract + encoding; no AOSP, no runtime)`;
`mapping up to date (811 lines)`; no `bash -n` output;
`BUILD VARIANT CHECK PASSED (5 cases)`.

The vectors in `../state-publisher/tests/vectors/` are committed; the publisher's
own `tests/run_tests.sh` regenerates them and they must come out byte-identical. If
the vector check cannot find them it prints `NOT CHECKED` and exits 2 — that is a
missing cross-check, not a pass: record it as such. If a vector disagrees, stop: the
S-CORE encoder and this contract disagree about the wire, and no VM time fixes that.

The contract test's first line says how it compiled the contract: with `AOSP_TOP`
exported (or `VSIDL_PROTO_ROOT`) it uses the tree's `sdv/vsidl/v1/annotations.proto`
and reads the publication options through the descriptor; without it, it compiles
a copy with the VSIDL options removed (names, numbers and types unchanged) and
checks the options as text.

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

Expected, each after `mapping up to date (811 lines)`:

- `check: ok (variant: three, units: de4sdv-driving-operational-state-plan de4sdv-driving-operational-state-vehicle-state de4sdv-driving-operational-state-health)`;
- `check: ok (artifacts agree; nothing touched)`;
- disk free **≥ 32 GB** (the AEBS floor and the clean build's ~30 GB peak; that bench
  started with 19 GB once and had to prune the `android-cuttlefish` Bazel cache
  first). Keep `manifest-r.xml`: it is the identity of both builds.

If the core check says `ERROR: .../catalog/de4sdv_driving/Android.bp exists`, an
earlier revision of the stage script ran on this tree: restore the files in
`run/core-image-originals/` (`./scripts/stage_sdv_core_interop.sh revert`), then
delete `Android.bp`, `someip_type_definition.textproto` and
`de4sdv_driving_operational_state.vsidl` from that directory.

**G0 continues: do not build below 32 GB.** Prune first, with the owner's decision.

## 3. Probe the AOSP tree — the facts option B rests on (25 min)

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
| §6 catalog registration | the catalog's `Android.bp` globs `**/*.proto` and `**/*.vsidl`, so the files go into a subdirectory **without** an `Android.bp` (as `de4sdv_score/`); it also prints the tree's dotted `publisher { message: }` entries | no glob → the staging layout does not fit this tree; stop (G1) |
| §7 the mw::com frame | gatewayd is not in this tree, so the probe cannot see what reaches the SOME/IP payload | always `READ`: G3 settles it with a hexdump |

Expected summary line: `7 checks, 0 blocker(s)` (§4 and §7 say `READ`).

If the probe says `READ`, open the file and the lines it printed. Record what you
found in `run/aosp-tree-probe.txt`; the notes are evidence, and the next reader has
no VM.

**G1: no BLOCKER from the probe** — `UINT32`, `FLOAT32`, `REFLECTION` and a
`type_definition` consumer all exist. A BLOCKER here is an owner-level finding
before a single build hour is spent: record it and stop.

## 4. Read the S-CORE peer address and confirm the offer (15 min)

The core stack pins the provider of 0x4df0 to `SCORE_SOMEIP_PEER` and accepts the
reliable port 30510 only from that address (`secure-services` + `acceptances`).
There is no default: `stage_sdv_core_interop.sh stage` refuses to run without it.

On the three-host bench the S-CORE host holds **192.168.98.1** on the VXLAN segment:
its someipd's vsomeip `unicast` is 192.168.98.1, on the bridge that carries the
`vx98` VXLAN port (or on `vx98` itself). The guest host's bridge,
which held `.1` on the two-host bench, moves to **192.168.98.254** when the guest-host
half of the VXLAN is added. So, once both halves are up:

```bash
export SCORE_SOMEIP_PEER=192.168.98.1
```

Check it before any build. On the S-CORE host:

```bash
ip -brief addr show | grep 192.168.98.1/24     # the bridge with vx98 (or vx98 itself)
ss -ltnp | grep 30510                          # someipd listening on TCP 30510
ping -c1 -W2 192.168.98.254                    # the guest host's bridge answers through vx98
```

On the guest host, `ip -brief addr show | grep 192.168.98.` must show `.254` and not
`.1`. If the guest host still holds `.1`, the guest-host half was not added: two hosts
would claim the address the core accepts. Stop and fix the VXLAN first.

**G2: the S-CORE host holds 192.168.98.1, listens on 30510 and offers 0x4df0, the
guest host is on .254, and `SCORE_SOMEIP_PEER=192.168.98.1`.** Without it the guest
can subscribe to nothing and every later gate fails for the wrong reason.

## 5. Stage, validate (G1b) and build the SDV Core image (1.5 h clean, 20–30 min incremental)

```bash
cd "$SLICE"
: "${SCORE_SOMEIP_PEER:?export it from step 4}"
./scripts/stage_sdv_core_interop.sh stage
./scripts/stage_sdv_core_interop.sh validate        # G1b; full log run/g1b-build.log
sudo loginctl enable-linger "$USER"                 # once, so the build survives an SSH drop
systemd-run --user --unit=de4sdv-core-build --working-directory="$PWD" \
  env AOSP_TOP="$AOSP_TOP" SCORE_SOMEIP_PEER="$SCORE_SOMEIP_PEER" ./scripts/stage_sdv_core_interop.sh build
tail -f run/core-build.log
```

`stage` backs up the three files it edits into `run/core-image-originals/` (once),
then:

- copies the typed proto and the generated mapping into
  `$SAMPLES/some_ip/catalog/de4sdv_driving/` as plain files: the catalog's own
  `Android.bp` takes every `**/*.proto` and `**/*.vsidl` below it, so the directory
  gets **no** `Android.bp` (as `de4sdv_score/`);
- appends the broker publish ACL of the three units once;
- inserts the broker's `publisher { message: "de4sdv.driving.v1.DrivingOperationalState" }`
  after the first existing publisher entry;
- renders `vsomeip_config.json` with the peer: 0x4dee kept, 0x4df0 added, the
  acceptances of one address merged into one entry;
- checks that the earlier increment's entries survived.

Expected lines (on a re-run, `already present` replaces the first two):

- `appended the broker publish ACL (three unit variant)`;
- `broker.vsidl publisher inserted: de4sdv.driving.v1.DrivingOperationalState`;
- `stack config rendered: services ['0x4dee', '0x4df0'], 0x4df0 provider 192.168.98.1`;
- `staged into .../samples/some_ip/catalog/de4sdv_driving (backup in .../run/core-image-originals); variant three`.

`validate` re-runs `stage`, then `lunch sdv_core_cf-cp2a-eng` and
`m generate_vsidl_files_someip_catalog_protos_with_bp_file vsidlc_someip_catalog_protos_with_bp_file libsomeip_messages_catalog aprotoc`
(`G1B_MODULES` in `bench_env.sh`): `vsidl_rc_generator` and `vsidlc` run the pdk29
checks over the whole catalog, every catalog proto is compiled in the catalog's Rust
crate, and `aprotoc` decodes the generated `someip-config.binpb` into
`run/someip-config.decoded.txt`, which the script then checks.

**G1b (before the long build): the last line is
`G1b: someip-config.binpb holds 0x4df0, events 0x8001-0x8003, 3 x 43 fields, unit type de4sdv.driving.v1`.**
Do not start the 1.5 h image build on an unvalidated mapping.

| Text in `run/g1b-build.log` | Cause | Fix (and cost) |
|---|---|---|
| `Publisher message type ... has no Proto publication` | the contract lost its `(.sdv.vsidl.v1.publication)` option | restore the contract (step 2's `check` catches it). +20–30 min |
| `variable_type_max_size annotation for '<field>' is missing` / `repeated_field_max_count annotation for '<field>' is missing` | a string or repeated field lost its size annotation | same |
| `Warning: Unresolved publication reference` | `vsidlc` does not resolve the dotted `message:` in `broker.vsidl` | RISKS R6: the bare-name variant (one line) and a re-run. +20–30 min |
| `Service unit name for ... exceeds ...` | a unit name is over the catalog's limit | owner decision: shorter unit names in the mapping, both IVI ACLs and the app |

`build` re-runs `stage` and G1b, checks the disk floor (32 GB), runs a plain `m`
(the partitions, then `super.img`, then `vbmeta.img`), refuses to record anything if
`super.img` or `vbmeta.img` is older than the staged proto, and writes
`run/core-image-identity.txt` only if the build passed. The change reaches the
broker APEX, system and vendor, so never build `systemextimage productimage` alone
for it. Expected tail: `recorded the build identity in .../run/core-image-identity.txt`.
Read that file: manifest digest, `device/google/sdv` diff digest, the peer, the
three units and the hashes of the staged inputs at their destinations.

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
for `4df0.0001`, a `REMOTE SUBSCRIBE` to 192.168.98.1, and the broker creating one
publisher per unit (`-plan`, `-vehicle-state`, `-health`). The broker's own errors:

```bash
"$ADB" -s 0.0.0.0:6521 shell 'grep -c 4df0 /vendor/etc/someip/vsomeip_config.json'   # >= 1
"$ADB" -s 0.0.0.0:6521 logcat -d -s someip_broker_agent | grep -E \
  'Encountered error|Unable to build|Failed to create publisher|Couldn.t get publication|Error processing|Error translating|No publication metadata|no known mapping'
"$ADB" -s 0.0.0.0:6521 shell 'ip rule add to 192.168.98.0/24 lookup main priority 15000'   # every boot (the AEBS bench's buried_eth0 note)
```

Expected: no broker error line names 0x4df0 or `de4sdv-driving-operational-state-*`.
`Failed to create publisher with service_unit_name ...` is RISKS R4.

Then the payload itself — this is where option B is decided:

```bash
"$ADB" -s 0.0.0.0:6521 shell "tcpdump -i any -n -X 'tcp port 30510' | head -120"
```

| First payload bytes after the SOME/IP header | Meaning | Action |
|---|---|---|
| `00 00 00 02` | `schema_major = 2`: the struct starts at byte 0. **Expected.** | continue |
| `xx xx 00 00` with `xx xx` a little-endian length (e.g. `da 00 00 00`, `12 05 00 00`) | the library frame's 4-byte prefix is on the wire: an unpatched `state_publisher` sends the whole frame, and the broker rejects every event (`Unknown BOM for string`) | RISKS R2: rebuild and restart the patched publisher on the S-CORE host; the mapping is not wrong |
| `08 01 ...` | protobuf: the S-CORE side is still sending option A | stop and report; the two sides are not the same contract |

Cross-check the size, the struct alone: VEHICLE_STATE **218 bytes**; HEALTH 218 to
367 and PLAN 274 to 1390 bytes, depending on the strings and the point count (a
64-point plan is 1298 with the publisher's own strings), as the publisher's vectors
show. `python3 codec/someip_struct.py decode --hex "<payload bytes>"` decodes one
payload and prints `# consumed N of M bytes`.

**G3: the subscription is seen, the three units are published, and the payload
starts with the struct.** A missed G3 at T+6 h is an owner-level finding (ADR 0025 decision 4's
trigger: "a run in which the stack does not subscribe to the frame event"): record
the stack and broker logs and stop.

## 8. Build the observer app (10 min)

```bash
cd "$SLICE"
./scripts/stage_ivi_observer.sh build
```

The script copies the Soong modules into
`$AOSP_TOP/system/software_defined_vehicle/samples/de4sdv_driving_observer/{app,contract}`
(Soong only sees modules inside the tree), copies the tree's own Gateway Java client
sources (`sdv_gateway/libsdvgatewayclient_java/src/google/...`) into
`app/src/google/sdv/gateway/client/` (the INC-AEBS-010 app carries the same copy),
then `lunch sdv_ivi_cf-cp2a-<variant>; m De4sdvDrivingStateObserver
De4sdvDrivingStateObserverTests`. The full build log is `run/observer-build.log`.

The variant is the one the IVI product was last built with, read from
`out/target/product/sdv_ivi_cf/previous_build_config.mk` (`IVI_VARIANT` in
`bench_env.sh`); the script refuses any other. A module build under another variant
makes the build system run an installclean of the product directory first, which
deletes the IVI images (RISKS R14). Before the build, note the line the script will
use: `cat $AOSP_TOP/out/target/product/sdv_ivi_cf/previous_build_config.mk`.

Expected: `built .../out/target/product/sdv_ivi_cf/vendor/priv-app/De4sdvDrivingStateObserver/De4sdvDrivingStateObserver.apk`
(a vendor privileged app, the AEBS app's module shape: the Gateway Java client is a
vendor `java_sdk_library`) and no Soong error. `m` builds the JVM tests but does not
run them; run them with the tree's JDK:

```bash
cd "$AOSP_TOP"
JAR=$(find out/soong/.intermediates/system/software_defined_vehicle/samples/de4sdv_driving_observer/app/De4sdvDrivingStateObserverTests \
  -name 'De4sdvDrivingStateObserverTests.jar' -path '*combined*' | head -1)
# The combined jar carries junit and hamcrest (static_libs); nothing else is needed.
prebuilts/jdk/jdk21/linux-x86/bin/java -cp "$JAR" org.junit.runner.JUnitCore \
  org.de4sdv.drivingstate.StateRecordTest org.de4sdv.drivingstate.PlanGeometryTest \
  org.de4sdv.drivingstate.PlanKinematicsTest org.de4sdv.drivingstate.ScreenModelTest
```

Expected: `OK (39 tests)` (7 + 11 + 7 + 14; the subscriber's own 8 tests need the Gateway
client classes and run off the tree).

This can run while the core image builds only if the tree is already built for
`sdv_ivi_cf`; otherwise run it here, after step 5.

## 9. Install: ACLs, APK, reboot (20 min)

```bash
./scripts/stage_ivi_observer.sh install
```

What it does, and why each piece is not optional:

1. `adb root` + `remount` on the IVI (eng/UNLOCKED). `/vendor` must be writable; on a
   guest with verity on, the first `remount` disables it and asks for a reboot, which
   the script does once and remounts again.
2. Pushes the subject ACL to
   `/product/etc/sdv_authz_acls/org.de4sdv.drivingstate/DrivingStateObserver.textproto`
   and the broker object policy to
   `/product/etc/sdv_authz_acls/com.android.sdv.someip/SomeIpBroker.textproto`.
   Both name `message: "de4sdv.driving.v1.DrivingOperationalState"` and the three
   units as `topic:`; the object policy also lists them as `service_units`. The SD agent
   reads ACLs **only at its start** and exits if a second file names one subject, so
   the script refuses to continue on a duplicate.
3. Removes a `/data/app` copy of the package if an earlier `adb install` left one
   (it would shadow the image path as an update), then pushes the APK to
   `/vendor/priv-app/De4sdvDrivingStateObserver/` (`restorecon` after the push).
4. Reboots; PackageManager scans the APK, the SD agent reads the ACLs.
5. Prints `installed: package:/vendor/priv-app/...apk` (anything else fails the step) and writes
   `run/ivi-observer-identity.txt` (APK sha256 host and guest, IVI fingerprint,
   subject and message, the publisher and its three units, both ACL digests).

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

**SELinux mode.** This runbook does not change the guest's SELinux mode, and
`stage_ivi_observer.sh` never does. The recorded runs of 2026-11-10 did: each
was made after `adb shell setenforce 0` on the IVI guest, applied after every
boot of the guest and before this step. Under enforcing this step is untested
(`sepolicy/README.md`). `verify` writes the mode of the run into
`observer-verify.log`; quote it with every result.

```bash
cd "$SLICE"
./scripts/stage_ivi_observer.sh start
"$ADB" -s 0.0.0.0:6522 logcat -s DE4SDV_DRIVING_STATE | head -40
```

The IVI's window is edge to edge, so the status bar and the bottom bar lie over the
window's top and bottom. The app draws its whole screen inside the area the bars
leave free and logs what it was given (`screen insets left=0 top=57 right=0
bottom=72` on the 1080 x 600 centre display). `OBSERVER_IMMERSIVE=1
./scripts/stage_ivi_observer.sh start` asks for hidden bars instead (`lifecycle
config immersive=requested`, then `screen insets ... top=0 ... bottom=0`): the app
then fills the display. The IVI's system bar policy decides whether the request is
granted; the screen is complete either way.

Expected lines (all under the one tag `DE4SDV_DRIVING_STATE`). The first six come in
this order; the per-unit lines come once per unit, in whatever order the units
register (`<unit>` is each of `de4sdv-driving-operational-state-plan`,
`-vehicle-state`, `-health`):

```
lifecycle start subject=org.de4sdv.drivingstate.DrivingStateObserver
lifecycle config message=de4sdv.driving.v1.DrivingOperationalState
lifecycle config publisher=com.android.sdv.someip.SomeIpBroker units de4sdv-driving-operational-state-plan,de4sdv-driving-operational-state-vehicle-state,de4sdv-driving-operational-state-health
lifecycle config translation=REFLECTION at the SDV Core SOME/IP broker
lifecycle initComms package=org.de4sdv.drivingstate bundle=DrivingStateObserver
lifecycle config initComms=org.de4sdv.drivingstate.DrivingStateObserver
discovery by name vm='' package=com.android.sdv.someip bundle=SomeIpBroker unit=<unit>        (x3)
lifecycle config link=WAITING 0 of 3 units subscribed; <unit> WAITING; ...
service unit Registered <vm>:com.android.sdv.someip.SomeIpBroker/<instance> unit <unit> type <package>/<bundle>/DrivingOperationalState topic ... slot <bytes> B x <count>   (x3)
lifecycle config publisher_registered=<the same identity>                                     (x3)
subscribed unit=<unit> message=de4sdv.driving.v1.DrivingOperationalState vm=<vm> publisher=com.android.sdv.someip.SomeIpBroker slot=<bytes> B x <count>   (x3)
lifecycle config subscribed=<vm>:com.android.sdv.someip.SomeIpBroker/<unit> slot ...         (x3)
lifecycle ready link=3 of 3 units subscribed on <vm>
seq=1 kind=HEALTH sequence=... schema=2.0 publish_real=... mode=0(kStarting) cause=...
status link=SUBSCRIBED receipts=<n> errors=0                                                  (every 5 s)
```

The app subscribes **by name** to each of the broker's three units, so it does not
depend on the unit type the broker registers; the `service unit Registered` lines
show that type. The link is `SUBSCRIBED` only when all three units are; the line
names every unit that is not, and why. If the app stays at `link=WAITING ...` for a
unit, the broker has not registered that unit on any VM the IVI sees: that is a
core-side or SD-agent fault, not an app fault (DESIGN §8 localizes it; one unit
missing and the others present is RISKS R4). If the subscribe call reports
`PERMISSION_DENIED`, compare the registered type with `message:` in both ACL files.
`./scripts/stage_ivi_observer.sh verify` (read-only) counts the receipts per kind.

Read four things from the first receipt:

| Observation | Expected | If not |
|---|---|---|
| `kind` / `sequence` | all three kinds arrive; per kind, `sequence` rises without gaps (each kind is its own unit; the first receipt of a unit can be its last published message) | a parse error instead → the gateway handed the app something else (R5) |
| strings | `producer=statePublisher` | `contract=producer_empty` or an empty producer → the string translation failed (R2) |
| arrays | a PLAN receipt with `points=64` and a non-zero `plan_x` | `points=0` → REFLECTION did not fill a repeated field (R2) |
| `all_defaults=1` | never | every kind field at its default → a `field_name` does not match the protobuf name (R2) |

**G5: a typed receipt with non-default fields.** If the app instead logs `error
reason=read: ...` or a protobuf parse exception, the gateway did not deliver the
typed message; that is R5, not an app bug. Do not spend the day on the Java path:
the fallback is the native C++ subscriber plus the loopback feed (RISKS R5, 2–3 h).

## 12. Prove the values are the published ones, all 43 fields (30 min)

`pull` reads the record from the app's own files directory, which belongs to the
IVI's current user (`am get-current-user`, user 10 on this image), and refuses a
file that does not start with a JSON record.

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

Compare with `<run_dir>/score/statePublisher.jsonl` for the same `kind` and
`sequence` (each kind has its own sequence):

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

Expected: `run/ivi_screen.mp4` (~40 s), `run/ivi_screen_logcat.txt` (epoch stamps)
and `run/ivi_screen_t0.txt` (the guest's real time just before and just after
`screenrecord` started; the clip has no usable creation time). `screenrecord` takes the
default display, the 1080 x 600 centre display; set `IVI_DISPLAY_ID` to a physical id
from `dumpsys SurfaceFlinger --display-id` only if it does not. Watch the clip: the two
clocks one above the other (IVI now, message publish real time), the receipt lag and
the plan age (both labelled as differences of two clocks), the plan path drawn to scale
with its metric grid (the spacing is printed under the panel), the freshness chip
(`LIVE`, or `STALE` when the newest HEALTH receipt is older than 0.5 s), health changing
on a stop, the plan frame and its image capture time. Recorded on the guest, nothing
retimed.

## 14. The judged run and the pull (30 min)

Start the S-CORE side's recorded run (out of this slice's scope), then:

```bash
./scripts/stage_ivi_observer.sh record 120        # optional second clip
./scripts/stage_ivi_observer.sh pull "$RUN_DIR/guest/observer.jsonl"
sha256sum "$RUN_DIR/guest/observer.jsonl" >> "$RUN_DIR/MANIFEST.sha256"
```

Expected: one record per receipt for the whole run, no `error` line after `ready`,
screen `receipts` equal to the file's `in.operational_state` lines. Copy
`run/aosp-tree-probe.txt`, `run/g1b-build.log`, `run/someip-config.decoded.txt` and
`run/core-image-identity.txt` beside it: they are the tree-specific evidence for
G1/G1b.

## 15. Teardown (15 min)

```bash
cd "$SLICE"; ./scripts/stage_ivi_observer.sh remove
cd "$BENCH"; ./scripts/launch_two_vms.sh down
cd "$SLICE"; ./scripts/stage_ivi_observer.sh unstage    # the app modules out of the AOSP tree
cd "$SLICE"; ./scripts/stage_sdv_core_interop.sh revert     # restores the AOSP tree
```

Keep `run/`: `aosp-tree-probe.txt`, `core-image-identity.txt`, `manifest-r.xml`,
`observer.jsonl`, `ivi_screen.mp4`, the logcat captures.

## 16. What is cut when a gate is late

| Gate | Limit | If missed |
|---|---|---|
| G0 | T+0.5 h | fix the artifacts; no VM time |
| G1 | T+1 h | a BLOCKER from the probe is an owner decision: option A (model amendment) or stop. Do not build. |
| G1b | T+2 h | read `run/g1b-build.log` against step 5's table, fix once (the dotted name is the likeliest), then report with the `vsidlc` output |
| G2 | T+1.5 h | stop; the S-CORE side is not ready, no guest work can help |
| G3 | T+6 h | record the stack/broker logs and the payload hexdump, report to the owner (ADR 0025 decision 4's trigger) and stop the slice |
| G4 | T+5 h | run with the known offset, mark cross-host comparisons unscoped, keep going (a measurement rule, not a path rule) |
| G5 | T+12 h | if the message is not typed: RISKS R5 (native subscriber, 2–3 h). If it is typed but empty: R2, report with the broker log |
| G6 | end of day 1 | the path works but the values differ: report with both records, do not adjust one side |

## 17. Rollback

`stage_sdv_core_interop.sh revert` restores `broker.vsidl`, `someip_acl.textproto`
and the stack config from `run/core-image-originals/`, and removes the staged
proto and mapping and the then empty `catalog/de4sdv_driving/`; the core image then
needs a rebuild to be clean.
`stage_ivi_observer.sh remove` deletes the two ACL files and the APK and reboots;
`stage_ivi_observer.sh unstage` removes the staged app modules from the AOSP tree.
Nothing in this slice alters the IVI image, so the IVI returns to its image state by
itself.
