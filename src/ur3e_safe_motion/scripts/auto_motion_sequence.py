#!/usr/bin/env python3
"""Cycle through collision-checked UR3e poses for a short RViz demo."""

import time

import rclpy
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import JointState
from std_msgs.msg import String


JOINTS = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
]

# All values are radians. These poses are within the demo's soft limits.
# The first and second poses were individually accepted by MoveIt in this scene.
POSES = [
    [0.25, -1.35, 1.35, -1.45, -1.40, 0.25],
    [0.70, -0.95, 1.00, -1.25, -0.90, 0.75],
    [0.45, -1.15, 1.20, -1.35, -1.15, 0.50],
    [0.70, -0.95, 1.00, -1.25, -0.90, 0.75],
    [0.25, -1.35, 1.35, -1.45, -1.40, 0.25],
    [0.45, -1.15, 1.20, -1.35, -1.15, 0.50],
    [0.70, -0.95, 1.00, -1.25, -0.90, 0.75],
]


class AutoMotionSequence(Node):
    def __init__(self):
        super().__init__("auto_motion_sequence")
        self.target_pub = self.create_publisher(
            JointState, "/safe_motion/joint_target", 10)
        status_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.status_sub = self.create_subscription(
            String, "/safe_motion/status", self.on_status, status_qos)
        self.started_at = None
        self.next_send_at = None
        self.waiting_for_result = False
        self.result_deadline = None
        self.index = 0
        self.active_waypoint = 0
        self.finished = False
        # Use wall time because the simulation clock can jump backwards.
        steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(0.1, self.tick, clock=steady_clock)

    def on_status(self, message):
        status = message.data
        terminal = status.startswith((
            "Motion completed", "Blocked:", "Rejected:", "Motion failed", "Busy:"))
        if terminal and self.waiting_for_result:
            self.get_logger().info(f"Waypoint {self.active_waypoint} result: {status}")
            self.waiting_for_result = False
            self.result_deadline = None
            self.next_send_at = time.monotonic() + 1.6

    def tick(self):
        now = time.monotonic()
        if self.started_at is None:
            if self.target_pub.get_subscription_count() < 1:
                return
            self.started_at = now
            self.next_send_at = now
            self.get_logger().info(
                "Motion node connected. Starting automatic 20-second UR3e sequence; no slider input.")
        if now - self.started_at >= 20.0:
            self.finished = True
            self.timer.cancel()
            self.get_logger().info("20-second automatic motion sequence finished.")
            return
        if self.waiting_for_result:
            if self.result_deadline is not None and now >= self.result_deadline:
                self.get_logger().warning(
                    "No planner result received within 8 seconds; skipping to next waypoint.")
                self.waiting_for_result = False
                self.result_deadline = None
                self.next_send_at = now + 1.6
            return
        if now < self.next_send_at:
            return

        pose = POSES[self.index % len(POSES)]
        self.active_waypoint = self.index + 1
        message = JointState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.name = JOINTS
        message.position = pose
        self.target_pub.publish(message)
        self.get_logger().info(
            f"Sent automatic waypoint {self.index + 1}: "
            f"{[round(value, 3) for value in pose]} rad")
        self.waiting_for_result = True
        self.result_deadline = now + 8.0
        self.index += 1


def main(args=None):
    rclpy.init(args=args)
    node = AutoMotionSequence()
    try:
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
