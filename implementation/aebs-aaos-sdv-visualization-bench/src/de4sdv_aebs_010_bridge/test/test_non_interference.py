"""Non-interference contract tests: the bridge must not command anything.

REQ-AEBS-S2-005 requires no command path from the visualization chain into
Autoware, the AEBS coordinator, or vehicle control. These tests enforce the
ROS-graph shape of the bridge at the source level: no publisher/service/
action declarations exist anywhere in the bridge package.
"""

from __future__ import annotations

from pathlib import Path

BRIDGE_DIR = Path(__file__).resolve().parents[1] / "de4sdv_aebs_010_bridge"


def _bridge_sources() -> list[str]:
    return [p.read_text(encoding="utf-8") for p in sorted(BRIDGE_DIR.glob("*.py"))]


def test_no_publisher_declarations_in_bridge() -> None:
    for source in _bridge_sources():
        assert "create_publisher" not in source, "bridge must not publish ROS topics"


def test_no_service_or_action_servers_in_bridge() -> None:
    for source in _bridge_sources():
        assert "create_service" not in source, "bridge must not expose ROS services"
        assert "create_action" not in source and "ActionServer" not in source, (
            "bridge must not expose ROS actions"
        )


def test_no_control_topic_references() -> None:
    forbidden = (
        "/control/command",
        "/control/trajectory_follower",
        "emergency_cmd",
        "gear_cmd",
        "turn_indicators",
    )
    for source in _bridge_sources():
        for token in forbidden:
            assert token not in source, f"bridge references a control surface: {token}"


def test_no_client_calls_toward_aebs_nodes() -> None:
    forbidden = ("create_client", "call_async", "inject_target")
    for source in _bridge_sources():
        for token in forbidden:
            assert token not in source, f"bridge calls into AEBS nodes: {token}"


def test_socket_server_is_send_only() -> None:
    server_source = (BRIDGE_DIR / "source_adapter.py").read_text(encoding="utf-8")
    # The only socket receive-family call allowed is none: server sends frames
    # and never reads commands from the guest.
    for token in ("recv(", "recvfrom(", "recvmsg("):
        assert token not in server_source, f"frame server reads from the client: {token}"


def test_transport_is_not_the_mw010_port() -> None:
    node_source = (BRIDGE_DIR / "ros_node.py").read_text(encoding="utf-8")
    assert "4721" in node_source, "bridge must use the new 010 transport port"
    assert "4711" not in node_source, "bridge must not reuse the INC-MW-010 port"
