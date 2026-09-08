#!/usr/bin/env bash
# Kill every leftover process from a previous real-robot bringup session
# (turtlebot3_bringup + nav2_bringup + app.launch.py's stt/dest_resolver/ui).
#
# Why this exists: cleanup_sim.sh already proved that closing a terminal or a
# dropped SSH session doesn't propagate Ctrl+C to the whole launched process
# tree on this Jetson, leaving orphaned map_server/amcl instances from
# multiple days running at once (duplicate nodes on the graph, stale map
# silently served). Same risk applies here since full_system.launch.py now
# bundles robot hardware + Nav2 + the voice/UI chain into one tree.
#
# Run inside the ros_humble container:
#   bash /workspace/ecc-guide-robot/src/mov_navigation/scripts/cleanup_real.sh
set -e

PATTERNS=(
  "real_bringup.launch.py"
  "full_system.launch.py"
  "turtlebot3_node/turtlebot3_ros"
  "hlds_laser_publisher"
  "ld08_driver"
  "coin_d4_driver"
  "robot_state_publisher"
  # nav2_bringup은 기본적으로 composition을 쓰기 때문에 map_server/amcl/
  # controller_server 등이 각자 별도 실행파일이 아니라 아래 component
  # container 프로세스 하나에 플러그인으로 로드된다 — 위의
  # "nav2_map_server/map_server" 같은 패턴은 그 컨테이너의 실제 커맨드라인에
  # 나타나지 않아서 절대 매치되지 않고, 그 결과 컨테이너가 매번 orphan으로
  # 남아 map_server/amcl이 중복 실행되는 원인이었다(2026-09-02, 실기
  # end-to-end 테스트 중 발견 — RViz에 맵이 안 보이는 증상으로 나타남).
  # non-composed로 기동하는 경우를 위해 개별 실행파일 패턴은 남겨둔다.
  "component_container_isolated"
  "nav2_map_server/map_server"
  "nav2_amcl/amcl"
  "nav2_controller/controller_server"
  "nav2_planner/planner_server"
  "nav2_bt_navigator/bt_navigator"
  "nav2_behaviors/behavior_server"
  "nav2_lifecycle_manager/lifecycle_manager"
  "mov_stt/stt_node"
  "mov_dest_resolver/dest_resolver_node"
  "mov_ui/ui_node"
  "mov_tts/tts_node"
)

echo "killing stale real-robot bringup processes..."
for p in "${PATTERNS[@]}"; do
  pkill -9 -f "$p" 2>/dev/null || true
done
sleep 2

echo "remaining processes (should be empty):"
ps aux | grep -E "turtlebot3_ros|hlds_laser_publisher|ld08_driver|coin_d4_driver|component_container_isolated|nav2_map_server|nav2_amcl|nav2_controller|nav2_planner|nav2_bt_navigator|nav2_lifecycle_manager|stt_node|dest_resolver_node|ui_node|tts_node" | grep -v grep || echo "  (none)"
