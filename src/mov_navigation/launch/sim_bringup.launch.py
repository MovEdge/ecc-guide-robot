"""
sim_localization + sim_navigation + RViz를 한 번에 띄우는 원샷 launch.
run_sim.sh(Gazebo + 스폰 + 브리지)가 이미 떠 있는 상태에서 실행:

    ros2 launch /workspace/ecc-guide-robot/src/mov_navigation/launch/sim_bringup.launch.py

localization은 즉시 시작하고, navigation은 sim_localization의 lifecycle
activate + 15초 뒤 자동 /initialpose 발행이 끝날 시간을 벌어주기 위해 17초
지연 후 시작한다. RViz는 그보다 조금 더 늦게(19초) 띄워서 맵/코스트맵이 이미
퍼블리시된 상태로 뜨게 한다. Jetson 부하가 크면(여러 프로세스 동시 기동) 이 타이밍도
밀릴 수 있으니, 그래도 map 프레임이 안 뜨면 RViz의 '2D Pose Estimate'로 직접 위치를
찍어주는 게 제일 확실하다. 지연 시간을 바꾸고 싶으면 아래 두 TimerAction의
period만 조정하면 됨.
"""
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

NAV_LAUNCH_DIR = "/workspace/ecc-guide-robot/src/mov_navigation/launch"
RVIZ_CONFIG = f"{get_package_share_directory('mov_navigation')}/rviz/ecc_default_view.rviz"


def generate_launch_description():
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(f"{NAV_LAUNCH_DIR}/sim_localization.launch.py")
    )

    navigation = TimerAction(
        period=17.0,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(f"{NAV_LAUNCH_DIR}/sim_navigation.launch.py")
        )],
    )

    rviz = TimerAction(
        period=19.0,
        actions=[Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            arguments=["-d", RVIZ_CONFIG],
            parameters=[{"use_sim_time": True}],
            output="screen",
        )],
    )

    return LaunchDescription([localization, navigation, rviz])
