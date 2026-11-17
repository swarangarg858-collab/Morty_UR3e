#!/usr/bin/env python3
"""Validate an OpenPI action chunk and forward its first UR3e target safely."""

import json
import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String


JOINTS = (
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
)
SOFT_LIMITS = {
    "shoulder_pan_joint": (-1.50, 1.50),
    "shoulder_lift_joint": (-2.00, 0.80),
    "elbow_joint": (-2.00, 2.00),
    "wrist_1_joint": (-2.00, 2.00),
    "wrist_2_joint": (-2.00, 2.00),
    "wrist_3_joint": (-2.00, 2.00),
}


class OpenPIActionReceiver(Node):
    def __init__(self):
        super().__init__("openpi_action_receiver")
        self.target_publisher = self.create_publisher(
            JointState, "/safe_motion/joint_target", 10)
        self.subscription = self.create_subscription(
            String, "/openpi/action", self.receive_action, 10)
        self.status_subscription = self.create_subscription(
            String, "/safe_motion/status", self.receive_motion_status, 10)

    def receive_motion_status(self, message):
        status = message.data
        if status.startswith("Motion completed"):
            self.get_logger().info("Safety planner reports: motion completed.")
        elif status.startswith(("Blocked:", "Rejected:", "Busy:", "Motion failed")):
            self.get_logger().warning(f"Safety planner reports: {status}")

    def receive_action(self, message):
        try:
            payload = json.loads(message.data)
            policy_output = payload["policy_output"]
            action_chunk = policy_output["actions"]
            action_spec = payload["robot_action_spec"]
            joint_names = action_spec["joint_names"]
            action_indices = action_spec["action_indices"]

            if action_spec.get("robot") != "UR3e":
                raise ValueError("robot_action_spec.robot must be UR3e")
            if action_spec.get("semantics") != "absolute_joint_positions_rad":
                raise ValueError(
                    "demo expects absolute joint positions in radians")
            if tuple(joint_names) != JOINTS:
                raise ValueError("UR3e joint_names must match the six arm joints")
            if len(action_indices) != len(JOINTS):
                raise ValueError("provide one action index for every UR3e joint")
            if len(set(action_indices)) != len(action_indices):
                raise ValueError("action_indices must be unique")
            if not isinstance(action_chunk, list) or not action_chunk:
                raise ValueError("policy_output.actions must be a non-empty matrix")

            model_config = payload.get("policy_config", {})
            expected_horizon = model_config.get("action_horizon")
            expected_dim = model_config.get("policy_output_action_dim")
            if expected_horizon is not None and expected_horizon != len(action_chunk):
                raise ValueError("action_horizon does not match actions row count")
            if expected_dim is not None and expected_dim != len(action_chunk[0]):
                raise ValueError(
                    "policy_output_action_dim does not match actions row width")

            if len(action_chunk) != 15 or any(
                    not isinstance(row, list) or len(row) != 7 for row in action_chunk):
                raise ValueError("Morty expects an exact 15 x 7 action chunk")
            if action_indices != list(range(6)):
                raise ValueError("arm action indices must be 0 through 5")
            if action_spec.get("gripper_action_index") != 6:
                raise ValueError("gripper action index must be 6")
            if action_spec.get("gripper_semantics") != "normalized_position_0_open_1_closed":
                raise ValueError("unsupported gripper convention")
            for row in action_chunk:
                if any(isinstance(v, bool) or not isinstance(v, (int, float))
                       or not math.isfinite(v) for v in row):
                    raise ValueError("all seven channels must be finite numbers")
                if not 0.0 <= row[6] <= 1.0:
                    raise ValueError("gripper must be in [0, 1]")

            mapped_chunk = []
            for row_index, row in enumerate(action_chunk):
                if not isinstance(row, list):
                    raise ValueError(f"actions[{row_index}] must be a numeric row")
                if expected_dim is not None and expected_dim != len(row):
                    raise ValueError(
                        "policy output dimension does not match actions row width")
                if any(index < 0 or index >= len(row) for index in action_indices):
                    raise ValueError("an action index is outside the action row")

                mapped = [float(row[index]) for index in action_indices]
                for joint, value in zip(JOINTS, mapped):
                    if not math.isfinite(value):
                        raise ValueError(f"actions[{row_index}] has a non-finite value")
                    low, high = SOFT_LIMITS[joint]
                    if not low <= value <= high:
                        raise ValueError(
                            f"actions[{row_index}] {joint}={value} is outside "
                            f"[{low}, {high}] rad")
                mapped_chunk.append(mapped)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            self.get_logger().error(f"Rejected OpenPI action chunk: {error}")
            return

        self.get_logger().warning(
            f"Gripper target {action_chunk[0][6]:.3f} validated but not executed; "
            "the safety planner currently controls only the six arm joints.")
        # Execute the first predicted timestep; MoveIt checks its complete path.
        target = JointState()
        target.header.stamp = self.get_clock().now().to_msg()
        target.name = list(JOINTS)
        target.position = mapped_chunk[0]
        self.target_publisher.publish(target)
        source = payload.get("source", "unspecified")
        self.get_logger().info(
            f"Received {len(mapped_chunk)}-step, {len(action_chunk[0])}-channel "
            f"action chunk from {source}; "
            "forwarded step 1/" + str(len(mapped_chunk)) +
            " to the MoveIt collision-checked planner.")
        joint_values = ", ".join(
            f"{name}={value:.3f}" for name, value in zip(JOINTS, target.position))
        self.get_logger().info(
            f"Published /safe_motion/joint_target (radians): {joint_values}")


def main(args=None):
    rclpy.init(args=args)
    node = OpenPIActionReceiver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

