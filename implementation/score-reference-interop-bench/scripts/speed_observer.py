#!/usr/bin/env python3
"""Independent observer of /de4sdv/middleware/velocity_status (bench use).

A separate process in another language than the adapter. It subscribes with
the adapter's QoS (reliable, keep last 10) and writes one JSON line per
VelocityReport: the CLOCK_MONOTONIC receipt time, the header stamp, the
float32 bit pattern of longitudinal_velocity, lateral_velocity, heading_rate
and frame_id. It publishes nothing.
"""

from __future__ import annotations

import argparse
import json
import signal
import struct
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

from autoware_vehicle_msgs.msg import VelocityReport

TOPIC = "/de4sdv/middleware/velocity_status"


class SpeedObserver(Node):
    def __init__(self, out_path: str) -> None:
        super().__init__("de4sdv_score_speed_observer")
        self._out = open(out_path, "a", encoding="utf-8")
        qos = QoSProfile(depth=10, history=HistoryPolicy.KEEP_LAST, reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(VelocityReport, TOPIC, self._on_message, qos)

    def _on_message(self, message: VelocityReport) -> None:
        record = {
            "receipt_monotonic_ns": time.monotonic_ns(),
            "stamp_ns": message.header.stamp.sec * 1_000_000_000 + message.header.stamp.nanosec,
            "longitudinal_velocity_bits": struct.pack(">f", message.longitudinal_velocity).hex(),
            "lateral_velocity": message.lateral_velocity,
            "heading_rate": message.heading_rate,
            "frame_id": message.header.frame_id,
        }
        self._out.write(json.dumps(record) + "\n")
        self._out.flush()

    def close(self) -> None:
        self._out.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    arguments = parser.parse_args()
    rclpy.init(signal_handler_options=rclpy.signals.SignalHandlerOptions.NO)
    node = SpeedObserver(arguments.out)
    stop = {"requested": False}

    def _on_signal(_signum, _frame) -> None:
        stop["requested"] = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    print(json.dumps({"event": "observer_ready", "topic": TOPIC}), flush=True)
    while not stop["requested"]:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.close()
    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
