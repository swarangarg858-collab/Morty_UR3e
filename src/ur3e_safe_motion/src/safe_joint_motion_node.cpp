#include <array>
#include <chrono>
#include <cmath>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <thread>

#include "moveit/move_group_interface/move_group_interface.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/joint_state.hpp"
#include "std_msgs/msg/string.hpp"

namespace
{
const std::array<std::string, 6> kJointNames = {
  "shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
  "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"};

const std::map<std::string, std::pair<double, double>> kJointLimits = {
  {"shoulder_pan_joint", {-6.2832, 6.2832}},
  {"shoulder_lift_joint", {-6.2832, 6.2832}},
  {"elbow_joint", {-3.1416, 3.1416}},
  {"wrist_1_joint", {-6.2832, 6.2832}},
  {"wrist_2_joint", {-6.2832, 6.2832}},
  {"wrist_3_joint", {-6.2832, 6.2832}},
};
}  // namespace

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("safe_joint_motion");

  std::mutex request_mutex;
  std::optional<sensor_msgs::msg::JointState> pending_target;
  bool motion_in_progress = false;
  auto status_pub = node->create_publisher<std_msgs::msg::String>(
    "/safe_motion/status", rclcpp::QoS(1).transient_local());
  const auto publish_status = [node, status_pub](const std::string & text) {
      std_msgs::msg::String message;
      message.data = text;
      status_pub->publish(message);
      RCLCPP_INFO(node->get_logger(), "%s", text.c_str());
    };

  auto target_sub = node->create_subscription<sensor_msgs::msg::JointState>(
    "/safe_motion/joint_target", rclcpp::QoS(10),
    [node, &request_mutex, &pending_target, &motion_in_progress, publish_status](
      sensor_msgs::msg::JointState::ConstSharedPtr msg) {
      if (msg->name.size() != kJointNames.size() || msg->position.size() != kJointNames.size()) {
        publish_status("Rejected: send exactly six UR3e joint names and positions.");
        return;
      }

      std::set<std::string> received_names(msg->name.begin(), msg->name.end());
      std::set<std::string> expected_names(kJointNames.begin(), kJointNames.end());
      if (received_names != expected_names || received_names.size() != msg->name.size()) {
        publish_status("Rejected: joint names must be the six unique UR3e arm joints.");
        return;
      }

      for (size_t i = 0; i < msg->name.size(); ++i) {
        const double value = msg->position[i];
        if (!std::isfinite(value)) {
          publish_status("Rejected: joint values must be finite.");
          return;
        }
        const auto & bounds = kJointLimits.at(msg->name[i]);
        if (value < bounds.first || value > bounds.second) {
          publish_status("Rejected: a joint target is outside its URDF limits.");
          return;
        }
      }

      std::lock_guard<std::mutex> lock(request_mutex);
      if (motion_in_progress) {
        publish_status("Busy: another target is being planned or executed; request ignored.");
        return;
      }
      motion_in_progress = true;
      pending_target = *msg;
      publish_status("Target received. Checking for a collision-free path...");
    });
  static_cast<void>(target_sub);

  rclcpp::executors::MultiThreadedExecutor executor;
  executor.add_node(node);
  std::thread spin_thread([&executor]() {executor.spin();});

  try {
    moveit::planning_interface::MoveGroupInterface move_group(node, "ur_manipulator");
    move_group.setPlanningPipelineId("ompl");
    move_group.setPlannerId("RRTConnectkConfigDefault");
    move_group.setPlanningTime(8.0);
    move_group.setNumPlanningAttempts(5);
    // The mock arm should feel responsive while retaining controller limits.
    // MoveIt still validates and executes a collision-free timed trajectory.
    move_group.setMaxVelocityScalingFactor(0.70);
    move_group.setMaxAccelerationScalingFactor(0.70);
    if (!move_group.startStateMonitor(10.0)) {
      throw std::runtime_error("No current joint state received; refusing to plan.");
    }

    publish_status("Ready: set joint angles and request a safe move.");

    while (rclcpp::ok()) {
      std::optional<sensor_msgs::msg::JointState> target;
      {
        std::lock_guard<std::mutex> lock(request_mutex);
        if (pending_target.has_value()) {
          target = std::move(pending_target);
          pending_target.reset();
        }
      }

      if (!target.has_value()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        continue;
      }

      std::map<std::string, double> joint_target;
      for (size_t i = 0; i < target->name.size(); ++i) {
        joint_target.emplace(target->name[i], target->position[i]);
      }

      if (!move_group.setJointValueTarget(joint_target)) {
        {
          std::lock_guard<std::mutex> lock(request_mutex);
          motion_in_progress = false;
        }
        publish_status("Rejected: MoveIt could not accept this joint target.");
        continue;
      }

      moveit::planning_interface::MoveGroupInterface::Plan plan;
      const auto plan_result = move_group.plan(plan);
      if (plan_result != moveit::core::MoveItErrorCode::SUCCESS) {
        {
          std::lock_guard<std::mutex> lock(request_mutex);
          motion_in_progress = false;
        }
        publish_status("Blocked: no collision-free path found; arm stayed in place.");
        continue;
      }

      publish_status("Safe path found. Moving at reduced speed...");
      const auto execute_result = move_group.execute(plan);
      {
        std::lock_guard<std::mutex> lock(request_mutex);
        motion_in_progress = false;
      }
      if (execute_result != moveit::core::MoveItErrorCode::SUCCESS) {
        publish_status("Motion failed or was stopped.");
      } else {
        publish_status("Motion completed.");
      }
    }
  } catch (const std::exception & error) {
    RCLCPP_FATAL(node->get_logger(), "Safe motion initialization failed: %s", error.what());
  }

  executor.cancel();
  if (spin_thread.joinable()) {
    spin_thread.join();
  }
  rclcpp::shutdown();
  return 0;
}
