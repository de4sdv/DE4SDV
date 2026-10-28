"""Tests of the check of the adapter node's ROS 2 endpoints in a member run.

In a member run the adapter node has its VelocityReport publication and the
/parameter_events subscription of rclcpp's time source, and nothing else: no
parameter services, no parameter event publisher, no /rosout.
"""

from pathlib import Path
import sys

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.node_info import check_member_endpoints, parse_node_info  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MEMBER = (FIXTURES / "ros2_node_info_member_run.txt").read_text(encoding="utf-8")
WITH_SERVICES = (FIXTURES / "ros2_node_info_parameter_services.txt").read_text(encoding="utf-8")


def test_reads_the_sections_of_ros2_node_info():
    sections = parse_node_info(MEMBER)
    assert sections["Subscribers"] == {"/parameter_events": "rcl_interfaces/msg/ParameterEvent"}
    assert sections["Service Servers"] == {}
    assert len(parse_node_info(WITH_SERVICES)["Service Servers"]) == 6


def test_the_member_endpoints_pass():
    check = check_member_endpoints(MEMBER)
    assert check["passed"], check["reasons"]


def test_parameter_services_fail():
    check = check_member_endpoints(WITH_SERVICES)
    assert not check["passed"]
    assert any("set_parameters" in reason for reason in check["reasons"])


def test_rosout_and_a_parameter_event_publisher_fail():
    text = MEMBER.replace(
        "  Publishers:\n",
        "  Publishers:\n    /parameter_events: rcl_interfaces/msg/ParameterEvent\n    /rosout: rcl_interfaces/msg/Log\n")
    check = check_member_endpoints(text)
    assert not check["passed"]
    assert any("/rosout" in reason for reason in check["reasons"])


def test_a_node_that_was_not_found_fails():
    check = check_member_endpoints("Unable to find node '/de4sdv_score_adapter'\n")
    assert not check["passed"]


def test_a_missing_publication_fails():
    text = MEMBER.replace("    /de4sdv/middleware/velocity_status: autoware_vehicle_msgs/msg/VelocityReport\n", "")
    assert not check_member_endpoints(text)["passed"]
