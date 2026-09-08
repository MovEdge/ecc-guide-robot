#!/usr/bin/env bash
# One command, one terminal, real robot: cleanup(이전 세션 잔류 프로세스 정리)
# → 로봇 하드웨어 + Nav2 + 음성/UI 체인 전체(launch/full_system.launch.py)를
# 띄운다. run_full_sim.sh의 실기 버전.
#
# 실행 전:
#   - OpenCR USB 연결 확인 (기본 /dev/ttyACM0), 라이다 전원 확인
#   - .env에 GEMINI_API_KEY 설정 (mov_dest_resolver)
#   - 물리 터치스크린 X서버가 :1이 아니면 DISPLAY 값 조정
#
# Run inside the ros_humble container:
#   bash /workspace/ecc-guide-robot/src/mov_navigation/scripts/run_full_real.sh
set -e

WS=/workspace/ecc-guide-robot
export DISPLAY="${DISPLAY:-:1}"

bash "$WS/src/mov_navigation/scripts/cleanup_real.sh"

source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash"

exec ros2 launch "$WS/launch/full_system.launch.py"
