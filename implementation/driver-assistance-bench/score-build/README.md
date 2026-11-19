# S-CORE build of VisionPilot (build item B2)

Status: draft, not yet validated. The scripts have not run on any VM yet. Only the local checks in `tests/` have run.

## The problem

INC-DRIVING-002 runs VisionPilot at `014e0e7a56ee8e597c2cab8175233f74edd9b856` as one Eclipse S-CORE application on
the S-CORE host. That process links mw::com, the CARLA 1.0 C++ client, ONNX Runtime with its CUDA provider, OpenCV
and the Rerun SDK (PSR `VisionPilotSCOREApplication`). Two gaps stand before the first closed loop:

- No probe has built VisionPilot itself under S-CORE. The readiness probe of 2026-11-15 (its runs e and h) linked only a probe
  binary with those libraries. The VIS8 probe used upstream's Docker and CMake build.
- The supervision decision of 2026-11-18 keeps VisionPilot a native process under the Launch Manager, not a
  container. Every GPU run so far took its CUDA runtime from upstream's container image. The S-CORE host has none.

This folder holds the build and the GPU runtime for the S-CORE host. The first probe on the S-CORE host and the first closed-loop probe need both.

## What is here

| Path | Content |
|---|---|
| `build_score_bench.sh` | The one build script. It runs on a fresh x86_64 Ubuntu 22.04 host, builds everything below and packs `<root>/bundle` |
| `install_gpu_runtime.sh` | For the S-CORE host (L4, Ubuntu 22.04, driver 580). It installs the CUDA and cuDNN runtime, then checks the CUDA provider and `nvh264enc` |
| `fallback_cmake_build.sh` | The fallback of brief risk R3: upstream's CMake build, linking a Bazel-built static archive of the binding units. Ready, not run |
| `pins.sh` | Every pinned input: commits, URLs, sha256 values, apt versions |
| `workspace/visionpilot.BUILD.bazel` | The overlay BUILD file of VisionPilot: one `cc_library` per CMake target, the three binding units, and the `VisionPilot` binary (installed as `bin/vision_pilot`) |
| `workspace/thirdparty.BUILD.in` | `@da_b2_thirdparty`: ONNX Runtime, OpenCV, Rerun, Eigen, CppAD/Ipopt, Boost headers, GStreamer |
| `workspace/MODULE.fragment.bazel`, `BUILD.bazel`, `interfaces.BUILD.bazel`, `launch_manager.BUILD.bazel`, `fallback.BUILD.bazel` | The workspace's own repository and packages |
| `workspace/ort_cuda_check.cpp` | A small binary. It loads ONNX Runtime's CUDA provider and runs a network on it |
| `tests/` | Local checks (pytest), registered in `tools/run_bench_unit_tests.py` |

## Running it

On the build host, an x86_64 Ubuntu 22.04 VM with 8 vCPU, at least 32 GB RAM and 100 GB of disk, run from a
checkout of this branch:

```bash
implementation/driver-assistance-bench/score-build/build_score_bench.sh --root /opt/da-b2 --jobs 8
```

It ends with `=== BUILD OK`, the sha256 of each binary and library, and `/opt/da-b2/da-b2-bundle.tgz`. A failure
prints `BUILD FAILED in stage <stage>: <reason>` and the log path, under `/opt/da-b2/logs/`. A rerun skips the stages
that finished (`/opt/da-b2/.done-<stage>`). The preflight asks for 70 GB free under the root; `--min-free-gb N` lowers
that for a rerun with finished stages or for a run that a disk guard watches. Each stage line prints the free bytes.

On the S-CORE host, copy the bundle and run:

```bash
tar -xzf da-b2-bundle.tgz -C /opt/da-b2
implementation/driver-assistance-bench/score-build/install_gpu_runtime.sh --bundle /opt/da-b2/bundle
```

It ends with `GPU RUNTIME OK`. It needs about 3 GB of downloads and 8 GB of disk. The check prints
`ORT_CUDA_CHECK PASS` after 20 runs of `autosteer_fp32.onnx` on the CUDA provider, and encodes 100 frames with
`nvh264enc`. Without `--bundle`, the script fetches the pinned ONNX Runtime and builds the check with g++. That checks
the runtime only, not the S-CORE binary.

The build needs Ubuntu 22.04, the S-CORE host's release, because the binary links Ubuntu 22.04's GStreamer, Ipopt and
CppAD. The script refuses another release. If the CPU VM runs another release, run the build on the L4 host itself.

Estimates, not measured: a cold build takes about 60 to 90 minutes on 8 vCPU. Run e of the readiness probe took 22 min, run h 4 min for
the CARLA client; OpenCV, Arrow, VisionPilot and the gateway come on top. It downloads about 6 GB and uses about
70 GB of disk. The GPU runtime takes about 10 minutes.

## How it builds

| Stage | What | From |
|---|---|---|
| `workspace` | FEO `313b3d84` with the bench diff's `MODULE.bazel` and `.bazelrc` hunks (communication 0.6.0, lifecycle 0.10.0, the overrides, clippy off), `@libcarla` repointed, `@python312` dropped, `@da_b2_thirdparty` added; Bazel 8.3.0; `--config=x86_64-linux` = S-CORE gcc 12.2.0, sysroot glibc 2.31 | run e |
| `carla` | CARLA 1.0 client `14ac3b1a50` by CARLA's CMake with the S-CORE gcc, with the Boost.Python workaround; the 17 archives in the example client's link order | run h |
| `opencv` | OpenCV 4.6.0, static: core, imgproc, imgcodecs, videoio with GStreamer, highgui without a GUI back end | run e, extended |
| `rerun` | Rerun C++ SDK 0.34.1 and its Arrow 18, static | run e |
| `thirdparty` | ONNX Runtime 1.26.0 GPU (shared), Eigen 5.0.0, the CppAD and Ipopt headers, CARLA's Boost headers, nlohmann json, GStreamer include directories | new |
| `gateway` | inc_someip_gateway `d9eac670`: gatewayd, someipd, the null serializer and the warning's config binary (`score-path/config/`), at communication 0.6.0, baselibs 0.2.17 and lifecycle 0.10.0 | probe P5, brief R4 |
| `bazel` | `//visionpilot:VisionPilot`, `//de4sdv_da_bench/actuation-adapter:actuation_adapter`, `//de4sdv_da_bench/score-build/workspace:ort_cuda_check`, the Launch Manager daemon `@score_lifecycle//score/launch_manager:launch_manager`, `//de4sdv_da_bench/launch-manager:de4sdv_lm_config` and `:de4sdv_lm_config_path_only` (Lifecycle's own schema check, mapping and flatbuffer of `launch-manager/config/launch_manager_config.json` and of `score-path/config/launch_manager_config_path_only.json`), the identity recorder and its late subscriber `//de4sdv_da_bench/identity-recorder:identity_recorder` and `:candidate_record_probe`, and p10-3's test publisher `//de4sdv_da_bench/ivi-warning/injector:warning_injector` | new |
| `bundle` | `bin/` with the Launch Manager's binary names (`vision_pilot`, `actuation_adapter`, `gatewayd`, `someipd`, `identity_recorder`) plus `launch_manager`, `ort_cuda_check`, `candidate_record_probe` and `warning_injector`; `lib/`; `config/` (`launch_manager/` with both flatbuffers beside their JSON and the Launch Manager's own mw::com configuration `mw_com_config_launch_manager.json`, `gateway/`, `actuation_adapter/`, `visionpilot/` with upstream's files and the derived `homography_C_matrix.yaml`); the networks, the icons; `facts/` with the patch series and its `SHA256SUMS` as the candidate's source difference (the build's own diffs under `facts/build/`, since the identity recorder refuses a `.diff` that `SHA256SUMS` does not list); binary checks, the Lifecycle client symbols in both supervised binaries; `ort_cuda_check --cpu-only`; `SHA256SUMS` of every other file | new |

The bundle is the input of `../score-path/scripts/stage_score_side.py`. Every path that the staging requires or reads
when present comes from the `bundle` stage; `tests/test_score_build.py` checks that contract statically, from both
scripts.

The `visionpilot` stage first runs `score-interface/check_patch.sh`. It then copies `VisionPilot/` of the pin with
patches 0001 and 0002 into the package `//visionpilot`, with the overlay as its `BUILD.bazel`. No upstream file
changes beyond the two patches. The overlay mirrors upstream's CMake targets. Bazel needs two changes:

- The module headers form one header library, because upstream's headers include each other across modules in a cycle.
- Every library is `alwayslink`, because the static libraries reference each other in a cycle.

Mapping ids:

- Two of the three binding units carry the S-CORE ports. `lola_bindings.cpp` carries MAP-DRIVING-DA-COMMAND,
  MAP-DRIVING-DA-WARNING-REQUEST and MAP-DRIVING-DA-CANDIDATE-RECORD. `carla_client.cpp` carries
  MAP-DRIVING-DA-CAMERA-IMAGE and MAP-DRIVING-DA-VEHICLE-SPEED. The third, `lifecycle_bindings.cpp`, is the
  candidate's lifecycle client on S-CORE Lifecycle v0.10.0 (`:alive_cc` and `:lifecycle_cc`), for the Launch
  Manager's alive supervision (`../launch-manager/README.md`).
- S-CORE Lifecycle 0.10.0 is declared once, by the bench diff's `MODULE.bazel` hunk; the `workspace` stage checks
  that declaration and the `bazel` stage records the resolved version (`facts/score-mod-explain.txt`).
- `carla_client.cpp` is the one C++20 unit (run h, owner decision h-a). Everything else builds at the toolchain's
  C++17.

The bench configuration follows the model and upstream's defaults:

- GPU on, ROS 2 off, tests off, occupancy view off.
- `ENABLE_RERUN` on, because `rrd_on = true` gives the evaluators their record.
- `ENABLE_SCORE_INTERFACE` on.
- The WebRTC sources in. `vision_pilot.cpp:80-82` builds the streamer without a guard, so the link needs them.
  `webrtc_on` stays false.

## Decisions and assumptions taken here

- **ONNX Runtime is a CUDA 12 build, so the runtime is CUDA 12.8, not 13.** On 2026-11-18 the GitHub release of
  1.26.0 could not be reached: `github.com/microsoft/onnxruntime` and its API answered 404, and the release assets
  could not be listed. The build therefore uses Microsoft's prebuilt GPU package on nuget.org,
  `Microsoft.ML.OnnxRuntime.Gpu.Linux` 1.26.0, from branch `rel-1.26.0` at commit `8c546c37`. It is pinned by the
  sha256 of the file downloaded here.
  - ONNX Runtime's CUDA provider page says 1.26.x is built with CUDA 12.8 and cuDNN 9.x, and that CUDA 13.0 becomes
    the default from 1.27.
  - `readelf` of `libonnxruntime_providers_cuda.so` agrees: `libcudart.so.12`, `libcublas.so.12`,
    `libcublasLt.so.12`, `libcufft.so.11`, `libcurand.so.10` and `libcudnn.so.9`.
  - So the host gets CUDA 12.8 Update 1 and cuDNN 9.28.1.4 for CUDA 12, from NVIDIA's redistributable archives.
  - VIS8 ran upstream's image with CUDA 13.0, cuDNN 9.28.1.4 and the `gpu_cuda13` build of 1.26.0. The native runtime
    therefore differs from VIS8's in the CUDA major version. The first probe on the S-CORE host measures its cycle anyway.
- **A second libstdc++ in the process** (owner decision 5a): the binary links libstdc++ statically, and ONNX Runtime,
  Ipopt and CppAD load the host's. Ipopt and CppAD exchange C++ types with VisionPilot's planner across that line
  (`std::string` options), unlike ONNX Runtime, which keeps to its C API. This holds only if both runtimes use the
  same ABI (gcc 12 on both sides). It is an assumption, and the first probe on the S-CORE host must exercise the planner.
- **Host libraries in an S-CORE binary.** GStreamer, Ipopt and CppAD come from Ubuntu 22.04, as in upstream's
  Dockerfile. They are linked by full path, and their headers are copied out of `/usr/include`, so that no host
  include root reaches an S-CORE compile. Their glibc symbol versions are newer than the sysroot's 2.31, so the link
  uses `--allow-shlib-undefined`, as upstream's app already does.
- **One Boost.** The WebRTC sources compile against the headers of the Boost that CARLA's build fetched. CARLA's client
  in the same process uses the same Boost, so the binary holds one definition of each Boost.Asio template.
- **The gateway builds in its own workspace.** gatewayd and someipd use the gateway's toolchain and module set, with
  probe P5's three version lines. That is the proven route. It replaces building them inside the S-CORE workspace
  (brief R4). They share mw::com 0.6.0 with VisionPilot.
- **Plain Bazel 8.3.0**, pinned by sha256, replaces the Aspect CLI 5.9.36 wrapper that FEO's `.bazeliskrc` names.
- **Transitive downloads** are pinned by their parents, not by `pins.sh`. These are the Bazel modules from the S-CORE
  registry and BCR (`MODULE.bazel.lock`), CARLA's FetchContent dependencies (its commit) and Arrow (URL and MD5 inside
  the pinned Rerun archive). The S-CORE registry is read at `main`, as in the readiness probe.

## What the local tests show, and what they cannot

```bash
python -m pytest -q implementation/driver-assistance-bench/score-build/tests
```

The tests check five things:

- The scripts parse.
- Every download goes through the sha256-checked helper, and every git source through the commit-checked helper.
- The overlay names exactly the source files that upstream's CMake build compiles in the bench configuration,
  plus the patch series' CMake sources and its binding units. They read upstream at the pin with `git show` and the
  series from the patch files; the module's sources in the repository must equal those the patch adds.
- The workspace edits find their anchors, and the pinned CUDA runtime covers the provider's needs.
- C++ files include `<cstdint>`.

The probes must show what these tests cannot:

- The first probe on the S-CORE host: the Bazel build compiles and links at all; OpenCV finds GStreamer in the sysroot build; the CUDA provider
  loads in the S-CORE binary; the second-libstdc++ assumption holds for the planner; `nvh264enc` encodes natively.
- The first closed-loop probe: the process runs against CARLA 1.0.

## The p10-1 check (`scripts/p10_1_check.sh`)

`ENTRY_SCORE_P10_1` of `../session/entrypoints.env`, run as `p10_1_check.sh <out>` on the S-CORE host. It writes one
line per check, `PASS`, `FAIL` or `NOT RUN` with its detail, into `<out>/p10_1_verdicts.txt` and
`p10_1_verdicts.json`. It exits 1 on any FAIL. A NOT RUN is no pass: the line says what is missing.

| Check | What it shows | Needs |
|---|---|---|
| C1 | the Launch Manager takes the full and the path-only configuration; the recorder reports running before `vision_pilot` and `actuation_adapter` start; `gatewayd` starts after `someipd` | the bundle; for the full configuration a CARLA 1.0 server at `DA_P10_1_CARLA_HOST` (else NOT RUN, or FAIL when the path part failed) |
| C2 | `LCM_ALIVE_INTERFACE_PATH` is set in the candidate's and the adapter's environment; both log the start of their supervision; no expiry in `DA_P10_1_ALIVE_HOLD_S` | a ticking world |
| C3 | a SIGSTOPped candidate leads to the expiry and `fallback_run_target` in the Launch Manager's log; the candidate and the adapter are gone; the recorder, `someipd` and `gatewayd` run on with the same pids | a ticking world |
| C4 | mw::com takes the ASIL B command path: the candidate sent driving commands and the adapter accepted one | a ticking world |
| C5 | `gatewayd` (QM) receives from a process of global ASIL B: three sends of the test publisher, matched by `GATEWAYD_RX_REGEX` in the Launch Manager's log | a receive line of `gatewayd`, which as built prints none per sample (else NOT RUN; `p10-3` judges the receipt on the guest) |
| C6 | no pass after the first of the three networks on the CUDA provider takes longer than 0.4 s (`ort_cuda_check`, `DA_P10_1_CUDA_RUNS` runs each) | the bundle's `ort_cuda_check` |
| C7 | the candidate record reaches a subscriber that subscribes after the first publication (`candidate_record_probe`), with the file's digest | the bundle's probe |
| C8 | the candidate on a replayed clip: always NOT RUN, since the S-CORE interface module has no clip replayer and the brief's B0 clip replayer is not in the bench | — |

C2 to C4 need the candidate's first completed pass, so a CARLA 1.0 server with a world that ticks at
`DA_P10_1_CARLA_HOST`. The caller starts the world side's pacer. Without it they are NOT RUN. C1's full configuration
needs that server too: the real `vision_pilot` and `actuation_adapter` exit at once on a refused CARLA connection, and
the Launch Manager then switches to `fallback_run_target` (S-CORE build session 5 on the L4, 2026-11-19). So without
`DA_P10_1_CARLA_HOST`, or when its port 2000 does not answer, the check never starts the full configuration: C1 is
NOT RUN, its line names the reason and the path part's result, and it is FAIL when the path part failed. `gatewayd` prints
no line per received sample (the same session: only its offer lines), so C5 stays NOT RUN without a pattern, and
`p10-3` judges the receipt on the guest. C6 times each network
alone, one after another, not the loop's pass with its pre- and post-processing. The dry runs
(`tests/test_p10_1_check.py`) use the fake Launch Manager of `../score-path/tests/` and stand-ins for the probe and
`ort_cuda_check`. They show the verdict logic only.

## Fallback (brief R3)

Use it if the `bazel` stage fails and cannot be fixed in time. Run `fallback_cmake_build.sh --root /opt/da-b2` after
`build_score_bench.sh` has finished its `thirdparty` stage. It has two steps:

1. Bazel builds `cc_static_library` `//de4sdv_da_bench/score-build/fallback:de4sdv_score_bindings`, the three binding
   units with mw::com, the CARLA client and Lifecycle. Its facade is `seams.hpp`, which uses plain types.
2. Upstream's CMake builds VisionPilot with Ubuntu's g++ 12, as is. It sets `-DENABLE_SCORE_INTERFACE=ON` and
   `DE4SDV_SCORE_BINDINGS` = the archive, CARLA's 17 archives and the archive's link options. ONNX Runtime and Rerun
   come from the main build; OpenCV, Ipopt, CppAD and GStreamer from Ubuntu.

The script replaces `bundle/bin/vision_pilot` and keeps the Bazel binary as `vision_pilot.bazel`, if there is one.

## Not done here (deferred)

- VisionPilot's mw::com configuration and the run configuration (`source.mode = score`, `engine.provider = cuda`) are
  B6 and B13 inputs. The bundle carries upstream's `config/` unchanged.
- `ldconfig` makes the CUDA libraries visible system-wide on the S-CORE host. No `LD_LIBRARY_PATH` is set.
- The ffmpeg encoder fallback of the recorder (`DE4SDV_VISUALIZATION_ENCODER=ffmpeg`) is not checked.
- No GitHub Actions job: the brief's CI link with CPU ONNX Runtime is not set up.
