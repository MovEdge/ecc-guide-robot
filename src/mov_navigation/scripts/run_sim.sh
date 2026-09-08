#!/usr/bin/env bash
# One-shot: kill any previous sim, start the ECC map world (headless),
# spawn the robot in a free room pocket (~2.3m clearance, so /scan isn't all
# inf), and start the ROS2<->Gazebo bridge. Everything backgrounded with logs.
#
# Run inside the ros_humble container:
#   bash /workspace/ecc-guide-robot/src/mov_navigation/scripts/run_sim.sh
set -e

WS=/workspace/ecc-guide-robot/src/mov_navigation
LOG_DIR=/tmp/sim_logs
# The old spawn (-66.45, -0.75) sat inside the middle corridor, which is now
# a mapjh.pgm no-go zone burned into ecc_map_world.sdf as a real wall -- that
# would spawn the robot inside solid geometry. Moved to the free room pocket
# just south of it (~2.3m clearance to the nearest wall/no-go boundary).
SPAWN_X=-66.45
SPAWN_Y=-12.2

mkdir -p "$LOG_DIR"

# Ogre2's GL3Plus render path is GLX-based and needs *some* X display to
# create even a headless (-s) dummy render context -- without one, gazebo
# crashes deep in Ogre's Hlms material compiler with a segfault (misleading
# "libGL.so.1 failed to load" in ~/.ignition/rendering/ogre2.log). Default to
# :1 (this Jetson's Xorg display, check `ls /tmp/.X11-unix/` on the host if
# that ever changes) but don't override an explicitly-set DISPLAY.
export DISPLAY="${DISPLAY:-:1}"

echo "[1/3] stopping any previous gazebo/bridge..."
pkill -f "ign gazebo" 2>/dev/null || true
pkill -f "parameter_bridge" 2>/dev/null || true
sleep 2

echo "[2/3] starting gazebo server (headless)..."
# Without real GPU/EGL access (no nvidia-drm driver in this container), Ogre2
# falls back to software rendering (llvmpipe) -- but llvmpipe under-reports
# its own OpenGL version, so Ogre2 rejects it with "OpenGL 3.3 is not
# supported" and crashes instead of falling back cleanly. Force the version
# strings so Ogre2 accepts it. Standard Mesa/llvmpipe workaround.
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_GL_VERSION_OVERRIDE=3.3
export MESA_GLSL_VERSION_OVERRIDE=330
nohup ign gazebo -s -r -v 4 "$WS/worlds/ecc_map_world.sdf" > "$LOG_DIR/gazebo.log" 2>&1 &
echo "  pid $!, log: $LOG_DIR/gazebo.log"
sleep 6

echo "[2.5/3] spawning robot at ($SPAWN_X, $SPAWN_Y)..."
ign service -s /world/ecc_map_world/create \
  --reqtype ignition.msgs.EntityFactory \
  --reptype ignition.msgs.Boolean \
  --timeout 3000 \
  --req "sdf_filename: \"$WS/urdf/turtlebot3_waffle_sim.urdf\", name: \"waffle\", pose: {position: {x: $SPAWN_X, y: $SPAWN_Y, z: 0.05}}"

echo "[3/3] starting ROS2<->Gazebo bridge..."
source /opt/ros/humble/setup.bash
# NOTE: originally omitted Gazebo's own odom->base_footprint TF here so that
# ekf_node (matching the real robot's architecture, see config/ekf.yaml)
# would be the sole publisher -- but ekf_node's cross-process /clock timing
# couldn't keep up with AMCL's laser message filter (scans piled up in the
# filter's queue and got dropped, see docs/GAZEBO.md). Bridging Gazebo's own
# TF instead is simpler and known-reliable (same sim clock source as the
# lidar sensor, no cross-process lag). ekf_node/IMU fusion fidelity is a
# follow-up once this baseline is confirmed working.
nohup ros2 run ros_gz_bridge parameter_bridge \
  /cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist \
  /odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry \
  /scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan \
  /imu@sensor_msgs/msg/Imu[ignition.msgs.IMU \
  /clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock \
  /model/waffle/pose@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V \
  /model/turtlebot3_waffle/pose@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V \
  > "$LOG_DIR/bridge.log" 2>&1 &
echo "  pid $!, log: $LOG_DIR/bridge.log"

sleep 2
echo ""
echo "done. checks:"
echo "  tail -f $LOG_DIR/gazebo.log     # look for 'Unable to extrude' errors"
echo "  ign topic -e -t /stats -n 1     # real_time_factor should be ~1.0"
echo "  ros2 topic echo /scan --once    # ranges should NOT be all .inf"
echo "  ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \"{linear: {x: 0.2}}\" -r 10"
echo "  ign gazebo -g                   # GUI client, if you want to see it"
