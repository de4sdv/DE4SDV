"""Independent ROS 2 observer for the Autoware VelocityReport result."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import rclpy
from autoware_vehicle_msgs.msg import VelocityReport
from rclpy.node import Node

from .bridge_core import ROS_VELOCITY_REPORT_TOPIC


class VelocityReportObserver(Node):
    """Observe the ROS topic independently of the TCP bridge publisher."""

    def __init__(
        self,
        *,
        topic: str,
        expected_mps: float,
        tolerance_mps: float,
        timeout_s: float,
        output: Path | None,
    ) -> None:
        super().__init__("de4sdv_velocity_report_independent_observer")
        self._expected_mps = expected_mps
        self._tolerance_mps = tolerance_mps
        self._deadline = time.monotonic() + timeout_s
        self._output = output
        self._topic = topic
        self.success = False
        self.failure_reason: str | None = None
        self._subscription = self.create_subscription(
            VelocityReport,
            topic,
            self._on_message,
            10,
        )

    def _on_message(self, message: VelocityReport) -> None:
        value = message.longitudinal_velocity
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            self.failure_reason = "received non-finite longitudinal velocity"
            return
        observation = {
            "topic": self._topic,
            "longitudinal_velocity_mps": float(value),
            "received_at_ns": time.time_ns(),
        }
        rendered = json.dumps(observation, sort_keys=True)
        print(f"DE4SDV_VELOCITY_REPORT_OBSERVED {rendered}", flush=True)
        if abs(float(value) - self._expected_mps) <= self._tolerance_mps:
            self.success = True
            if self._output is not None:
                self._output.parent.mkdir(parents=True, exist_ok=True)
                self._output.write_text(rendered + "\n", encoding="utf-8")
            print(f"DE4SDV_VEHICLE_SPEED_VALIDATED {rendered}", flush=True)

    def timed_out(self) -> bool:
        return time.monotonic() >= self._deadline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default=ROS_VELOCITY_REPORT_TOPIC)
    parser.add_argument("--expected-mps", type=float, default=10.0)
    parser.add_argument("--tolerance-mps", type=float, default=1e-9)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if not math.isfinite(args.expected_mps) or not math.isfinite(args.tolerance_mps):
        parser.error("expected and tolerance values must be finite")

    rclpy.init(args=None)
    observer = VelocityReportObserver(
        topic=args.topic,
        expected_mps=args.expected_mps,
        tolerance_mps=args.tolerance_mps,
        timeout_s=args.timeout_s,
        output=args.output,
    )
    try:
        while rclpy.ok() and not observer.success and not observer.timed_out():
            rclpy.spin_once(observer, timeout_sec=0.2)
    finally:
        observer.destroy_node()
        rclpy.shutdown()
    if observer.success:
        return 0
    print(
        "DE4SDV_VEHICLE_SPEED_VALIDATION_FAILED "
        f"reason={observer.failure_reason or 'timeout'}",
        flush=True,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
