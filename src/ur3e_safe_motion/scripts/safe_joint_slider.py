#!/usr/bin/env python3
"""Slider GUI for requesting collision-checked UR3e joint motion."""

import queue
import threading
import tkinter as tk
from tkinter import ttk

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import String


JOINTS = [
    ("shoulder_pan_joint", -1.50, 1.50, 0.0),
    ("shoulder_lift_joint", -2.00, 0.80, -1.5708),
    ("elbow_joint", -2.00, 2.00, 1.5708),
    ("wrist_1_joint", -2.00, 2.00, -1.5708),
    ("wrist_2_joint", -2.00, 2.00, -1.5708),
    ("wrist_3_joint", -2.00, 2.00, 0.0),
]


class SafeJointSlider:
    def __init__(self):
        rclpy.init()
        self.node = rclpy.create_node("safe_joint_slider_gui")
        self.target_pub = self.node.create_publisher(
            JointState, "/safe_motion/joint_target", 10)
        status_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.status_sub = self.node.create_subscription(
            String, "/safe_motion/status", self.on_status, status_qos)
        self.status_queue = queue.Queue()
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.spin_thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.spin_thread.start()

        self.root = tk.Tk()
        self.root.title("UR3e Safe Joint Control")
        self.root.resizable(False, False)
        self.scales = {}
        self.readouts = {}
        self.busy = False
        self.deferred_move = False
        self.auto_move_timer = None

        main = ttk.Frame(self.root, padding=14)
        main.grid(row=0, column=0, sticky="nsew")
        ttk.Label(
            main,
            text="Drag a joint slider and release it to request a safe move. Angles are radians.",
            wraplength=390,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        ttk.Label(
            main,
            text="MoveIt checks the full path before moving. Use the button after setting several sliders.",
            wraplength=390,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

        for row, (joint, low, high, home) in enumerate(JOINTS, start=2):
            ttk.Label(main, text=joint).grid(row=row, column=0, sticky="w", padx=(0, 8))
            scale = tk.Scale(
                main,
                from_=low,
                to=high,
                resolution=0.01,
                orient=tk.HORIZONTAL,
                length=255,
                showvalue=False,
                command=lambda value, key=joint: self.update_readout(key, value),
            )
            scale.set(home)
            scale.grid(row=row, column=1, sticky="ew")
            scale.bind("<ButtonRelease-1>", self.on_slider_release)
            scale.bind("<KeyRelease>", self.on_slider_release)
            home_degrees = home * 180.0 / 3.141592653589793
            value_label = ttk.Label(
                main, text=f"{home:.2f} rad / {home_degrees:.0f}°",
                width=16, anchor="e")
            value_label.grid(row=row, column=2, sticky="e", padx=(8, 0))
            self.scales[joint] = scale
            self.readouts[joint] = value_label

        controls = ttk.Frame(main)
        controls.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(12, 6))
        ttk.Button(controls, text="Move to home safely", command=self.center_sliders).pack(
            side=tk.LEFT)
        self.move_button = ttk.Button(
            controls, text="Plan & move safely", command=self.send_target, state=tk.DISABLED)
        self.move_button.pack(side=tk.RIGHT)

        self.status_var = tk.StringVar(value="Waiting for the safe-motion planner...")
        ttk.Label(main, textvariable=self.status_var, wraplength=390).grid(
            row=9, column=0, columnspan=3, sticky="w", pady=(6, 0))

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self.drain_status)

    def update_readout(self, joint, value):
        radians = float(value)
        degrees = radians * 180.0 / 3.141592653589793
        self.readouts[joint].configure(text=f"{radians:.2f} rad / {degrees:.0f}°")

    def center_sliders(self):
        if self.auto_move_timer is not None:
            self.root.after_cancel(self.auto_move_timer)
            self.auto_move_timer = None
        for joint, _, _, home in JOINTS:
            self.scales[joint].set(home)
        self.status_var.set("Planning a collision-checked move to the saved home pose...")
        self.root.after(100, self.send_target)

    def on_slider_release(self, _event=None):
        if self.auto_move_timer is not None:
            self.root.after_cancel(self.auto_move_timer)
        # Wait briefly so a drag is treated as one target, not many tiny moves.
        self.auto_move_timer = self.root.after(250, self.send_target)

    def on_status(self, message):
        self.status_queue.put(message.data)

    def drain_status(self):
        while True:
            try:
                status = self.status_queue.get_nowait()
            except queue.Empty:
                break
            self.status_var.set(status)
            if status.startswith(("Ready:", "Motion completed.", "Blocked:", "Rejected:", "Busy:")):
                self.busy = False
                self.move_button.configure(state=tk.NORMAL)
                if self.deferred_move:
                    self.deferred_move = False
                    self.root.after(100, self.send_target)
            elif status.startswith(("Target received.", "Safe path found.")):
                self.busy = True
                self.move_button.configure(state=tk.DISABLED)
        self.root.after(100, self.drain_status)

    def send_target(self):
        self.auto_move_timer = None
        if self.busy:
            self.deferred_move = True
            return
        message = JointState()
        message.header.stamp = self.node.get_clock().now().to_msg()
        message.name = [joint for joint, _, _, _ in JOINTS]
        message.position = [float(self.scales[joint].get()) for joint, _, _, _ in JOINTS]
        self.target_pub.publish(message)
        self.busy = True
        self.move_button.configure(state=tk.DISABLED)
        self.status_var.set("Target sent; waiting for collision checking...")

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        rclpy.try_shutdown()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    SafeJointSlider().run()


if __name__ == "__main__":
    main()
