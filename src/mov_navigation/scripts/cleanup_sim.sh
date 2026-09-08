#!/usr/bin/env bash
# Kill every leftover process from a previous Gazebo+Nav2 sim session.
#
# Why this exists: run_sim.sh only ever cleaned up `ign gazebo` and
# `parameter_bridge` -- everything ros2-launched (sim_localization,
# sim_navigation, and everything they spawn: map_server, amcl,
# controller/planner/bt_navigator, lifecycle_manager, static_transform_
# publisher, odom_to_tf.py, rviz2) was never killed anywhere. Closing a
# terminal or a dropped SSH session doesn't propagate Ctrl+C to that whole
# tree, so orphans pile up across days -- found map_server/amcl instances
# from three separate calendar days alive at once (duplicate node names on
# the graph), which is why config/map edits looked like they weren't taking
# effect: RViz and the active map_server were still the old ones.
#
# Scoped to the sim/nav stack only -- does NOT touch mov_ui/mov_stt/
# mov_dest_resolver (app.launch.py), that's a separate track.
#
# Run inside the ros_humble container:
#   bash /workspace/ecc-guide-robot/src/mov_navigation/scripts/cleanup_sim.sh
set -e

PATTERNS=(
  "ign gazebo"
  "ros_gz_bridge/parameter_bridge"
  "sim_bringup.launch.py"
  "sim_localization.launch.py"
  "sim_navigation.launch.py"
  "nav2_map_server/map_server"
  "nav2_amcl/amcl"
  "nav2_controller/controller_server"
  "nav2_planner/planner_server"
  "nav2_bt_navigator/bt_navigator"
  "nav2_behaviors/behavior_server"
  "nav2_lifecycle_manager/lifecycle_manager"
  "lidar_frame_static_tf"
  "base_link_static_tf"
  "mov_navigation/scripts/odom_to_tf.py"
  "rviz2 -d /opt/ros/humble/share/nav2_bringup"
)

echo "killing stale sim/nav2 processes..."
for p in "${PATTERNS[@]}"; do
  pkill -9 -f "$p" 2>/dev/null || true
done
sleep 2

echo "remaining sim-related processes (should be empty):"
ps aux | grep -E "ign gazebo|parameter_bridge|nav2_map_server|nav2_amcl|nav2_controller|nav2_planner|nav2_bt_navigator|nav2_lifecycle_manager|odom_to_tf|rviz2 -d" | grep -v grep || echo "  (none)"
