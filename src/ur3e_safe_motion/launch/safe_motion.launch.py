import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, TimerAction
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _read_yaml(path):
    with open(path, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def generate_launch_description():
    safe_share = get_package_share_directory("ur3e_safe_motion")
    description_share = get_package_share_directory("ur3e_learning_description")
    urdf_file = os.path.join(
        description_share, "urdf", "final_morty_workcell.urdf")
    srdf_file = os.path.join(safe_share, "config", "ur3e.srdf")

    with open(urdf_file, "r", encoding="utf-8") as urdf_stream:
        robot_description = {"robot_description": urdf_stream.read()}
    with open(srdf_file, "r", encoding="utf-8") as semantic_file:
        robot_description_semantic = {
            "robot_description_semantic": semantic_file.read()}

    kinematics = _read_yaml(os.path.join(safe_share, "config", "kinematics.yaml"))
    joint_limits = _read_yaml(os.path.join(safe_share, "config", "joint_limits.yaml"))
    robot_description_planning = {"robot_description_planning": joint_limits}
    ompl = _read_yaml(os.path.join(safe_share, "config", "ompl_planning.yaml"))
    ros2_controllers = os.path.join(safe_share, "config", "ros2_controllers.yaml")
    moveit_controllers = _read_yaml(
        os.path.join(safe_share, "config", "moveit_controllers.yaml"))

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_description, ros2_controllers],
        output="screen",
    )
    state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[robot_description],
        output="screen",
    )
    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_planning,
            {"robot_description_kinematics": kinematics},
            {
                "planning_pipelines": ["ompl"],
                "default_planning_pipeline": "ompl",
                "ompl": ompl,
                "publish_planning_scene": True,
                "publish_geometry_updates": True,
                "publish_state_updates": True,
                "publish_transforms_updates": True,
            },
            moveit_controllers,
        ],
    )

    state_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        output="screen",
    )
    arm_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["arm_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )
    safe_motion_node = Node(
        package="ur3e_safe_motion",
        executable="safe_joint_motion_node",
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_planning,
            {"robot_description_kinematics": kinematics},
        ],
        output="screen",
    )
    slider_gui = Node(
        package="ur3e_safe_motion",
        executable="safe_joint_slider.py",
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_slider")),
    )
    rviz_config = PathJoinSubstitution([
        FindPackageShare("ur3e_learning_description"), "rviz", "view_robot.rviz"])
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", rviz_config],
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_rviz")),
    )

    return LaunchDescription([
        DeclareLaunchArgument("launch_rviz", default_value="true"),
        DeclareLaunchArgument("launch_slider", default_value="true"),
        state_publisher,
        control_node,
        move_group,
        TimerAction(period=2.0, actions=[state_spawner]),
        RegisterEventHandler(
            OnProcessExit(target_action=state_spawner, on_exit=[arm_spawner])),
        RegisterEventHandler(
            OnProcessExit(target_action=arm_spawner, on_exit=[safe_motion_node])),
        RegisterEventHandler(
            OnProcessStart(target_action=safe_motion_node, on_start=[slider_gui])),
        rviz,
    ])
