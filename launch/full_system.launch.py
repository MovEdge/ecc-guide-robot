"""
전체 시스템 원샷 launch: 로봇 하드웨어 + Nav2 풀스택
(mov_navigation/launch/real_bringup.launch.py) + 음성/UI 체인
(mov_stt + mov_dest_resolver + mov_ui, launch/app.launch.py).

이제 Nav2 풀스택이 실기에서 검증됐으므로(2026-09-01, mapjh.pgm/yaml 기준),
그동안 소프트웨어 개발용으로 Nav2 없이 따로 띄우던 app.launch.py를 여기서
real_bringup.launch.py와 합쳐 실제 사용자가 로봇을 켜고 바로 쓸 수 있는
end-to-end 진입점으로 만든다.

실행 전:
  - 워크스페이스 빌드/소싱 (colcon build --symlink-install && source install/setup.bash)
  - export DISPLAY=:1 (물리 터치스크린 X서버) — mov_ui에 필요
  - .env에 GEMINI_API_KEY 설정 — mov_dest_resolver에 필요
  - OpenCR USB 연결 확인 (기본 /dev/ttyACM0)

    export DISPLAY=:1
    ros2 launch /workspace/ecc-guide-robot/launch/full_system.launch.py
"""
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

REPO_DIR = "/workspace/ecc-guide-robot"


def generate_launch_description():
    robot_and_nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f"{REPO_DIR}/src/mov_navigation/launch/real_bringup.launch.py"
        ),
    )

    voice_and_ui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(f"{REPO_DIR}/launch/app.launch.py"),
    )

    return LaunchDescription([robot_and_nav2, voice_and_ui])
