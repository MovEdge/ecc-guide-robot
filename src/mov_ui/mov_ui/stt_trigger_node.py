import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty

class SttTriggerNode(Node):
    def __init__(self):
        super().__init__('stt_trigger_node')
        self.get_logger().info('STT Trigger Node 시작')
        self.publisher_ = self.create_publisher(Empty, '/stt/start_listening', 10)
        self.timer_ = self.create_timer(5.0, self.timer_callback)
    def timer_callback(self):
        msg = Empty()
        self.publisher_.publish(msg)
        self.get_logger().info('STT Trigger 메시지 발행됨')


def main(args=None):
    rclpy.init(args=args)
    node = SttTriggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()