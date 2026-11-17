# UR3e safe motion

This package plans joint targets with MoveIt before sending them to the mock
`ros2_control` arm controller. MoveIt uses the workcell Xacro collision geometry
for the UR3e, gripper, stand, charger, wall, table, and mount surface. A target is executed only when
MoveIt returns a valid collision-free plan. Targets outside the URDF joint
limits or with malformed joint names are rejected before planning.

## Install on Ubuntu 24.04 / ROS 2 Jazzy

```bash
sudo apt update
sudo apt install ros-jazzy-moveit ros-jazzy-ros2-control ros-jazzy-ros2-controllers python3-tk
```

## Build and launch

From the workspace root:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select ur3e_learning_description ur3e_safe_motion
source install/setup.bash
ros2 launch ur3e_safe_motion safe_motion.launch.py
```

The mock arm now starts at the SRDF `home` configuration instead of all-zero
joint angles. The sliders also open at that same home pose, and **Safe home
pose** restores it. Release a slider to plan and execute its target
automatically; the button remains available when changing several targets.
This avoids beginning from the folded all-zero pose shown in the earlier
screenshot.

The package also loads conservative MoveIt velocity and acceleration limits
for every arm joint. These are required by MoveIt's time-optimal trajectory
adapter; without them a valid OMPL path is discarded before execution. The
mock planner now uses 70% of those limits, instead of the previous 15% speed
and 10% acceleration scaling.

The launch file starts the robot state publisher, mock ros2_control system,
joint-state broadcaster, trajectory controller, MoveIt `move_group`, a safe
joint slider window, and RViz. Do not run `view_robot.launch.xml` at the same
time; it starts a separate joint-state publisher for slider-only visualization.

## Send a joint target

Use the six bounded sliders and click **Plan & move safely**. MoveIt checks the
complete path against self-collision and the workcell collision geometry in the
URDF. Unsafe or unplannable paths are not executed. The ROS topic can also be
used directly; publish exactly six arm joints and six positions in radians.

```bash
ros2 topic pub --once /safe_motion/joint_target sensor_msgs/msg/JointState \
  "{name: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint], position: [0.3, -1.57, 1.57, -1.57, -1.57, 0.0]}"
```

This setup uses mock hardware for visualization and software integration. It
does not send commands to a physical UR3e.

## What OpenPI Pi0.5 returns

OpenPI `Policy.infer()` returns a dictionary with `state`, `actions`, and
`policy_timing`. `actions` is a numeric chunk with shape
`[action_horizon, action_dim]`; the dimensions come from the model/config and
the configured output transforms. The base Pi0.5 config defaults to 50 x 32.
The official `pi05_droid` config uses a 15-step horizon and 32 model action
channels; its DROID output transform returns the first 8 channels, so the
policy result has `actions` shaped 15 x 8. Other Pi0.5 tasks can use different
dimensions. See the official [Policy.infer implementation](https://github.com/Physical-Intelligence/openpi/blob/main/src/openpi/policies/policy.py),
[Pi0.5 config](https://github.com/Physical-Intelligence/openpi/blob/main/src/openpi/models/pi0_config.py),
[training configs](https://github.com/Physical-Intelligence/openpi/blob/main/src/openpi/training/config.py),
and [DROID output transform](https://github.com/Physical-Intelligence/openpi/blob/main/src/openpi/policies/droid_policy.py).

### Morty synthetic interface: 15 x 7

Each row is [shoulder_pan, shoulder_lift, elbow, wrist_1, wrist_2, wrist_3, gripper].
Six arm channels are absolute positions in radians. Gripper is normalized:
0 = open, 1 = closed (demo convention). State also has seven values.
This custom Morty sample is synthetic, not stock DROID inference.
The receiver validates all 15 rows, arm soft limits, and gripper range.
Only the first arm pose is sent to MoveIt. The gripper is validated and logged
but not executed because the current controller supports only the six arm joints.
The remaining 14 rows are not executed.

## Run the full OpenPI dummy demo

From an Ubuntu terminal, after building and sourcing the workspace, run one
command:

```bash
ros2 launch ur3e_safe_motion openpi_safe_demo.launch.py
```

This starts the mock robot, MoveIt collision-aware planner, joint sliders, and
RViz, then launches the sender/receiver after the workcell is up. The dummy
publisher waits for its receiver, then sends the replayable
`config/synthetic_openpi_pi05_droid_motion_check.json` sample (15 steps x 7
channels) on
`/openpi/action`. The receiver validates all mapped values against the UR3e
slider soft limits, takes the first predicted step, converts it to
`sensor_msgs/JointState`, and publishes to `/safe_motion/joint_target`. MoveIt
checks the path against the robot and workcell collision geometry, then
executes only a valid plan. Inspect the status in the `UR3e Safe Joint
Control` window and the resulting pose in RViz. Later chunk steps are not
streamed in this demo.

To run only the bridge against an already running workcell, use
`ros2 launch ur3e_safe_motion openpi_bridge_demo.launch.py` in another
terminal. Each launch publishes the sample once. To replay it, stop that
bridge with Ctrl+C, then run the same launch command again. The workcell can
stay running.

You can also replay a different compatible JSON file without editing the
node. It must use the same `policy_output.actions` structure, UR3e joint order,
and radian position semantics. Pass its absolute path as a launch argument:

```bash
ros2 launch ur3e_safe_motion openpi_bridge_demo.launch.py \
  action_file:=/absolute/path/to/my_openpi_output.json
```

For the full demo, which starts the workcell too, pass the same argument to
`openpi_safe_demo.launch.py`. The receiver publishes only the first action
row to the safety planner; later chunk rows are validated but not streamed.

Run `openpi_safe_demo.launch.py` only once. It includes the workcell launch;
starting it again while another `safe_motion.launch.py` or
`openpi_safe_demo.launch.py` is active creates duplicate controller managers
and MoveIt action servers, which can preempt trajectories. To restart, press
Ctrl+C in the old launch terminal and wait for it to exit first. If the
workcell is already running, start only `openpi_bridge_demo.launch.py` in a
second terminal.

