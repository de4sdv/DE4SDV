"""DE4SDV nominal AEBS integration coordinator around pinned native Autoware AEB.

Native Autoware retains path, obstacle, relative-speed, RSS-distance, and collision
assessment responsibility. This prototype adds warning, explicit override evaluation,
and a nominal-path EmergencyBrakingRequest. It never emits an MRM request.
"""
from __future__ import annotations

import json
import math
import struct

from autoware_control_msgs.msg import Control
from autoware_internal_debug_msgs.msg import BoolStamped
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Bool, String
from tier4_debug_msgs.msg import Float32Stamped

from .aebs_coordination_core import (
    InterventionLatch,
    classify_override_source,
    next_warning_state,
)

_DIAGNOSTIC_NAME = "autonomous_emergency_braking: aeb_emergency_stop"
_INTERVENTION_MESSAGE = "[AEB]: Emergency Brake"


def _stamp_nanoseconds(stamp: object) -> int:
    sec = int(getattr(stamp, "sec"))
    nanosec = int(getattr(stamp, "nanosec"))
    if sec < 0 or nanosec < 0 or nanosec >= 1_000_000_000:
        return 0
    return sec * 1_000_000_000 + nanosec


def _source_age_s(stamp: object, now_ns: int, max_age_s: float) -> float | None:
    source_ns = _stamp_nanoseconds(stamp)
    if source_ns <= 0:
        return None
    age = (now_ns - source_ns) / 1e9
    return age if 0.0 <= age <= max_age_s else None


class AebsCoordinator(Node):
    def __init__(self) -> None:
        super().__init__("de4sdv_aebs_coordinator")
        self.declare_parameter("warning_margin_m", 3.0)
        self.declare_parameter("braking_acceleration_mps2", -6.0)
        self.declare_parameter("override_max_age_s", 0.2)
        self.declare_parameter("stop_speed_mps", 0.1)
        self.declare_parameter("stop_hold_s", 0.5)
        self.declare_parameter("odometry_max_age_s", 0.2)
        self.warning_margin_m = float(self.get_parameter("warning_margin_m").value)
        self.braking_acceleration_mps2 = float(self.get_parameter("braking_acceleration_mps2").value)
        self.override_max_age_s = float(self.get_parameter("override_max_age_s").value)
        self._latch = InterventionLatch(
            self.get_parameter("stop_speed_mps").value,
            self.get_parameter("stop_hold_s").value,
            self.get_parameter("odometry_max_age_s").value,
        )
        if not math.isfinite(self.override_max_age_s) or self.override_max_age_s <= 0.0:
            raise ValueError("override_max_age_s must be finite and positive")
        self._nominal: Control | None = None
        self._override: bool | None = None
        self._override_received_ns: int | None = None
        self._override_source_ns: int | None = None
        self._rss_m: float | None = None
        self._distance_m: float | None = None
        self._warning = False
        self._ego_speed_mps: float | None = None
        self._odometry_received_ns: int | None = None
        self.warning_pub = self.create_publisher(Bool, "/de4sdv/aebs_009b/warning_request", 1)
        self.override_eval_pub = self.create_publisher(String, "/de4sdv/aebs_009b/override_evaluated_clear", 1)
        self.risk_pub = self.create_publisher(String, "/de4sdv/aebs_009b/risk_assessment", 1)
        self.brake_pub = self.create_publisher(Control, "/de4sdv/aebs_009b/emergency_braking_request", 1)
        self.state_pub = self.create_publisher(String, "/de4sdv/aebs_009b/coordination_state", 1)
        self.override_authorization_pub = self.create_publisher(
            DiagnosticArray, "/de4sdv/aebs_009d/override_authorization", 1
        )
        self.control_pub = self.create_publisher(Control, "/control/trajectory_follower/control_cmd", 1)
        self.create_subscription(Control, "/de4sdv/aebs_009b/nominal_control_cmd", self._on_nominal, 1)
        self.create_subscription(BoolStamped, "/de4sdv/aebs_009b/driver_override", self._on_override, 1)
        self.create_subscription(Float32Stamped, "/control/autonomous_emergency_braking/debug/rss_distance", self._on_rss, 1)
        self.create_subscription(PointCloud2, "/perception/obstacle_segmentation/pointcloud", self._on_cloud, 1)
        self.create_subscription(DiagnosticArray, "/diagnostics", self._on_diagnostics, 10)
        self.create_subscription(Odometry, "/localization/kinematic_state", self._on_odometry, 10)
        self.create_timer(0.05, self._publish)

    def _on_nominal(self, message: Control) -> None:
        self._nominal = message

    def _on_override(self, message: BoolStamped) -> None:
        now_ns = self.get_clock().now().nanoseconds
        source_ns = _stamp_nanoseconds(message.stamp)
        self._override = bool(message.data)
        self._override_received_ns = now_ns
        self._override_source_ns = source_ns

    def _override_is_fresh_and_clear(self) -> bool:
        if self._override is not False or self._override_received_ns is None or self._override_source_ns is None:
            return False
        now_ns = self.get_clock().now().nanoseconds
        receipt_age_s = (now_ns - self._override_received_ns) / 1e9
        source_age_s = (now_ns - self._override_source_ns) / 1e9
        return 0.0 <= receipt_age_s <= self.override_max_age_s and 0.0 <= source_age_s <= self.override_max_age_s

    def _on_rss(self, message: Float32Stamped) -> None:
        value = float(message.data)
        if math.isfinite(value) and value >= 0.0:
            self._rss_m = value

    def _on_cloud(self, message: PointCloud2) -> None:
        x_field = next((field for field in message.fields if field.name == "x"), None)
        if x_field is None or message.point_step <= 0:
            return
        endian = ">" if message.is_bigendian else "<"
        distances = []
        raw = bytes(message.data)
        for offset in range(int(x_field.offset), len(raw), int(message.point_step)):
            if offset + 4 > len(raw):
                break
            value = struct.unpack_from(endian + "f", raw, offset)[0]
            if math.isfinite(value) and value > 0.0:
                distances.append(value)
        if distances:
            self._distance_m = min(distances)

    def _on_diagnostics(self, message: DiagnosticArray) -> None:
        for status in message.status:
            if status.name != _DIAGNOSTIC_NAME:
                continue
            intervention = (
                status.level == DiagnosticStatus.ERROR
                and status.message == _INTERVENTION_MESSAGE
            )
            override_clear = self._override_is_fresh_and_clear()
            diagnostic_ns = _stamp_nanoseconds(message.header.stamp)
            if intervention:
                self._publish_typed_override_authorization(
                    message.header.stamp, diagnostic_ns
                )
            if intervention and override_clear:
                diagnostic_stamp = (
                    f"{int(message.header.stamp.sec)}."
                    f"{int(message.header.stamp.nanosec):09d}"
                )
                self._publish_override_evaluation(
                    "intervention", diagnostic_source_stamp=diagnostic_stamp
                )
            self._latch.observe_diagnostic(intervention, override_clear)
            return

    @staticmethod
    def _format_stamp(nanoseconds: int | None) -> str:
        if nanoseconds is None:
            return "none"
        return (
            f"{nanoseconds // 1_000_000_000}."
            f"{nanoseconds % 1_000_000_000:09d}"
        )

    def _publish_typed_override_authorization(
        self, diagnostic_stamp: object, diagnostic_ns: int
    ) -> None:
        disposition = classify_override_source(
            self._override,
            self._override_source_ns,
            diagnostic_ns,
            self.override_max_age_s,
        )
        authorization = DiagnosticArray()
        authorization.header.stamp = diagnostic_stamp
        status = DiagnosticStatus()
        status.name = "de4sdv_aebs_009d: override_authorization"
        status.hardware_id = "de4sdv_aebs_coordinator"
        status.level = {
            "control_clear": DiagnosticStatus.OK,
            "conscious_override": DiagnosticStatus.OK,
            "degraded_stale_source": DiagnosticStatus.WARN,
            "inconclusive_missing_source": DiagnosticStatus.STALE,
            "error_malformed_source": DiagnosticStatus.ERROR,
            "error_future_source": DiagnosticStatus.ERROR,
        }[disposition]
        status.message = disposition
        status.values = [
            KeyValue(
                key="override_source_stamp",
                value=self._format_stamp(self._override_source_ns),
            ),
            KeyValue(
                key="authorization_diagnostic_source_stamp",
                value=self._format_stamp(diagnostic_ns),
            ),
            KeyValue(
                key="override_source_value",
                value=(
                    "none" if self._override is None
                    else "true" if self._override else "false"
                ),
            ),
            KeyValue(key="disposition", value=disposition),
        ]
        authorization.status = [status]
        self.override_authorization_pub.publish(authorization)

    def _on_odometry(self, message: Odometry) -> None:
        if message.header.frame_id != "map":
            return
        speed = float(message.twist.twist.linear.x)
        now_ns = self.get_clock().now().nanoseconds
        age = _source_age_s(message.header.stamp, now_ns, self._latch.odometry_max_age_s)
        if not math.isfinite(speed) or age is None:
            return
        self._ego_speed_mps = speed
        self._odometry_received_ns = now_ns
        was_active = self._latch.active
        self._latch.observe_motion(speed, age, now_ns / 1e9)
        if was_active and not self._latch.active:
            self._warning = False

    @staticmethod
    def _copy_control(source: Control) -> Control:
        target = Control()
        target.stamp = source.stamp
        target.lateral = source.lateral
        target.longitudinal = source.longitudinal
        return target

    def _publish_override_evaluation(
        self, context: str, *, diagnostic_source_stamp: str = "none"
    ) -> None:
        if self._override is None or self._override_source_ns is None:
            return
        now_ns = self.get_clock().now().nanoseconds
        override_eval = String()
        override_eval.data = json.dumps({
            "clear": self._override_is_fresh_and_clear(),
            "source_value": self._override,
            "source_age_s": (now_ns - self._override_source_ns) / 1e9,
            "source_stamp": (
                f"{self._override_source_ns // 1_000_000_000}."
                f"{self._override_source_ns % 1_000_000_000:09d}"
            ),
            "context": context,
            "diagnostic_source_stamp": diagnostic_source_stamp,
        }, sort_keys=True, separators=(",", ":"))
        self.override_eval_pub.publish(override_eval)

    def _publish(self) -> None:
        if self._nominal is None:
            return
        state = String()
        state.data = self._latch.state
        self.state_pub.publish(state)
        self._publish_override_evaluation("monitoring")
        if self._rss_m is not None and self._distance_m is not None:
            self._warning = next_warning_state(
                self._warning,
                self._latch.state,
                self._distance_m,
                self._rss_m,
                self.warning_margin_m,
            )
            risk = String()
            risk.data = json.dumps({
                "rss_distance_m": self._rss_m,
                "object_distance_m": self._distance_m,
                "warning": self._warning,
                "intervention": self._latch.active,
            }, sort_keys=True, separators=(",", ":"))
            self.risk_pub.publish(risk)
        warning = Bool()
        warning.data = self._warning
        self.warning_pub.publish(warning)
        command = self._copy_control(self._nominal)
        command.stamp = self.get_clock().now().to_msg()
        command.longitudinal.stamp = command.stamp
        if self._latch.active:
            command.longitudinal.velocity = 0.0
            command.longitudinal.acceleration = self.braking_acceleration_mps2
            command.longitudinal.jerk = -10.0
            self.brake_pub.publish(command)
        self.control_pub.publish(command)


def main() -> None:
    rclpy.init()
    node = AebsCoordinator()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
