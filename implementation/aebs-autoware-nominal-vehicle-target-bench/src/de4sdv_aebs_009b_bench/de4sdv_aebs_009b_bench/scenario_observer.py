"""Single-threaded ROS 2 observation adapter and target-activation orchestrator."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Callable

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.parameter import Parameter

from autoware_control_msgs.msg import Control
from diagnostic_msgs.msg import DiagnosticArray
from geometry_msgs.msg import AccelWithCovarianceStamped, PoseStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger
from tier4_system_msgs.msg import OperationModeAvailability
from tier4_vehicle_msgs.msg import VehicleEmergencyStamped

from .footprint_geometry import footprint_relation
from .scenario_contract import BASELINE_REQUIRED_INPUTS, Pose2D, load_scenario_config
from .scenario_evaluator import Observation, ObservationKind
from .scenario_observer_core import (
    ObserverCore,
    atomic_write_json,
    closed_constant,
    exception_report,
    normalize_risk_payload,
    validate_installed_config_path,
)

_DIAGNOSTIC_NAME = "autonomous_emergency_braking: aeb_emergency_stop"
_INTERVENTION_MESSAGE = "[AEB]: Emergency Brake"
_MRM_TOPICS = (
    "/system/fail_safe/mrm_state",
    "/system/mrm/emergency_stop/status",
)
_TOPIC_KIND = {
    "/diagnostics": ObservationKind.DIAGNOSTIC,
    "/system/operation_mode/availability": ObservationKind.AUTONOMOUS_AVAILABILITY,
    "/control/trajectory_follower/control_cmd": ObservationKind.NOMINAL_COMMAND,
    "/control/command/control_cmd": ObservationKind.GATE_COMMAND,
    "/localization/kinematic_state": ObservationKind.ODOMETRY,
}


def _stamp(message: Any) -> str | None:
    header = getattr(message, "header", None)
    stamp = getattr(header, "stamp", None) or getattr(message, "stamp", None)
    if stamp is None:
        return None
    return f"{int(stamp.sec)}.{int(stamp.nanosec):09d}"


def _control(message: Control) -> tuple[float, float]:
    longitudinal = message.longitudinal
    speed = float(longitudinal.velocity)
    acceleration = float(longitudinal.acceleration)
    if not math.isfinite(speed) or not math.isfinite(acceleration):
        raise ValueError("control command contains a non-finite value")
    return speed, acceleration


def _planar_pose(pose: Any, label: str) -> Pose2D:
    position, q = pose.position, pose.orientation
    values = tuple(float(value) for value in (position.x, position.y, q.x, q.y, q.z, q.w))
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"{label} pose contains non-finite values")
    if not math.isclose(q.x, 0.0, abs_tol=1e-6) or not math.isclose(q.y, 0.0, abs_tol=1e-6):
        raise ValueError(f"{label} quaternion must be planar")
    norm = math.hypot(q.z, q.w)
    if not math.isclose(norm, 1.0, rel_tol=1e-6, abs_tol=1e-6):
        raise ValueError(f"{label} quaternion must be normalized")
    yaw = (2.0 * math.atan2(q.z, q.w) + math.pi) % (2.0 * math.pi) - math.pi
    return Pose2D(values[0], values[1], yaw)


class ScenarioObserver(Node):
    """Owns only subscriptions and the one target-injection Trigger client."""

    def __init__(self) -> None:
        super().__init__("scenario_observer")
        self.declare_parameter("scenario_config", Parameter.Type.STRING)
        self.declare_parameter("raw_output", Parameter.Type.STRING)
        self.declare_parameter("timeout_s", Parameter.Type.DOUBLE)
        config_path = self.get_parameter("scenario_config").value
        raw_output = self.get_parameter("raw_output").value
        timeout_s = self.get_parameter("timeout_s").value
        if not isinstance(config_path, str) or not config_path or not Path(config_path).is_absolute():
            raise ValueError("scenario_config must be a required absolute installed path")
        if not isinstance(raw_output, str) or not raw_output or not Path(raw_output).is_absolute():
            raise ValueError("raw_output must be a required absolute path")
        if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError("timeout_s must be finite and positive")
        installed_config = Path(get_package_share_directory("de4sdv_aebs_009b_bench")) / "config"
        validate_installed_config_path(
            config_path,
            installed_config,
            "scenario-009b-moving-vehicle-target.yaml",
        )
        self.raw_output = Path(raw_output)
        self.core = ObserverCore(load_scenario_config(config_path), float(timeout_s), time.monotonic())
        self.terminal_reason: str | None = None
        self._receipt: dict[str, float] = {}
        self._instrument_state: dict[str, bool] = {}
        self._activation_future: Any = None
        self._latest_ego_speed_mps: float | None = None
        self._latest_ego_pose_map: tuple[Pose2D, float] | None = None
        self.create_subscription(DiagnosticArray, "/diagnostics", self._safe(self._diagnostics, "/diagnostics"), 10)
        self.create_subscription(OperationModeAvailability, "/system/operation_mode/availability", self._safe(self._availability, "/system/operation_mode/availability"), 10)
        self.create_subscription(Control, "/control/trajectory_follower/control_cmd", self._safe(self._nominal, "/control/trajectory_follower/control_cmd"), 10)
        self.create_subscription(Control, "/system/emergency/control_cmd", self._safe(self._emergency, None), 10)
        self.create_subscription(VehicleEmergencyStamped, "/control/command/emergency_cmd", self._safe(self._gate_emergency, None), 10)
        self.create_subscription(Control, "/control/command/control_cmd", self._safe(self._gate, "/control/command/control_cmd"), 10)
        self.create_subscription(Odometry, "/localization/kinematic_state", self._safe(self._odometry, "/localization/kinematic_state"), 10)
        self.create_subscription(AccelWithCovarianceStamped, "/localization/acceleration", self._safe(self._acceleration, None), 10)
        self.create_subscription(PoseStamped, "/de4sdv/aebs_009b/target_pose_map", self._safe(self._target, None), 10)
        self.create_subscription(String, "/de4sdv/aebs_009b/risk_assessment", self._safe(self._risk, None), 10)
        self.create_subscription(Bool, "/de4sdv/aebs_009b/warning_request", self._safe(self._warning, None), 10)
        self.create_subscription(String, "/de4sdv/aebs_009b/override_evaluated_clear", self._safe(self._override, None), 10)
        self.create_subscription(Control, "/de4sdv/aebs_009b/emergency_braking_request", self._safe(self._braking_request, None), 10)
        self.create_subscription(String, "/de4sdv/aebs_009b/coordination_state", self._safe(self._coordination_state, None), 10)
        self._trigger_client = self.create_client(Trigger, "/de4sdv/aebs_009b/inject_target")
        self.create_timer(max(0.05, self.core.config.baseline.required_input_max_age_s / 2), self._tick)

    def _safe(
        self, callback: Callable[[Any, float], bool | None], topic: str | None
    ) -> Callable[[Any], None]:
        def guarded(message: Any) -> None:
            at = time.monotonic()
            try:
                accepted = callback(message, at)
                if topic is not None and accepted is not False:
                    self._receipt[topic] = at
                    self._instrument(topic, True, at)
            except Exception as error:  # callbacks must never terminate the process
                self.core.error(f"{topic or callback.__name__}: {type(error).__name__}: {error}")
                if topic is not None:
                    self._instrument(topic, False, at)
        return guarded

    def _instrument(self, topic: str, available: bool, at: float) -> None:
        if self._instrument_state.get(topic) is available:
            return
        self._instrument_state[topic] = available
        self.core.add(Observation(ObservationKind.INSTRUMENT_STATUS, {
            "topic": topic, "available": available,
        }, at))

    def _diagnostics(self, message: DiagnosticArray, at: float) -> bool:
        status = next((item for item in message.status if item.name == _DIAGNOSTIC_NAME), None)
        if status is None:
            return False
        level = closed_constant(
            type(status), status.level, ("OK", "WARN", "ERROR", "STALE")
        )
        self.core.add(Observation(ObservationKind.DIAGNOSTIC, {
            "node": "autonomous_emergency_braking", "task": "aeb_emergency_stop", "level": level,
        }, at, source_stamp=_stamp(message)))
        if level == "ERROR" and status.message == _INTERVENTION_MESSAGE:
            pairs = [(item.key, item.value) for item in status.values]
            keys = [key for key, _ in pairs]
            required = {"RSS", "Distance", "Object Speed"}
            if any(keys.count(key) != 1 for key in required):
                raise ValueError("exact intervention diagnostic requires unique RSS, Distance, and Object Speed values")
            values = dict(pairs)
            numeric = {key: float(values[key]) for key in required}
            if not all(math.isfinite(value) for value in numeric.values()):
                raise ValueError("intervention diagnostic values must be finite")
            self.core.add(Observation(ObservationKind.AEB_INTERVENTION, {
                "node": "autonomous_emergency_braking",
                "task": "aeb_emergency_stop",
                "level": "ERROR",
                "message": _INTERVENTION_MESSAGE,
                "rss_distance_m": numeric["RSS"],
                "object_distance_m": numeric["Distance"],
                "object_speed_mps": numeric["Object Speed"],
            }, at, source_stamp=_stamp(message)))
        return True

    def _risk(self, message: String, at: float) -> None:
        payload = normalize_risk_payload(json.loads(message.data))
        self.core.add(Observation(ObservationKind.RISK_ASSESSMENT, payload, at))
        if self._latest_ego_speed_mps is not None:
            closing = self._latest_ego_speed_mps - self.core.config.target_speed_mps
            self.core.add(Observation(ObservationKind.RELATIVE_STATE, {
                "gap_m": payload["object_distance_m"] - 3.79,
                "ego_speed_mps": self._latest_ego_speed_mps,
                "target_speed_mps": self.core.config.target_speed_mps,
                "closing_speed_mps": closing,
            }, at))

    def _warning(self, message: Bool, at: float) -> None:
        self.core.add(Observation(ObservationKind.WARNING_REQUEST, {"active": bool(message.data)}, at))

    def _override(self, message: String, at: float) -> None:
        value = json.loads(message.data)
        if set(value) != {
            "clear", "source_value", "source_age_s", "source_stamp",
            "context", "diagnostic_source_stamp",
        }:
            raise ValueError("override evaluation has an open or incomplete payload")
        source_stamp = value["source_stamp"]
        if source_stamp is not None and (not isinstance(source_stamp, str) or not source_stamp):
            raise TypeError("override source stamp must be a nonempty string or null")
        self.core.add(Observation(ObservationKind.OVERRIDE_EVALUATION, {
            "clear": value["clear"],
            "source_value": value["source_value"],
            "source_age_s": value["source_age_s"],
            "context": value["context"],
            "diagnostic_source_stamp": value["diagnostic_source_stamp"],
        }, at, source_stamp=value["source_stamp"]))

    def _braking_request(self, message: Control, at: float) -> None:
        speed, acceleration = _control(message)
        self.core.add(Observation(ObservationKind.BRAKING_REQUEST, {
            "speed_mps": speed, "acceleration_mps2": acceleration,
        }, at, source_stamp=_stamp(message)))

    def _coordination_state(self, message: String, at: float) -> None:
        self.core.add(Observation(
            ObservationKind.COORDINATION_STATE, {"state": str(message.data)}, at
        ))

    def _availability(self, message: OperationModeAvailability, at: float) -> None:
        available = message.autonomous
        if not isinstance(available, bool):
            raise TypeError("autonomous availability is not boolean")
        self.core.add(Observation(ObservationKind.AUTONOMOUS_AVAILABILITY, {"available": available}, at))

    def _nominal(self, message: Control, at: float) -> None:
        speed, acceleration = _control(message)
        self.core.add(Observation(ObservationKind.NOMINAL_COMMAND, {
            "speed_mps": speed, "acceleration_mps2": acceleration,
        }, at, source_stamp=_stamp(message)))

    def _emergency(self, message: Control, at: float) -> None:
        speed, acceleration = _control(message)
        self.core.add(Observation(ObservationKind.EMERGENCY_COMMAND, {
            "speed_mps": speed, "acceleration_mps2": acceleration,
        }, at, source_stamp=_stamp(message)))

    def _gate_emergency(self, message: VehicleEmergencyStamped, at: float) -> None:
        self.core.note_gate_emergency(bool(message.emergency), at)

    def _gate(self, message: Control, at: float) -> bool:
        _, acceleration = _control(message)
        path = self.core.classify_gate(at)
        if path is None:
            return False
        self.core.add(Observation(ObservationKind.GATE_COMMAND, {
            "path": path, "acceleration_mps2": acceleration,
        }, at, source_stamp=_stamp(message)))
        return True

    def _acceleration(self, message: AccelWithCovarianceStamped, at: float) -> None:
        self.core.note_acceleration(float(message.accel.accel.linear.x), at, _stamp(message))

    def _odometry(self, message: Odometry, at: float) -> bool:
        if message.header.frame_id != "map":
            raise ValueError("ego odometry frame must be map")
        self._latest_ego_speed_mps = float(message.twist.twist.linear.x)
        now_ns = self.get_clock().now().nanoseconds
        collector_ros_stamp = f"{now_ns // 1_000_000_000}.{now_ns % 1_000_000_000:09d}"
        item = self.core.make_odometry(
            self._latest_ego_speed_mps,
            at,
            _stamp(message),
            collector_ros_stamp,
        )
        if item is None:
            return False
        ego_pose = _planar_pose(message.pose.pose, "ego")
        self._latest_ego_pose_map = (ego_pose, at)
        self.core.add(item)
        return True

    def _target(self, message: PoseStamped, at: float) -> None:
        if message.header.frame_id != "map":
            raise ValueError("target frame must be map")
        target_pose = _planar_pose(message.pose, "target")
        self.core.add(Observation(ObservationKind.TARGET_PUBLICATION, {
            "identity": "target-1", "frame": "map", "x": target_pose.x,
            "y": target_pose.y, "yaw_rad": target_pose.yaw_rad,
        }, at, source_stamp=_stamp(message)))
        if self._latest_ego_pose_map is None:
            return
        ego_pose, ego_at = self._latest_ego_pose_map
        relation = footprint_relation(
            ego_pose, self.core.config.ego_footprint,
            target_pose, self.core.config.geometry,
        )
        self.core.add(Observation(ObservationKind.FOOTPRINT_STATE, {
            "ego_x": ego_pose.x, "ego_y": ego_pose.y, "ego_yaw_rad": ego_pose.yaw_rad,
            "target_x": target_pose.x, "target_y": target_pose.y, "target_yaw_rad": target_pose.yaw_rad,
            "sample_skew_s": abs(at - ego_at),
            "separation_m": relation.separation_m, "overlap": relation.overlap,
        }, at, source_stamp=_stamp(message)))

    def _activation_done(self, future: Any) -> None:
        at = time.monotonic()
        try:
            response = future.result()
            self.core.mark_activation_response(at, bool(response.success), str(response.message))
        except Exception as error:
            self.core.mark_activation_response(at, False, f"{type(error).__name__}: {error}")

    def _tick(self) -> None:
        now = time.monotonic()
        nominal_publishers = tuple(sorted(
            f"{info.node_namespace}:{info.node_name}"
            for info in self.get_publishers_info_by_topic(
                "/control/trajectory_follower/control_cmd"
            )
        ))
        mrm_publishers = tuple(sorted(
            f"{info.node_namespace}:{info.node_name}"
            for topic in _MRM_TOPICS
            for info in self.get_publishers_info_by_topic(topic)
        ))
        self.core.add(Observation(ObservationKind.RUNTIME_GRAPH, {
            "nominal_publisher_count": float(len(nominal_publishers)),
            "nominal_publishers": ",".join(nominal_publishers) or "none",
            "mrm_publisher_count": float(len(mrm_publishers)),
            "mrm_publishers": ",".join(mrm_publishers) or "none",
        }, now))
        maximum_age = self.core.config.baseline.required_input_max_age_s
        for topic in BASELINE_REQUIRED_INPUTS:
            fresh = topic in self._receipt and now - self._receipt[topic] <= maximum_age
            if not fresh:
                try:
                    discovered = bool(self.get_publishers_info_by_topic(topic))
                except Exception as error:
                    self.core.error(f"graph discovery {topic}: {error}")
                    discovered = False
                self._instrument(topic, discovered and topic not in self._receipt, now)
        if self.core.should_request_activation():
            self.core.mark_activation_requested(now)
            # One asynchronous request is queued even while discovery is converging;
            # there is deliberately no elapsed-time or readiness autoactivation path.
            self._activation_future = self._trigger_client.call_async(Trigger.Request())
            self._activation_future.add_done_callback(self._activation_done)
        self.terminal_reason = self.core.poll_terminal(now)

    def operator_abort(self, reason: str) -> None:
        self.core.add(Observation(ObservationKind.OPERATOR_ABORT, {"reason": reason}, time.monotonic()))
        self.terminal_reason = "operator_abort"

    def finish(self) -> int:
        reason = self.terminal_reason or "observer_exception"
        outcome = self.core.evaluate().outcome.value
        exit_code = 0 if outcome == "pass_observed_chain" else (130 if reason == "operator_abort" else 1)
        atomic_write_json(
            self.raw_output,
            self.core.result_document(
                reason, exit_code, ended_at_s=time.monotonic()
            ),
        )
        return exit_code


def main(args: list[str] | None = None) -> int:
    rclpy.init(args=args)
    node: ScenarioObserver | None = None
    try:
        node = ScenarioObserver()
        while rclpy.ok() and node.terminal_reason is None:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        if node is not None:
            node.operator_abort("SIGINT/KeyboardInterrupt")
    except Exception as error:
        print(
            exception_report(error, raw_output_available=node is not None),
            file=sys.stderr,
            flush=True,
        )
        if node is not None:
            node.core.error(f"observer exception: {type(error).__name__}: {error}")
            node.terminal_reason = "observer_exception"
    finally:
        exit_code = node.finish() if node is not None else 1
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
