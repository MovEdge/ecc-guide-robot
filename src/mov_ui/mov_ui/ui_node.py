import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty
from mov_interfaces.msg import SttResult
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from mov_ui.main_window import MainWindow


class UiNode(Node):
    """터치스크린 UI ROS2 노드.

    아직 mov_fsm이 없어서, 상태 전이 판단(어떤 이벤트가 오면 어느 화면으로
    넘어갈지)을 이 노드가 임시로 담당한다. mov_fsm이 생기면 이 판단 로직은
    거기로 옮기고, 여기는 상태 토픽 구독 → set_state() 호출만 남기면 된다.
    """

    def __init__(self, window: MainWindow):
        super().__init__('ui_node')
        self.window = window

        self.stt_trigger_pub = self.create_publisher(
            Empty, '/stt/start_listening', 10)
        self.create_subscription(
            SttResult, '/stt/result', self.on_stt_result, 10)

    def on_speak_clicked(self):
        self.stt_trigger_pub.publish(Empty())
        self.get_logger().info('STT 트리거 발행, LISTENING으로 전환')
        self.window.set_state('LISTENING')

    def on_stt_result(self, msg: SttResult):
        if msg.success:
            self.window.confirming_page.set_text(msg.text)
            self.window.set_state('CONFIRMING')
        else:
            self.window.error_page.set_message(msg.error_message)
            self.window.set_state('ERROR')

    def on_confirm_clicked(self):
        # TODO: mov_dest_resolver 연동 전까지는 자리만. 확정되면 목적지 요청 발행.
        self.get_logger().info('확인 클릭 (목적지 해석 연동 전)')

    def on_retry_clicked(self):
        self.window.set_state('IDLE')

    def on_cancel_clicked(self):
        # TODO: Nav2 취소 액션 연동 전까지는 자리만.
        self.window.set_state('IDLE')

    def on_new_destination_clicked(self):
        self.window.set_state('IDLE')

    def on_home_clicked(self):
        self.window.set_state('IDLE')


def main(args=None):
    rclpy.init(args=args)

    app = QApplication(sys.argv)

    node_holder = {}
    callbacks = {
        'on_speak_clicked': lambda: node_holder['node'].on_speak_clicked(),
        'on_confirm_clicked': lambda: node_holder['node'].on_confirm_clicked(),
        'on_retry_clicked': lambda: node_holder['node'].on_retry_clicked(),
        'on_cancel_clicked': lambda: node_holder['node'].on_cancel_clicked(),
        'on_new_destination_clicked': lambda: node_holder['node'].on_new_destination_clicked(),
        'on_home_clicked': lambda: node_holder['node'].on_home_clicked(),
    }

    window = MainWindow(callbacks)
    node = UiNode(window)
    node_holder['node'] = node

    # Qt 메인루프 안에서 주기적으로 rclpy를 폴링해서, 별도 스레드 없이
    # 위젯은 항상 메인 스레드에서만 건드리게 한다.
    spin_timer = QTimer()
    spin_timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0))
    spin_timer.start(50)

    window.show()
    exit_code = app.exec_()

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
