"""Publish typed initialization inputs for the INC-AEBS-009A launch bench.

These messages establish a nominal, stationary, autonomous-ready harness. They
are prerequisites only: this node never publishes MRM state, emergency control,
selected gate output, obstacles, or braking evidence.
"""

from autoware_adapi_v1_msgs.msg import OperationModeState
from autoware_control_msgs.msg import Control
from autoware_system_msgs.msg import AutowareState
from autoware_vehicle_msgs.msg import Engage
from autoware_vehicle_msgs.msg import GearCommand
from autoware_vehicle_msgs.msg import HazardLightsCommand
from autoware_vehicle_msgs.msg import TurnIndicatorsCommand
from geometry_msgs.msg import PoseWithCovarianceStamped
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import PointCloud2, PointField


class NominalFixture(Node):
    def __init__(self) -> None:
        super().__init__("nominal_fixture")
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
        self.timer = self.create_timer(0.1, self.publish_inputs)

    def publish_inputs(self) -> None:
        stamp = self.get_clock().now().to_msg()

        cloud = PointCloud2()
        cloud.header.stamp = stamp
        cloud.header.frame_id = "base_link"
        cloud.height = 1
        cloud.width = 0
        cloud.fields = [
            PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        cloud.is_bigendian = False
        cloud.point_step = 12
        cloud.row_step = 0
        cloud.data = b""
        cloud.is_dense = True
        self.cloud_pub.publish(cloud)

        initial_pose = PoseWithCovarianceStamped()
        initial_pose.header.stamp = stamp
        initial_pose.header.frame_id = "map"
        initial_pose.pose.pose.orientation.w = 1.0
        self.initial_pose_pub.publish(initial_pose)

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
        control.longitudinal.velocity = 0.0
        control.longitudinal.acceleration = 0.0
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
    node = NominalFixture()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
