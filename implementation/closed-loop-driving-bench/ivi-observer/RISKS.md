# Risks: option B (struct → REFLECTION → typed topic) in 2 days

Ordered by likelihood, each with the check that catches it early and what it costs.
The gates are the RUNBOOK's. "Likely" means more than one chance in three on this
bench as it now stands.

## R1. REFLECTION does not fill a repeated float, or reads strings without the BOM — likely

The AOSP page states the type-definition rules and the mapping example, but not the
translator's code path for a `repeated float` protobuf field filled from a
length-prefixed `FLOAT32` array, nor whether its string reader applies the AUTOSAR
BOM/NUL convention (the page only says "including byte order mark and
null-termination handling"). The whole option-B premise is that both work.

- **Detect:** `scripts/probe_aosp_tree.sh` §3/§4/§5 (before the build) prints the
  code and the branch; and gate G6, field by field: an array that arrives with 0
  elements, a string that arrives empty where the S-CORE log has text, or a
  `plan_reference` that arrives with a leading `U+FEFF` (or truncated by 4 bytes)
  is this risk and nothing else.
- **Cost if hit:** this is the fallback trigger. Option A (`fallback-a/`) needs a
  model amendment and the owner's decision, then ~4 h on the VM (the carrier build
  plus the app's decode path, which is entirely in `fallback-a/` and was already
  written). The 2-day timebox does not hold; say so at the decision.

## R2. The mw::com 4-byte prefix survives into the SOME/IP payload — unlikely once the publisher is patched

gatewayd's null serializer copies `data[0..size)` of the `PreSerializedData<2048>`
sample onto the SOME/IP payload without reading it, and someipd removes only
gatewayd's own 16-byte header. So the publisher decides the payload. Its library
frame carries a 4-byte little-endian length in front of the struct (the vectors in
`state-publisher/tests/vectors/*.bin`: frame 222 B, message 218 B); the shell now
sends the struct alone, `data[0..size)` = frame bytes 4.., `size` = the message
length (ICD §2, A31). An older shell that sends the whole frame puts the prefix on
the wire, and every event then fails in the broker (`Unknown BOM for string`).

- **Detect:** RUNBOOK step 7's hexdump. `00 00 00 02` first means the struct starts
  at 0 (right). A little-endian length first (`da 00 00 00`, `12 05 00 00`) means
  the prefix survived: an unpatched `state_publisher` is running.
- **Cost if hit:** rebuild and restart the patched publisher on the S-CORE host,
  not an AOSP change. Zero hours on this VM; the check is at T+3 h, not at G6.

## R3. The catalog does not compile or resolve the new type — medium

`vsidlc` must resolve `de4sdv.driving.v1.DrivingOperationalState` for
`broker.vsidl`'s `publisher` entry, and the pdk29 catalog accepts a publisher type
only if the message is a VSIDL publication with a max size on every string and a
max count on every repeated field. The stage script adds no module: the catalog's
`Android.bp` already takes every `**/*.proto` and `**/*.vsidl` below it, so the
proto and the mapping go into `catalog/de4sdv_driving/` as plain files (this
release registers no `proto_library` module type).

- **Detect:** gate G1b (`stage_sdv_core_interop.sh validate`) before the long build:
  `vsidl_rc_generator` and `vsidlc` over the whole catalog, the catalog's Rust
  crate, and the generated `someip-config.binpb` decoded.
- **Cost if hit:** 20–30 min per attempt. If the type cannot be registered at all,
  that is an owner-level finding about the reference stack, and the first fallback
  is option A.

## R4. The runtime refuses three service units of one publication type — possible

The broker creates one SDV publisher per offered event, so the mapping gives each
event its own service unit (`de4sdv-driving-operational-state-plan`, `-vehicle-state`,
`-health`) of the one type: one publisher per unit, as SINGLE_PUB requires. The
VSIDL model gives a SINGLE_PUB publication without `channels_enum` one channel only,
so three units of that type are not something the catalog declares; G1b cannot see
them (it checks the one `publisher` entry of `broker.vsidl`), and the run-time rule
is in `sdv_comms`, which is not in the AOSP source subset this slice read. The
one-unit form (`interop/variants/`) would put three publishers on one unit, which
SINGLE_PUB excludes outright.

- **Detect:** the broker's start log (`Failed to create publisher with
  service_unit_name ...`), then the app's three `subscribed unit=` lines (G5).
- **Cost if hit:** an owner decision: a `channels_enum` with three channels on the
  publication (a contract change, then a core rebuild), or the one-unit variant.

## R5. The typed message does not reach the Java app — possible

Three sub-causes, all silent at first: the ACL pair is wrong (root, duplicate,
topic name), the pushed app cannot bind the gateway (SELinux domain), or the
gateway's Java client does not hand a broker-published type to the parser the way
an app-published one arrives. The AEBS precedent proved the client against a
*bench* publisher, not against the SOME/IP broker's publication.

- **Detect:** the observer's own log within 30 s. `initComms` failing → SELinux or
  ACL root; `NOT_FOUND`/`No publication ...` → ACL or publication name;
  `error reason=read: ...`/parse exception → the client, not the app. `verify`
  greps `avc: denied` for the package.
- **Cost if hit:** 30–60 min per ACL iteration (the SD agent reads ACLs only at
  boot, ~3 min reboot). A SELinux denial is 2 h (policy + IVI image build). A
  client that cannot parse is the largest: the native C++ subscriber plus a
  loopback feed, 2–3 h — the sofa in `sepolicy/README.md` and `fallback-a/`'s
  reasoning still apply, and it keeps the app's screen and record.

## R6. The dotted message name is refused in `broker.vsidl` — possible

`publisher { message: "de4sdv.driving.v1.DrivingOperationalState" }` names a type
from another package than the declaration's. The AEBS precedent used a same-package
name, so the tree may have no example of the dotted form.

- **Detect:** probe §6 prints every `publisher { message: ... }` under the catalog's
  agent directory; `vsidlc` at G1b is the real answer.
- **Cost if hit:** a one-line change to the bare name (plus the package, if the
  grammar wants it) and a 20–30 min rebuild. Do not "fix" it by moving the proto
  into `com.android.sdv.someip`: the message name is the contract the model and the
  app use.

## R7. The peer address / VXLAN acceptance is wrong — possible

The core stack pins the S-CORE host's address and accepts the service only from it
(`secure-services` + `acceptances`). On the three-host bench the S-CORE host holds
`192.168.98.1` on the VXLAN segment and the guest host's bridge moves to
`192.168.98.254`. If that move was not made, two hosts claim `.1` on one segment and
the address the core accepts is ambiguous. The stage script has no default for the peer.

- **Detect:** RUNBOOK step 4, before any build. On the guest, `tcpdump` shows the
  handshake unanswered and no `REMOTE SUBSCRIBE`; SD offers may arrive and be
  ignored, which looks exactly like an ACL fault — that is why G2 exists first.
- **Cost if hit:** 15 min if found at step 4, one rebuild (20 min) later, because
  the address is in the image's stack config.

## R8. The core image build does not fit the disk or the day — possible

The AEBS bench measured ~30 GB peak for the clean build and had to prune the
`android-cuttlefish` Bazel cache after the owner's decision. Two products in one day
may need two out/ trees.

- **Detect:** `df -h /` at step 2, the script's 32 GB floor.
- **Cost if hit:** 1–2 h (prune + rebuild), and an owner decision if the prune is
  not authorized.

## R9. The IVI clock budget (20 ms) over a long run — likely over hours

At about 60 ppm the 20 ms budget lasts a few minutes after a setting; the AEBS
bench's first-ranked risk. Every cross-host number depends on it; the path does not.

- **Detect:** `set_ivi_clock.sh drift` (two measures a session apart), the printed
  offset and uncertainty at start.
- **Cost if hit:** session sizing, not a path change; a run outside the bound is
  void for cross-host comparison and must say so.

## R10. The screen does not show or record what is expected — possible

The app may start off-screen, the panel may sleep, or `screenrecord` may capture a
black frame. New in B: the plan path is drawn from floats that are non-finite or all
zero if the translation failed, so the panel is blank rather than wrong.

- **Detect:** `dumpsys window | grep mCurrentFocus` in `start`; watching the first
  40 s clip at step 13 (the mp4 is reviewed, never assumed).
- **Cost if hit:** 20–30 min (stay-awake, `am start`, launcher metadata).

## R11. A u32 field wraps or a value is unsigned-but-negative — unlikely

Every number is UINT32. `publish_real_s` in 2026 is 1.76e9 < 2^31, `_ns` < 1e9, and
`step_capture_ms` reaches 2^31 only after 24 days of simulation, so nothing on this
bench wraps. The trap is on the reader side: protobuf's `uint32` arrives as a signed
Java `int`, so `MessageMapper` converts with `Integer.toUnsignedLong` — without
that, a value above 2^31 would print negative and the evaluator would see a
different number from the publisher's.

- **Detect:** `StateRecordTest.unsignedValuesAboveTwoPow31StayPositive` (offline);
  G6 compares against the publisher's own integers.
- **Cost if hit:** minutes; the test exists so it is not hit at the gate.

## R12. The typed message is larger than the stack or the topic allows — unlikely

A full 64-point plan is 1301 bytes of struct; the largest vector is 1390 bytes of
struct (`plan_max_strings`, 1394 with the library frame's prefix, which is not
sent), well under the S-CORE `PreSerializedData<2048>` bound. The typed message
carries the catalog's size annotations (strings 128 bytes, arrays 64 elements), from
which the broker takes its publication's message size.

- **Detect:** G6's plan receipt decodes with 64 points; a truncated array or a
  short read is this risk. The codec's sizes are asserted in the local test.
- **Cost if hit:** a stack buffer setting (`max-payload-size`), one rebuild.

## R13. The evidence does not identify itself — possible, and cheap to avoid

The AEBS bench's known limit: the IVI identity and the relay digests were recorded
by hand. This slice records the APK sha256 (host and guest), the IVI fingerprint,
both ACL digests (`run/ivi-observer-identity.txt`), the core identity at build
(`run/core-image-identity.txt`) and now the tree probe (`run/aosp-tree-probe.txt`).

- **Detect:** the three files exist at step 14's pull.
- **Cost if hit:** 10 min, at the end, when it is most annoying.

## Cross-cutting: what a failure does **not** mean

A missed gate is not evidence that AAOS SDV cannot do a typed topic. G3 failing is
an interoperability finding about the reference stack and someipd (ADR 0025 decision
4 names that trigger); G5 failing with a parse error is a finding about one client
library; G6 failing on strings or arrays only is a finding about the broker's
REFLECTION translator. Each is reportable on its own, and none is a conformance or
safety statement. Do not paper over any of them by decoding bytes in the app: that
is option A, and it needs the owner.
