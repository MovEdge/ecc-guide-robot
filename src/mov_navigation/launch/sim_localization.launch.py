"""
Localization stack for the Gazebo sim, mirroring the real robot's architecture:
ekf_node (robot_localization) fuses /odom + /imu and publishes odom->base_footprint
TF, then map_server + amcl (same config/nav2_params_waffle_pi.yaml used on the
real robot, already pointed at real.yaml) publish map->odom.

Run after scripts/run_sim.sh has the simulator + bridge up:
    ros2 launch /workspace/ecc-guide-robot/src/mov_navigation/launch/sim_localization.launch.py
"""
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node

SCRIPT_DIR = "/workspace/ecc-guide-robot/src/mov_navigation/scripts"

CONFIG_DIR = "/workspace/ecc-guide-robot/config"
EKF_CONFIG = f"{CONFIG_DIR}/ekf.yaml"
NAV2_CONFIG = f"{CONFIG_DIR}/nav2_params_waffle_pi.yaml"

# Must match SPAWN_X/SPAWN_Y in scripts/run_sim.sh
SPAWN_X = -66.45
SPAWN_Y = -12.2


def generate_launch_description():
    return LaunchDescription([
        # No robot_state_publisher is running, and Ignition's URDF->SDF
        # conversion merges base_link/base_scan (fixed joints) into
        # base_footprint's rigid body -- so the lidar's actual published
        # frame_id ends up "waffle/base_footprint/lidar", not "base_scan".
        # AMCL's laser message filter needs a TF chain to that exact frame,
        # so publish it statically at the scan_joint offset from the URDF.
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="lidar_frame_static_tf",
            arguments=[
                "--x", "-0.064", "--y", "0", "--z", "0.132",
                "--frame-id", "base_footprint",
                "--child-frame-id", "waffle/base_footprint/lidar",
            ],
        ),
        # nav2_params_waffle_pi.yaml's costmaps/bt_navigator/behavior_server
        # all use robot_base_frame: base_link, but base_link doesn't exist as
        # its own TF frame in the sim (Ignition's URDF->SDF conversion merged
        # it into base_footprint, same issue as the lidar frame above).
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="base_link_static_tf",
            arguments=[
                "--x", "0", "--y", "0", "--z", "0.010",
                "--frame-id", "base_footprint",
                "--child-frame-id", "base_link",
            ],
        ),
        # ekf_node (robot_localization, config/ekf.yaml) is deliberately NOT
        # launched here for now -- its cross-process /clock timing couldn't
        # keep up with AMCL's laser message filter, starving it of usable
        # odom->base_footprint TF (see docs/GAZEBO.md). Whether Gazebo's own
        # DiffDrive plugin even exposes a bridgeable TF topic is also
        # unverified, so bypass both: republish /odom (confirmed reliable)
        # as TF directly. Revisit EKF/IMU fusion once this baseline works.
        ExecuteProcess(
            cmd=["python3", f"{SCRIPT_DIR}/odom_to_tf.py"],
            output="screen",
        ),
        Node(
            package="nav2_map_server",
            executable="map_server",
            name="map_server",
            output="screen",
            parameters=[NAV2_CONFIG, {"use_sim_time": True}],
        ),
        Node(
            package="nav2_amcl",
            executable="amcl",
            name="amcl",
            output="screen",
            parameters=[NAV2_CONFIG, {"use_sim_time": True}],
        ),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_localization",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                "autostart": True,
                "node_names": ["map_server", "amcl"],
            }],
        ),
        # AMCL needs an /initialpose seed before it publishes anything
        # (set_initial_pose: false in nav2_params_waffle_pi.yaml). Fire this
        # once, after giving map_server/amcl time to activate via the
        # lifecycle manager -- avoids the manual step being forgotten on
        # every restart.
        TimerAction(
            period=15.0,
            actions=[ExecuteProcess(
                cmd=[
                    "ros2", "topic", "pub", "-1", "/initialpose",
                    "geometry_msgs/msg/PoseWithCovarianceStamped",
                    "{header: {frame_id: 'map'}, pose: {pose: {position: "
                    f"{{x: {SPAWN_X}, y: {SPAWN_Y}, z: 0.0}}, orientation: "
                    "{w: 1.0}}, covariance: [0.25,0,0,0,0,0, 0,0.25,0,0,0,0, "
                    "0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.06]}}",
                ],
                output="screen",
            )],
        ),
    ])
