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

With parameter services, any ROS 2 process that reaches the host's DDS ports
could abort the adapter: for a request that names an undeclared parameter,
rclcpp throws and catches `ParameterNotDeclaredException` inside the service,
and the override turns that throw into an abort. The adapter has no
parameter services, also not in the abort matrix. The health proxy node will
start with the same node options.

One way to abort the adapter stays. rmw_cyclonedds_cpp 1.3.5 takes samples
of other participants on the `ros_discovery_info` subscription of its
context (rmw_node.cpp:849 and 1261) and on `/parameter_events`. Both go
through a deserialization that throws and catches (serdata.cpp:383-389).
With the override linked, one malformed sample from any DDS participant in
the domain aborts the adapter. That is outside normal operation, and no
configuration of ROS 2 Humble removes it. Only a process that reaches the
host's DDS ports can send such a sample; the host must keep these ports off
the guest network (REQ-MW-016). That host configuration is not authored yet
(GAP-MW-046). The bench makes no claim about this malformed-sample path.

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
port 4721 takes the stream from the adapter, and the adapter then gets no
frame and no end of stream. So the adapter must be the only client of the
frame server (ASM-MW-029). The frame server binds 0.0.0.0, so the host must
keep the guest network off port 4721; that host configuration is not
authored yet (GAP-MW-046). In the soak, the synthetic frame source binds
127.0.0.1, and `ss -tnp` must show at each liveness check that the adapter
is its only client.

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
  on its normal startup path. Under rmw_fastrtps_cpp the adapter aborted at
  start with the default transports, and with a UDP-only profile after
  another participant (section "Earlier Fast DDS cases"). The model records
  the choice (comment `adapterAbortConditions`, GAP-MW-035).
  `rmw_cyclonedds_cpp` is C++ too and showed no throw in the tested setups.
- `ROS_DOMAIN_ID=91`, one fixed domain, as the AEBS Autoware benches.
- `CYCLONEDDS_URI` to [`config/cyclonedds.xml`](config/cyclonedds.xml), the
  configuration of the AEBS Autoware benches. It selects the loopback
  interface for its locators and sends; its receive sockets bind INADDR_ANY
  (CycloneDDS 0.10.5 ddsi_udp.c:453-456, 479-480). It sets
  `MaxAutoParticipantIndex` to 120. On the loopback, which has no multicast,
  CycloneDDS 0.10.5 gives each process an automatic participant index. With
  the default (`MaxAutoParticipantIndex` 9), at most 9 processes get a
  participant: a bind at the last index fails too (q_init.c:1609,
  1627-1631). The next process gets no participant, so rclcpp throws, and in
  the adapter that is an abort at start. This file's 120 allows 120
  processes, more than the bench runs. The startup probe measured 9 of 11
  with the default.
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
| `config/` | ROS 2 environment and CycloneDDS configuration of the host, mw::com and mw::log configurations, gateway configuration, vsomeip loopback configuration for CI |
| `launch-manager/` | Launch Manager configuration (lifecycle overlay) |
| `src/de4sdv_score_bench/` | Pure Python evaluators of the abort matrix, the refused subscription, the startup probe and the soak, and the VisualizationFrame encoder |
| `scripts/` | CI build steps (runner only), the runtime facts, the renderer of the Launch Manager configuration and its load check, the runners, and the VisualizationFrame source for plumbing tests of the relay chain |
| `tests/` | Evaluator unit tests, and the source checks of the IVI frame relay |
| `ivi-frame-relay/` | DE4SDV IVI frame relay of the AAOS SDV guest: pure core, POSIX shell, gtest suites with a fake gateway client, golden fixtures, the AOSP adapter to libsdvgatewayclient and the main, `Android.bp` and init script (the AOSP parts are not built by CI) |

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
  the error of the second interface.

The runners write raw artifacts (adapter log, provider and observer records,
backtraces and core mappings) and evaluate them with `src/de4sdv_score_bench`.
The outcomes use the evidence outcome names of the middleware verification
model.

### Earlier Fast DDS cases

The startup probe ran five Fast DDS cases to show why the bench runs
rmw_cyclonedds_cpp. The model records that choice (comment
`adapterAbortConditions`, GAP-MW-035). So the probe no longer runs these
cases, and the CI no longer installs Fast DDS. The last two runs with them,
[40704447008](https://github.com/de4sdv/DE4SDV/actions/runs/40704447008) and
[40714437918](https://github.com/de4sdv/DE4SDV/actions/runs/40714437918)
(2026-10-28, ubuntu-22.04 image 20261026.341.1, rmw_fastrtps_cpp 6.2.10,
Fast DDS 2.6.12), showed the same in each case:

| Fast DDS setup | Build | Result |
|---|---|---|
| Default transports, `ROS_LOCALHOST_ONLY=1`, first participant | adapter | Aborted at start, SIGABRT at the override. First named frame below it: `eprosima::fastdds::rtps::SharedMemTransport::CreateInputChannelResource` in `libfastrtps.so.2.6.12` |
| The same | control build | Ran for the hold time of 30 s and stopped with 0 on SIGTERM |
| UDP-only profile, first participant | adapter | Ran for the hold time of 30 s and stopped with 0 on SIGTERM |
| UDP-only profile, after 1 other participant (ready) | adapter | Aborted at start, SIGABRT at the override. First named frame below it: `eprosima::fastdds::rtps::UDPv4Transport::OpenAndBindInputSocket` in `libfastrtps.so.2.6.12` |
| The same | control build | Ran for the hold time of 30 s and stopped with 0 on SIGTERM |

The shared-memory transport opens its port with `open_only` and creates the
port in the catch. The UDP transport catches the error of a port that is
taken. The UDP-only profile had one UDPv4 transport with the interface
whitelist 127.0.0.1, and no builtin transports. The control build is the
adapter without the override, so each abort came from the override. The
artifacts of the two runs expire on 2026-11-27.

## Bench VM

The `ci_*` scripts are for a disposable CI runner only. They install
packages, write `~/.bazelrc` and put bazelisk in `/usr/local/bin`, so each
one refuses to run unless `GITHUB_ACTIONS=true` or its first argument is
`--runner` (the guard [`scripts/runner_only.sh`](scripts/runner_only.sh),
which each one sources first). On the shared bench VM that would redirect
every Bazel run, android-cuttlefish with its large output base among them,
and shadow the VM's own Bazel. A bench session on the VM takes its own path,
and nothing goes into `$HOME` or `/usr/local`:

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
malformed-sample path of rmw_cyclonedds_cpp, a host that keeps the guest
network off its DDS ports and port 4721 (GAP-MW-046), and the timing of any
case. No safety, cybersecurity, compliance or certification claim is made. The
relay below has its own claim boundary.

## IVI frame relay of the AAOS SDV guest

The HMI path of this member ends in the IVI VM of the AAOS SDV guest
(ADR 0025). someipd on the Linux host sends the frame event over SOME/IP to
the SOME/IP stack of the SDV Core VM. The SOME/IP broker there maps it to a
topic, and Data Tunnel carries the topic to the IVI VM.
[`ivi-frame-relay/`](ivi-frame-relay) is the DE4SDV relay at the end of that
chain. It subscribes to the topic through the SDV Gateway on IVI and serves
the frames to the unchanged ingress of INC-AEBS-010 on the loopback of the IVI
VM. It realizes `iviFrameRelay` and `relaySubscriptionPhaseDiscardRule` of
the phase-8 realization model.

What the relay does:

- It subscribes by name with libsdvgatewayclient, with the subscriber flag
  `ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE`. By the documented behavior of
  the library (`libsdvgatewayclient.h:302-316`), it then reads only the
  messages published after its subscription. CI does not run the library.
  The default publication is the one of the feasibility run of 2026-10-28
  (design data): VM `instance1`, package `com.android.sdv.someip`, bundle
  `SomeIpBroker`, unit `de4sdv-score-aebs-signal-frame`. An option can follow
  the mapping of phase 10 without a new build. The relay's own subject for
  `initComms` is `de4sdv.ivi_frame_relay`, bundle `IviFrameRelay`, instance
  `default` (the relay's reading, not a value of the model). Exactly one ACL
  file for that subject must be on the IVI VM before it boots.
- It parses the broker's wrapper in each slot strictly
  (`broker_wrapper.hpp`, owner decision of 2026-10-29). How it reads the rule
  for a slot of fixed size is the relay's reading, not a value of the model,
  until the model states it: the outer varint gives the message, which must
  fit in the slot. The message holds exactly one field: field 1 of wire
  type 2 (tag `0x0A`), whose length equals the rest of the message. Every
  byte of the slot after the message is zero, as the broker writes it. Each
  varint is in its shortest form. Each failed check is a drop with its own
  reason. A `wrapper_fill_not_zero` drop logs the message length, the offset
  of the first byte that is not zero and its value: no run has yet recorded
  the bytes of a slot after its message in the IVI VM, so the first session
  of phase 10 uses frames of variable size and requires
  `drop_wrapper_fill_not_zero` to stay 0. Then it checks the payload: at most
  2048 bytes, and its own 4-byte little-endian length prefix must count the
  bytes after it. So a corrupted payload cannot shift the stream framing of
  the ingress (GAP-MW-040).
- It serves each frame unchanged, prefix and frame, on 127.0.0.1:4731 to one
  client, the ingress. It refuses a second client while one is connected. It
  keeps the ingress connection open while the publication is unavailable. It
  sends nothing to the host or to the SDV Core VM: the narrow gateway
  interface has no call that publishes, offers or calls a service. Only the
  SDV Gateway on IVI exchanges subscription control with the SDV Core VM for
  it. That is a design property, not the protection of REQ-MW-016.
  `client_connected` and `client_refused` name the peer process (its pid,
  uid and port, from `/proc/net/tcp`), so the bench can check that the client
  is the ingress. `SO_PEERCRED` gives no credentials on a TCP socket.
- It keeps one subscription for its lifetime, with or without a client, and
  holds at most one at a time (owner decision of 2026-10-29). Where a value
  below is the relay's reading, not a value of the model, it says so:
  - on PublicationDestroyed it ends the subscription, unsubscribes and
    subscribes again: every 100 ms for the first 5 s, then every second. The
    first attempt comes at once (the relay's reading, not a value of the
    model);
  - on Disconnected, and when `initComms` fails, it logs
    `gateway_client_lost` with the stage and the status, ends the phase as a
    phase end of the layer, and ends the process with code 4. init starts
    the relay again as a new process, and that start triggers the ingress
    again. The relay never deletes and re-creates its gateway client (owner
    decision of 2026-10-29, revised the same day: the library allows one
    client per process (`libsdvgatewayclient.h:473-475`); the model states
    it in `iviFrameRelay`). Only an `ASDVGateway_Client_new` that itself failed, which
    leaves no client, is tried again in the process: every second, and every
    10 s once the failures have lasted 30 s (the relay's reading, not a
    value of the model);
  - when no message comes for 3 s it ends the subscription, unsubscribes and
    subscribes again. After three subscriptions in a row that brought no
    message, it waits 5 s before each attempt. That the wait applies after
    the ends by the timeout only is the relay's reading, not a value of the
    model;
  - it logs each failed attempt with its status code and text. If no
    subscription succeeds within 30 s of its start, it logs
    `subscription_start_diagnostic` once: a likely fault of the ACL or of the
    mapping when a client exists, of the gateway client when none was
    created. From then on it tries every 10 s. Before that, it tries every
    second (the relay's reading, not a value of the model);
  - a DATA_LOSS status of a read is a gap (GAP-MW-037): it is counted and
    logged, and the phase goes on. A DATA_LOSS also counts as a sign of life
    for the 3 s timer, and the next read follows at once (the relay's
    reading, not a value of the model).
- The discard rule: a subscription phase holds while the relay is subscribed
  and the ingress is its one client. It starts when the second of the two
  starts to hold, on `CLOCK_REALTIME` of the IVI VM, and ends when one of
  them ends. Outside a phase the relay reads every slot and drops it. In a
  phase it drops a frame with a sequence or a `frame_timestamp_ns` that is
  not positive, a frame older than the phase start less 20 ms (the bound of
  ASM-MW-030), and a copy of a frame served in the phase. The copy window
  holds the last 40 frames served (20 + 20 sample slots) and is cleared at
  each phase start. The margin is fixed: an option that names a margin or a
  bound stops the relay at start. A frame that the AEBS stack produced in the
  margin before the phase start can still pass (the band of GAP-MW-045). A
  phase end by PublicationDestroyed,
  Disconnected or the timeout while the ingress stays connected is a delivery
  failure of the layer: its `phase_end` line has `layer_caused` set.
- The ingress trigger: the ingress is a oneshot service and exits when
  nothing listens. At each start of the relay, once its loopback server
  listens, the relay sets the host property of the ingress and then
  `de4sdv.aebs.ingress.start` to 0 and 1. Until the first client of the
  process connects, it repeats the trigger every 1 s, at most 10 times, then
  logs `ingress_trigger_gave_up`. After the first client it never triggers the
  ingress again, with one case of the relay's reading, not a value of the
  model: when the relay itself closes the ingress stream after a write stall,
  it triggers the ingress again in the same way.
- The host property: the ingress defaults its frame-server host to
  10.250.0.3 (`ingress/main.cpp:144` of the visualization bench). So the
  relay sets `de4sdv.aebs.frame_server.host` to 127.0.0.1 at each of its
  starts (`--announce-property` in its init file), and the init file sets the
  port property to 4731. Setting the host property also starts the ingress
  (`de4sdv_aebs_ingress.rc:9-13`), as the model states.
- The clock controls of ASM-MW-030: it logs `CLOCK_REALTIME` minus
  `CLOCK_MONOTONIC` at the start, at each phase start and in each status line,
  and each step of 1 ms or more. For the frames served in a phase it logs the
  minimum and the maximum of receipt time minus frame timestamp. That minimum
  bounds the offset from one side only, so it is no bounding control.

Two threads. A worker thread makes every call into the gateway client. The
main thread runs the loopback server, the ingress connection and the
decisions on each frame, and never waits for the worker. A library call can
block (the feasibility runs saw `initComms` block while the SD agent of the
IVI VM could not start), and it cannot be cancelled. So the main thread
reports a gateway call that has run for 10 s (`gateway_call_stalled`) and its
return. Only the main thread takes SIGTERM and SIGINT: the binder pool and
the worker thread start with them blocked. At stop, the relay ends the phase,
unsubscribes and deletes the client within 150 ms, inside the 200 ms of
init's `gentle_kill`, unless the worker is inside a gateway call; then the
relay logs `gateway_worker_not_joined` and ends without unsubscribing. A stop
that ends a blocked write to the ingress drops that frame as `relay_stop`, and
the phase ends with the cause `relay_stop`.

The log lines are JSON objects in liblog with the tag `de4sdv_ivi_frame_relay`,
one per event: `start`, `gateway_client_create`, `subscribed`,
`subscribe_failed`, `subscription_ended`, `unsubscribed`,
`gateway_client_destroyed`, `phase_start`, `phase_end`, `frame` (each drop
with its reason, and served frames), `data_loss`, `read_failed`,
`gateway_notification`, `gateway_client_lost`, `client_connected` and
`client_refused` (with
`peer_pid`, `peer_uid` and `peer_port`), `client_lost`, `ingress_trigger`,
`ingress_trigger_gave_up`, `clock_step`, `subscription_start_diagnostic`,
`gateway_call_stalled`, `gateway_call_returned`, `status`, `final_status`. A
`frame` line of a wrapper drop also has `message_bytes`, and one of
`wrapper_fill_not_zero` has `fill_offset` and `fill_value`. Every slot read
ends in exactly one outcome: `messages_read` equals `frames_delivered` plus
the sum of the `drop_*` counters.

Frames for plumbing tests:
[`scripts/visualization_frame_source.py`](scripts/visualization_frame_source.py)
serves VisualizationFrames with `sequence` from 1, `frame_timestamp_ns` on the
host's `CLOCK_REALTIME` and sizes that vary up to 2044 bytes. The bench's
`synthetic_frame_source.py` sends no VisualizationFrame, so the relay drops
each of its frames as `frame_unreadable`. Cases of record use the frame
assembler of INC-AEBS-010.

### What CI builds and what phase 10 builds

The gateway client of AOSP (libsdvgatewayclient of android17-release,
manifest ad156f32) does not build on CI. So the relay keeps it behind a narrow
interface (`gateway_client.hpp`):

- CI builds and tests, with CMake on ubuntu-22.04, the core and the shell
  with a fake gateway client: the strict parse, the payload checks, the
  phase and discard logic, the retry and back-off rules, the gateway worker,
  the loopback server with real sockets, and the two threads. Four jobs of
  the workflow do it: `ivi-frame-relay-unit` (g++),
  `ivi-frame-relay-clang` (clang++), `ivi-frame-relay-sanitizers` (g++ with
  ASan and UBSan) and `ivi-frame-relay-tsan` (g++ with TSan).
- The AOSP adapter (`src/aosp/sdv_gateway_client.cpp`), the main
  (`src/aosp/relay_main.cpp`), `Android.bp` and the init file
  `de4sdv_ivi_frame_relay.rc` are in the repository, and no CI job builds
  them. The VM session of phase 10 stages the directory in the AOSP tree of
  the bench and builds it there, together with the IVI image or for the
  instance overlay (step 5 of the next action of the mapping record).

Build and test the core and the shell with CMake and GTest (Ubuntu:
`libgtest-dev`):

```bash
cmake -S implementation/score-reference-interop-bench/ivi-frame-relay -B build/ivi-frame-relay -G Ninja
ninja -C build/ivi-frame-relay && build/ivi-frame-relay/de4sdv_ivi_frame_relay_tests
```

`de4sdv_ivi_frame_relay.rc` is the init file for the eng or userdebug image of
the IVI VM of the bench: `seclabel u:r:su:s0` with SELinux permissive, as on
the INC-AEBS-010 bench, so a product needs its own SELinux domain
(GAP-MW-038). The service is not oneshot, so init restarts the relay when it
exits. The exit codes: 0 after a stop, 2 for a refused option, 3 when the
loopback server cannot listen, 4 when the gateway client is lost. The file
sets the frame-server port of the ingress to 4731.

### Claim boundary of the relay

The CI runs are regression and design data on GitHub-hosted ubuntu-22.04
runners. They are not evidence of record, they verify no requirement, and
every result stays draft until independent review.

Shown by a passing run: the core and the shell of the relay on Linux with a
fake gateway client, with the discard rule and the subscription rules of the
model and the relay's own readings, not values of the model. Not shown: the
AOSP build of the relay, the gateway client at run time, the cross-VM
subscription, the init service and the ACL on the IVI VM, the relay under its
init user, group and SELinux label, the property service that the ingress
trigger uses (off Android the setter only logs), the ingress, the clock of a
real IVI VM (ASM-MW-030), and any timing of record. No safety,
cybersecurity, compliance or certification claim is made.
