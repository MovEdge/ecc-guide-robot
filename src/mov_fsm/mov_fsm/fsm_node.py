"""
정순서(성공 경로) 배회 오케스트레이션 — ROADMAP Phase 4-B Step 3의 mov_fsm 1차 구현.

기존에 이미 완성된 mov_ui/mov_stt/mov_dest_resolver 체인은 그대로 서로 토픽을
직접 구독하는 방식을 유지한다(SESSION_LOG.md #7 결정 — 지금 이걸 중앙 허브로
재배선하는 건 범위 밖). mov_fsm은 그 위에 "배달 사이 배회" 행동 하나만
얹는다: 평소엔 landmarks.csv의 랜덤 지점을 하나씩 찍고 다니다가, 사용자가
말하기 버튼을 누르면 즉시 멈추고(PAUSED), 실제 안내가 끝나면(도착/실패/취소
또는 목적지 해석 실패) 다시 배회를 이어간다.

Nav2 goal 소유권: dest_resolver_node와 이 노드가 각자 별도의 navigate_to_pose
ActionClient를 갖는다. 둘이 동시에 goal을 보내는 경쟁을 막기 위해, PAUSED
상태는 "말하기 버튼을 누른 시점"부터 "실제 주행 결과(/navigation/result) 또는
목적지 해석 실패(/dest_resolver/result, success=false)"까지 걸쳐 있어야
한다 — 이 구간 동안 이 노드는 배회 goal을 절대 새로 보내지 않는다(진행 중이던
배회 goal은 즉시 취소). 이렇게 하면 두 ActionClient가 같은 시점에 활성
goal을 두고 경합할 일이 없다.

안전장치: CONFIRMING 화면에서 사용자가 "확인"도 "취소"도 아닌 경로로 빠져나가는
경우처럼(INTERFACES.md 기준 그 경로엔 별도 발행 토픽이 없음) 이 노드가 못 보는
채로 상호작용이 끝날 수 있다 — 이런 놓친 경로에서도 무한정 멈춰있지 않도록
RESUME_TIMEOUT_SEC 뒤엔 무조건 배회를 재개한다.

초기 위치: `nav2_params_waffle_pi.yaml`이 `set_initial_pose: false`라 AMCL은
부팅 직후 (0,0,0) 기본값 기준으로만 서 있다 — 사용자가 RViz "2D Pose Estimate"로
실제 위치를 찍기 전까지는 그 기본값이 실제 로봇 위치와 무관하다. 그 상태에서
배회를 시작하면 엉뚱한 좌표로 이동을 시도하게 되므로, `/initialpose`(RViz가
찍을 때 발행하는 바로 그 토픽)가 최소 한 번 들어오기 전까지는 배회를 시작하지
않는다. 즉 "맨 처음 1회 수동 위치 지정 → 그 이후 자동 배회"가 이 게이트로
보장된다.
"""
import random

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import Empty
from mov_interfaces.msg import DestResult, NavResult

from mov_fsm.landmarks import DEFAULT_LANDMARKS_CSV, load_patrol_points

RESUME_TIMEOUT_SEC = 60.0
NAV2_RETRY_SEC = 5.0


class FsmNode(Node):

    def __init__(self):
        super().__init__('fsm_node')

        self.declare_parameter('landmarks_csv_path', DEFAULT_LANDMARKS_CSV)
        csv_path = self.get_parameter('landmarks_csv_path').value
        self.patrol_points = load_patrol_points(csv_path)
        self.get_logger().info(
            f'배회 지점 {len(self.patrol_points)}개 로드됨 ({csv_path})')

        self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._patrol_goal_handle = None
        self._paused = False
        self._resume_timer = None
        self._initial_pose_set = False

        self.create_subscription(
            Empty, '/stt/start_listening', self.on_user_interaction, 10)
        self.create_subscription(
            DestResult, '/dest_resolver/result', self.on_dest_result, 10)
        self.create_subscription(
            NavResult, '/navigation/result', self.on_navigation_result, 10)
        self.create_subscription(
            PoseWithCovarianceStamped, '/initialpose', self.on_initial_pose, 10)

        self.get_logger().info(
            'FSM Node 준비 완료 — RViz "2D Pose Estimate"로 초기 위치를 '
            '지정하면 배회를 시작함')

    # ---- 초기 위치 게이트 ----

    def on_initial_pose(self, _msg: PoseWithCovarianceStamped):
        if self._initial_pose_set:
            return
        self._initial_pose_set = True
        self.get_logger().info('초기 위치 설정됨 — 배회 시작')
        self._start_patrol_leg()

    # ---- 일시정지/재개 트리거 ----

    def on_user_interaction(self, _msg):
        self.get_logger().info('사용자 상호작용 시작 — 배회 일시정지')
        self._pause()

    def on_dest_result(self, msg: DestResult):
        # success=true는 지금부터 dest_resolver가 실제 주행을 시작한다는 뜻이라
        # /navigation/result가 올 때까지 계속 일시정지 상태를 유지해야 한다.
        if not msg.success:
            self.get_logger().info('목적지 해석 실패 — 배회 재개')
            self._resume()
            return

        # RESUME_TIMEOUT_SEC 안전 타이머는 "상호작용은 시작됐는데 dest_resolver까지
        # 못 가고 끊긴" 경로(CONFIRMING 취소, LISTENING 취소 등 이 노드가 못 보는
        # 경로)를 위한 안전장치였다 — 실제 주행이 시작된 지금부터는 dest_resolver가
        # /navigation/result를 반드시 보내주므로(성공/실패/거부 전부 포함,
        # dest_resolver_node._nav_goal_response_callback/_nav_get_result_callback
        # 참고) 더 이상 필요 없다. 안 끄면 실제 주행이 60초를 넘길 때(건물을
        # 가로지르는 실제 이동에서는 흔함) 이 타이머가 주행 도중에 발화해서
        # 배회 goal을 새로 쏘고, Nav2가 그걸로 진행 중이던 안내 goal을
        # preempt(취소)해버리는 버그가 있었다 — UI에 "주행이 취소됨" 에러로 보임.
        self._cancel_resume_timer()

    def on_navigation_result(self, _msg: NavResult):
        self.get_logger().info('실제 주행 종료 — 배회 재개')
        self._resume()

    def _pause(self):
        self._paused = True
        self._cancel_resume_timer()
        if self._patrol_goal_handle is not None:
            self._patrol_goal_handle.cancel_goal_async()
            self._patrol_goal_handle = None
        self._resume_timer = self.create_timer(
            RESUME_TIMEOUT_SEC, self._on_resume_timeout)

    def _on_resume_timeout(self):
        self.get_logger().info(
            f'{RESUME_TIMEOUT_SEC:.0f}초 동안 상호작용 종료 신호 없음 — '
            '안전장치로 배회 재개')
        self._resume()

    def _resume(self):
        if not self._paused:
            return
        self._paused = False
        self._cancel_resume_timer()
        self._start_patrol_leg()

    def _cancel_resume_timer(self):
        if self._resume_timer is not None:
            self._resume_timer.cancel()
            self._resume_timer = None

    # ---- 배회 ----

    def _start_patrol_leg(self):
        if self._paused or not self._initial_pose_set or not self.patrol_points:
            return

        if not self._nav_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().warn(
                f'Nav2 액션 서버를 찾을 수 없음 — {NAV2_RETRY_SEC:.0f}초 뒤 배회 재시도')
            self._run_once_after(NAV2_RETRY_SEC, self._start_patrol_leg)
            return

        target = random.choice(self.patrol_points)
        self.get_logger().info(f'배회 목표: {target.name} ({target.x}, {target.y})')

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = target.x
        goal.pose.pose.position.y = target.y
        goal.pose.pose.orientation.w = 1.0

        send_goal_future = self._nav_client.send_goal_async(goal)
        send_goal_future.add_done_callback(self._on_patrol_goal_response)

    def _on_patrol_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            if not self._paused:
                # bt_navigator가 아직 lifecycle activate 중이면 액션 서버는
                # 이미 찾아지는데(wait_for_server 통과) goal은 계속 거부되는
                # 구간이 있음 — 지연 없이 바로 재시도하면 그 짧은 구간에 초당
                # 수백 번 goal을 쏘게 됨(실제로 관측됨). 서버 못 찾을 때와
                # 동일하게 백오프를 준다.
                self.get_logger().warn(
                    f'배회 목표가 거부됨 — {NAV2_RETRY_SEC:.0f}초 뒤 재시도')
                self._run_once_after(NAV2_RETRY_SEC, self._start_patrol_leg)
            return
        if self._paused:
            # 목표 전송 후 accept 응답이 오기 전 사이에 일시정지가 걸린 경우 —
            # 이미 Nav2가 수락해버린 이동을 즉시 취소.
            goal_handle.cancel_goal_async()
            return
        self._patrol_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._on_patrol_goal_result)

    def _on_patrol_goal_result(self, future):
        self._patrol_goal_handle = None
        if self._paused:
            # 일시정지 중에 취소돼서 들어온 결과 — 다음 배회는 _resume()이 시작한다.
            return
        status = future.result().status
        if status != GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f'배회 이동 실패/중단(status={status}) — 다음 목표로 계속')
        self._start_patrol_leg()

    def _run_once_after(self, period: float, callback):
        timer_box = {}

        def _fire():
            timer_box['timer'].cancel()
            callback()

        timer_box['timer'] = self.create_timer(period, _fire)


def main(args=None):
    rclpy.init(args=args)
    node = FsmNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
