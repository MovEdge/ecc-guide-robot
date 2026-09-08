#!/usr/bin/env bash
# One command, one terminal: cleanup(이전 세션 잔류 프로세스 정리) → Gazebo+
# 스폰+브리지(run_sim.sh) → localization+navigation+RViz(sim_bringup.launch.py)
# 순서로 띄운다.
#
# Run inside the ros_humble container:
#   bash /workspace/ecc-guide-robot/src/mov_navigation/scripts/run_full_sim.sh
set -e

WS=/workspace/ecc-guide-robot/src/mov_navigation
export DISPLAY="${DISPLAY:-:1}"

bash "$WS/scripts/cleanup_sim.sh"
bash "$WS/scripts/run_sim.sh"

echo ""
echo "[bringup] gazebo/bridge settling, waiting 3s before localization+navigation+rviz..."
sleep 3

source /opt/ros/humble/setup.bash
source /workspace/ecc-guide-robot/install/setup.bash

exec ros2 launch "$WS/launch/sim_bringup.launch.py"
