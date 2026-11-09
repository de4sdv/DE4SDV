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

## R2. The mw::com 4-byte prefix survives into the SOME/IP payload — likely

ICD §2 says the publisher's event payload is `PreSerializedData<2048>`: bytes 0–1 a
little-endian length, the struct from byte 4. ICD §3 says the SOME/IP payload is the
struct with no prefix. The vectors in `state-publisher/tests/vectors/*.bin` confirm
the host-side frame is `length + struct` (frame 222 B, message 218 B), so the
gateway must drop four bytes — and gatewayd is not in the AOSP tree.

- **Detect:** RUNBOOK step 7's hexdump. `00 00 00 02` first means the struct starts
  at 0 (right). A little-endian length first means the prefix survived: the broker
  would then read `schema_major = 0x0000xxxx` and every field would be shifted.
- **Cost if hit:** an S-CORE-side change (strip the prefix at gatewayd before the
  SOME/IP event), not an AOSP change. Zero hours on this VM; the slice waits on the
  other side, which is why the check is at T+3 h and not at G6.

## R3. The catalog does not compile or resolve the new type — medium

Soong only sees modules in an `Android.bp` in the directory, and `vsidlc` must
resolve `de4sdv.driving.v1.DrivingOperationalState` for `broker.vsidl`'s `publisher`
entry. The scripts append a `proto_library`-shaped module (`CATALOG_MODULE_KIND`),
but the shipped catalog may use another kind, or the broker bundle may compile its
own proto list that the new file is not in. No offline tree can settle it.

- **Detect:** RUNBOOK step 3 §6 prints the catalog's own module kinds and proto
  lists; gate G1b builds the module before the 1.5 h image build.
- **Cost if hit:** 20–30 min per attempt (module kind, then the bundle's proto
  srcs). If the type cannot be registered at all, that is an owner-level finding
  about the reference stack, and the first fallback is option A.

## R4. vsidlc refuses three offered events on one topic parameter — possible

The mapping gives three `offered_event` blocks one `sdv_topic_parameterization` key;
the documented examples use one event per topic. Nothing says three may share one.

- **Detect:** `vsidlc`/G1b, before the long build.
- **Cost if hit:** regenerate with three topic parameters (one generator change,
  ~20 min) plus three subscriptions in the app (~30 min) and a rebuild.

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
(`secure-services` + `acceptances`). On the three-host bench that address is new: it
is not the guest host, and the AEBS default (`192.168.98.1`) is.

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

A full 64-point plan is 1301 bytes of struct (1305 with the S-CORE frame prefix);
the largest vector is 1394 bytes (`plan_max_strings`), well under the S-CORE
`PreSerializedData<2048>` bound. The typed message has no `variable_type_max_size`
annotation because it is not a bytes field.

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
