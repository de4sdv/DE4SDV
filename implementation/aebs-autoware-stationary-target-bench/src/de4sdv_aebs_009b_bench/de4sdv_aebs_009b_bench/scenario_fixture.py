"""ROS adapter for the manually activated, stationary 009B target fixture.

The node supplies scenario inputs only.  It does not evaluate outcomes or emit
claims about the response of the composed system.
"""

from __future__ import annotations

import math

from autoware_adapi_v1_msgs.msg import OperationModeState
from autoware_control_msgs.msg import Control
from autoware_system_msgs.msg import AutowareState
from autoware_vehicle_msgs.msg import Engage
from autoware_vehicle_msgs.msg import GearCommand
from autoware_vehicle_msgs.msg import HazardLightsCommand
from autoware_vehicle_msgs.msg import TurnIndicatorsCommand
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import PointCloud2, PointField
from std_srvs.srv import Trigger

from .scenario_contract import Pose2D, load_scenario_config
from .scenario_fixture_core import (
    ScenarioFixtureState,
    pack_xyz_float32,
    quaternion_to_yaw,
)

POINT_STEP = 12
XYZ_FIELDS = (("x", 0), ("y", 4), ("z", 8))


def _set_planar_pose(message_pose, pose: Pose2D) -> None:
    message_pose.position.x = pose.x
    message_pose.position.y = pose.y
    message_pose.position.z = 0.0
    message_pose.orientation.x = 0.0
    message_pose.orientation.y = 0.0
    message_pose.orientation.z = math.sin(pose.yaw_rad / 2.0)
    message_pose.orientation.w = math.cos(pose.yaw_rad / 2.0)


class ScenarioFixture(Node):
    """Sole point-cloud authority with explicit one-shot target activation."""

    def __init__(self) -> None:
        super().__init__("scenario_fixture")
        self.declare_parameter("scenario_config")
        scenario_path = self.get_parameter("scenario_config").value
        if not isinstance(scenario_path, str) or not scenario_path:
            raise ValueError("scenario_config parameter must be a nonempty installed YAML path")
        config = load_scenario_config(scenario_path)
        self._state = ScenarioFixtureState(config)

        transient = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.cloud_pub = self.create_publisher(
            PointCloud2, "/perception/obstacle_segmentation/pointcloud", 1
        )
        self.initial_pose_pub = self.create_publisher(
            PoseWithCovarianceStamped, "/initialpose3d", transient
        )
        self.engage_pub = self.create_publisher(Engage, "/autoware/engage", 1)
        self.api_operation_mode_pub = self.create_publisher(
            OperationModeState, "/api/operation_mode/state", transient
        )
        self.system_operation_mode_pub = self.create_publisher(
            OperationModeState, "/system/operation_mode/state", transient
        )
        self.autoware_state_pub = self.create_publisher(
            AutowareState, "/autoware/state", 1
        )
        self.control_pub = self.create_publisher(
            Control, "/control/trajectory_follower/control_cmd", 1
        )
        self.gear_pub = self.create_publisher(
            GearCommand, "/control/shift_decider/gear_cmd", 1
        )
        self.turn_pub = self.create_publisher(
            TurnIndicatorsCommand, "/planning/turn_indicators_cmd", 1
        )
        self.hazard_pub = self.create_publisher(
            HazardLightsCommand, "/planning/hazard_lights_cmd", 1
        )
        self.target_pose_pub = self.create_publisher(
            PoseStamped, "/de4sdv/aebs_009b/target_pose_map", transient
        )

        self.odometry_sub = self.create_subscription(
            Odometry, "/localization/kinematic_state", self._on_odometry, 1
        )
        self.activation_service = self.create_service(
            Trigger, "/de4sdv/aebs_009b/inject_target", self._on_activate
        )
        self.cloud_timer = self.create_timer(
            1.0 / config.pointcloud_rate_hz, self._publish_cloud
        )
        self.nominal_timer = self.create_timer(
            1.0 / config.ego_state_rate_hz, self._publish_nominal_inputs
        )
        self._publish_initial_pose()

    def _on_odometry(self, message: Odometry) -> None:
        if message.header.frame_id != "map":
            self.get_logger().warning(
                f"Ignoring odometry in unexpected frame {message.header.frame_id!r}"
            )
            return
        pose = message.pose.pose
        orientation = pose.orientation
        try:
            ego = Pose2D(
                pose.position.x,
                pose.position.y,
                quaternion_to_yaw(
                    orientation.x, orientation.y, orientation.z, orientation.w
                ),
            )
            self._state.update_ego(ego)
        except (TypeError, ValueError) as error:
            self.get_logger().warning(f"Ignoring invalid odometry pose: {error}")
            return

    def _on_activate(self, _request: Trigger.Request, response: Trigger.Response):
        try:
            anchored = self._state.activate()
        except RuntimeError as error:
            response.success = False
            response.message = str(error)
            return response

        target = PoseStamped()
        target.header.stamp = self.get_clock().now().to_msg()
        target.header.frame_id = "map"
        _set_planar_pose(target.pose, anchored)
        self.target_pose_pub.publish(target)
        response.success = True
        response.message = "stationary map target activated"
        return response

    def _publish_cloud(self) -> None:
        try:
            points = self._state.target_points()
            packed_points = pack_xyz_float32(points)
        except (TypeError, ValueError, OverflowError) as error:
            self.get_logger().error(f"Skipping invalid point cloud: {error}")
            return
        cloud = PointCloud2()
        cloud.header.stamp = self.get_clock().now().to_msg()
        cloud.header.frame_id = "base_link"
        cloud.height = 1
        cloud.width = len(points)
        cloud.fields = [
            PointField(name=name, offset=offset, datatype=PointField.FLOAT32, count=1)
            for name, offset in XYZ_FIELDS
        ]
        cloud.is_bigendian = False
        cloud.point_step = POINT_STEP
        cloud.row_step = cloud.width * POINT_STEP
        cloud.data = packed_points
        cloud.is_dense = True
        self.cloud_pub.publish(cloud)

    def _publish_initial_pose(self) -> None:
        stamp = self.get_clock().now().to_msg()
        config = self._state.config

        initial_pose = PoseWithCovarianceStamped()
        initial_pose.header.stamp = stamp
        initial_pose.header.frame_id = "map"
        _set_planar_pose(initial_pose.pose.pose, config.initial_pose_map)
        self.initial_pose_pub.publish(initial_pose)

    def _publish_nominal_inputs(self) -> None:
        stamp = self.get_clock().now().to_msg()
        config = self._state.config

        engage = Engage()
        engage.stamp = stamp
        engage.engage = True
        self.engage_pub.publish(engage)

        operation_mode = OperationModeState()
        operation_mode.stamp = stamp
        operation_mode.mode = OperationModeState.AUTONOMOUS
        operation_mode.is_autoware_control_enabled = True
        operation_mode.is_in_transition = False
        operation_mode.is_stop_mode_available = True
        operation_mode.is_autonomous_mode_available = True
        operation_mode.is_local_mode_available = True
        operation_mode.is_remote_mode_available = True
        self.api_operation_mode_pub.publish(operation_mode)
        self.system_operation_mode_pub.publish(operation_mode)

        autoware_state = AutowareState()
        autoware_state.stamp = stamp
        autoware_state.state = AutowareState.DRIVING
        self.autoware_state_pub.publish(autoware_state)

        control = Control()
        control.stamp = stamp
        control.longitudinal.stamp = stamp
        control.longitudinal.velocity = config.nominal_command_speed_mps
        control.longitudinal.acceleration = config.nominal_command_acceleration_mps2
        control.longitudinal.jerk = 0.0
        control.lateral.stamp = stamp
        self.control_pub.publish(control)

        gear = GearCommand()
        gear.stamp = stamp
        gear.command = GearCommand.DRIVE
        self.gear_pub.publish(gear)

        turn = TurnIndicatorsCommand()
        turn.stamp = stamp
        turn.command = TurnIndicatorsCommand.NO_COMMAND
        self.turn_pub.publish(turn)

        hazard = HazardLightsCommand()
        hazard.stamp = stamp
        hazard.command = HazardLightsCommand.NO_COMMAND
        self.hazard_pub.publish(hazard)


def main() -> None:
    rclpy.init()
    node = None
    try:
        node = ScenarioFixture()
        rclpy.spin(node)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()
