"""
Full Nav2 navigation stack (controller/planner/behavior/bt_navigator) on top
of the localization stack. Run after run_sim.sh + sim_localization.launch.py
are already up and AMCL is publishing:

    ros2 launch /workspace/ecc-guide-robot/src/mov_navigation/launch/sim_navigation.launch.py

Then send a goal, e.g.:
    ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
      "{pose: {header: {frame_id: 'map'}, pose: {position: {x: -0.1, y: -0.1, z: 0.0}, orientation: {w: 1.0}}}}" \
      --feedback
"""
from launch import LaunchDescription
from launch_ros.actions import Node

CONFIG_DIR = "/workspace/ecc-guide-robot/config"
NAV2_CONFIG = f"{CONFIG_DIR}/nav2_params_waffle_pi.yaml"

# nav2_params_waffle_pi.yaml points at a BT xml filename that doesn't exist
# in this Nav2 version's nav2_bt_navigator package (navigate_to_pose_w_
# replanning_and_recovery.xml) -- override with the one that's actually
# installed.
BT_XML = (
    "/opt/ros/humble/share/nav2_bt_navigator/behavior_trees/"
    "nav_to_pose_with_consistent_replanning_and_if_path_becomes_invalid.xml"
)

# nav2_params_waffle_pi.yaml sets enable_stamped_cmd_vel: true for these
# servers, but our Gazebo bridge (and the real robot's turtlebot3_node
# firmware, per config/turtlebot3_waffle_pi.yaml) expects plain
# geometry_msgs/Twist on /cmd_vel, not TwistStamped -- override to match.
NOT_STAMPED = {"enable_stamped_cmd_vel": False}


def generate_launch_description():
    lifecycle_nodes = ["controller_server", "planner_server", "behavior_server", "bt_navigator"]
    return LaunchDescription([
        Node(
            package="nav2_controller",
            executable="controller_server",
            name="controller_server",
            output="screen",
            parameters=[NAV2_CONFIG, {"use_sim_time": True}, NOT_STAMPED],
        ),
        Node(
            package="nav2_planner",
            executable="planner_server",
            name="planner_server",
            output="screen",
            parameters=[NAV2_CONFIG, {"use_sim_time": True}],
        ),
        Node(
            package="nav2_behaviors",
            executable="behavior_server",
            name="behavior_server",
            output="screen",
            parameters=[NAV2_CONFIG, {"use_sim_time": True}, NOT_STAMPED],
        ),
        Node(
            package="nav2_bt_navigator",
            executable="bt_navigator",
            name="bt_navigator",
            output="screen",
            parameters=[NAV2_CONFIG, {
                "use_sim_time": True,
                "default_nav_to_pose_bt_xml": BT_XML,
                "default_nav_through_poses_bt_xml": BT_XML,
            }],
        ),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_navigation",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                "autostart": True,
                "node_names": lifecycle_nodes,
            }],
        ),
    ])
