"""ROS 2 TCP ingress node for the AAOS Vehicle.Speed transfer bench."""

from __future__ import annotations

import argparse
import socketserver
import threading
import time

import rclpy
from autoware_vehicle_msgs.msg import VelocityReport
from rclpy.node import Node

from .bridge_core import (
    ROS_VELOCITY_REPORT_TOPIC,
    StalenessWatchdog,
    VehicleSpeedTcpBridgeCore,
)


class _VehicleSpeedRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        node = self.server.node  # type: ignore[attr-defined]
        peer = self.client_address
        node.get_logger().info(
            "AAOS Vehicle.Speed TCP client connected "
            f"peer={peer[0]}:{peer[1]}"
        )
        for line in self.rfile:
            node.handle_wire_line(line)
        node.get_logger().info("AAOS Vehicle.Speed TCP client disconnected")


class _VehicleSpeedTcpServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, handler, node: "VehicleSpeedTcpBridgeNode"):
        super().__init__(address, handler)
        self.node = node


class VehicleSpeedTcpBridgeNode(Node):
    """Publish normalized AAOS samples as Autoware VelocityReport messages."""

    def __init__(self, topic: str = ROS_VELOCITY_REPORT_TOPIC) -> None:
        super().__init__("de4sdv_vehicle_speed_tcp_bridge")
        self._publisher = self.create_publisher(VelocityReport, topic, 10)
        self._health_publisher = self.create_publisher(
            VelocityReport, topic + "_health", 10
        )
        self._core = VehicleSpeedTcpBridgeCore(self._publish)
        self._topic = topic
        self._watchdog = StalenessWatchdog(
            on_degraded=self._emit_degraded,
            on_restored=self._emit_restored,
        )
        self._watchdog.mark_valid(now_ns=time.time_ns())
        self._watchdog_period_s = 1.0
        self._watchdog_timer = self.create_timer(
            self._watchdog_period_s, self._check_staleness
        )

    def _publish(self, output) -> None:
        self._watchdog.mark_valid(now_ns=time.time_ns())
        message = VelocityReport()
        message.longitudinal_velocity = output.longitudinal_velocity_mps
        self._publisher.publish(message)
        self.get_logger().info(
            "DE4SDV_VELOCITY_REPORT_PUBLISHED "
            f"longitudinal_velocity_mps={output.longitudinal_velocity_mps} "
            f"source_timestamp_ns={output.timestamp_ns} topic={self._topic}"
        )

    def _emit_degraded(self, age_ns: int) -> None:
        # Honest degraded disposition: stale marker on the health topic.
        message = VelocityReport()
        message.longitudinal_velocity = float("nan")
        self._health_publisher.publish(message)
        self.get_logger().warning(
            "DE4SDV_VELOCITY_HEALTH degraded=stale "
            f"last_valid_age_ns={age_ns} topic={self._topic}_health"
        )

    def _emit_restored(self) -> None:
        self.get_logger().warning(
            f"DE4SDV_VELOCITY_HEALTH restored=healthy topic={self._topic}_health"
        )

    def _check_staleness(self) -> None:
        self._watchdog.tick(now_ns=time.time_ns())

    def handle_wire_line(self, line: bytes) -> None:
        try:
            self._core.handle_line(line, now_ns=time.time_ns())
        except (ValueError, TypeError) as error:
            self.get_logger().error(f"rejected AAOS Vehicle.Speed record: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=4711)
    parser.add_argument("--topic", default=ROS_VELOCITY_REPORT_TOPIC)
    args = parser.parse_args(argv)

    rclpy.init(args=None)
    node = VehicleSpeedTcpBridgeNode(topic=args.topic)
    server = _VehicleSpeedTcpServer(
        (args.listen_host, args.listen_port),
        _VehicleSpeedRequestHandler,
        node,
    )
    server_thread = threading.Thread(
        target=server.serve_forever,
        name="vehicle-speed-tcp-server",
        daemon=True,
    )
    server_thread.start()
    node.get_logger().info(
        "Vehicle.Speed TCP ingress listening "
        f"host={args.listen_host} port={args.listen_port}"
    )
    try:
        rclpy.spin(node)
    finally:
        server.shutdown()
        server.server_close()
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
