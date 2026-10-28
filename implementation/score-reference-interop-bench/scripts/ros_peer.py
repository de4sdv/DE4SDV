#!/usr/bin/env python3
"""Another ROS 2 participant on the bench host, for the startup probe (bench use).

One process with one node, so one DDS participant. It prints one JSON line
when its node exists, and spins until SIGTERM. With --count-velocity it also
subscribes to /de4sdv/middleware/velocity_status with the adapter's QoS and
prints, at the end, how many VelocityReports it received; that shows
discovery between it and the adapter. It publishes nothing. When the node
cannot be created, it ends with the exception, as any ROS 2 process would.
"""

from __future__ import annotations

import argparse
import json
import signal

import rclpy
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

from autoware_vehicle_msgs.msg import VelocityReport

TOPIC = "/de4sdv/middleware/velocity_status"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--count-velocity", action="store_true")
    arguments = parser.parse_args()
    rclpy.init(signal_handler_options=rclpy.signals.SignalHandlerOptions.NO)
    node = rclpy.create_node(arguments.name)
    received = {"count": 0}
    if arguments.count_velocity:
        qos = QoSProfile(depth=10, history=HistoryPolicy.KEEP_LAST, reliability=ReliabilityPolicy.RELIABLE)

        def on_message(_message: VelocityReport) -> None:
            received["count"] += 1

        node.create_subscription(VelocityReport, TOPIC, on_message, qos)
    stop = {"requested": False}

    def on_signal(_signum, _frame) -> None:
        stop["requested"] = True

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    print(json.dumps({"event": "peer_ready", "name": arguments.name}), flush=True)
    while not stop["requested"]:
        rclpy.spin_once(node, timeout_sec=0.1)
    print(json.dumps({"event": "peer_stopped", "name": arguments.name, "velocity_reports": received["count"]}),
          flush=True)
    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
