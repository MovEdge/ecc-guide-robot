"""
실기 로봇 하드웨어(turtlebot3_bringup) + Nav2 풀스택(nav2_bringup)을 한 번에
띄우는 launch. sim_bringup.launch.py의 실기 버전 — 시뮬레이터/Gazebo 없이
실제 OpenCR/라이다/Nav2를 그대로 사용한다.

사용자가 수동으로 검증한 두 커맨드를 하나로 합친 것:
  ros2 launch turtlebot3_bringup robot.launch.py
  ros2 launch nav2_bringup bringup_launch.py \
    map:=/workspace/slam/slam_frommap/out3/mapjh.yaml \
    use_sim_time:=false \
    params_file:=/workspace/ecc-guide-robot/config/nav2_params_waffle_pi.yaml

로봇 하드웨어(OpenCR 시리얼 연결, 라이다 스핀업)가 먼저 안정화될 시간을 벌기
위해 Nav2는 5초 지연 후 시작한다. Jetson 부하가 크면 이 지연으로 부족할 수
있으니, map_server/amcl이 lifecycle activate되기 전에 Nav2 로그에 시리얼
관련 에러가 보이면 지연 시간을 늘릴 것.

실행 전 확인:
  - USB 포트: turtlebot3_bringup 기본값은 /dev/ttyACM0 (OpenCR). 다르면
    launch_arguments에 usb_port 추가 필요.
  - map/params 경로는 아래 상수로 고정되어 있음 — 다른 맵을 쓰려면 MAP_YAML만 바꾸면 됨.

    ros2 launch /workspace/ecc-guide-robot/src/mov_navigation/launch/real_bringup.launch.py
"""
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

CONFIG_DIR = "/workspace/ecc-guide-robot/config"
NAV2_CONFIG = f"{CONFIG_DIR}/nav2_params_waffle_pi.yaml"
MAP_YAML = f"{get_package_share_directory('mov_slam')}/maps/mapjh.yaml"

NAV2_BRINGUP_DELAY = 5.0


def generate_launch_description():
    turtlebot3_bringup_dir = get_package_share_directory("turtlebot3_bringup")
    nav2_bringup_dir = get_package_share_directory("nav2_bringup")

    robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f"{turtlebot3_bringup_dir}/launch/robot.launch.py"
        ),
    )

    nav2 = TimerAction(
        period=NAV2_BRINGUP_DELAY,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                f"{nav2_bringup_dir}/launch/bringup_launch.py"
            ),
            launch_arguments={
                "map": MAP_YAML,
                "use_sim_time": "false",
                "params_file": NAV2_CONFIG,
                "autostart": "true",
            }.items(),
        )],
    )

    return LaunchDescription([
        SetEnvironmentVariable("TURTLEBOT3_MODEL", "waffle_pi"),
        robot,
        nav2,
    ])
