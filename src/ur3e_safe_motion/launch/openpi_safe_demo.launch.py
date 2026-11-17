"""Launch the mock workcell, collision-checked mover, and one OpenPI sample."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    package_share = get_package_share_directory("ur3e_safe_motion")
    safe_motion = os.path.join(package_share, "launch", "safe_motion.launch.py")
    bridge_demo = os.path.join(package_share, "launch", "openpi_bridge_demo.launch.py")

    return LaunchDescription([
        DeclareLaunchArgument("launch_rviz", default_value="true"),
        DeclareLaunchArgument(
            "action_file",
            default_value=os.path.join(
                get_package_share_directory("ur3e_safe_motion"),
                "config",
                "synthetic_openpi_pi05_droid_motion_check.json"),
            description="JSON file containing a policy_output.actions chunk."),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(safe_motion),
            launch_arguments={
                "launch_rviz": LaunchConfiguration("launch_rviz"),
                "launch_slider": "false",
            }.items(),
        ),
        # Let ROS 2 control, MoveIt, and the safety node come up first.
        TimerAction(
            period=8.0,
            actions=[IncludeLaunchDescription(
                PythonLaunchDescriptionSource(bridge_demo),
                launch_arguments={
                    "action_file": LaunchConfiguration("action_file")
                }.items(),
            )],
        ),
    ])
