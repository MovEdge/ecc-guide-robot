#!/usr/bin/env python3
"""
Compares AMCL's pose estimate against Gazebo's ground-truth pose for the
"waffle" model, printing position/yaw error on every AMCL update. This is
the actual point of the whole simulator exercise: if error stays small here,
the field localization problem is more likely hardware/sensor-side; if it's
large here too, it's more likely Nav2/AMCL tuning or map quality.

Run after scripts/run_sim.sh and launch/sim_localization.launch.py are up:
    python3 scripts/localization_error_monitor.py
"""
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
from tf2_msgs.msg import TFMessage


def yaw_from_quat(q):
    siny_cosp = 2 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class LocalizationErrorMonitor(Node):
    def __init__(self):
        super().__init__("localization_error_monitor")
        self.ground_truth = None  # (x, y, yaw)
        self.create_subscription(
            TFMessage, "/model/waffle/pose", self.on_ground_truth, 10
        )
        self.create_subscription(
            TFMessage, "/model/turtlebot3_waffle/pose", self.on_ground_truth, 10
        )
        self.create_subscription(
            PoseWithCovarianceStamped, "/amcl_pose", self.on_amcl_pose, 10
        )
        self.get_logger().info("waiting for /amcl_pose and ground truth pose...")

    def on_ground_truth(self, msg: TFMessage):
        for t in msg.transforms:
            if t.child_frame_id in ("waffle", "turtlebot3_waffle"):
                p = t.transform.translation
                yaw = yaw_from_quat(t.transform.rotation)
                self.ground_truth = (p.x, p.y, yaw)
                return

    def on_amcl_pose(self, msg: PoseWithCovarianceStamped):
        if self.ground_truth is None:
            self.get_logger().warn("no ground truth pose yet, skipping comparison")
            return
        gx, gy, gyaw = self.ground_truth
        ap = msg.pose.pose.position
        ayaw = yaw_from_quat(msg.pose.pose.orientation)

        pos_err = math.hypot(ap.x - gx, ap.y - gy)
        yaw_err = math.atan2(math.sin(ayaw - gyaw), math.cos(ayaw - gyaw))

        self.get_logger().info(
            f"ground_truth=({gx:+.3f},{gy:+.3f},{math.degrees(gyaw):+.1f}deg)  "
            f"amcl=({ap.x:+.3f},{ap.y:+.3f},{math.degrees(ayaw):+.1f}deg)  "
            f"pos_err={pos_err:.3f}m  yaw_err={math.degrees(yaw_err):+.1f}deg"
        )


def main():
    rclpy.init()
    node = LocalizationErrorMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
