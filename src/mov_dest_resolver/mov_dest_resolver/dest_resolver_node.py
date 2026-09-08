import os

from dotenv import load_dotenv
from google import genai

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import Empty, Float32, String
from mov_interfaces.msg import DestChoices, DestResult, NavResult, SttResult

from mov_dest_resolver.resolver_core import (
    DEFAULT_LANDMARKS_CSV, load_landmarks, resolve,
)


class DestResolverNode(Node):

    def __init__(self):
        super().__init__('dest_resolver_node')
        load_dotenv()

        self.declare_parameter('landmarks_csv_path', DEFAULT_LANDMARKS_CSV)
        csv_path = self.get_parameter('landmarks_csv_path').value

        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            self.get_logger().error(
                'GEMINI_API_KEY가 설정되지 않음 — .env 파일을 확인하세요')
            raise RuntimeError(
                'GEMINI_API_KEY 미설정: dest_resolver_node를 실행하려면 '
                '.env에 GEMINI_API_KEY를 설정해야 함')
        self.client = genai.Client(api_key=api_key)

        self.landmarks = load_landmarks(csv_path)
        self.get_logger().info(f'랜드마크 {len(self.landmarks)}개 로드됨 ({csv_path})')

        # /stt/result가 아니라 /stt/confirmed를 구독한다 — CONFIRMING 화면에서
        # 사용자가 "확인"을 눌러야만 목적지 해석/주행이 시작되도록 하기 위함
        # (예전엔 STT 결과가 오는 즉시 자동 실행돼서 UI 확인 절차를 건너뛰었음).
        self.subscription = self.create_subscription(
            SttResult, '/stt/confirmed', self.stt_confirmed_callback, 10)
        self.publisher_ = self.create_publisher(DestResult, '/dest_resolver/result', 10)
        self.nav_result_publisher_ = self.create_publisher(NavResult, '/navigation/result', 10)
        self.nav_distance_publisher_ = self.create_publisher(
            Float32, '/navigation/distance_remaining', 10)
        self.choices_publisher_ = self.create_publisher(
            DestChoices, '/dest_resolver/choices', 10)
        self.create_subscription(
            Empty, '/navigation/cancel', self.cancel_callback, 10)
        # 카테고리 후보가 여럿이라 /dest_resolver/choices로 물어봤을 때,
        # 사용자가 화면에서 하나를 탭하면 그 장소명이 여기로 옴.
        self.create_subscription(
            String, '/dest_resolver/choice_selected', self.choice_selected_callback, 10)

        # "제일/가장 가까운 화장실" 같은 wants_nearest 요청을 실제로 계산하려면
        # 로봇의 현재 위치가 필요함 — resolver_core.resolve()는 이미 이 파라미터를
        # 받게 설계돼 있었지만(2026-08-30), 그동안 위치 소스가 없어서 항상 None으로
        # 호출해 후보 나열로만 귀결됐음. Nav2(AMCL)가 실기에서 붙었으니 /amcl_pose를
        # 구독해서 최신 위치를 들고 있다가 resolve() 호출 시 넘겨준다.
        self._current_x = None
        self._current_y = None
        self.create_subscription(
            PoseWithCovarianceStamped, '/amcl_pose', self.amcl_pose_callback, 10)

        # 좌표(x/y)는 이 노드 안에서만 쓰고 밖으로 내지 않는다 — INTERFACES.md 계약상
        # DestResult에는 좌표를 담지 않으므로, Nav2 목표 전달은 액션 클라이언트로 직접 처리.
        self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        # 취소 요청을 받으려면 현재 진행 중인 goal handle을 들고 있어야 함.
        self._current_goal_handle = None

        self.get_logger().info('Dest Resolver Node 준비 완료')

    def amcl_pose_callback(self, msg: PoseWithCovarianceStamped):
        self._current_x = msg.pose.pose.position.x
        self._current_y = msg.pose.pose.position.y

    def stt_confirmed_callback(self, msg):
        if not msg.success:
            return

        self.get_logger().info(f'목적지 해석 시작(사용자 확인됨): "{msg.text}"')
        result = resolve(
            msg.text, self.landmarks, self.client,
            current_x=self._current_x, current_y=self._current_y)

        if result.needs_choice:
            self.get_logger().info(
                f'"{result.category}" 후보 {len(result.candidates)}개 — 사용자 선택 대기')
            choices_msg = DestChoices()
            choices_msg.category = result.category or ''
            choices_msg.place_names = result.candidates
            self.choices_publisher_.publish(choices_msg)
            return

        dest_msg = DestResult()
        dest_msg.success = result.success
        dest_msg.place_name = result.place_name or ''
        dest_msg.error_message = result.error_message
        dest_msg.category = result.auto_resolved_category or ''
        self.publisher_.publish(dest_msg)

        if not result.success:
            self.get_logger().warn(
                f'미해결 [{result.target_type}]: {result.error_message} '
                f'(발화: "{msg.text}")')
            return

        self.get_logger().info(
            f'매칭됨: {result.place_name} ({result.x}, {result.y})')
        self._send_nav_goal(result.place_name, result.x, result.y)

    def choice_selected_callback(self, msg: String):
        place_name = msg.data
        match = next((lm for lm in self.landmarks if lm.name == place_name), None)

        dest_msg = DestResult()
        if match is None:
            self.get_logger().error(f'선택된 장소가 DB에 없음: {place_name!r}')
            dest_msg.success = False
            dest_msg.place_name = ''
            dest_msg.error_message = f'선택한 장소를 찾을 수 없음: {place_name}'
            self.publisher_.publish(dest_msg)
            return

        self.get_logger().info(f'사용자가 선택함: {match.name}')
        dest_msg.success = True
        dest_msg.place_name = match.name
        dest_msg.error_message = ''
        self.publisher_.publish(dest_msg)
        self._send_nav_goal(match.name, match.x, match.y)

    def _send_nav_goal(self, place_name: str, x: float, y: float):
        # wait_for_server는 스핀 없이 자체 폴링으로 동작하므로 구독 콜백 안에서
        # 블로킹 호출해도 안전함(Nav2 BasicNavigator도 같은 패턴 사용).
        if not self._nav_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error(
                f'Nav2 액션 서버(navigate_to_pose)를 찾을 수 없음 — "{place_name}" 이동 취소')
            return

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y
        # landmarks.csv의 yaw는 전부 0(RViz Publish Point가 방향을 안 찍음) —
        # resolver_core.load_landmarks가 애초에 yaw를 안 읽으므로 기본 방향(단위 쿼터니언) 사용.
        goal.pose.pose.orientation.w = 1.0

        self.get_logger().info(f'Nav2로 목표 전송: {place_name} ({x}, {y})')
        send_goal_future = self._nav_client.send_goal_async(
            goal, feedback_callback=self._nav_feedback_callback)
        send_goal_future.add_done_callback(
            lambda future: self._nav_goal_response_callback(future, place_name))

    def _nav_feedback_callback(self, feedback_msg):
        # NavigateToPose 액션 피드백(controller_frequency=10Hz 정도로 옴)의
        # distance_remaining(float32, meter)을 그대로 UI로 흘려보낸다 —
        # 좌표 원본은 여기서만 쓰고 밖으로 안 내는 규칙(DestResult처럼)과 달리,
        # 남은 거리는 좌표가 아니라 스칼라값이라 그대로 내보내도 무방함.
        distance = feedback_msg.feedback.distance_remaining
        self.nav_distance_publisher_.publish(Float32(data=distance))

    def _nav_goal_response_callback(self, future, place_name: str):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error(f'Nav2가 목표를 거부함: {place_name}')
            self._publish_nav_result(False, place_name, '주행 목표가 거부됨')
            return

        self.get_logger().info(f'Nav2가 목표를 수락함: {place_name}')
        self._current_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda future: self._nav_get_result_callback(future, place_name))

    def _nav_get_result_callback(self, future, place_name: str):
        self._current_goal_handle = None
        status = future.result().status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f'목적지 도착: {place_name}')
            self._publish_nav_result(True, place_name, '')
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().info(f'주행 취소됨: {place_name}')
            self._publish_nav_result(False, place_name, '주행이 취소됨')
        else:
            self.get_logger().warn(f'주행 실패/중단 [{place_name}]: status={status}')
            self._publish_nav_result(False, place_name, f'주행 실패 (status={status})')

    def _publish_nav_result(self, success: bool, place_name: str, error_message: str):
        msg = NavResult()
        msg.success = success
        msg.place_name = place_name
        msg.error_message = error_message
        self.nav_result_publisher_.publish(msg)

    def cancel_callback(self, _msg):
        if self._current_goal_handle is None:
            self.get_logger().info('취소 요청을 받았으나 진행 중인 목표가 없음')
            return

        self.get_logger().info('진행 중인 Nav2 목표 취소 요청')
        self._current_goal_handle.cancel_goal_async()


def main(args=None):
    rclpy.init(args=args)
    node = DestResolverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
