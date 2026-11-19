"""The Launch Manager's own mw::com configuration (launch-manager/config/mw_com_config_launch_manager.json).

Why the daemon needs one, read at the pins (eclipse-score/lifecycle v0.10.0 2afae116, eclipse-score/communication
v0.6.0 c5efd74f, the version Lifecycle v0.10.0 itself depends on, MODULE.bazel:317):
- the daemon offers the LmControl service for a state manager: run.cpp:179-189 creates the ControlProvider after the
  process group manager's initialize and ends with EXIT_FAILURE when that fails; control_provider.hpp:32-35 resolves
  the instance specifier "LaunchManager/StateManager/Instance", and lm_control_service.h:118-147 defines the service
  (methods ActivateRunTarget and GetActiveRunTarget, event ActivationResult);
- the daemon passes no configuration path to mw::com, so mw::com reads its default "./etc/mw_com_config.json"
  relative to the working directory (communication score/mw/com/runtime_configuration.cpp:31, 37), and a file it
  cannot read stops the process (configuration_json_parsing_strategy.cpp:1370-1376, the abort of session 4's
  rehearsal);
- "serviceTypes" and "serviceInstances" must be present (configuration_json_parsing_strategy.cpp:1104-1106,
  865-867), and the skeleton's instance must resolve to exactly one deployment (skeleton_base.cpp:346-355): a file
  without the instance makes ControlProvider::Create fail, and the daemon exits;
- upstream deploys the file as etc/mw_com_config.json beside etc/<config>.bin and runs the daemon in that directory
  (tests/utils/bazel/integration.bzl:98-103; tests/integration/smoke/smoke.py:38-42 runs it with cwd there), with
  the service type and
  the server instance this test compares against (tests/utils/environments/mw_com_config.json, the target
  //score/launch_manager:example_com_config).

The bench has no state manager, so the file holds the server instance only. The bench's processes all run as uid 0
(test_every_mw_com_manifest_of_the_bench_has_its_own_application_id), so the daemon takes its own applicationID,
3417; without one mw::com would fall back to the uid (communication bindings/lola/runtime.cpp:39-56).

With LIFECYCLE_SRC set to a checkout of eclipse-score/lifecycle at v0.10.0, the type and the server instance are
compared with upstream's file; otherwise that test is skipped with the reason.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
LM = HERE.parent
BENCH = LM.parent
CONFIG = LM / "config" / "mw_com_config_launch_manager.json"
SPECIFIER = "LaunchManager/StateManager/Instance"
SERVICE_TYPE = "/score/mw/lifecycle/LmControlService"
APPLICATION_ID = 3417


def load() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_the_file_offers_the_launch_managers_control_instance_and_nothing_else() -> None:
    data = load()
    assert sorted(data) == ["global", "serviceInstances", "serviceTypes"]
    assert [i["instanceSpecifier"] for i in data["serviceInstances"]] == [SPECIFIER]
    assert [t["serviceTypeName"] for t in data["serviceTypes"]] == [SERVICE_TYPE]
    instance = data["serviceInstances"][0]
    assert instance["serviceTypeName"] == SERVICE_TYPE
    assert instance["version"] == data["serviceTypes"][0]["version"] == {"major": 1, "minor": 0}
    assert [(i["instanceId"], i["binding"], i["asil-level"]) for i in instance["instances"]] == [(1, "SHM", "QM")]


def test_the_element_names_are_those_of_the_service_definition() -> None:
    """lm_control_service.h:131-143 at v0.10.0 names the methods and the event; mw::com matches them by name."""
    data = load()
    binding = data["serviceTypes"][0]["bindings"][0]
    assert binding["binding"] == "SHM"
    assert [e["eventName"] for e in binding["events"]] == ["ActivationResult"]
    assert sorted(m["methodName"] for m in binding["methods"]) == ["ActivateRunTarget", "GetActiveRunTarget"]
    instance = data["serviceInstances"][0]["instances"][0]
    assert [e["eventName"] for e in instance["events"]] == ["ActivationResult"]
    assert sorted(m["methodName"] for m in instance["methods"]) == ["ActivateRunTarget", "GetActiveRunTarget"]


def test_the_launch_manager_has_its_own_application_id_and_is_qm() -> None:
    assert load()["global"] == {"asil-level": "QM", "applicationID": APPLICATION_ID}


def test_no_other_service_of_the_bench_takes_the_service_id() -> None:
    ours = load()["serviceTypes"][0]["bindings"][0]["serviceId"]
    for path in sorted(BENCH.rglob("*.json")):
        if path == CONFIG or "tests" in path.relative_to(BENCH).parts:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        for service_type in data.get("serviceTypes", []):
            for binding in service_type.get("bindings", []):
                assert binding.get("serviceId") != ours, (path, service_type["serviceTypeName"])


def test_the_type_and_the_server_instance_are_upstreams() -> None:
    source = os.environ.get("LIFECYCLE_SRC")
    if not source:
        pytest.skip("LIFECYCLE_SRC is not set to a checkout of eclipse-score/lifecycle at v0.10.0")
    upstream = json.loads((Path(source) / "tests" / "utils" / "environments" / "mw_com_config.json").read_text())
    data = load()
    assert data["serviceTypes"] == upstream["serviceTypes"]
    assert data["serviceInstances"] == [i for i in upstream["serviceInstances"] if i["instanceSpecifier"] == SPECIFIER]
    assert upstream["global"] == {"asil-level": "QM"}  # the applicationID is the bench's addition
    header = (Path(source) / "score" / "launch_manager" / "src" / "daemon" / "src" / "control" /
              "control_provider.hpp").read_text()
    assert f'"{SPECIFIER}"' in header
