#!/usr/bin/env python3
"""
Republishes /odom as the odom->base_footprint TF. Bypasses uncertainty
around whether/how Gazebo's DiffDrive plugin exposes its own TF topic over
the bridge (see docs/GAZEBO.md) -- /odom itself is confirmed reliable, so
just broadcast TF from it directly.
"""
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped


class OdomToTf(Node):
    def __init__(self):
        super().__init__("odom_to_tf")
        self.broadcaster = TransformBroadcaster(self)
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)

    def on_odom(self, msg: Odometry):
        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = msg.header.frame_id
        t.child_frame_id = msg.child_frame_id
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = msg.pose.pose.position.z
        t.transform.rotation = msg.pose.pose.orientation
        self.broadcaster.sendTransform(t)


def main():
    rclpy.init()
    node = OdomToTf()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
