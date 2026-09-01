"""ROS 2 node wiring for the 010 visualization bridge.

Node construction requires a ROS 2 installation (rclpy). The pure core and
the source-adapter handlers are tested without ROS; this module is exercised
on the bench host (vmB) by the Phase 10 campaign.
"""

from __future__ import annotations

import threading

from rclpy.node import Node
from std_msgs.msg import Bool, String
from diagnostic_msgs.msg import DiagnosticArray
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from tier4_debug_msgs.msg import Float32Stamped
from autoware_control_msgs.msg import Control

from .frame_assembler import FrameAssembler
from .source_adapter import SourceAdapter, FrameServer, encode_frame_protobuf


class Aebs010BridgeNode(Node):
    """Read-only ROS 2 bridge: subscribes to pinned AEBS sources, serves frames.

    Declares no publisher, service, or action. The sole output path is the
    outbound length-delimited frame stream consumed by the AAOS ingress.
    """

    def __init__(
        self,
        *,
        frame_host: str = "0.0.0.0",
        frame_port: int = 4721,
        source_identity: str = "de4sdv_aebs_010_bridge",
    ) -> None:
        super().__init__("de4sdv_aebs_010_bridge")
        self._assembler = FrameAssembler(source_identity)
        clock = self.get_clock()
        self._adapter = SourceAdapter(self._assembler, lambda: clock.now().nanoseconds)
        self._server = FrameServer(frame_host, frame_port)
        self._server_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._server_thread.start()

        # Read-only subscriptions to the pinned 009B bench sources.
        self.create_subscription(Float32Stamped, "/control/autonomous_emergency_braking/debug/rss_distance", self._on_rss, 1)
        self.create_subscription(PointCloud2, "/control/autonomous_emergency_braking/debug/obstacle_pointcloud", self._on_cloud, 1)
        self.create_subscription(Odometry, "/localization/kinematic_state", self._on_odom, 1)
        self.create_subscription(DiagnosticArray, "/diagnostics", self._on_diagnostics, 10)
        self.create_subscription(Bool, "/de4sdv/aebs_009b/warning_request", self._on_warning, 1)
        self.create_subscription(Control, "/de4sdv/aebs_009b/emergency_braking_request", self._on_braking, 1)
        self.create_subscription(String, "/de4sdv/aebs_009b/coordination_state", self._on_lifecycle, 1)

        # Periodic frame assembly + publish to any connected client.
        self.create_timer(0.1, self._publish_frame)

    # -- subscription callbacks -------------------------------------------

    def _on_rss(self, msg: Float32Stamped) -> None:
        self._adapter.on_rss_distance(msg)

    def _on_cloud(self, msg: PointCloud2) -> None:
        self._adapter.on_obstacle_pointcloud(msg)

    def _on_odom(self, msg: Odometry) -> None:
        self._adapter.on_kinematic_state(msg)

    def _on_diagnostics(self, msg: DiagnosticArray) -> None:
        self._adapter.on_diagnostics(msg)

    def _on_warning(self, msg: Bool) -> None:
        self._adapter.on_warning_request(msg)

    def _on_braking(self, msg: Control) -> None:
        self._adapter.on_emergency_braking_request(msg)

    def _on_lifecycle(self, msg: String) -> None:
        self._adapter.on_coordination_state(msg)

    # -- frame output -------------------------------------------------------

    OBSTACLE_PROJECTION_MAX_AGE_NS = 500_000_000

    def _accept_loop(self) -> None:
        while True:
            try:
                self._server.serve_once()
            except OSError:
                return

    def _publish_frame(self) -> None:
        now_ns = self.get_clock().now().nanoseconds
        self._adapter.expire_obstacle_projection(
            now_ns=now_ns,
            max_age_ns=self.OBSTACLE_PROJECTION_MAX_AGE_NS,
        )
        frame = self._assembler.assemble(now_ns)
        try:
            self._server.send_frame(encode_frame_protobuf(frame))
        except (ConnectionError, OSError):
            pass  # no client connected; frames are dropped, not queued

    def destroy_node(self) -> bool:
        self._server.close()
        return super().destroy_node()


def main() -> None:
    import rclpy

    rclpy.init()
    node = Aebs010BridgeNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
