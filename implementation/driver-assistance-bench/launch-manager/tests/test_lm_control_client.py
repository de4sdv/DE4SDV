"""The stop run's Launch Manager control client (launch-manager/control/) and its mw::com configuration.

Why a client of our own, read at eclipse-score/lifecycle v0.10.0 (2afae116):
- the daemon offers LmControl (methods ActivateRunTarget and GetActiveRunTarget, event ActivationResult) for a state
  manager (src/daemon/src/control/control_provider.hpp:32-35, :113-160), and the library //score/launch_manager:
  control_cc (src/lm_control/src/ilm_control.hpp) is its client; Lifecycle ships no command-line client of it: the
  example lmcontrol (examples/control_application/control_app_cli.cpp) only writes to a socket of control_daemon, a
  process that would have to run as a component of the configuration;
- the daemon refuses a queued request (control_provider.hpp:131-138, kNotImplemented), so the client asks with force;
- every state manager in upstream's tests calls ILmControl::Create("StateManager/LaunchManager/Instance") with that
  proxy-side instance in its mw::com configuration (tests/utils/environments/mw_com_config.json).

What is pinned here: the core's order and outcome (lm_control_client_test.cpp), the main's syntax against the API's
declarations (tests/lifecycle_mock), the client's mw::com configuration against the daemon's, and the build and bundle
wiring. The real compile is the S-CORE Bazel build's, the real activation a run on the S-CORE host.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
LM = HERE.parent
BENCH = LM.parent
CONTROL = LM / "control"
CLIENT_CONFIG = LM / "config" / "mw_com_config_lm_control_client.json"
DAEMON_CONFIG = LM / "config" / "mw_com_config_launch_manager.json"
MWCOM_MOCK = BENCH.parent / "closed-loop-driving-bench" / "state-publisher" / "tests" / "mock"
BUILD = BENCH / "score-build" / "build_score_bench.sh"
LM_BUILD = BENCH / "score-build" / "workspace" / "launch_manager.BUILD.bazel"
FLAGS = ["-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic"]
PROXY_SPECIFIER = "StateManager/LaunchManager/Instance"


def _compiler() -> str:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is not installed")
    assert compiler is not None
    return compiler


def test_the_core(tmp_path: Path) -> None:
    binary = tmp_path / "lm_control_client_test"
    subprocess.run([_compiler(), *FLAGS, "-pthread", f"-I{CONTROL}", str(HERE / "lm_control_client_test.cpp"),
                    str(CONTROL / "lm_control_client.cpp"), "-o", str(binary)], check=True)
    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "lm_control_client_test: all passed" in result.stdout


def test_the_main_against_the_api_declarations() -> None:
    if not (MWCOM_MOCK / "score" / "mw" / "com" / "runtime.h").is_file():
        pytest.skip("the closed-loop driving bench's mw::com mock is not present")
    subprocess.run([_compiler(), *FLAGS, "-fsyntax-only", f"-I{CONTROL}", f"-I{HERE / 'lifecycle_mock'}",
                    f"-I{MWCOM_MOCK}", str(CONTROL / "lm_control_client_main.cpp")], check=True)
    main = (CONTROL / "lm_control_client_main.cpp").read_text()
    # force = true: the daemon rejects a queued request at v0.10.0
    assert "activate_run_target(lc::RunTargetName{std::string_view{target}}, true)" in main
    assert "RuntimeConfiguration{options.mw_com_config}" in main


def test_the_client_config_is_the_proxy_side_of_the_daemons_instance() -> None:
    client = json.loads(CLIENT_CONFIG.read_text(encoding="utf-8"))
    daemon = json.loads(DAEMON_CONFIG.read_text(encoding="utf-8"))
    assert sorted(client) == ["global", "serviceInstances", "serviceTypes"]
    assert client["serviceTypes"] == daemon["serviceTypes"]
    [instance] = client["serviceInstances"]
    assert instance["instanceSpecifier"] == PROXY_SPECIFIER
    assert instance["serviceTypeName"] == daemon["serviceInstances"][0]["serviceTypeName"]
    [deployment] = instance["instances"]
    [server] = daemon["serviceInstances"][0]["instances"]
    assert (deployment["instanceId"], deployment["binding"]) == (server["instanceId"], server["binding"])
    assert [e["eventName"] for e in deployment["events"]] == ["ActivationResult"]
    assert client["global"] == {"asil-level": "QM", "applicationID": 3418}
    header = (CONTROL / "lm_control_client.h").read_text()
    assert f'std::string instance_specifier = "{PROXY_SPECIFIER}";' in header


def test_the_client_config_is_upstreams_proxy_instance() -> None:
    source = os.environ.get("LIFECYCLE_SRC")
    if not source:
        pytest.skip("LIFECYCLE_SRC is not set to a checkout of eclipse-score/lifecycle at v0.10.0")
    upstream = json.loads((Path(source) / "tests" / "utils" / "environments" / "mw_com_config.json").read_text())
    client = json.loads(CLIENT_CONFIG.read_text(encoding="utf-8"))
    assert client["serviceTypes"] == upstream["serviceTypes"]
    assert client["serviceInstances"] == [i for i in upstream["serviceInstances"]
                                          if i["instanceSpecifier"] == PROXY_SPECIFIER]
    driver = (Path(source) / "tests" / "integration" / "explicit_fallback_request" /
              "control_client_test_driver.cpp").read_text()
    assert f'ILmControl::Create("{PROXY_SPECIFIER}")' in driver


def test_the_build_compiles_the_client_into_the_bundle() -> None:
    build = BUILD.read_text()
    assert "//de4sdv_da_bench/launch-manager:lm_control_client" in build
    for name in ("lm_control_client.h", "lm_control_client.cpp", "lm_control_client_main.cpp"):
        assert f'"$BENCH"/launch-manager/control/{name}' in build
    bundle = build.split("\nstep bundle\n", 1)[1]
    assert 'cp -L "$SB/de4sdv_da_bench/launch-manager/lm_control_client" "$B/bin/"' in bundle
    assert ('cp "$BENCH/launch-manager/config/mw_com_config_lm_control_client.json" "$B/config/launch_manager/"'
            in bundle)
    rules = LM_BUILD.read_text()
    assert re.search(r'cc_binary\(\s*name = "lm_control_client",', rules)
    assert '"@score_lifecycle//score/launch_manager:control_cc"' in rules
    assert '"@score_communication//score/mw/com"' in rules
    # Bazel refuses a load() after another statement
    first_rule = rules.index("launch_manager_config(")
    assert all(m.start() < first_rule for m in re.finditer(r"^load\(", rules, flags=re.M))
