"""Tests of the Launch Manager configuration of the bench and of its renderer.

The Launch Manager passes a component only the environment variables of its
configuration, as literal values. So the configuration gives each component
what it needs: someipd and gatewayd the library directory of the bundle and
someipd its vsomeip configuration; the adapter and the health proxy node the
ROS 2 environment of the bench, and the renderer adds the host's ROS 2 setup
to them. The components start their executables directly, with their
arguments, so the Launch Manager's signals and process states are theirs.
"""

import json
from pathlib import Path
import subprocess
import sys

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "scripts"))

import check_launch_manager_environment as loader  # noqa: E402
import render_launch_manager_config as renderer  # noqa: E402

CONFIG_PATH = BENCH / "launch-manager" / "launch_manager_config.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
WORKING_DIR = CONFIG["defaults"]["deployment_config"]["working_dir"]


def _variables(config: dict, name: str) -> dict[str, str]:
    return (config["components"][name].get("deployment_config") or {}).get("environmental_variables", {})


def test_the_daemons_get_the_library_directory_and_someipd_its_vsomeip_configuration():
    for name in ("someipd", "gatewayd"):
        assert _variables(CONFIG, name)["LD_LIBRARY_PATH"] == f"{WORKING_DIR}/lib", name
    assert _variables(CONFIG, "someipd")["VSOMEIP_CONFIGURATION"] == f"{WORKING_DIR}/config/vsomeip_loopback.json"


def test_each_component_starts_its_executable_directly_with_files_of_the_bundle():
    bin_dir = CONFIG["defaults"]["deployment_config"]["bin_dir"]
    assert bin_dir == f"{WORKING_DIR}/bin"
    bundled = {path.name for path in (BENCH / "config").iterdir()} | {"someip_gateway_config.bin"}
    for name, component in CONFIG["components"].items():
        properties = component["component_properties"]
        assert not properties["binary_name"].endswith(".sh"), name
        for argument in properties.get("process_arguments", []):
            if argument.startswith(f"{WORKING_DIR}/config/"):
                assert argument.rsplit("/", 1)[-1] in bundled, (name, argument)


def test_the_ros2_components_are_the_only_ones_with_the_ros2_environment():
    for name in ("someipd", "gatewayd"):
        assert "RMW_IMPLEMENTATION" not in _variables(CONFIG, name)
    for name in ("adapter", "health_proxy"):
        assert _variables(CONFIG, name)["RMW_IMPLEMENTATION"] == "rmw_cyclonedds_cpp"
    assert _variables(CONFIG, "adapter")["MW_LOG_CONFIG_FILE"] == f"{WORKING_DIR}/config/mw_log_adapter.json"


def _fake_setup(tmp_path: Path, body: str) -> Path:
    setup = tmp_path / "setup.bash"
    setup.write_text(body, encoding="utf-8")
    return setup


def test_the_renderer_adds_the_variables_of_the_setup_script_to_the_ros2_components(tmp_path):
    setup = _fake_setup(tmp_path, "export AMENT_PREFIX_PATH=/opt/ros/humble\n"
                                  "export LD_LIBRARY_PATH=/opt/ros/humble/lib\n"
                                  "export PATH=/opt/ros/humble/bin:$PATH\n"
                                  "export ROS_LOCALHOST_ONLY=0\n"
                                  "export ROS_DISTRO=humble\n")
    variables = renderer.ros_setup_variables(setup, WORKING_DIR)
    assert variables["AMENT_PREFIX_PATH"] == "/opt/ros/humble"
    assert variables["PATH"].startswith("/opt/ros/humble/bin:")
    assert "ROS_LOCALHOST_ONLY" not in variables
    rendered = renderer.render(CONFIG, variables, ["adapter", "health_proxy"], 1001, 1001)
    adapter = _variables(rendered, "adapter")
    assert adapter["LD_LIBRARY_PATH"] == "/opt/ros/humble/lib"
    assert adapter["ROS_DISTRO"] == "humble"
    assert adapter["RMW_IMPLEMENTATION"] == "rmw_cyclonedds_cpp"
    assert _variables(rendered, "someipd") == _variables(CONFIG, "someipd")
    assert rendered["defaults"]["deployment_config"]["sandbox"]["uid"] == 1001
    assert "sandbox" not in CONFIG["defaults"]["deployment_config"]


def test_the_committed_values_win_over_the_setup_script():
    rendered = renderer.render(CONFIG, {"RMW_IMPLEMENTATION": "rmw_fastrtps_cpp", "ROS_DISTRO": "humble"},
                               ["adapter"], 1, 1)
    assert _variables(rendered, "adapter")["RMW_IMPLEMENTATION"] == "rmw_cyclonedds_cpp"


def test_the_renderer_refuses_a_value_that_needs_expansion():
    with pytest.raises(SystemExit):
        renderer.render(CONFIG, {"LD_LIBRARY_PATH": "$HOME/lib"}, ["adapter"], 1, 1)


def test_the_renderer_refuses_more_than_one_hundred_variables():
    with pytest.raises(SystemExit):
        renderer.render(CONFIG, {f"V{index}": "x" for index in range(101)}, ["adapter"], 1, 1)


def test_the_renderer_runs_as_a_script(tmp_path):
    setup = _fake_setup(tmp_path, "export AMENT_PREFIX_PATH=/opt/ros/humble\n")
    rendered_path = tmp_path / "rendered.json"
    subprocess.run([sys.executable, str(BENCH / "scripts" / "render_launch_manager_config.py"), str(CONFIG_PATH),
                    str(rendered_path), "--uid", "7", "--gid", "8", "--ros-setup", str(setup)],
                   check=True, capture_output=True)
    rendered = json.loads(rendered_path.read_text(encoding="utf-8"))
    assert _variables(rendered, "health_proxy")["AMENT_PREFIX_PATH"] == "/opt/ros/humble"
    assert rendered["defaults"]["deployment_config"]["sandbox"]["gid"] == 8


def test_the_load_check_names_each_library_that_ldd_cannot_find():
    output = ("\tlinux-vdso.so.1 (0x00007ffd)\n"
              "\tlibrclcpp.so => /opt/ros/humble/lib/librclcpp.so (0x00007f1)\n"
              "\tlibautoware_vehicle_msgs__rosidl_typesupport_cpp.so => not found\n")
    assert loader.ldd_problems(output) == ["libautoware_vehicle_msgs__rosidl_typesupport_cpp.so => not found"]
    assert loader.ldd_problems("\tlibc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x1)\n") == []


def test_the_load_check_runs_ldd_in_the_rendered_environment_only(tmp_path):
    config = json.loads(json.dumps(CONFIG))
    config["defaults"]["deployment_config"]["bin_dir"] = "/usr/bin"
    config["components"]["someipd"]["component_properties"]["binary_name"] = "true"
    config["components"]["gatewayd"]["component_properties"]["binary_name"] = "de4sdv-no-such-binary"
    results, passed = loader.check(config)
    by_name = {result["component"]: result for result in results}
    assert by_name["someipd"]["result"] == "loads"
    assert by_name["someipd"]["variables"] == 2
    assert by_name["gatewayd"]["result"] == "not in bin_dir yet"
    assert passed


def test_the_load_check_fails_when_a_required_executable_is_missing():
    config = json.loads(json.dumps(CONFIG))
    config["defaults"]["deployment_config"]["bin_dir"] = "/usr/bin"
    config["components"]["someipd"]["component_properties"]["binary_name"] = "true"
    config["components"]["gatewayd"]["component_properties"]["binary_name"] = "de4sdv-no-such-binary"
    results, passed = loader.check(config, ("someipd", "gatewayd"))
    assert not passed
    assert {result["component"]: result["result"] for result in results}["gatewayd"] == "missing from bin_dir"
