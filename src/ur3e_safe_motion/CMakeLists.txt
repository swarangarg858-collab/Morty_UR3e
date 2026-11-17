cmake_minimum_required(VERSION 3.8)
project(ur3e_safe_motion)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)

add_executable(safe_joint_motion_node src/safe_joint_motion_node.cpp)
ament_target_dependencies(safe_joint_motion_node
  rclcpp
  sensor_msgs
  std_msgs
  moveit_ros_planning_interface
)

install(TARGETS safe_joint_motion_node DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS
  scripts/safe_joint_slider.py
  scripts/openpi_sample_publisher.py
  scripts/openpi_action_receiver.py
  scripts/auto_motion_sequence.py
  DESTINATION lib/${PROJECT_NAME}
)
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})

ament_package()
