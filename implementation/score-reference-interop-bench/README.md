# DE4SDV S-CORE reference interoperability bench

This bench holds the DE4SDV-owned software of the Eclipse S-CORE member of
INC-MW-011 (MW-CONFIG-002) and the CI that builds and exercises it. Its first
part is the AutowareToSCORE adapter: one process that is an S-CORE
communication (mw::com) application and a ROS 2 node. The bench answers one
question early: can one process host both libraries, with baselibs'
`aborts_upon_exception` linked (REQ-MW-018, GAP-MW-035)?

Status: CI regression and design data on GitHub-hosted runners. It is not
evidence of record, it verifies no requirement, and every result stays draft
until independent review.

## What the adapter does

The adapter realizes the phase-8 ports of
[`middleware_score_physical_software_realization.sysml`](../../textual-notation-of-model/packages/features/middleware/middleware_score_physical_software_realization.sysml),
one to one:

| Port | Realization |
|---|---|
| `referenceSpeedIn` | mw::com proxy of `de4sdv/reference_vehicle_speed`, one event, sample `speed_kmh` (double) |
| `middlewareVelocityStatusOut` | `/de4sdv/middleware/velocity_status`, `autoware_vehicle_msgs/msg/VelocityReport`, reliable, depth 10; `longitudinal_velocity` is the float32 of `speed_kmh / 3.6`, stamp is the receipt time, `frame_id` is `base_link` |
| `aebsSignalFrameIn` | TCP client of 127.0.0.1:4721; the 4-byte little-endian length prefix only delimits the frames |
| `aebsSignalFrameOut` | mw::com skeleton of `de4sdv/aebs_signal_frame`, event type `PreSerializedData<2048>`, 20 sample slots; a sample holds prefix and frame |

The node creates no other publisher or subscription. Its parameter event
publisher and `/rosout` are off. Its parameter services stay, because the
abort matrix uses them.

The adapter follows the three LoLa rules of the model:

1. Stored samples (GAP-MW-039): the first stable read after each entry into
   the subscribed state discards the samples that the provider sent before.
   The controller counts each leave of the subscribed state, so a provider
   restart gets its own discard read. A read that does not stay in one
   subscribed phase is dropped. As the model states, a sample that arrives
   during the discard read is lost.
2. Shutdown (GAP-MW-041): SIGTERM sets a flag only. The main thread then
   unsets the receive handler, calls `Unsubscribe()`, waits for the
   not-subscribed state and destroys the proxy. Then it stops the frame path
   and ROS 2 and exits with 0. It never destroys a subscribed proxy.
3. Frame provider: the skeleton is offered once at start. A lost frame stream
   leads to a reconnect with backoff (100 ms to 2 s), never to a stop of the
   offer. The skeleton goes only at exit. A frame without a free sample slot
   is dropped and counted (GAP-MW-037).

The adapter withholds a sample whose float32 value is not finite: NaN, +inf
and -inf (REQ-MW-011), and also a finite value beyond the float32 range,
which would otherwise become an infinity. The model names only the
non-finite samples; the range case is open for the architect.

## Build route

S-CORE builds with Bazel and its own LLVM toolchain, which links libstdc++
statically into executables. ROS 2 Humble links the shared libstdc++. So
the adapter is built in two steps, and the process holds one libstdc++:

1. The CI copies the DE4SDV overlay (`interface/`, `adapter/facade/`,
   `provider/`, `config/`) into a throwaway checkout of
   `eclipse-score/inc_someip_gateway` at `d9eac670b7534352749da3d30f52aebf5129f168`
   as the package `//de4sdv_score_bench`. Only new files appear there, and no
   S-CORE file enters this repository. Bazel 8.6.0 builds two
   `cc_static_library` archives with the gateway's toolchain, communication
   0.5.0 and baselibs 0.2.16: the facade with mw::com, and baselibs'
   `abortsuponexception`. The facade header uses plain types only.
2. The ament_cmake package [`adapter/de4sdv_score_adapter`](adapter/de4sdv_score_adapter)
   links the two archives with g++ 12, rclcpp and `autoware_vehicle_msgs`.
   The abort archive comes first, as a whole archive, and the link exports
   `__cxa_allocate_exception`. So a throw inside `librclcpp.so` or
   `libstdc++.so` also binds to the override.

The same overlay builds the vehicle-speed provider, an S-CORE application
outside the system of interest, and the gateway configuration binary. The
[`launch-manager/`](launch-manager) package goes into a checkout of
`eclipse-score/lifecycle` v0.6.1 (`432c85d91db8bd72a39a61f245eaf119a570b88d`);
lifecycle's own tool checks and serializes the Launch Manager configuration
of the layer. That configuration starts someipd, gatewayd and the adapter in
that order, and the health proxy node. The fallback Run Target holds only
the health proxy node. The wrapper scripts of the components and the health
proxy node come with the next steps.

## Layout

| Path | Content |
|---|---|
| `interface/` | DE4SDV mw::com service interfaces of the reference vehicle speed and the AEBS signal frame |
| `adapter/facade/` | Facade header and its mw::com implementation, Bazel overlay |
| `adapter/de4sdv_score_adapter/` | ament_cmake package: pure core, adapter executable, control build, unit tests |
| `provider/` | Vehicle-speed provider (Bazel overlay) |
| `config/` | mw::com configurations, gateway configuration, vsomeip loopback configuration for CI, Fast DDS UDP-only profile for the startup probe |
| `launch-manager/` | Launch Manager configuration (lifecycle overlay) |
| `src/de4sdv_score_bench/` | Pure Python evaluators of the abort matrix, the soak and the SOME/IP receiver runs |
| `scripts/` | CI build steps and the runners: abort matrix, soak, middleware startup probe, SOME/IP receiver runs |
| `tests/` | Evaluator unit tests |
| `someip-receiver/` | DE4SDV minimal SOME/IP receiver of the AAOS SDV guest: pure core, POSIX shell, gtest suites, golden fixtures, `Android.bp` and init script |

## Pure core and its tests

The core holds the speed translation, the frame splitter and the controllers
of the three LoLa rules. It uses no S-CORE and no ROS 2 header; ports
connect it to the facade and to rclcpp. Its gtest suites run with `colcon
test`. In a ROS 2 Humble environment without the facade:

```bash
colcon build --packages-select de4sdv_score_adapter --cmake-args -DDE4SDV_BUILD_ADAPTER=OFF
colcon test --packages-select de4sdv_score_adapter && colcon test-result --verbose
```

The evaluator tests need Python 3.10 or later and pytest:

```bash
pytest -q implementation/score-reference-interop-bench/tests
```

## Abort matrix, soak and startup probe

The workflow `.github/workflows/score-reference-interop-bench.yml` runs on
pull requests that change this directory, on ubuntu-22.04, without
secrets. Every bench process runs as the non-root runner user. ROS 2 Humble
comes from the ROS snapshot of 2026-10-12.

- Abort matrix (rehearsal of VC-MW-019): three exceptions, each inside a
  try/catch. The first is an undeclared parameter that rclcpp throws and
  catches in its parameter service; the fault hook is off. The second is a
  throw in adapter code, and the third is `std::vector::at` inside the shared
  libstdc++. These two use the fault hook, which only
  `DE4SDV_ADAPTER_FAULT_HOOK=1` enables; the adapter logs the setting at
  start. A variant passes when the adapter ends with SIGABRT after the
  trigger, with a core whose top frames are `abort ← __cxa_allocate_exception`
  of the executable and the expected thrower below. The same adapter
  without the override must survive all three, so the matrix discriminates.
- Soak: 30 minutes with someipd and gatewayd on the host loopback, the
  provider at 10 Hz, the synthetic frame source and an independent observer.
  A throw on a normal path of any linked library aborts the adapter, so the
  soak fails then and names the thrower.
- Startup probe: the adapter with the override under several ROS 2
  middleware setups, as first ROS 2 participant on the host and after
  another one.

The runners write raw artifacts (adapter log, provider and observer records,
backtraces) and evaluate them with `src/de4sdv_score_bench`. The outcomes use
the evidence outcome names of the middleware verification model.

## Claim boundary

Shown by a passing run, on a GitHub-hosted ubuntu-22.04 runner only: the
build and link of one adapter process with S-CORE communication and ROS 2,
the exported override, the abort mechanism for the three variants, and the
absence of an abort over the soak in the tested ROS 2 middleware setup.

Not shown: any requirement of INC-MW-011 as verified, the behavior on the
bench VM, the guest side, the SOME/IP crossing, the Launch Manager at run
time, the health proxy node, and the timing of any case. No safety,
cybersecurity, compliance or certification claim is made.

## SOME/IP receiver of the AAOS SDV guest

The guest needs a SOME/IP client that receives the AEBS signal frames from
someipd on the Linux host. It hands them to the HMI ingress on the guest
loopback. [`someip-receiver/`](someip-receiver) is a small DE4SDV receiver
for this: portable C++17 on POSIX sockets, without Boost and without
vsomeip. The owner has not yet decided between this receiver and a port of
vsomeip to AOSP.

What the receiver does:

- It connects TCP to the reliable endpoint of the frame event, then sends
  SubscribeEventgroup with an IPv4 endpoint option that names the local end
  of that connection. It handles Ack and Nack, and renews the subscription
  every second for a TTL of 3 s. A TTL that ends without an Ack ends the
  subscription.
- It listens for offers of the configured server. Without an offer, it
  tries the configured server every 500 ms (the unicast fallback for a guest
  that receives no multicast). A StopOffer, a Nack, a closed connection or a
  reboot of the server ends the connection, and the receiver starts again.
- It reassembles SOME/IP over TCP, checks that the 4-byte little-endian
  length prefix counts the bytes of the frame, and reads `sequence` and
  `frame_timestamp_ns` with a minimal protobuf wire reader.
- It serves one client on 127.0.0.1:4731. It forwards each payload unchanged,
  prefix and frame. It holds no queue: a frame without a client is dropped.
- Every frame ends delivered or dropped with one reason, and a counter per
  reason shows it. The start line repeats the whole configuration.

The discard rule is a separate component (`FrameDiscardPolicy`). It is
`receiverSubscriptionPhaseDiscardRule` of the phase-8 realization model:

- A subscription phase holds while the receiver is subscribed at someipd and
  the ingress is its only loopback client. The phase starts when the second
  of the two conditions starts to hold, and ends when one of them ends. The
  receiver takes the phase start from its own `CLOCK_REALTIME`, the clock
  with which the frame assembler stamps `frame_timestamp_ns` on the host.
- The receiver is not subscribed at its start. A Nack, the loss of the TCP
  connection to someipd, a StopOffer, or the end of the TTL of the last
  acknowledged subscription ends the subscription. The next Ack starts it
  again; the Ack of a renewal changes nothing.
- A second client is refused while one is connected. It is not served and
  starts no phase.
- Outside a phase, the receiver reads every frame and drops it.
- In a phase, it serves a frame unchanged only if its `frame_timestamp_ns`
  is not earlier than the phase start less 20 ms, the bound of ASM-MW-030,
  and the frame is no copy of a frame served in this phase. A copy has the
  same `sequence` and the same `frame_timestamp_ns`. The rule does not
  filter on sequence order, so a test of REQ-MW-014 still sees each gap and
  each change of order.
- It drops a frame whose `sequence` or `frame_timestamp_ns` has no positive
  value.

The copy memory keeps the 40 frames served last in the phase. A copy comes
only from the stored frames that a new subscription in the host half reads
after a restart during the phase (GAP-MW-039). A stored frame is still in a
sample slot, and each of the two LoLa hops of the frame path has 20 slots:
the adapter's frame event and gatewayd's bridged service. So a copy repeats
one of the 20 newest frames of its hop, and 40 frames cover both hops. The
receiver logs each phase start and end, and each dropped frame with its
reason.

The receiver sets the ingress host property itself once its loopback server
listens (`--announce-property`, Android only), because the ingress exits when
nothing listens. The init script sets the port property.

Build and test the receiver with CMake and GTest (Ubuntu: `libgtest-dev`):

```bash
cmake -S implementation/score-reference-interop-bench/someip-receiver -B build/someip-receiver -G Ninja
ninja -C build/someip-receiver && build/someip-receiver/de4sdv_someip_receiver_tests
```

`Android.bp` builds the same sources as a native binary (liblog only) with
`de4sdv_someip_receiver.rc`, an init script for the eng or userdebug image:
`seclabel u:r:su:s0`, a service that init restarts, the ingress property
`de4sdv.aebs.frame_server.port=4731`, and
`de4sdv.aebs.frame_server.host=127.0.0.1` through the receiver.

### Runs against the real someipd

Three jobs of the workflow cover the receiver. `someip-receiver-unit` builds
it with g++ and runs the gtest suites; this binary goes to the namespace runs.
`someip-receiver-clang` builds and tests it with clang++. The third job,
`someip-receiver-interop`, runs `scripts/run_someip_receiver_interop.py` as root
with the runtime bundle of the build job. The script creates a "host" and a
"guest" network namespace, joined by a veth pair, with a route for
224.0.0.0/4 in both. Every bench process runs as the non-root runner user.

- Host namespace: someipd with service discovery on and the unicast address
  10.250.0.1 (`config/vsomeip_netns_host.json`), gatewayd, the adapter, and
  `scripts/visualization_frame_source.py`. The source sends VisualizationFrame
  encodings of 64 to 2044 bytes, because the receiver reads `sequence` and
  `frame_timestamp_ns`.
- Guest namespace, with a private `/tmp` and `/dev/shm`: the receiver and
  `scripts/loopback_frame_recorder.py`, a loopback client that reads the
  stream as the ingress does and records every frame.
- A capture of the link on the host end, and a record of the LoLa shared
  memory files that someipd, gatewayd and the adapter map.

Each case starts a fresh stack:

| Case | What it shows |
|---|---|
| `identity` | 200 frames reach the client byte for byte, in order, with the 2044-byte frames |
| `resubscribe` | after a receiver restart by SIGTERM, one by SIGKILL, a restart of the gateway pair and a 5 s link outage, the receiver subscribes again and delivery resumes; no frame comes twice; every drop has a reason |
| `no_client` | frames without a client are dropped and not queued; the client receives no frame produced before it connected |
| `stored_samples` | frames go into the adapter before gatewayd starts; then gatewayd restarts beside the running someipd in the phase (a stimulus outside the operating rules), so that its stored frames repeat served frames; then the gateway pair restarts. Per step, the stored frames are counted, and the rule drops the copies and the frames older than the new phase |
| `ttl_renewal` | without multicast offers, the receiver renews its subscription over five TTLs, without a lapse or a gap |

`src/de4sdv_score_bench/someip_receiver_interop.py` evaluates the raw records
of each case. A case also fails on a "Failed to subscribe" line of gatewayd,
on LoLa shared memory that the adapter, gatewayd and someipd do not share, on
any frame at the client that is not byte-identical to a source frame, on a
frame served outside a phase or older than its phase start less 20 ms, and on
a copy served in a phase. The results list the phase starts of each case. A
frame that the AEBS stack produced in the 20 ms before a phase start (the
band of GAP-MW-045) is reported, not failed.

Both namespaces share the clock of one kernel, so ASM-MW-030 holds in these
runs by construction. They do not measure a host-guest clock offset.

### Claim boundary of the receiver runs

These runs are CI regression and design data on GitHub-hosted ubuntu-22.04
runners. They are not evidence of record, they verify no requirement, and
every result stays draft until independent review.

Shown by a passing run: the receiver's interoperation over a veth pair with
the someipd and gatewayd of the bundle, on Linux, with the discard rule of
the model, on one clock. Not shown: the Android build of the receiver, the
AAOS SDV guest, the Cuttlefish network, the HMI ingress, the clock offset of
a real guest (ASM-MW-030), and any timing of record. No safety,
cybersecurity, compliance or certification claim is made.
