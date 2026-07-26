"""Collect live typed ROS readiness without asserting scenario behavior."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rosidl_runtime_py.utilities import get_message

EXPECTED = {
    "/map/vector_map": "autoware_map_msgs/msg/LaneletMapBin",
    "/diagnostics": "diagnostic_msgs/msg/DiagnosticArray",
    "/system/operation_mode/availability": "tier4_system_msgs/msg/OperationModeAvailability",
    "/system/fail_safe/mrm_state": "autoware_adapi_v1_msgs/msg/MrmState",
    "/system/emergency/control_cmd": "autoware_control_msgs/msg/Control",
    "/control/command/control_cmd": "autoware_control_msgs/msg/Control",
    "/localization/kinematic_state": "nav_msgs/msg/Odometry",
    "/localization/acceleration": "geometry_msgs/msg/AccelWithCovarianceStamped",
    "/vehicle/status/steering_status": "autoware_vehicle_msgs/msg/SteeringReport",
    "/control/command/gear_cmd": "autoware_vehicle_msgs/msg/GearCommand",
    "/system/mrm/emergency_stop/status": "tier4_system_msgs/msg/MrmBehaviorStatus",
}
EXPECTED_DIAGNOSTIC_IDENTITY = (
    "autonomous_emergency_braking: aeb_emergency_stop"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    rclpy.init()
    node = Node("de4sdv_readiness_collector")
    started = time.monotonic()
    deadline = started + args.timeout
    received: dict[str, float] = {}
    diagnostic_names: set[str] = set()
    subscriptions = []

    def mark_received(topic: str):
        def callback(_message) -> None:
            received[topic] = time.monotonic()

        return callback

    def mark_diagnostic(message) -> None:
        diagnostic_names.update(status.name for status in message.status)
        if EXPECTED_DIAGNOSTIC_IDENTITY in diagnostic_names:
            received["/diagnostics"] = time.monotonic()

    for topic, type_name in EXPECTED.items():
        qos = QoSProfile(depth=10)
        if topic == "/map/vector_map":
            qos = QoSProfile(
                depth=1,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            )
        callback = mark_diagnostic if topic == "/diagnostics" else mark_received(topic)
        subscriptions.append(
            node.create_subscription(get_message(type_name), topic, callback, qos)
        )

    actual: dict[str, list[str]] = {}
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.2)
        actual = dict(node.get_topic_names_and_types())
        types_ready = all(
            expected in actual.get(name, []) for name, expected in EXPECTED.items()
        )
        if types_ready and set(received) == set(EXPECTED):
            break

    finished = time.monotonic()
    endpoints = [
        {
            "name": name,
            "expected_type": expected,
            "actual_types": actual.get(name, []),
            "message_received": name in received,
            "received_after_start": received.get(name, 0.0) >= started,
            "last_message_age_seconds": (
                round(finished - received[name], 6) if name in received else None
            ),
            "ready": (
                expected in actual.get(name, [])
                and name in received
                and received[name] >= started
            ),
        }
        for name, expected in sorted(EXPECTED.items())
    ]
    document = {
        "built": None,
        "launched": True,
        "ready": all(item["ready"] for item in endpoints),
        "scenario_executed": False,
        "collection_window_seconds": round(finished - started, 6),
        "diagnostic_identity": {
            "expected": EXPECTED_DIAGNOSTIC_IDENTITY,
            "matched": EXPECTED_DIAGNOSTIC_IDENTITY in diagnostic_names,
            "observed_names": sorted(diagnostic_names),
        },
        "endpoints": endpoints,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    node.destroy_node()
    rclpy.shutdown()
    raise SystemExit(0 if document["ready"] else 1)


if __name__ == "__main__":
    main()
