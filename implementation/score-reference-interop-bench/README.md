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
  interface and sets `MaxAutoParticipantIndex` to 120, more than the number
  of ROS 2 processes of the bench. On the loopback, which has no multicast,
  CycloneDDS 0.10.5 gives each process an automatic participant index, by
  default up to MaxAutoParticipantIndex 9. A process beyond that gets no
  participant, so rclcpp throws, and in the adapter that is an abort at
  start. The startup probe runs both sides and reports how many processes
  got a participant.
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
| `src/de4sdv_score_bench/` | Pure Python evaluators of the abort matrix, the refused subscription, the startup probe and the soak |
| `scripts/` | CI build steps, the runtime facts, the renderer of the Launch Manager configuration, and the runners |
| `tests/` | Evaluator unit tests |

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
  - Every process lived at every check, and gatewayd subscribed the frame
    event without a failure line.
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
safety, cybersecurity, compliance or certification claim is made.
