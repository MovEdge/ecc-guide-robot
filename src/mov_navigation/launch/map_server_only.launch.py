"""
AMCL/Nav2 스택 없이 map_server만 단독으로 띄운다 — RViz에서 /map 토픽만
확인하고 싶을 때(맵 자체가 맞는지, red zone/장애물이 잘 반영됐는지 등) 굳이
로봇 하드웨어/AMCL까지 다 켜지 않아도 되게 하기 위함. lifecycle_manager로
map_server를 configure+activate까지 자동으로 올린다(autostart).

    ros2 launch /workspace/ecc-guide-robot/src/mov_navigation/launch/map_server_only.launch.py
"""
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

MAP_YAML = f"{get_package_share_directory('mov_slam')}/maps/mapjh.yaml"


def generate_launch_description():
    map_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        parameters=[{"yaml_filename": MAP_YAML, "use_sim_time": False}],
    )

    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_map_server",
        output="screen",
        parameters=[{
            "autostart": True,
            "node_names": ["map_server"],
            "use_sim_time": False,
        }],
    )

    return LaunchDescription([map_server, lifecycle_manager])
