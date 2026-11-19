"""The environment the Launch Manager gives the processes that link LibCarla's client.

Session 5's rehearsal on the L4 (not evidence) found vision_pilot and actuation_adapter killed by SIGSEGV within
0.2 s of their start under the real Launch Manager (its debug log: "PID ... was killed by signal 11"; the kernel:
"segfault at 0 ... in libc.so.6"). Read at the pins:
- Lifecycle v0.10.0 (2afae116) starts a process with exactly the environment of its configuration: execve gets
  deployment_config.environmental_variables.envp() (score/launch_manager/src/daemon/src/process_group_manager/details/
  process_launcher.cpp:395), to which the daemon adds only LCM_ALIVE_INTERFACE_PATH for a supervised component
  (component.cpp:63). HOME is not inherited.
- LibCarla's client at CARLA 14ac3b1a50 sets its cache path in a static initializer from CARLA_CACHE_DIR, else from
  std::getenv("HOME") with no check for null (LibCarla/source/carla/client/FileTransfer.cpp:17-31), so a process
  without both crashes before main. Reproduced on the L4: `env -i LD_LIBRARY_PATH=... bin/actuation_adapter --help`
  exits 139, with CARLA_CACHE_DIR set it prints its usage.
- Both binaries link @libcarla//:client (actuation-adapter/BUILD.bazel, score-build/workspace/visionpilot.BUILD.bazel);
  the identity recorder, someipd and gatewayd do not.

So both components get CARLA_CACHE_DIR in their own configuration, a directory under the run directory that the stop
collects.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
CONFIG = BENCH / "launch-manager" / "config" / "launch_manager_config.json"
PATH_ONLY = BENCH / "score-path" / "config" / "launch_manager_config_path_only.json"
CACHE = "/tmp/de4sdv-da-bench/run/carla_cache"
LINKS_LIBCARLA = {"actuation_adapter": BENCH / "actuation-adapter" / "BUILD.bazel",
                  "vision_pilot": BENCH / "score-build" / "workspace" / "visionpilot.BUILD.bazel"}


def test_the_binaries_named_here_are_the_ones_that_link_libcarla() -> None:
    for name, build in LINKS_LIBCARLA.items():
        assert "@libcarla//:client" in build.read_text(encoding="utf-8"), name
    recorder = (BENCH / "identity-recorder" / "BUILD.bazel").read_text(encoding="utf-8")
    assert "libcarla" not in recorder


def test_every_component_that_links_libcarla_gets_a_carla_cache_dir() -> None:
    for config_path in (CONFIG, PATH_ONLY):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert "CARLA_CACHE_DIR" not in config["defaults"]["deployment_config"].get("environmental_variables", {})
        for name, component in config["components"].items():
            env = component.get("deployment_config", {}).get("environmental_variables", {})
            if name in LINKS_LIBCARLA:
                assert env.get("CARLA_CACHE_DIR") == CACHE, (config_path.name, name)
                # the component's own list replaces the defaults' list: LD_LIBRARY_PATH must stay in it
                assert env.get("LD_LIBRARY_PATH") == "/tmp/de4sdv-da-bench/lib", (config_path.name, name)
            else:
                assert "CARLA_CACHE_DIR" not in env, (config_path.name, name)
            assert "HOME" not in env, (config_path.name, name)


def test_the_cache_lies_in_the_run_directory_the_stop_collects() -> None:
    stop = (BENCH / "score-path" / "scripts" / "stop_score_side.sh").read_text(encoding="utf-8")
    assert re.search(r'collect "\$DA_STAGE/run" run', stop)
    assert CACHE.startswith("/tmp/de4sdv-da-bench/run/")
