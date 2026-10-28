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
| `middlewareVelocityStatusOut` | `/de4sdv/middleware/velocity_status`, `autoware_vehicle_msgs/msg/VelocityReport`, reliable, depth 10; `longitudinal_velocity` is the float32 of `speed_kmh / 3.6`, stamp is the receipt time in system time, `frame_id` is `base_link` |
| `aebsSignalFrameIn` | TCP client of 127.0.0.1:4721; the 4-byte little-endian length prefix only delimits the frames |
| `aebsSignalFrameOut` | mw::com skeleton of `de4sdv/aebs_signal_frame`, event type `PreSerializedData<2048>`, 20 sample slots; a sample holds prefix and frame |

ROS 2 endpoints: the node starts without parameter services, without a
parameter event publisher and without `/rosout`, as the model's conditions of
the one-process adapter set. So the node has its VelocityReport publication
and one more endpoint: rclcpp's time source subscribes to
`/parameter_events`. There the time source reads only this node's
`use_sim_time`, and it logs a value of a wrong type without a throw. A peer
can still switch the node's clock to `/clock` that way; the inspection on
the bench VM keeps that open. The stamps do not depend on it: the adapter
stamps each VelocityReport from a clock of system time (`RCL_SYSTEM_TIME`),
not from the node clock. The soak checks the endpoints with
`ros2 node info`.

With parameter services, any ROS 2 process on the host could abort the
adapter: for a request that names an undeclared parameter, rclcpp throws and
catches `ParameterNotDeclaredException` inside the service, and the override
turns that throw into an abort. The adapter has no parameter services, also
not in the abort matrix. The health proxy node will start with the same node
options.

One way to abort the adapter stays. rmw_cyclonedds_cpp 1.3.5 takes samples
of other participants on the `ros_discovery_info` subscription of its
context (rmw_node.cpp:849 and 1261) and on `/parameter_events`. Both go
through a deserialization that throws and catches (serdata.cpp:383-389).
With the override linked, one malformed sample from any DDS participant in
the domain aborts the adapter. That is outside normal operation, and no
configuration of ROS 2 Humble removes it. With DDS on the loopback, only
processes on the host can send such a sample. The bench makes no claim about
it.

The adapter follows the three LoLa rules of the model:

1. Stored samples (GAP-MW-039): the first stable read after each entry into
   the subscribed state discards the samples that the provider sent before.
   The discard goes on while the reads are full (5 samples), because a full
   read can leave more stored samples behind. The first read with fewer
   samples ends it. The controller counts each leave of the subscribed
   state, so a provider restart gets its own discard. A read that does not
   stay in one subscribed phase is dropped. As the model states, a sample
   that arrives just before or during a discard read is lost.
2. Shutdown (GAP-MW-041): SIGTERM sets a flag only. The main thread then
   unsets the receive handler, calls `Unsubscribe()`, waits for the
   not-subscribed state and destroys the proxy. Then it stops the frame path
   and ROS 2 and exits with 0. It never destroys a subscribed proxy.
3. Frame provider: the skeleton is offered once at start. After a failed
   connect or a lost frame stream, the client waits before the next
   attempt. The delay doubles from 100 ms to 2 s, and it goes back to 100 ms
   only after a complete frame came over a connection. A lost stream never
   stops the offer. The skeleton goes only at exit. A frame without a free
   sample slot is dropped and counted (GAP-MW-037).

LoLa delivers at most 5 new samples in one read, the newest ones, and skips
the older new samples for good. So a burst of more than 5 speed samples
between two reads of the adapter loses its oldest samples, and the adapter
cannot count them. The adapter reads at once on the receive handler, and at
least every 20 ms; the provider of the bench sends every 100 ms.

The INC-AEBS-010 frame server serves its newest client. A second client of
127.0.0.1:4721 takes the stream from the adapter, and the adapter then gets
no frame and no end of stream. So the adapter must be the only client of the
frame server; the soak checks that with `ss -tnp` at each liveness check.

The adapter withholds a sample whose float32 value is not finite: NaN, +inf
and -inf (REQ-MW-011), and also a finite value beyond the float32 range,
which would otherwise become an infinity. The model names only the
non-finite samples; the range case is open for the architect.

Exit codes: 0 is a clean stop on SIGTERM or SIGINT. The Launch Manager
treats every other end as a failure of the component.

| Code | Cause |
|---|---|
| 2 | Bad command line, or the mw::com configuration file cannot be read |
| 3 | The speed proxy stayed subscribed after `Unsubscribe()` (second rule); the process ends without destructors |
| 4 | The frame skeleton cannot be created or offered |
| 5 | mw::com refuses the state handler, the receive handler or the subscription of the speed proxy; the adapter cleans up by the second rule and ends, without a retry in the process |

Logging: the adapter writes its own events to stdout, one JSON object per
line. mw::log writes its own text lines to stdout too. The adapter's
mw::log configuration [`config/mw_log_adapter.json`](config/mw_log_adapter.json)
(console, warnings and above) comes through `MW_LOG_CONFIG_FILE`. rclcpp and
CycloneDDS write to stderr. The evaluators read only the JSON event lines.

## ROS 2 environment

Every ROS 2 process on the bench host runs in one ROS 2 environment:
Autoware, the ROS 2 processes of the middleware integration layer, and the
ros2 command line tools with their daemon. For a shell it comes from
[`config/ros_environment.sh`](config/ros_environment.sh), sourced after
`/opt/ros/humble/setup.bash` and before the first ros2 command. The CI
runtime jobs source it for every ROS 2 process they start. It sets:

- `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`. Fast DDS 2.6 throws and catches
  on its normal startup path in two places: its shared-memory transport
  opens its port with `open_only` and creates the port in the catch, and its
  UDP transport catches the error of a port that is taken. In the startup
  probe the adapter aborted at start with the default transports of Fast DDS
  (the shared-memory transport), and with a UDP-only profile after another
  participant (the port probe). With the UDP-only profile as first
  participant, it started and stopped with 0. `rmw_cyclonedds_cpp` is C++
  too and showed no throw in the tested setups.
- `ROS_DOMAIN_ID=91`, one fixed domain, as the AEBS Autoware benches.
- `CYCLONEDDS_URI` to [`config/cyclonedds.xml`](config/cyclonedds.xml), the
  configuration of the AEBS Autoware benches. It keeps DDS on the loopback
  interface and sets `MaxAutoParticipantIndex` to 120. On the loopback,
  which has no multicast, CycloneDDS 0.10.5 gives each process an automatic
  participant index. With the default (`MaxAutoParticipantIndex` 9), at
  most 9 processes get a participant: a bind at the last index fails too
  (q_init.c:1609, 1627-1631). The next process gets no participant, so
  rclcpp throws, and in the adapter that is an abort at start. This file's
  120 allows 120 processes, more than the bench runs. The startup probe
  measured 9 of 11 with the default.
- No `ROS_LOCALHOST_ONLY`, as the AEBS Autoware benches. With
  `ROS_LOCALHOST_ONLY=1`, rmw_cyclonedds_cpp 1.3.5 adds the address
  127.0.0.1 to the interface that `cyclonedds.xml` selects, and CycloneDDS
  0.10.5 refuses that ("the same interface may not be selected twice"). So
  no participant is created, and the adapter aborts. The startup probe shows
  it.

The Launch Manager starts the executable of each component directly, with
its arguments, and passes it only the environment variables of its
configuration, as literal values. So
[`launch_manager_config.json`](launch-manager/launch_manager_config.json)
gives each component what it needs:

- someipd and gatewayd: the library directory of the bundle, because their
  RUNPATH points into the Bazel output tree; someipd also
  `VSOMEIP_CONFIGURATION`, for now the loopback configuration of CI.
- The adapter and the health proxy node: the ROS 2 environment above, with
  the paths of the bench directory, a directory for their ROS 2 logs
  (`ROS_LOG_DIR`) and, for the adapter, its mw::log configuration.

[`scripts/render_launch_manager_config.py`](scripts/render_launch_manager_config.py)
adds, for the host it runs on, the ROS 2 setup to the adapter and the health
proxy node: the variables that `/opt/ros/humble/setup.bash` sets (library and
package paths, PATH, ROS_DISTRO and the like), as literal values. It also
sets the bench user as the sandbox user. The CI renders the configuration on
its runner, and lifecycle's own tool checks the rendered file against its
schema and serializes it. Literal values, and no wrapper scripts, for two
reasons: the Launch Manager's own check then sees every variable, and no
shell stands between the Launch Manager and the process, so its SIGTERM and
the end of the process are those of the component itself. Unit tests keep
the configuration in step with `ros_environment.sh`, and `cyclonedds.xml` in
step with that of the AEBS benches. The Launch Manager path is not run yet.

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
   `abortsuponexception`. The facade header uses plain types only. The build
   checks that the facade archive defines none of four libstdc++ sentinel
   functions.
2. The ament_cmake package [`adapter/de4sdv_score_adapter`](adapter/de4sdv_score_adapter)
   links the two archives with g++ 12, rclcpp and `autoware_vehicle_msgs`.
   The abort archive comes first, as a whole archive, and the link exports
   `__cxa_allocate_exception`. So a throw inside `librclcpp.so` or
   `libstdc++.so` also binds to the override.

The bench builds at `d9eac670` with baselibs 0.2.16, the pin of the phase-8
revision of the model. The phase-8 text before that revision cites
`951fbc09` with baselibs 0.2.15. The `aborts_upon_exception` tree of
baselibs is the same in both versions.

The same overlay builds the vehicle-speed provider, an S-CORE application
outside the system of interest, and the gateway configuration binary. The
mw::com configurations set the ASIL level per service instance only. That is
an mw::com setting: `QM` selects LoLa's QM path. It is not a safety
classification.

The [`launch-manager/`](launch-manager) package goes into a checkout of
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
| `config/` | ROS 2 environment and CycloneDDS configuration of the host, mw::com and mw::log configurations, gateway configuration, vsomeip loopback configuration for CI, Fast DDS UDP-only profile for the startup probe |
| `launch-manager/` | Launch Manager configuration (lifecycle overlay) |
| `src/de4sdv_score_bench/` | Pure Python evaluators of the abort matrix, the refused subscription, the startup probe, the soak and the SOME/IP receiver runs |
| `scripts/` | CI build steps (runner only), the runtime facts, the renderer of the Launch Manager configuration and its load check, and the runners, also of the SOME/IP receiver runs |
| `tests/` | Evaluator unit tests |
| `someip-receiver/` | DE4SDV minimal SOME/IP receiver of the AAOS SDV guest: pure core, POSIX shell, gtest suites, golden fixtures, `Android.bp` and init script (not built by CI) |

## Pure core and its tests

The core holds the speed translation, the frame splitter, the frame stream
client, the controllers of the three LoLa rules, the exit codes and the fault
signals of the abort matrix. It uses
no S-CORE and no ROS 2 header; ports connect it to the facade and to rclcpp.
Its gtest suites run with `colcon test`. In a ROS 2 Humble environment
without the facade:

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
pull requests that change this directory (a change of Markdown files only
does not start it), and by hand. It runs on ubuntu-22.04, without secrets.
Every bench process runs as the non-root runner user. ROS 2 Humble comes
from the ROS snapshot of 2026-10-12. Each runtime job records its runner
image, kernel, loopback flags, shared libstdc++ (version and SHA-256), gdb
and ROS 2 environment.

- Abort matrix (rehearsal of VC-MW-019): the adapter runs with the start
  configuration of a member run. A real-time signal selects one of three
  throws of its fault hook, each inside a try/catch: SIGRTMIN+1 calls
  `rclcpp::Node::get_parameter` for an undeclared parameter, so rclcpp
  throws `ParameterNotDeclaredException` inside `librclcpp.so`; SIGRTMIN+2
  throws in adapter code; SIGRTMIN+3 calls `std::vector::at` out of range,
  so the shared libstdc++ throws. The adapter logs these signals at start.
  Only a process of the same user, or root, can send them, and such a
  process can end the adapter anyway. A variant passes when the adapter ends
  with SIGABRT after the signal, with a core whose top frames are `abort`,
  then `__cxa_allocate_exception` at an address inside the executable, then
  the expected thrower, also located by its address in the core's mappings.
  The same adapter without the override must survive all three. The gate
  passes only when both hold, with one result per role and variant.
- Refused subscription: the provider offers 4 sample slots, the adapter asks
  for 5, so LoLa refuses the subscription. The check passes when the adapter
  logs the refused step and ends by itself with exit code 5.
- Soak: someipd and gatewayd on the host loopback, the provider at 10 Hz,
  the synthetic frame source and an independent observer; 600 s on a pull
  request, 1800 s by default by hand. The adapter runs as in a member run,
  without parameter services. The soak passes only when all of these hold:
  - `ros2 node info` shows the adapter node with its publication and the
    time source subscription only.
  - Each received VelocityReport pairs with one provider sample, in order:
    the same value, sent after the subscription, received within half the
    value repeat time. No VelocityReport pairs twice, no provider sample is
    missing between the first and the last paired one, and the observer
    received no more than the adapter published.
  - Every process lived at every check. gatewayd subscribed the frame event,
    someipd subscribed gatewayd's bridged event, and gatewayd logged no
    failure line. The one exception is a start-up race: until someipd's
    subscription takes effect, gatewayd drops a frame that comes, with "No
    client subscribed for event". The runner counts these lines one second
    after someipd logs its subscription, and the soak reports them as
    pre-subscription drops; a later line of that kind fails the soak.
  - The adapter forwarded the first frames of the source, in number and
    bytes, without an allocation failure or a lost stream.

  A throw on a normal path of any linked library aborts the adapter, so the
  soak fails then and names the first named frame below the override. The
  soak turns the cores of the other bench processes into backtraces too.
- Startup probe: the adapter in the bench environment as first ROS 2
  participant, after 11 others and before 11 others. Two controls must fail:
  the bench configuration without `MaxAutoParticipantIndex` after 11 others,
  and the bench environment with `ROS_LOCALHOST_ONLY=1`, whose log must hold
  the error of the second interface. Fast DDS runs with its default
  transports and `ROS_LOCALHOST_ONLY=1`, and with a UDP-only profile; each
  failing Fast DDS setup also runs with the control build, which must
  survive it.

The runners write raw artifacts (adapter log, provider and observer records,
backtraces and core mappings) and evaluate them with `src/de4sdv_score_bench`.
The outcomes use the evidence outcome names of the middleware verification
model.

## Bench VM

The `ci_*` scripts are for a disposable CI runner only. They install
packages, write `~/.bazelrc` and put bazelisk in `/usr/local/bin`, so each
one refuses to run unless `GITHUB_ACTIONS=true` or its first argument is
`--runner`. On the shared bench VM that would redirect every Bazel run,
android-cuttlefish with its large output base among them, and shadow the
VM's own Bazel. A bench session on the VM takes its own path, and nothing
goes into `$HOME` or `/usr/local`:

- Bazel: bazelisk (v1.29.0, checked by digest) in a bench directory, with
  `BAZELISK_HOME` in that directory, and the Bazel options in a bench
  bazelrc that the build names with `bazel --bazelrc=<bench>/bazelrc`, or in
  a `.bazelrc` inside the throwaway checkout: the output base, the disk cache
  and the repository cache all in the bench directory.
- ROS 2 setup of the Launch Manager configuration: render it with the setup
  script that holds `autoware_vehicle_msgs`. On the VM that is the Autoware
  workspace (`--ros-setup ~/autoware/install/setup.bash`, which also sources
  `/opt/ros/humble`); or install `ros-humble-autoware-vehicle-msgs` from the
  same ROS snapshot. Then run
  [`scripts/check_launch_manager_environment.py`](scripts/check_launch_manager_environment.py)
  with the same setup script: it runs `ldd` on each component in its
  rendered environment and fails on a library that is not found. CI runs it
  in the abort-matrix job.
- At its last inventory the VM had rclcpp 16.0.19, older than the 16.0.21
  of the snapshot that CI builds against. So the adapter is built on the VM,
  or the VM's ROS 2 packages come from the same snapshot.

## Claim boundary

Shown by a passing run, on a GitHub-hosted ubuntu-22.04 runner only: the
build and link of one adapter process with S-CORE communication and ROS 2,
the exported override, the abort mechanism for the three variants, the end
with code 5 on a refused subscription, the startup of the adapter in the
bench environment with 11 other ROS 2 processes on the host, the endpoints of
the adapter node in the soak, and the absence of an abort over the soak in
that environment.

Not shown: any requirement of INC-MW-011 as verified, the behavior on the
bench VM, the full Autoware graph, the guest side, the SOME/IP crossing to a
real subscriber, the Launch Manager at run time, the health proxy node, the
malformed-sample path of rmw_cyclonedds_cpp, and the timing of any case. No
safety, cybersecurity, compliance or certification claim is made. The
receiver runs below have their own claim boundary.

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
  A TCP stream that loses its SOME/IP framing also ends the connection.
- Every SD message takes a new session ID, also a message whose send fails.
  someipd reads a session ID that does not grow, with the reboot flag set, as
  a reboot of the receiver and ends its subscription.
- The receiver sets no TCP keepalive. So a link loss that lasts longer than
  the TTL ends its subscription when the TTL ends. When the link comes back,
  someipd sends a Nack only if it no longer holds the TCP connection
  (service_discovery_impl.cpp:2103-2112 of vsomeip 3.6.1). The receiver then
  ends the half-open connection. Otherwise someipd acknowledges the
  subscription. Design data: in the 5 s link outage of `resubscribe`, the
  receiver log shows `subscription_expired`, then `nack`, `tcp_connected` and
  `subscribed`.
- It reassembles SOME/IP over TCP, checks that the 4-byte little-endian
  length prefix counts the bytes of the frame, and reads `sequence` and
  `frame_timestamp_ns` with a minimal protobuf wire reader.
- It serves one client on 127.0.0.1:4731. It forwards each payload unchanged,
  prefix and frame. It holds no queue: a frame without a client is dropped.
- Every frame ends delivered or dropped with one reason, and a counter per
  reason shows it. Every dropped frame gives a log line with its reason, at
  most at the frame rate; `--log-frames` adds a line per served frame. The
  start line repeats the whole configuration.

The discard rule is a separate component (`FrameDiscardPolicy`). It is
`receiverSubscriptionPhaseDiscardRule` of the phase-8 realization model:

- A subscription phase holds while the receiver is subscribed at someipd and
  the ingress is its only loopback client. The phase starts when the second
  of the two conditions starts to hold, and ends when one of them ends. The
  receiver takes the phase start from its own `CLOCK_REALTIME`, the clock
  with which the frame assembler stamps `frame_timestamp_ns` on the host.
- The receiver is not subscribed at its start. A Nack, the loss of the TCP
  connection to someipd, a loss of the SOME/IP framing of the TCP stream, a
  StopOffer, a reboot of someipd, or the end of the TTL of the last
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
- The margin is fixed at 20 ms. No option sets it: the receiver stops at
  start (exit status 2) on any margin option.

The bound of the copy memory counts sample slots, not reads. A copy comes
only from the stored frames that a new subscription in the host half reads
after a restart during the phase (GAP-MW-039). A stored frame is still in a
sample slot: 20 slots in the adapter's frame event and 20 in gatewayd's
bridged service. So the memory keeps the 40 frames served last, and each
phase start clears it. When 12 stored frames arrive after 12 newer ones, a
memory of 10 or 20 frames serves 12 frames twice, and a memory of 40 frames
serves none twice (gtest `MemoryOfFortyServesNoStoredFrameTwice`). A copy of
a frame that left the memory would pass. The receiver logs each phase start
and end, and each dropped frame with its reason.

Clock controls for ASM-MW-030: the start record, each phase start and each
status record give `CLOCK_REALTIME` less `CLOCK_MONOTONIC`. A slew moves both
clocks alike, so this difference changes only when the realtime clock is
stepped or across a suspend. A change of 1 ms or more between two readings
(at most 100 ms apart) is a clock step. The receiver logs it as
`clock_step`, and the phase end and the status records count the steps in
the phase. A served frame in the log has `receipt_minus_frame_ns`, its
receipt time on the receiver clock less its `frame_timestamp_ns`: every
frame with `--log-frames`, else the first five of each phase. The phase end
and the status records give the minimum and the maximum in the phase. The
minimum bounds the host-guest offset from one side only: a negative minimum
shows a guest clock behind the host clock by at least that much, and a guest
clock ahead looks like latency. On the VM, these records and the measured
host-guest offset show which runs are void: a run is void when the offset is
not below 20 ms.

The ingress is oneshot: it exits when its connect fails or its stream
closes, and init does not start it again while it runs or before init has
reaped it. So the receiver starts the ingress itself. At each of its starts,
after its loopback server listens, it sets
`de4sdv.aebs.frame_server.host=127.0.0.1` (`--announce-property`), then
`de4sdv.aebs.ingress.start` to 0 and then to 1 (`--ingress-start-property`).
When a receiver starts after the end of an old one, the old ingress can
still run or wait for init to reap it, and that trigger does nothing. So,
until the first client of this receiver process connects, the receiver
repeats the trigger every 1 s, at most 10 times. The old ingress exits when
the end of the old receiver closes its stream, and init reaps it then; the
10 s of repeats cover an ingress that is slow to exit and an init that is
busy, with margin. The VM runs must show the restart. A start of a running
ingress does nothing, so a repeat is harmless. Each try gives one
`ingress_trigger` record, and 1 s after the last try without a client the
receiver logs `ingress_trigger_gave_up`. After the first client, the
receiver never triggers the ingress again in this process: an ingress that
exits by itself or that the bench stops stays down (the "HMI application
down" condition of VC-MW-020 holds). The period and the count are fixed. On
Linux, the receiver logs the properties and does not set them. The init
script sets only the port property and no ingress trigger.

Build and test the receiver with CMake and GTest (Ubuntu: `libgtest-dev`):

```bash
cmake -S implementation/score-reference-interop-bench/someip-receiver -B build/someip-receiver -G Ninja
ninja -C build/someip-receiver && build/someip-receiver/de4sdv_someip_receiver_tests
```

`Android.bp` builds the same sources as a native binary (liblog only) with
`de4sdv_someip_receiver.rc`, an init script for the eng or userdebug image;
CI does not build either. The init script has `seclabel u:r:su:s0` (bench
only; a product needs its own SELinux domain, GAP-MW-038), a service that
init restarts, and the ingress property `de4sdv.aebs.frame_server.port=4731`.
The receiver sets the host and the ingress start.

### Runs against the real someipd

Four jobs of the workflow cover the receiver. `someip-receiver-unit` builds
it with g++ and runs the gtest suites; this binary goes to the namespace runs.
`someip-receiver-clang` builds and tests it with clang++.
`someip-receiver-sanitizers` runs the gtest suites of a g++ build with ASan
and UBSan; every finding fails the job. The fourth job,
`someip-receiver-interop`, runs `scripts/run_someip_receiver_interop.py` as root
with the runtime bundle of the build job. The script creates a "host" and a
"guest" network namespace, joined by a veth pair, with a route for
224.0.0.0/4 in both. Every bench process runs as the non-root runner user,
except the capture (tcpdump runs as root).

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

Each case starts a fresh stack, and each case is a gate: the job passes only
when every case passes; an inconclusive case fails it too.

| Case | What it shows |
|---|---|
| `identity` | 200 frames reach the client byte for byte, in order, with the 2044-byte frames |
| `resubscribe` | after a receiver restart by SIGTERM, one by SIGKILL, a restart of the gateway pair and a 5 s link outage, the receiver subscribes again and delivery resumes; no frame comes twice; every drop has a reason |
| `no_client` | frames without a client are dropped and not queued; the client receives no frame produced more than 20 ms before it connected |
| `stored_samples` | in the order of the stored-sample cases of the gateway spike, with the source paused at each step so that the newest frames stay in the sample slots: frames into the adapter, then gatewayd and the subscription, then the source again (frames from before the phase arrive in it); then gatewayd restarted beside the running someipd in the phase, a stimulus outside the operating rules (stored frames repeat served frames); then a restart of the gateway pair. The case passes only when both checks of the rule acted: a frame older than its phase start less 20 ms dropped in a phase, and a copy dropped in a phase |
| `ttl_renewal` | without multicast offers, the receiver renews its subscription over five TTLs, without a lapse or a gap. someipd answers a subscription that comes before its first offer with a Nack, as it does for the vsomeip client; the case counts these as `nacks_before_first_ack` and fails only on a Nack after the first Ack |
| `ingress_start` | the client is a oneshot ingress stand-in (`loopback_frame_recorder.py --oneshot`). Only an init stand-in of the runner starts it, on the property records of the receiver, by the rule of init: no start while the ingress runs. (1) The receiver is killed and starts again while its old ingress still runs (the stand-in stays alive 2.5 s after its stream ends): a repeat of the trigger (reason `no_first_client`) starts the new ingress, which receives frames. (2) The bench stops the ingress after the first client of the receiver: no trigger, no start and no client follow. (3) A receiver starts while no ingress can start: it tries 11 times, 1 s apart, and logs `ingress_trigger_gave_up` |

`src/de4sdv_score_bench/someip_receiver_interop.py` evaluates the raw records
of each case. A case also fails on a "Failed to subscribe" line of gatewayd,
on LoLa shared memory that the adapter, gatewayd and someipd do not share, on
any frame at the client that is not byte-identical to a source frame, on a
frame served outside a phase or older than its phase start less 20 ms, on
a copy served in a phase, on a receiver run that does not set the ingress
properties in order after its start record, and on an ingress trigger after
the first client of a receiver run, a repeat not 1 s after the last try, more
than 10 repeats, or a give-up before the 10th repeat. The evaluator also
does not take the receiver's word for its own rule and phases:

- It uses its own margin of 20 ms and copy memory of 40 frames, and a start
  record that gives other values fails the case.
- A receiver that the runner stops with SIGTERM must end with 0 and log its
  final status; a missing final status is accepted only after a planned
  SIGKILL, and a receiver that ends without a planned stop fails the case.
- The runner records the cores of each case. A receiver core fails the case;
  the cores of other processes are recorded with their first named frames
  (gatewayd ends with SIGABRT at its stop, GAP-MW-041).
- Each phase start must lie at most 100 ms after the later of the last Ack
  of someipd in the capture (inside its TTL) and the connect of the client,
  and the later one must be the logged cause. Each phase end must lie within
  100 ms of an independent record of its cause: a Nack, a StopOffer, a FIN or
  RST of the TCP connection, a reboot of someipd or the StopSubscribe of the
  receiver in the capture, the end of the TTL after the last Ack, or the end
  of the client. In the CI runs so far, each start and end lay within
  0.1 ms of its record, and a TTL end 0.4 ms after the end of the TTL.

A clock step makes the case inconclusive. The results list the phase starts
of each case. A frame that the AEBS stack produced in the 20 ms before a
phase start (the band of GAP-MW-045) is reported, not failed.

Both namespaces share the clock of one kernel, so ASM-MW-030 holds in these
runs by construction. They do not measure a host-guest clock offset.

### Claim boundary of the receiver runs

These runs are CI regression and design data on GitHub-hosted ubuntu-22.04
runners. They are not evidence of record, they verify no requirement, and
every result stays draft until independent review.

Shown by a passing run: the receiver's interoperation over a veth pair with
the someipd and gatewayd of the bundle, on Linux, with the discard rule of
the model, on one clock. Not shown: the Android build of the receiver, the
AAOS SDV guest, the Cuttlefish network, the HMI ingress, the Android property
service and init (the runs use stand-ins for both), the receiver under its
init user and SELinux domain (the runs start it with setpriv as a non-root
user), the clock offset of a real guest (ASM-MW-030), and any timing of
record. No safety, cybersecurity, compliance or certification claim is made.
