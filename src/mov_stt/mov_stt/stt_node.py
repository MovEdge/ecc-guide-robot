import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty
from mov_interfaces.msg import SttResult

class SttNode(Node):
    def __init__(self):
        super().__init__('stt_node')
        self.get_logger().info('STT Node 시작')
        self.subscription = self.create_subscription(Empty, '/stt/start_listening', self.listener_callback, 10)
        self.publisher_ = self.create_publisher(SttResult, '/stt/result', 10)

    def listener_callback(self, msg):
        self.get_logger().info('STT Trigger 메시지 수신됨, 음성인식 시작')
        # 여기에 STT 처리 로직을 추가하고 결과를 발행합니다.
        result_msg = SttResult()
        result_msg.success = True
        result_msg.text = "스타벅스로 가려면 어디로 가야 하나요?"  # STT 처리 결과 예시
        result_msg.error_message = ''
        self.publisher_.publish(result_msg)
        self.get_logger().info(f'STT 결과 발행됨: {result_msg.text}')


def main(args=None):
    rclpy.init(args=args)
    node = SttNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()