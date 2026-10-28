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
| `src/de4sdv_score_bench/` | Pure Python evaluators of the abort matrix and the soak |
| `scripts/` | CI build steps and the runners: abort matrix, soak, middleware startup probe |
| `tests/` | Evaluator unit tests |

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
