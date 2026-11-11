# drivingAgent build workspace

drivingAgent builds inside an Eclipse S-CORE FEO workspace with the S-CORE
toolchain (`bazel build --config=x86_64-linux`). The bench sources go into that
workspace as `de4sdv_bench/`. This directory holds what the workspace needs
beyond upstream FEO.

| File | What it is |
|---|---|
| `feo-313b3d84-bench.diff` | The workspace change against eclipse-score/feo `313b3d849c17881d3a11b6bf62aa2afab6565ef0`: `.bazelrc`, `MODULE.bazel`, `src/feo/src/scheduler.rs` |
| `libcarla.BUILD` | The `@libcarla` repository: the LibCarla 0.9.16 client as static archives |
| `python312.BUILD` | The `@python312` repository: the CPython 3.12.16 the planner embeds |

## What the patch changes

- **`scheduler.rs`, the event trigger.** When `FEO_PACE_SOCKET` names a Unix datagram socket, the primary waits on it for the next frame instead of sleeping out its cycle timer.
  - It takes the newest frame and counts the frames it skipped.
  - It logs `FEO_PACE {cycle, events, skipped, t_real_ns}` to stderr.
  - It ends the main loop on a stop request or a failed source.
  - Without the variable, the timer paces as upstream does.
- **`MODULE.bazel`.** Adds the S-CORE reference_integration v0.10.0 module set: Communication 0.6.0, Lifecycle 0.10.0, and the tooling versions it pins. Also adds two local repositories, `@libcarla` and `@python312`. Their `path` values are host paths; set them to your installs.
- **`.bazelrc`.** Comments out the strict clippy aspect for the bench build.
  - **Open:** the bench's Rust shells (`agent/src`) have not been checked against it.

The patch is local to this bench. It has not been proposed upstream; contacting
the FEO maintainers needs the project owner's go-ahead.

## Build

1. Check out FEO and apply the patch:

   ```bash
   git clone https://github.com/eclipse-score/feo && cd feo
   git checkout 313b3d849c17881d3a11b6bf62aa2afab6565ef0
   git apply <bench>/agent/workspace/feo-313b3d84-bench.diff
   ```

2. Create the two packages the patch's labels name:

   ```bash
   mkdir -p probe/carla probe/embed
   cp <bench>/agent/workspace/libcarla.BUILD probe/carla/
   echo 'exports_files(["libcarla.BUILD"])' > probe/carla/BUILD.bazel
   cp <bench>/agent/workspace/python312.BUILD probe/embed/
   echo 'exports_files(["python312.BUILD"])' > probe/embed/BUILD.bazel
   ```

3. Install CPython 3.12.16 (`uv python install 3.12.16`) and point `@python312`'s `path` at it.
4. Install the LibCarla 0.9.16 client (`include/` and `lib/*.a`), built with the S-CORE gcc 12.2 toolchain outside Bazel, at `@libcarla`'s `path`.
   - **Gap:** the recipe for that build is not in this repository yet.
5. Copy the bench into the workspace as `de4sdv_bench/`: `interfaces`, `agent`, `actuation-adapter`, and the navigation rasterizer sources.
   - The rasterizer also needs upstream AutoE2E's native rasterizer in `navigation/.upstream/`; see `navigation/README.md`.
6. Build:

   ```bash
   bazel build --config=x86_64-linux //de4sdv_bench/agent:driving_agent \
     //de4sdv_bench/agent:agent_tap //de4sdv_bench/actuation-adapter:actuation_adapter
   ```

At run time the agent needs `LD_LIBRARY_PATH=<cpython>/lib`. Its configuration
also names a Python environment with numpy, plus torch for the checkpoint engine.
