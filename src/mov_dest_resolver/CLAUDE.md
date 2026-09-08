# mov_dest_resolver

담당: 배 — 전체 담당표는 [../../docs/TEAM.md](../../docs/TEAM.md) 참고

## 역할

`/stt/result`로 들어오는 발화 텍스트를 Gemini API로 분류해, ECC 랜드마크 DB
(`mov_slam` 패키지의 `landmarks.csv`, `get_package_share_directory('mov_slam')`로 참조 —
2026-09-03 이전엔 `/workspace/slam/slam_frommap/out3/landmarks.csv` 절대경로였음)에 있는
특정 장소인지 판단하고
좌표를 찾는다. LLM은 좌표를 직접 내지 않고 `target_type`/`place_name`/`category`만
구조화해서 뽑으며, 실제 좌표 매칭은 `resolver_core.py`의 결정론적 코드가 담당한다
(설계 배경: [../../docs/SESSION_LOG.md](../../docs/SESSION_LOG.md) #5).

## 인터페이스

전체 계약은 [../../docs/INTERFACES.md](../../docs/INTERFACES.md)가 원본(draft, 팀 리뷰 전).

| 방향 | 이름 | 타입 | 비고 |
|---|---|---|---|
| sub | `/stt/confirmed` | `mov_interfaces/SttResult` | `/stt/result`가 아니라 이 토픽을 구독함 — UI에서 사용자가 "확인" 눌러야 발행됨. `success=false`면 무시 |
| pub | `/dest_resolver/result` | `mov_interfaces/DestResult` | 좌표 미포함(success/place_name/error_message만) |
| pub | `/navigation/result` | `mov_interfaces/NavResult` | Nav2 goal 완료(도착/실패/취소) 결과를 UI로 알림 |
| sub | `/navigation/cancel` | `std_msgs/Empty` | UI의 취소 버튼 → 진행 중인 Nav2 goal 취소 |
| pub | `/dest_resolver/choices` | `mov_interfaces/DestChoices` | category 후보가 2개 이상일 때만 발행 |
| sub | `/dest_resolver/choice_selected` | `std_msgs/String` | UI에서 사용자가 탭한 장소명(`data`) — 이걸로 최종 확정 + Nav2 goal 전송 |
| sub | `/amcl_pose` | `geometry_msgs/PoseWithCovarianceStamped` | 로봇 현재 위치(2026-09-01 추가) — `wants_nearest` 최근접 계산에 씀 |
| pub | `/navigation/distance_remaining` | `std_msgs/Float32` | Nav2 `NavigateToPose` 피드백의 `distance_remaining`을 그대로 중계(2026-09-02 추가) — UI의 "N.Nm 남음" 표시용 |

## 실행/테스트 방법

```bash
# ROS2 없이 resolver_core 로직만 (DB 로딩은 키 없이도 실행됨)
cd src/mov_dest_resolver && python3 -m pytest test/test_resolver_core.py -v -p no:anyio

# ROS2 노드로 (GEMINI_API_KEY가 .env에 있어야 함)
colcon build --packages-select mov_interfaces mov_dest_resolver --symlink-install
ros2 run mov_dest_resolver dest_resolver_node
ros2 topic pub /stt/result mov_interfaces/msg/SttResult "{success: true, text: '스타벅스 어디야'}"
ros2 topic echo /dest_resolver/result
```

## 현재 상태 / TODO

- [x] ROADMAP Phase 4-A Step 2 (좌표 DB) — `landmarks.csv`(36개, 실측)를 직접 읽음, 새로 안 만듦
- [x] ROADMAP Phase 4-A Step 3 (LLM 프롬프트/매칭) — `named_place` 매칭 구현. `category`는
      인식은 하지만 아직 "미지원"으로만 응답 (최근접 계산 없음)
- [x] `GEMINI_API_KEY`로 실제 API 호출 검증 완료 (2026-08-29) — pytest 4개 + 실제 ROS2
      토픽(`/stt/result` → `/dest_resolver/result`) end-to-end 확인. 과정에서 버그 2개 발견/수정:
      (1) `response_schema` enum에 빈 문자열 사용 시 Gemini가 400 에러 → 전부 "NONE" 센티널로 교체,
      (2) 모델명 `gemini-2.5-flash`가 신규 사용자에게 제공 중단됨 → 최신 모델로 교체
- [x] 모델 선택: 플래그십 `gemini-3.6-flash`(평균 5.1초/건)는 음성 인터랙션에 너무 느려서
      `gemini-3.5-flash-lite`(평균 0.94초/건, 정확도 손실 없음)로 확정. `latest` 별칭 대신
      특정 버전 고정(재현성)
- [x] ROADMAP Phase 4-A Step 4(2026-08-30, 설계 변경) — `landmarks.csv`에 `category` 컬럼
      추가(36개 전부 채움), `place_name`과 동일한 패턴으로 `category`도 Gemini
      response_schema enum으로 제약(할루시네이션 방지). **최근접 자동 계산 대신, 후보가
      1개면 바로 확정하고 2개 이상이면 전부 사용자에게 보여주고 직접 고르게 하는 방식으로
      확정**("카페 가고 싶어"에 로봇이 임의로 하나를 고르면 "스타벅스 말고 다른 카페" 같은
      제외/선호가 섞인 발화에서 틀리기 쉬움 — 사람이 고르는 게 확실함). `ResolveResult`에
      `needs_choice`/`candidates` 필드 추가. 위치 정보가 필요 없어져서 `resolve()`의
      `current_x`/`current_y` 파라미터는 제거함. `/dest_resolver/choices`(신규
      `DestChoices.msg`)로 후보를 UI에 보내고, UI가 탭한 장소명을
      `/dest_resolver/choice_selected`(신규, `std_msgs/String`)로 돌려주면 그걸로 최종
      확정 + Nav2 goal 전송. 실제 API로 "화장실 가고 싶어"(5개 후보) / "헬스장 가고
      싶어"(1개뿐, 바로 확정) 둘 다 테스트 통과 확인
- [x] "제일/가장 가까운 X" 대응(2026-08-30) — `wants_nearest` boolean을 스키마에 추가해
      LLM이 명시적 최근접 요청인지 구분하게 함. `resolve()`에 `current_x`/`current_y`를
      선택 인자로 재도입(기본 None) — `_find_nearest_in_category()`도 부활. 후보가
      여럿이고 `wants_nearest=True`이면서 위치도 주어졌을 때만 최근접 하나로 바로 확정,
      그 외(최근접 미요청 또는 위치 없음)엔 기존처럼 후보 나열. 4가지 조합(단일후보/최근접+
      위치있음/최근접+위치없음/최근접미요청+위치있음) 전부 실제 API 테스트로 검증 완료
- [x] **위치 소스 연결(2026-09-01, 최가 작업)** — `dest_resolver_node.py`가 `/amcl_pose`를
      구독해 로봇 현재 위치를 들고 있다가 `resolve()` 호출 시 넘겨주도록 고침. 실기에
      Nav2(AMCL)가 붙은 뒤에야 가능해진 변경. 이제 "제일 가까운 화장실/엘리베이터" 같은
      발화가 실제로 최근접 계산으로 이어짐(`landmarks.csv` 기준 화장실 5개, 엘리베이터 7개
      후보 존재 확인). AMCL이 아직 위치를 못 잡은 시점(초기 pose 미설정)엔 `/amcl_pose`가
      한 번도 안 와서 `current_x/y`가 `None`으로 남고, 그럴 땐 기존처럼 후보 나열로 안전하게
      대체됨 — 코드 변경 없이 의도대로 동작. **아직 곽/배 리뷰 전 — mov_dest_resolver는 배
      담당이라 PR 전에 알릴 것 (TEAM.md 규칙)**
- [x] **남은 거리 피드백 중계(2026-09-02, 최가 작업)** — `send_goal_async`에
      `feedback_callback` 추가해서 `NavigateToPose` 액션 피드백의 `distance_remaining`을
      `/navigation/distance_remaining`(신규)으로 그대로 발행. UI의 `navigating_page.py`가
      이미 갖고 있던 `set_remaining()`에 연결(곽이 미리 만들어둔 위젯, 실데이터만 없었음).
      마찬가지로 배 리뷰 전.
- [x] Nav2 Action Client 연동 — `dest_resolver_node.py`에 `ActionClient(NavigateToPose)` 추가,
      `resolve()` 성공 시 x/y로 `map` 프레임 목표 전송 (`send_goal_async` →
      `goal_response_callback` → `get_result_callback` 콜백 체인). yaw는 랜드마크 DB에
      없어 단위 쿼터니언(정면) 고정. Nav2 풀스택(planner/controller/bt_navigator)이 아직
      어디에도 안 떠 있어(localization만 검증됨, `docs/GAZEBO.md` 참고) `navigate_to_pose`
      액션 서버 자체가 없는 상태 — `wait_for_server` 타임아웃으로 실패하는 게 현재 정상 동작.
      실제 Nav2 붙여서 하는 end-to-end 검증은 Nav2 풀스택이 뜬 뒤로 보류 (다음 작업)
- [x] UI 연동(2026-08-30) — 예전엔 `/stt/result`에 바로 반응해서 UI의 "확인" 절차를 건너뛰고
      있었음. `/stt/confirmed` 구독으로 바꿔서 UI가 확인을 눌러야만 동작하게 고침. Nav2 결과를
      `/navigation/result`(`NavResult.msg`, 신규)로 UI에 돌려주고, `/navigation/cancel`
      구독으로 진행 중인 goal 취소도 지원 (`goal_handle.cancel_goal_async()`). Nav2 서버가
      없는 지금은 취소할 goal 자체가 없어 실동작 검증은 Nav2 풀스택 이후로 보류
- [x] **화장실/엘리베이터 자동 최근접(2026-09-02)** — 사용자 요청으로, 이 두 카테고리는
      "제일/가장 가까운"이라는 명시적 wants_nearest 표현이 없어도 위치만 있으면 후보를
      나열하지 않고 바로 최근접으로 확정하도록 `resolve()`를 바꿈
      (`AUTO_NEAREST_CATEGORIES = {'화장실', '엘리베이터'}`). 카페/식당처럼 브랜드/선호가
      있을 수 있는 카테고리는 그대로 나열(기존 동작 유지, 회귀 테스트로 확인). `DestResult.msg`에
      `category`(신규) 필드를 추가해, 자동 확정된 경우에만 채워서 `mov_ui`가 TTS 문구를
      "동1 화장실로" 대신 "가까운 화장실로"처럼 일반화해 말하게 함(방향+번호 붙은 이름을
      그대로 읽으면 부자연스러움). `mov_ui/ui_node.py`의 `on_dest_result`도 같이 고침(화면
      표시는 여전히 구체적 place_name). `test_resolver_core.py`에 회귀 테스트 추가/갱신,
      14개 전부 통과 확인. **`mov_interfaces` 변경이라 곽/최 리뷰 필요 — 아직 커밋 전**
- [ ] `docs/INTERFACES.md`/`mov_interfaces` 변경사항 곽/최 리뷰 후 커밋
