# mov_fsm

담당: 최 — 전체 담당표는 [../../docs/TEAM.md](../../docs/TEAM.md) 참고

## 역할

배달 사이 로봇을 가만히 세워두지 않고 `landmarks.csv`의 지점들을 랜덤하게 순회(배회)시킨다.
사용자가 말하기 버튼을 누르면 즉시 배회를 멈추고, 실제 안내(도착/실패/취소) 또는 목적지 해석
실패가 끝나면 배회를 재개한다. mov_ui/mov_stt/mov_dest_resolver 사이의 기존 직접 토픽 체인은
건드리지 않고, 그 위에 이 배회 행동만 얹는 방식(중앙 허브로의 재배선은 범위 밖 — SESSION_LOG.md
#7 참고).

## 인터페이스

전체 계약은 [../../docs/INTERFACES.md](../../docs/INTERFACES.md)가 원본. 아래 토픽은 전부
기존에 다른 패키지가 이미 발행하던 것을 구독만 한다 — 새로 추가한 토픽 없음.

| 방향 | 이름 | 타입 | 비고 |
|---|---|---|---|
| sub | `/stt/start_listening` | `std_msgs/Empty` | 사용자가 말하기 버튼을 누른 시점 — 배회 즉시 일시정지 |
| sub | `/dest_resolver/result` | `mov_interfaces/DestResult` | `success=false`면 목적지 해석 실패 — 배회 재개 |
| sub | `/navigation/result` | `mov_interfaces/NavResult` | 실제 주행 종료(성공/실패/취소) — 배회 재개 |
| sub | `/initialpose` | `geometry_msgs/PoseWithCovarianceStamped` | RViz "2D Pose Estimate"가 발행. 최초 1회 들어오기 전까지는 배회를 시작하지 않음(AMCL 기본값(0,0,0) 기준으로 배회 goal을 잘못 보내는 것 방지) |
| — | `navigate_to_pose` (action) | `nav2_msgs/NavigateToPose` | 배회 목표 전송용 ActionClient. `mov_dest_resolver`도 별도 ActionClient로 같은 액션을 쓰지만, PAUSED 구간이 상호작용 시작부터 실제 결과까지 걸쳐 있어서 두 노드가 동시에 활성 goal을 갖는 경합은 없음 |

## 실행/테스트 방법

```bash
colcon build --packages-select mov_fsm --symlink-install
ros2 run mov_fsm fsm_node
# Nav2가 떠 있으면 배회 시작 로그 확인, /stt/start_listening을 수동 발행해 일시정지 확인:
ros2 topic pub -1 /stt/start_listening std_msgs/msg/Empty "{}"
```

## 현재 상태 / TODO

- [x] ROADMAP Phase 4-B Step 3 1차 구현(2026-09-01) — 정순서 배회/일시정지/재개만. cancel/retry의
      더 세밀한 분기(예: 배회 중 Nav2 자체 장애 재시도 백오프)는 나중 확장
- [x] 안전장치 타임아웃(`RESUME_TIMEOUT_SEC=60`) — CONFIRMING 화면 취소처럼 이 노드가 못 보는
      경로로 상호작용이 끝나도 무한정 멈춰있지 않도록
- [x] **버그 수정(2026-09-02, 배가 실기 테스트 중 발견)** — 위 안전 타이머가 `on_dest_result`
      성공 케이스에서 취소/연장되지 않고 그대로 방치돼 있었음. 그래서 "말하기→STT→확인→목적지
      해석→실제 주행"까지 총 60초를 넘기면(실제 이동 거리가 있으면 흔함) 타이머가 **실주행
      도중**에 발화해서 `_resume()`이 배회 goal을 새로 쏘고, Nav2가 그걸로 진행 중이던 안내
      goal을 preempt(취소)해버려 UI에 "주행이 취소됨" 에러 화면이 뜨는 버그로 이어짐.
      `on_dest_result(success=True)`에서 `_cancel_resume_timer()`를 호출하도록 고쳐서, 실제
      주행이 시작된 뒤엔 안전 타이머 대신 `/navigation/result`(dest_resolver가 성공/실패/거부
      모든 경우에 반드시 발행)로만 재개 판단하게 함. **mov_fsm은 최 담당이라 리뷰 필요 —
      아직 커밋 전.**
- [ ] 실기에서 배회 동작 자체는 아직 미검증 (Nav2 풀스택이 막 붙은 상태 — `launch/full_system.launch.py` 참고)
- [ ] 배회 중 UI에 "지금 순찰 중"임을 보여줄지는 아직 미정 — 지금은 UI에 아무것도 알리지 않음(요청 시 확장)
