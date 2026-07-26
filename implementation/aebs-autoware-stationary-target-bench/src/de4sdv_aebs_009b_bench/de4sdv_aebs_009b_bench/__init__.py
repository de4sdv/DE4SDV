"""ROS-independent building blocks for the 009B executable bench."""

from .scenario_contract import (
    BASELINE_REQUIRED_INPUTS,
    REQUIRED_NON_CLAIMS,
    BaselineContract,
    ClockContract,
    FixtureConstraints,
    ObstacleGeometry,
    Outcome,
    Point3D,
    Pose2D,
    ScenarioConfig,
    anchor_target_pose_map,
    load_scenario_config,
    map_pose_to_base_link,
    rectangular_obstacle_points,
)

__all__ = [
    "BASELINE_REQUIRED_INPUTS",
    "REQUIRED_NON_CLAIMS",
    "BaselineContract",
    "ClockContract",
    "FixtureConstraints",
    "ObstacleGeometry",
    "Outcome",
    "Point3D",
    "Pose2D",
    "ScenarioConfig",
    "anchor_target_pose_map",
    "load_scenario_config",
    "map_pose_to_base_link",
    "rectangular_obstacle_points",
]
