from launch import LaunchDescription
import os

from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory("ur3e_safe_motion")
    default_action_file = os.path.join(
        package_share, "config", "synthetic_openpi_pi05_droid_motion_check.json")
    receiver = Node(
        package="ur3e_safe_motion",
        executable="openpi_action_receiver.py",
        output="screen",
    )
    sample_publisher = Node(
        package="ur3e_safe_motion",
        executable="openpi_sample_publisher.py",
        parameters=[{"action_file": LaunchConfiguration("action_file")}],
        output="screen",
    )
    return LaunchDescription([
        DeclareLaunchArgument(
            "action_file",
            default_value=default_action_file,
            description="JSON file containing a policy_output.actions chunk."),
        receiver,
        # Start after the receiver so the single sample is not lost at startup.
        TimerAction(period=1.0, actions=[sample_publisher]),
    ])
