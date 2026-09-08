import os

from launch import LaunchDescription
from launch_ros.actions import Node

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            parameters=[os.path.join(CONFIG_DIR, 'ekf.yaml')],
        ),
    ])
