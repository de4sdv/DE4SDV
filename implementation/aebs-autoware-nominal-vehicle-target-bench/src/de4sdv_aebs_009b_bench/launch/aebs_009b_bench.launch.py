"""INC-AEBS-009B nominal moving-target integration composition."""

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def include(package: str, relative_path: str, arguments=None):
    source = AnyLaunchDescriptionSource(
        f"{get_package_share_directory(package)}/{relative_path}"
    )
    return IncludeLaunchDescription(
        source,
        launch_arguments=(arguments or {}).items(),
    )


def generate_launch_description():
    package_share = get_package_share_directory("de4sdv_aebs_009b_bench")
    proven_share = get_package_share_directory("de4sdv_aebs_bench")
    simulator_share = get_package_share_directory("autoware_simple_planning_simulator")
    gate_share = get_package_share_directory("autoware_vehicle_cmd_gate")
    vehicle_info_share = get_package_share_directory("autoware_vehicle_info_utils")
    map_path = LaunchConfiguration("map_path")

    map_loader = include(
        "tier4_map_launch",
        "launch/map.launch.xml",
        {
            "pointcloud_map_path": PathJoinSubstitution([map_path, "pointcloud_map.pcd"]),
            "pointcloud_map_metadata_path": PathJoinSubstitution(
                [map_path, "pointcloud_map_metadata.yaml"]
            ),
            "lanelet2_map_path": PathJoinSubstitution([map_path, "lanelet2_map.osm"]),
            "lanelet2_map_metadata_path": PathJoinSubstitution(
                [map_path, "lanelet2_map_metadata.yaml"]
            ),
            "map_projector_info_path": PathJoinSubstitution(
                [map_path, "map_projector_info.yaml"]
            ),
            "pointcloud_map_loader_param_path": (
                f"{proven_share}/config/pointcloud_map_loader.param.yaml"
            ),
            "lanelet2_map_loader_param_path": (
                f"{proven_share}/config/lanelet2_map_loader.param.yaml"
            ),
            "map_tf_generator_param_path": (
                f"{proven_share}/config/map_tf_generator.param.yaml"
            ),
            "map_projection_loader_param_path": (
                f"{proven_share}/config/map_projection_loader.param.yaml"
            ),
        },
    )

    simulator = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f"{simulator_share}/launch/simple_planning_simulator.launch.py"
        ),
        launch_arguments={
            "motion_publish_mode": "full_motion",
            "initial_engage_state": "true",
            "vehicle_model_pkg": vehicle_info_share,
        }.items(),
    )

    vehicle_gate = Node(
        package="autoware_vehicle_cmd_gate",
        executable="vehicle_cmd_gate_exe",
        name="vehicle_cmd_gate",
        output="screen",
        parameters=[
            f"{gate_share}/config/vehicle_cmd_gate.param.yaml",
            f"{vehicle_info_share}/config/vehicle_info.param.yaml",
            {
                "check_external_emergency_heartbeat": False,
                "use_emergency_handling": False,
            },
        ],
        remappings=[
            ("input/steering", "/vehicle/status/steering_status"),
            ("input/operation_mode", "/system/operation_mode/state"),
            ("input/auto/control_cmd", "/control/trajectory_follower/control_cmd"),
            ("input/auto/turn_indicators_cmd", "/planning/turn_indicators_cmd"),
            ("input/auto/hazard_lights_cmd", "/planning/hazard_lights_cmd"),
            ("input/auto/gear_cmd", "/control/shift_decider/gear_cmd"),
            ("input/external/control_cmd", "/external/selected/control_cmd"),
            ("input/external/turn_indicators_cmd", "/external/selected/turn_indicators_cmd"),
            ("input/external/hazard_lights_cmd", "/external/selected/hazard_lights_cmd"),
            ("input/external/gear_cmd", "/external/selected/gear_cmd"),
            ("input/external_emergency_stop_heartbeat", "/external/selected/heartbeat"),
            ("input/gate_mode", "/control/gate_mode_cmd"),
            ("input/emergency/control_cmd", "/system/emergency/control_cmd"),
            ("input/emergency/turn_indicators_cmd", "/system/emergency/turn_indicators_cmd"),
            ("input/emergency/hazard_lights_cmd", "/system/emergency/hazard_lights_cmd"),
            ("input/emergency/gear_cmd", "/system/emergency/gear_cmd"),
            ("input/mrm_state", "/system/fail_safe/mrm_state"),
            ("input/kinematics", "/localization/kinematic_state"),
            ("input/acceleration", "/localization/acceleration"),
            ("output/vehicle_cmd_emergency", "/control/command/emergency_cmd"),
            ("output/control_cmd", "/control/command/control_cmd"),
            ("output/gear_cmd", "/control/command/gear_cmd"),
            ("output/turn_indicators_cmd", "/control/command/turn_indicators_cmd"),
            ("output/hazard_lights_cmd", "/control/command/hazard_lights_cmd"),
            ("output/gate_mode", "/control/current_gate_mode"),
            ("output/engage", "/api/autoware/get/engage"),
            ("output/external_emergency", "/api/autoware/get/emergency"),
            ("output/operation_mode", "/control/vehicle_cmd_gate/operation_mode"),
            ("~/service/engage", "/api/autoware/set/engage"),
            ("~/service/external_emergency", "/api/autoware/set/emergency"),
            ("input/engage", "/autoware/engage"),
        ],
    )

    aeb = Node(
        package="autoware_autonomous_emergency_braking",
        executable="autoware_autonomous_emergency_braking",
        namespace="control",
        name="autonomous_emergency_braking",
        output="screen",
        parameters=[
            f"{package_share}/config/aebs-009b.param.yaml",
            f"{vehicle_info_share}/config/vehicle_info.param.yaml",
        ],
        remappings=[
            ("~/input/pointcloud", "/perception/obstacle_segmentation/pointcloud"),
            ("~/input/velocity", "/vehicle/status/velocity_status"),
            ("~/input/imu", "/sensing/imu/imu_data"),
        ],
    )

    fixture = Node(
        package="de4sdv_aebs_009b_bench",
        executable="scenario_fixture",
        name="scenario_fixture",
        output="screen",
        parameters=[
            {
                "scenario_config": (
                    f"{package_share}/config/scenario-009b-moving-vehicle-target.yaml"
                ),
                "override_scenario": LaunchConfiguration("override_scenario"),
            }
        ],
    )

    coordinator = Node(
        package="de4sdv_aebs_009b_bench",
        executable="aebs_coordinator",
        name="de4sdv_aebs_coordinator",
        output="screen",
        parameters=[{
            "warning_margin_m": 6.0,
            "override_max_age_s": 0.2,
            "stop_speed_mps": 0.1,
            "stop_hold_s": 0.5,
            "odometry_max_age_s": 0.2,
        }],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("map_path", description="verified extracted map directory"),
            DeclareLaunchArgument("override_scenario", default_value="fresh_false_control"),
            map_loader,
            simulator,
            vehicle_gate,
            fixture,
            aeb,
            coordinator,
        ]
    )
