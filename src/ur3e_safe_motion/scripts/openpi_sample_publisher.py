#!/usr/bin/env python3
"""Publish a synthetic Morty 15 x 7 result for the UR3e bridge demo."""

import json
import os

from ament_index_python.packages import get_package_share_directory
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


JOINTS = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
]


class OpenPISamplePublisher(Node):
    def __init__(self):
        super().__init__("openpi_sample_publisher")
        self.publisher = self.create_publisher(String, "/openpi/action", 10)
        default_action_file = os.path.join(
            get_package_share_directory("ur3e_safe_motion"),
            "config",
            "openpi_output_input.json",
        )
        self.declare_parameter("action_file", default_action_file)
        self.action_file = self.get_parameter("action_file").value
        self.timer = self.create_timer(2.0, self.publish_sample)
        self.sent = False

    def publish_sample(self):
        if self.sent:
            return
        if self.publisher.get_subscription_count() < 1:
            self.get_logger().info("Waiting for /openpi/action receiver...")
            return

        try:
            with open(self.action_file, "r", encoding="utf-8-sig") as action_stream:
                payload = json.load(action_stream)
            action_chunk = payload["policy_output"]["actions"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            self.get_logger().error(
                f"Could not load synthetic OpenPI output from {self.action_file}: {error}")
            self.sent = True
            return
        if (not isinstance(action_chunk, list) or not action_chunk or
                not isinstance(action_chunk[0], list) or not action_chunk[0]):
            self.get_logger().error(
                "policy_output.actions must be a non-empty matrix of rows.")
            self.sent = True
            return

        message = String()
        message.data = json.dumps(payload)
        self.publisher.publish(message)
        self.sent = True
        first_target = ", ".join(
            f"{value:.3f}" for value in action_chunk[0][:6])
        self.get_logger().info(
            f"Published OpenPI-shaped action chunk ({len(action_chunk)} x "
            f"{len(action_chunk[0])}) from {payload.get('source', 'unknown')} "
            f"on /openpi/action using {self.action_file}.")
        self.get_logger().info(
            f"Synthetic first action row: {action_chunk[0]}")
        self.get_logger().info(
            f"UR3e target preview (radians, first 6 channels): [{first_target}]")


def main(args=None):
    rclpy.init(args=args)
    node = OpenPISamplePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

