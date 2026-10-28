"""Tests of the one ROS 2 environment of the bench host (adapterAbortConditions).

Every ROS 2 process on the host runs with rmw_cyclonedds_cpp, one fixed
ROS_DOMAIN_ID and one CYCLONEDDS_URI, whose configuration keeps DDS on the
loopback interface and sets MaxAutoParticipantIndex to at least the number of
ROS 2 processes. config/ros_environment.sh gives that environment to shells;
the Launch Manager configuration carries the same values for the adapter and
the health proxy node, because the Launch Manager passes a component only the
variables of its configuration.
"""

import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ElementTree

BENCH = Path(__file__).resolve().parents[1]
REPOSITORY = BENCH.parents[1]
sys.path.insert(0, str(BENCH / "scripts"))

ENVIRONMENT_FILE = BENCH / "config" / "ros_environment.sh"
CYCLONEDDS = BENCH / "config" / "cyclonedds.xml"
AEBS_CYCLONEDDS = REPOSITORY / "implementation" / "aebs-autoware-executable-bench" / "cyclonedds.xml"
LAUNCH_MANAGER = BENCH / "launch-manager" / "launch_manager_config.json"
ROS_COMPONENTS = ("adapter", "health_proxy")
NAMESPACE = {"c": "https://cdds.io/config"}


def _sourced(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", **(extra or {})}
    output = subprocess.run(
        ["bash", "-c", f'source "{ENVIRONMENT_FILE}" && env -0'], env=env, capture_output=True, check=True,
    ).stdout.decode()
    return dict(item.split("=", 1) for item in output.split("\0") if "=" in item)


def _settings(path: Path) -> dict[str, object]:
    domain = ElementTree.parse(path).getroot().find("c:Domain", NAMESPACE)
    interface = domain.find("c:General/c:Interfaces/c:NetworkInterface", NAMESPACE)
    return {
        "ParticipantIndex": domain.findtext("c:Discovery/c:ParticipantIndex", namespaces=NAMESPACE),
        "MaxAutoParticipantIndex": domain.findtext("c:Discovery/c:MaxAutoParticipantIndex", namespaces=NAMESPACE),
        "Peers": [peer.get("Address") for peer in domain.findall("c:Discovery/c:Peers/c:Peer", NAMESPACE)],
        "Interface": dict(interface.attrib),
        "AllowMulticast": domain.findtext("c:General/c:AllowMulticast", namespaces=NAMESPACE),
    }


def test_the_environment_file_sets_cyclonedds_one_domain_and_its_configuration():
    env = _sourced({"ROS_LOCALHOST_ONLY": "1"})
    assert env["RMW_IMPLEMENTATION"] == "rmw_cyclonedds_cpp"
    assert env["ROS_DOMAIN_ID"] == "91"
    assert env["CYCLONEDDS_URI"] == f"file://{CYCLONEDDS}"
    assert "ROS_LOCALHOST_ONLY" not in env


def test_the_cyclonedds_configuration_is_that_of_the_aebs_benches():
    settings = _settings(CYCLONEDDS)
    assert settings == _settings(AEBS_CYCLONEDDS)
    assert settings["Interface"] == {"name": "lo", "priority": "default", "multicast": "false"}
    assert settings["AllowMulticast"] == "false"
    assert settings["ParticipantIndex"] == "auto"


def test_the_participant_indices_cover_the_ros2_processes_of_the_bench():
    import run_rmw_startup_probe as probe

    # The most at once: the other participants of the probe, the adapter and a ros2 command line.
    most_processes = max(case.peers_before + case.peers_after for case in probe.CASES) + 2
    assert int(_settings(CYCLONEDDS)["MaxAutoParticipantIndex"]) == 120
    assert int(_settings(CYCLONEDDS)["MaxAutoParticipantIndex"]) > most_processes


def test_the_launch_manager_carries_the_same_environment_for_its_ros2_components():
    config = json.loads(LAUNCH_MANAGER.read_text(encoding="utf-8"))
    working_dir = config["defaults"]["deployment_config"]["working_dir"]
    shell = _sourced()
    for name, component in config["components"].items():
        variables = (component.get("deployment_config") or {}).get("environmental_variables", {})
        if name not in ROS_COMPONENTS:
            assert not {"RMW_IMPLEMENTATION", "ROS_DOMAIN_ID", "CYCLONEDDS_URI"} & set(variables), name
            continue
        assert variables["RMW_IMPLEMENTATION"] == shell["RMW_IMPLEMENTATION"], name
        assert variables["ROS_DOMAIN_ID"] == shell["ROS_DOMAIN_ID"], name
        assert variables["CYCLONEDDS_URI"] == f"file://{working_dir}/config/cyclonedds.xml", name
        assert variables["ROS_LOG_DIR"].startswith(f"{working_dir}/"), name
        assert "ROS_LOCALHOST_ONLY" not in variables, name
    assert config["defaults"]["deployment_config"]["environmental_variables"] == {}
