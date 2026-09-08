import sys
import traceback

import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty, Float32, String
from mov_interfaces.msg import DestChoices, DestResult, NavResult, SttResult
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from mov_ui.main_window import MainWindow
from mov_ui.styles import STYLESHEET
from mov_ui.i18n import i18n, localize_category, localize_place_name


def _destination_particle(place_name: str) -> str:
    """place_name 뒤에 붙일 조사('로'/'으로')를 마지막 한글 음절의 받침
    유무로 고른다 — 받침이 없거나 받침이 'ㄹ'이면 '로', 그 외엔 '으로'.
    "아트하우스 모모 (영화관)"처럼 끝에 괄호/공백이 붙는 이름도 있어서,
    끝에서부터 거슬러 올라가며 실제 마지막 한글 음절을 찾는다. 한글 음절이
    하나도 없는 이름(숫자/영문뿐)이면 '으로'로 기본 처리.
    """
    for ch in reversed(place_name):
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            jongseong = (code - 0xAC00) % 28
            return '로' if jongseong in (0, 8) else '으로'
    return '으로'


def _build_navigating_speech(place_name: str, category: str) -> str:
    """주행 시작 안내 음성 문구를 현재 UI 언어(i18n.lang)에 맞게 만든다.

    category가 채워져 있으면(화장실/엘리베이터처럼 사용자에게 안 물어보고
    최근접으로 자동 확정된 경우, resolver_core.AUTO_NEAREST_CATEGORIES 참고)
    place_name 대신 카테고리명으로 일반화해서 말한다 — 방향+번호가 붙은 이름
    ("동1 화장실")을 그대로 읽으면 부자연스럽기 때문. 한국어는 조사(로/으로)가
    필요해서 _destination_particle로 고르고, 영어는 그런 문법 요소가 없어
    자연스러운 문장 하나로 만든다. 화면 표시(localize_place_name/category)와
    같은 로컬라이즈 함수를 써서, 화면에 뜨는 이름/카테고리와 음성이 말하는
    이름/카테고리가 서로 어긋나지 않게 한다.
    """
    if i18n.lang == 'en':
        spoken_name = (
            localize_category(category) if category else localize_place_name(place_name))
        prefix = 'the nearest ' if category else ''
        return f'Starting navigation to {prefix}{spoken_name}.'

    spoken_name = category or localize_place_name(place_name)
    particle = _destination_particle(spoken_name)
    prefix = '가까운 ' if category else ''
    return f'{prefix}{spoken_name}{particle} 안내를 시작합니다'


def _build_arrived_speech() -> str:
    return 'You have arrived.' if i18n.lang == 'en' else '도착했습니다'


class UiNode(Node):
    """터치스크린 UI ROS2 노드.

    아직 mov_fsm이 없어서, 상태 전이 판단(어떤 이벤트가 오면 어느 화면으로
    넘어갈지)을 이 노드가 임시로 담당한다. mov_fsm이 생기면 이 판단 로직은
    거기로 옮기고, 여기는 상태 토픽 구독 → set_state() 호출만 남기면 된다.
    """

    def __init__(self, window: MainWindow):
        super().__init__('ui_node')
        self.window = window
        # CONFIRMING에서 "확인"을 누르면 이 값을 그대로 /stt/confirmed로 재발행한다
        # (STT가 이미 뽑아준 텍스트를 다시 인식할 필요는 없으므로 들고만 있는다).
        self._pending_stt_result = None
        # LISTENING 화면에서 취소를 누르면 IDLE로 돌아가지만, mov_stt는 취소를 받는
        # 토픽이 아직 없어서(INTERFACES.md 미정의) 마이크는 계속 듣고 있다가 뒤늦게
        # /stt/result를 보내올 수 있다. 그때 그냥 처리해버리면 사용자가 이미 IDLE로
        # 나갔는데 갑자기 CONFIRMING/ERROR로 튕기는 문제가 생겨서, 취소 이후 도착하는
        # 결과 하나는 무시하도록 플래그로 막는다 — on_speak_clicked에서 다시 리스닝을
        # 시작할 때 해제.
        self._listening_cancelled = False
        # /navigation/distance_remaining은 "남은 거리"만 주고 총 거리는 안 줘서,
        # 퍼센티지로 보여주려면 총 거리를 직접 추정해야 한다 — 이번 주행에서 지금까지
        # 받은 distance_remaining 중 최댓값을 "총 거리"로 삼는다(첫 피드백이 보통
        # 최댓값이지만, 리플래닝으로 잠깐 늘어날 수도 있어 max로 갱신). 목적지가
        # 새로 정해질 때(on_dest_result) None으로 리셋.
        self._nav_total_distance = None

        self.stt_trigger_pub = self.create_publisher(
            Empty, '/stt/start_listening', 10)
        self.stt_confirmed_pub = self.create_publisher(
            SttResult, '/stt/confirmed', 10)
        self.nav_cancel_pub = self.create_publisher(
            Empty, '/navigation/cancel', 10)
        self.choice_selected_pub = self.create_publisher(
            String, '/dest_resolver/choice_selected', 10)
        self.tts_pub = self.create_publisher(String, '/tts/speak', 10)
        self.create_subscription(
            Empty, '/stt/listening_started', self.on_listening_started, 10)
        self.create_subscription(
            SttResult, '/stt/result', self.on_stt_result, 10)
        self.create_subscription(
            DestResult, '/dest_resolver/result', self.on_dest_result, 10)
        self.create_subscription(
            NavResult, '/navigation/result', self.on_nav_result, 10)
        self.create_subscription(
            DestChoices, '/dest_resolver/choices', self.on_dest_choices, 10)
        self.create_subscription(
            Float32, '/navigation/distance_remaining', self.on_distance_remaining, 10)

    def on_speak_clicked(self):
        self._listening_cancelled = False
        self.stt_trigger_pub.publish(Empty())
        self.get_logger().info('STT 트리거 발행, 마이크 준비 대기')
        # LISTENING 전환은 여기서 바로 하지 않고 /stt/listening_started(마이크가
        # 실제로 열린 시점)를 받은 뒤에 한다 — 안 그러면 마이크 열리기 전에도
        # "듣고 있어요" 화면부터 먼저 뜨는 문제가 있었음.

    def on_listening_started(self, _msg):
        self.window.set_state('LISTENING')

    def on_listening_cancel_clicked(self):
        self._listening_cancelled = True
        self.get_logger().info('LISTENING 취소 — IDLE로 복귀')
        self.window.set_state('IDLE')

    def on_stt_result(self, msg: SttResult):
        if self._listening_cancelled:
            self._listening_cancelled = False
            self.get_logger().info('취소 이후 도착한 STT 결과 — 무시')
            return
        if msg.success:
            self._pending_stt_result = msg
            self.window.confirming_page.set_text(msg.text)
            self.window.set_state('CONFIRMING')
        else:
            self.window.error_page.set_message(msg.error_message)
            self.window.set_state('ERROR')

    def on_confirm_clicked(self):
        if self._pending_stt_result is None:
            self.get_logger().warn('확인할 STT 결과가 없음 — 무시')
            return
        self.stt_confirmed_pub.publish(self._pending_stt_result)
        self.get_logger().info('목적지 해석 요청 발행 (dest_resolver 응답 대기)')
        # dest_resolver 응답(성공→NAVIGATING/실패→ERROR)이 올 때까지는
        # 화면을 그대로 CONFIRMING에 둔다 — 별도 "처리 중" 화면은 아직 없음.

    def on_dest_result(self, msg: DestResult):
        if msg.success:
            self._nav_total_distance = None
            # 화면은 항상 실제 도착지(예: "동1 화장실")를 보여준다 — 어디로
            # 가는지 구체적으로 아는 게 화면에서는 유용하다.
            self.window.navigating_page.set_destination(msg.place_name)
            self.window.set_state('NAVIGATING')
            speech = _build_navigating_speech(msg.place_name, msg.category)
            self.tts_pub.publish(String(data=speech))
        else:
            self.window.error_page.set_message(msg.error_message)
            self.window.set_state('ERROR')

    def on_dest_choices(self, msg: DestChoices):
        self.window.choosing_page.set_choices(msg.category, list(msg.place_names))
        self.window.set_state('CHOOSING')

    def on_choice_clicked(self, place_name: str):
        choice_msg = String()
        choice_msg.data = place_name
        self.choice_selected_pub.publish(choice_msg)
        self.get_logger().info(f'후보 선택함: {place_name} (dest_resolver 응답 대기)')
        # dest_resolver의 /dest_resolver/result 응답이 올 때까지 화면은 그대로 둔다
        # (on_confirm_clicked과 동일한 패턴 — 별도 "처리 중" 화면 없음).

    def on_distance_remaining(self, msg: Float32):
        remaining = msg.data
        if self._nav_total_distance is None or remaining > self._nav_total_distance:
            self._nav_total_distance = remaining

        if self._nav_total_distance and self._nav_total_distance > 0:
            percent = max(0.0, min(100.0, (1 - remaining / self._nav_total_distance) * 100))
        else:
            percent = 100.0

        self.window.navigating_page.set_remaining(f'{percent:.0f}%')
        self.window.navigating_page.set_progress_percent(percent)

    def on_nav_result(self, msg: NavResult):
        if msg.success:
            self.window.set_state('ARRIVED')
            self.tts_pub.publish(String(data=_build_arrived_speech()))
        else:
            self.window.error_page.set_message(msg.error_message)
            self.window.set_state('ERROR')

    def on_retry_clicked(self):
        self._pending_stt_result = None
        self.window.set_state('IDLE')

    def on_cancel_clicked(self):
        self.nav_cancel_pub.publish(Empty())
        self.get_logger().info('주행 취소 요청 발행')
        self.window.set_state('IDLE')

    def on_new_destination_clicked(self):
        self.window.set_state('IDLE')

    def on_home_clicked(self):
        self.window.set_state('IDLE')


def _log_uncaught_exception(exc_type, exc_value, exc_tb):
    # PyQt5(5.5+)는 슬롯(여기선 QTimer→rclpy.spin_once로 실행되는 ROS
    # 콜백 전부 포함) 안에서 처리 안 된 예외가 나오면 기본적으로 프로세스
    # 전체를 abort(SIGABRT, exit code -6)시킨다 — sys.excepthook을 직접
    # 설정해서 "로그만 남기고 계속 실행"으로 바꾼다. 실기 테스트 중(2026-09-03)
    # 사소한 예외 하나로 UI 전체가 죽어서 화면이 완전히 먹통되는 문제를
    # 겪어서 추가함 — 원인이 된 예외 자체를 고치는 것과 별개로, 예외가
    # 나도 UI가 죽지 않는 게 키오스크 화면엔 최소한의 안전장치.
    traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stderr)


def main(args=None):
    sys.excepthook = _log_uncaught_exception
    rclpy.init(args=args)

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    node_holder = {}
    callbacks = {
        'on_speak_clicked': lambda: node_holder['node'].on_speak_clicked(),
        'on_confirm_clicked': lambda: node_holder['node'].on_confirm_clicked(),
        'on_retry_clicked': lambda: node_holder['node'].on_retry_clicked(),
        'on_choice_clicked': lambda place_name: node_holder['node'].on_choice_clicked(place_name),
        'on_listening_cancel_clicked': lambda: node_holder['node'].on_listening_cancel_clicked(),
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

    window.showFullScreen()
    exit_code = app.exec_()

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
