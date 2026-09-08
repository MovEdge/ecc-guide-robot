# Interfaces (계약 문서)

이 문서는 노드 간 통신 계약이다. 여기 정의된 토픽/서비스/액션/FSM 상태는 모든 팀원이 스텁(가짜 입출력)과 실구현 모두에서 동일하게 따라야 한다.

**변경 규칙**: 이 문서를 수정하는 PR은 [GIT_WORKFLOW.md](GIT_WORKFLOW.md)에 따라 나머지 2인 모두의 승인이 필요하다. 변경 전 다른 팀원에게 먼저 알릴 것.

> Phase 0(규칙설계) 진행 중 — 아래 표는 채워나가는 템플릿이다.
>
> **draft (2026-08-29, 배)**: `/stt/result`(실제 타입 반영)와 `/dest_resolver/result`(신규)를 채워넣음.
> 아직 팀 리뷰 전이라 커밋하지 않음 — 곽/최 확인 후 반영할 것.
>
> **draft 추가 (2026-08-30)**: UI의 "확인" 버튼이 실제로 아무것도 발행하지 않아 dest_resolver가
> `/stt/result`에 자동으로 반응해버리던 문제를 고쳤다. dest_resolver는 이제 `/stt/result`가 아니라
> 신규 토픽 `/stt/confirmed`를 구독한다 — UI가 CONFIRMING 화면에서 "확인"을 눌러야만 발행됨.
> 주행 결과를 UI로 돌려주는 `/navigation/result`(신규, `NavResult.msg`)와 UI→dest_resolver 취소
> 요청용 `/navigation/cancel`(신규)도 추가했다. 이것도 아직 팀 리뷰 전.
>
> **draft 추가 (2026-08-30, 카테고리 선택 플로우)**: `target_type="category"`일 때 로봇이
> 임의로 고르지 않고, 후보가 여럿이면 기본적으로 전부 사용자에게 보여주고 직접 고르게 하는
> 것으로 설계 변경. `/dest_resolver/choices`(신규, `DestChoices.msg`)로 후보 목록을 UI에 보내고,
> UI가 사용자가 탭한 장소명을 `/dest_resolver/choice_selected`(신규, `std_msgs/String`)로 돌려줌.
> 후보가 1개뿐이면 물어보지 않고 바로 확정(`/dest_resolver/result`로 감). 단, "제일 가까운 X"처럼
> 명시적 최근접 요청은 예외 — `resolver_core.resolve()`가 `current_x`/`current_y`(선택 인자,
> 로봇 현재 위치)를 받으면 후보 나열 없이 최근접 하나로 바로 확정한다. 지금은
> `dest_resolver_node.py`가 위치 없이 호출해서 실질적으로 항상 나열로 귀결되지만, 위치 소스
> (`/amcl_pose` 등, Nav2 연동 대기 중)만 연결되면 그대로 동작함. 이것도 아직 팀 리뷰 전.
>
> **draft 추가 (2026-09-02, 최)**: `mov_tts` 신설 — `/tts/speak`(신규, `std_msgs/String`)으로
> 받은 텍스트를 Gemini TTS(`gemini-3.1-flash-tts-preview`, Interactions API)로 합성해 재생.
> 이어서 사용자 요청으로 `mov_ui`가 두 시점에 `/tts/speak`을 발행하도록 와이어링:
> 목적지 해석 성공 시 "{장소명}{로/으로} 안내를 시작합니다"(조사는 마지막 한글 음절 받침
> 유무로 자동 선택), 주행 성공 시 "도착했습니다". 문구/타이밍은 최가 사용자 요청대로 임시
> 확정한 것 — `mov_ui`는 곽 담당이라 정식 확정은 곽 리뷰 필요. 이것도 아직 팀 리뷰 전.
>
> **draft 추가 (2026-09-02, 배, 진행률 표시로 변경)**: NAVIGATING 화면 UI를 사용자 요청대로
> 고침 — `remaining_label`에 "N.Nm 남음" 대신 진행률 퍼센티지("NN%")를 표시하고, 출발/도착
> 자리의 고정 원(●) 두 개는 도착지 표시용 작은 점 하나만 남기고 없앤 뒤, 그 자리를
> 진행률만큼 좌→우로 움직이는 마스코트(`RouteTrack`, `navigating_page.py`)로 대체함. 토픽
> 자체(`/navigation/distance_remaining`, 단위 meter)는 안 바꿨고, `ui_node.on_distance_remaining`이
> 이번 주행 중 관측된 최대 `distance_remaining`을 "총 거리"로 삼아
> `퍼센트 = (1 - remaining/총거리) * 100`으로 UI 쪽에서만 환산 — 아직 팀 리뷰 전.
>
> **draft 추가 (2026-09-02, 최, 남은 거리 표시)**: `dest_resolver_node.py`의 Nav2
> ActionClient에 `feedback_callback`을 추가해 `NavigateToPose` 피드백의
> `distance_remaining`(meter)을 `/navigation/distance_remaining`(신규, `std_msgs/Float32`)으로
> 중계. `navigating_page.py`엔 이미 `set_remaining()` 메서드와 `remaining_label`이 준비돼
> 있었는데(곽이 미리 만들어둠, 실제 데이터 연결만 안 된 상태였음) 여기 연결만 함 — UI 쪽
> 새 코드는 구독 추가/포맷팅 한 줄뿐. 이것도 아직 팀 리뷰 전.
>
> **draft 추가 (2026-09-01, 최)**: 실기에서 Nav2 풀스택이 붙어서 두 가지가 새로 가능해짐.
> (1) `dest_resolver_node.py`가 `/amcl_pose`를 구독해 현재 위치를 `resolver_core.resolve()`에
> 넘기도록 고쳐서, "제일 가까운 X" 요청이 실제로 최근접 계산으로 이어짐(더 이상 항상 후보
> 나열로 귀결되지 않음). (2) `mov_fsm` 패키지 신설 — 배달 사이 `landmarks.csv` 랜덤 지점을
> 순회하다가 사용자가 말하기 버튼을 누르면 멈추고, 실제 안내가 끝나면 재개하는 배회 동작.
> 새 토픽은 없고, 기존 `/stt/start_listening`·`/dest_resolver/result`·`/navigation/result`를
> 추가로 구독만 함(아래 표의 Subscriber 열에 `mov_fsm` 추가). 이것도 아직 팀 리뷰 전.
>
> **draft 추가 (2026-09-02, 배)**: 화장실/엘리베이터는 (사용자 요청으로) "제일/가장
> 가까운"이라고 명시하지 않아도, 위치만 있으면 후보를 나열하지 않고 바로 최근접 하나로
> 확정하도록 `resolver_core.resolve()`를 바꿈 — 이 두 카테고리는 어느 후보든 사용자
> 목적(용변/이동)에 차이가 없어 매번 물어볼 필요가 없기 때문(`AUTO_NEAREST_CATEGORIES`,
> 카페/식당 등 브랜드 선호가 있을 수 있는 카테고리는 기존처럼 나열). 이걸 TTS에도 반영하려고
> `DestResult.msg`에 `category`(신규) 필드를 추가함 — 비어있지 않으면 "동1 화장실"처럼
> 방향+번호가 붙은 place_name 대신 "화장실"이라는 카테고리명으로 일반화해서 말해야 한다는
> 신호. `mov_ui.ui_node.on_dest_result`가 이걸 보고 "가까운 화장실로 안내를 시작합니다"처럼
> 문구를 바꿔 `/tts/speak`로 발행하도록 고침(화면 표시는 여전히 구체적 place_name 그대로).
> `mov_interfaces` 변경이라 곽/최 리뷰 필요 — 아직 팀 리뷰 전.

## 좌표계 규약

ROS2/Nav2 표준 관례를 그대로 따른다 (SLAM/Nav2가 기본으로 이 이름을 쓰므로 리매핑 불필요).

| 항목 | 값 |
|---|---|
| 전역 좌표계(frame_id) | `map` |
| 로봇 기준 좌표계 | `base_link` |
| 오도메트리 좌표계 | `odom` |
| 단위 | 거리: meter, 각도: radian |
| 원점 기준 | SLAM 시작 지점(맵 생성 시 로봇 초기 위치). 랜드마크 DB는 반드시 `map` 프레임 기준 절대좌표로 저장 — Phase 3에서 ECC 맵으로 교체되면 원점도 같이 바뀜에 유의 |

## FSM 상태

| 상태값 | 의미 | 진입 조건 | 다음 상태 |
|---|---|---|---|
| (예) `IDLE` | 대기 중 | 부팅 완료 | `LISTENING` |
| | | | |

## 토픽

| 토픽명 | 메시지 타입 | Publisher | Subscriber | 설명 |
|---|---|---|---|---|
| `/stt/start_listening` | `std_msgs/Empty` | mov_ui | mov_stt, mov_fsm | 음성 인식 시작 트리거. mov_fsm은 이걸로 배회를 일시정지함 |
| `/stt/listening_started` | `std_msgs/Empty` | mov_stt | mov_ui | 마이크 스트림이 실제로 열린 시점(트리거 수신 시점 아님)에 발행. UI는 이걸 받아야 LISTENING 화면으로 전환 — 트리거 발행 즉시 전환하면 마이크가 실제로 열리기 전에 화면만 먼저 바뀌는 문제가 있었음 |
| `/stt/result` | `mov_interfaces/SttResult` | mov_stt | mov_ui | 인식된 발화 텍스트. `success`는 음향적 성패(무음/API오류)만 의미. UI가 CONFIRMING 화면에 표시 |
| `/stt/confirmed` | `mov_interfaces/SttResult` | mov_ui | mov_dest_resolver | CONFIRMING 화면에서 사용자가 "확인"을 눌렀을 때만 발행 (STT가 뽑은 텍스트를 그대로 재발행). dest_resolver의 실제 트리거는 이 토픽이지 `/stt/result`가 아님 |
| `/dest_resolver/result` | `mov_interfaces/DestResult` | mov_dest_resolver | mov_ui, mov_fsm | 목적지 해석 결과. 좌표는 포함 안 함 — place_name/success/error_message/category만. 좌표는 dest_resolver 내부에서만 쓰고 Nav2 호출에 사용. 실패 시 UI는 ERROR로, 성공 시 NAVIGATING으로 전환. mov_fsm은 success=false일 때 배회를 재개함. category는 화장실/엘리베이터처럼 안 물어보고 자동 확정됐을 때만 채워짐(비었으면 명명된 장소거나 사용자가 직접 고른 것) — mov_ui가 TTS 문구 선택에 씀 |
| `/navigation/cancel` | `std_msgs/Empty` | mov_ui | mov_dest_resolver | NAVIGATING 화면의 취소 버튼 → 진행 중인 Nav2 goal 취소 요청 |
| `/navigation/distance_remaining` | `std_msgs/Float32` | mov_dest_resolver | mov_ui | Nav2 `NavigateToPose` 액션 피드백의 `distance_remaining`(meter)을 그대로 중계. mov_ui가 이번 주행 중 관측된 최대값을 총 거리로 삼아 진행률(%)로 환산해 NAVIGATING 화면에 표시 — 값 자체는 여전히 meter |
| `/navigation/result` | `mov_interfaces/NavResult` | mov_dest_resolver | mov_ui, mov_fsm | Nav2 주행 완료 결과(도착/실패/취소). 성공 시 UI는 ARRIVED로, 실패 시 ERROR로 전환. mov_fsm은 이 결과와 무관하게(성공이든 실패든) 배회를 재개함 |
| `/dest_resolver/choices` | `mov_interfaces/DestChoices` | mov_dest_resolver | mov_ui | category 후보가 2개 이상일 때만 발행. UI는 CHOOSING으로 전환해 후보를 버튼으로 나열 |
| `/dest_resolver/choice_selected` | `std_msgs/String` | mov_ui | mov_dest_resolver | CHOOSING 화면에서 사용자가 탭한 장소명(`data`). dest_resolver가 이걸로 최종 확정 + Nav2 goal 전송 |
| `/tts/speak` | `std_msgs/String` | mov_ui | mov_tts | 말할 텍스트. Gemini TTS로 합성 후 스피커로 재생. `/dest_resolver/result`(success) 수신 시 "OO로 안내를 시작합니다"(`category`가 채워져 있으면 place_name 대신 "가까운 OO로"처럼 카테고리명 사용), `/navigation/result`(success) 수신 시 "도착했습니다" 발행 — 문구는 최/배가 임시로 넣음, 곽 확정 필요 |

## 서비스

| 서비스명 | 타입 | 제공 노드 | 설명 |
|---|---|---|---|
| | | | |

## 액션

| 액션명 | 타입 | 제공 노드 | 설명 |
|---|---|---|---|
| (예) `/navigate_to_pose` | `nav2_msgs/NavigateToPose` | mov_navigation | 목적지 좌표까지 자율주행 |
| | | | |

## 커스텀 메시지 정의 (`mov_interfaces`)

### `SttResult.msg`
```
bool success          # 음성 인식 자체의 성패 (무음/API에러 등)
string text
string error_message  # success=false일 때만
```

### `DestResult.msg`
```
bool success
string place_name      # 매칭된 정식 장소명 (success=true일 때만 유효)
string error_message   # success=false일 때: "장소를 찾을 수 없음" | "카테고리 검색 미지원" | "LLM 오류" 등
string category         # 비어있지 않으면 place_name이 사용자에게 안 물어보고 자동으로
                         # 고른 최근접이라는 뜻(2026-09-02 추가) — mov_ui는 TTS에서
                         # place_name 대신 이 카테고리명을 말해야 함(아래 draft 참고)
```

### `NavResult.msg`
```
bool success
string place_name      # 어느 목적지에 대한 결과인지
string error_message   # success=false일 때만 (예: "주행 실패", "주행 취소됨")
```

### `DestChoices.msg`
```
string category         # 사용자가 말한 카테고리 (예: "카페")
string[] place_names    # 그 카테고리에 속한 후보 장소명 전체 (2개 이상일 때만 발행됨)
```
