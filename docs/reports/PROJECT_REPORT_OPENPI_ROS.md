# Morty UR3e + OpenPI Pi0.5

## ROS 2 Integration Demonstration

**Project report · ROS 2 Jazzy · Ubuntu 24.04**

---

## Executive summary

This project demonstrates a software pipeline connecting an OpenPI-shaped action message to a **UR3e robot simulation**. A sample publisher sends a synthetic action chunk, a ROS 2 receiver converts its first action into a six-joint target, and MoveIt checks a path against the robot and workcell before the mock controller executes it.

> **Result:** The demonstration ran successfully. MoveIt planned a collision-checked path, the mock arm controller reported success, and the motion node reported **“Motion completed.”**

> **Scope:** This is a simulation using synthetic sample data. It does not run live Pi0.5 inference and does not control a physical robot.

## At a glance

| Area | What the project demonstrates |
| --- | --- |
| Robot and scene | UR3e arm, gripper, controller stand, charger, and floor collision geometry |
| Motion planning | MoveIt planning against robot self-collision and workcell collision geometry |
| OpenPI-style input | One sample action chunk shaped **15 steps × 8 channels** |
| Execution | First action row mapped to six UR3e joints and sent to a mock controller |
| Observed outcome | Motion planned and completed in the software simulation |

## 1. OpenPI Pi0.5 output

OpenPI's `Policy.infer()` returns a dictionary containing `state`, `actions`, and `policy_timing`. The `actions` field is a sequence of future action steps. Its shape depends on the model configuration and output transforms.

For the `pi05_droid` configuration described by the OpenPI source, the model produces 15 action steps with 32 channels; the DROID output transform keeps the first 8 channels. The resulting action matrix is **15 × 8**. Other model configurations can have different dimensions.

```json
{
  "state": "state vector from the configured policy",
  "actions": "15 steps × 8 channels for pi05_droid after its output transform",
  "policy_timing": { "infer_ms": "inference time in milliseconds" }
}
```

OpenPI does not inherently identify these channels as UR3e joint angles. Their units, order, and meaning—such as absolute positions or deltas—depend on the training embodiment and transforms.

**OpenPI references:**

- [Policy inference API](https://github.com/Physical-Intelligence/openpi/blob/main/src/openpi/policies/policy.py)
- [Pi0.5 model configuration](https://github.com/Physical-Intelligence/openpi/blob/main/src/openpi/models/pi0_config.py)
- [Training configurations, including `pi05_droid`](https://github.com/Physical-Intelligence/openpi/blob/main/src/openpi/training/config.py)
- [DROID input and output transforms](https://github.com/Physical-Intelligence/openpi/blob/main/src/openpi/policies/droid_policy.py)

## 2. Morty UR3e workcell

The workcell description combines the UR3e arm and gripper with collision geometry for the controller stand, upright post, controller box, side cylinder, charger, and floor. Temporary green and white box obstacles were removed from the current scene. The dimensions below are the values modeled in the current Xacro files.

| Workcell component | Modeled dimensions and placement |
| --- | --- |
| Tapered controller stand | 60 cm lower diameter; 30 cm upper diameter; 45 cm high; 12 cm center hole |
| Blue top collar | Positioned above the tapered stand |
| Upright square post | 8 × 8 cm section; 102.5 cm modeled height |
| Side cylinder | 13 cm diameter × 13 cm long; centered 81 cm above floor; perpendicular to post and facing charger |
| Top controller box | 60 × 15 × 40 cm; mounted at post top and rotated 90° |
| Charger | 50 × 15 × 30 cm; modeled beside stand with collision geometry |
| Floor collision plate | 200 × 200 cm; 10 cm thick |

All modeled workcell parts have visual and collision geometries, and their placements are represented by fixed URDF joints.

### Workcell source files

- [Complete workcell Xacro](C:/Users/ragha/Downloads/morty_vla-main/morty_vla-main/src/ur3e_learning_description/urdf/custom_env.xacro) — robot, stand, charger, and floor
- [Robot and controller pillar Xacro](C:/Users/ragha/Downloads/morty_vla-main/morty_vla-main/src/ur3e_learning_description/urdf/ur3e_with_gripper_3d.urdf.xacro) — UR3e arm, gripper, pillar, and top box
- [Shareable workcell ZIP](C:/Users/ragha/Downloads/morty_vla-main/morty_vla-main/Morty_UR3e_Workcell_Share.zip)

## 3. Collision-aware motion package

The ROS 2 package `ur3e_safe_motion` starts MoveIt, the mock `ros2_control` arm controller, the safe motion node, joint sliders, and RViz.

When a six-joint target arrives, the motion node checks the joint names, joint count, numeric values, and configured joint limits. MoveIt then plans a path using the robot and workcell collision geometry. The mock arm controller receives the trajectory only after MoveIt finds a valid plan. If planning fails, the target is blocked and the arm remains in place.

The motion node prevents a new target from overlapping an active planning or execution request. Run only one workcell launch at a time; a second copy can create duplicate MoveIt and controller servers.

## 4. OpenPI-style publisher-to-robot demo

### Data flow

| Stage | Node or topic | Function |
| --- | --- | --- |
| 1 | `openpi_sample_publisher.py` | Publishes one synthetic JSON action chunk (15 × 8) on `/openpi/action` as `std_msgs/msg/String`; waits for the receiver to subscribe |
| 2 | `openpi_action_receiver.py` | Validates the message shape, values, joint order, and configured soft limits; takes the first six channels of the first action row |
| 3 | `/safe_motion/joint_target` | Carries the six UR3e joint positions in radians as `sensor_msgs/msg/JointState` |
| 4 | MoveIt + mock `arm_controller` | Plans against collision geometry and executes the approved path in simulation |

```text
openpi_sample_publisher.py
    │  synthetic 15 × 8 JSON action
    ▼
/openpi/action
    ▼
openpi_action_receiver.py ── validates and maps the first action row
    │
    ▼
/safe_motion/joint_target
    ▼
MoveIt collision check and path planning
    ▼
mock arm_controller executes the approved path
```

### What the demo does—and does not do

- Sends one synthetic OpenPI-shaped action chunk and executes **only its first row**.
- Demonstrates the ROS message bridge, input checks, collision-aware planning, and mock execution.
- Does **not** load Pi0.5 weights or perform live policy inference.
- Does **not** establish a calibrated DROID-to-UR3e action conversion. The first-six-channel mapping is only a wiring example.
- Does **not** establish that motion is safe on physical hardware. Real deployment needs a suitable UR3e-trained or fine-tuned policy, verified units and action semantics, and hardware safety validation.

## 5. Run the demonstration

On Ubuntu 24.04 with ROS 2 Jazzy, open a terminal and build the package from the workspace root:

```bash
source /opt/ros/jazzy/setup.bash
cd /mnt/c/Users/ragha/Downloads/morty_vla-main/morty_vla-main
colcon build --symlink-install --packages-select ur3e_safe_motion
source install/setup.bash
```

Start the complete one-shot demonstration:

```bash
ros2 launch ur3e_safe_motion openpi_safe_demo.launch.py
```

This launch starts RViz, the mock workcell, the safety planner, and both OpenPI demo nodes. If the workcell is already running, start only the bridge in another terminal:

```bash
ros2 launch ur3e_safe_motion openpi_bridge_demo.launch.py
```

To restart the complete demo, stop the existing launch with `Ctrl+C` and wait for it to exit before starting it again.

## 6. Run result

In the observed single-instance run, the sample action was received, MoveIt computed a path, the `arm_controller` reported **“Goal reached, success!”**, and the safe motion node reported **“Motion completed.”** RViz shows a small arm movement because the demo executes only the first action row rather than streaming all 15 rows.

## Completion summary

- Inspected and documented the OpenPI Pi0.5 output shape for `pi05_droid`.
- Modeled the controller, charger, floor, and UR3e workcell collision geometry.
- Built a MoveIt-based motion and safety layer for the mock UR3e arm.
- Ran the synthetic publisher → receiver → MoveIt → mock controller pipeline successfully.

**The successful run verifies the software simulation pipeline only.** Physical deployment requires a suitable robot policy, verified action conversion, and separate hardware-level safety validation.
