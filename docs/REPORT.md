# ECC 실내 음성 안내 자율주행 로봇 개발 — 중간보고서 (본문)

**팀명**: MovEdge
**프로젝트명**: ECC(이화캠퍼스콤플렉스) 실내 음성 안내 자율주행 로봇
**작성일**: 2026-09-03
**팀원**: 곽(STT·터치스크린 UI·음성출력) / 최(내비게이션·시스템 통합·FSM·하드웨어) / 배(SLAM·좌표 DB·LLM 연동)

> 본 문서는 실제 저장소 코드(`src/mov_*`)와 프로젝트 문서(`docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/INTERFACES.md`, `docs/GAZEBO.md`, `docs/SESSION_LOG.md`, 각 패키지 `CLAUDE.md`)를 근거로 작성했으며, 코드로 검증되지 않은 내용·추측은 포함하지 않았다. 구글 독스로 옮겨 편집하는 것을 전제로, 표/목록 위주로 정리하고 다이어그램은 텍스트 시퀀스로도 병기했다.

---

## I. 본문

### 1. 문제정의

#### 1.1 최종 목표

ECC 실내에서 사용자가 음성으로 목적지를 말하면, 로봇이 이를 이해하여 자율주행으로 해당 위치까지 안내하고, 이동 중에는 터치스크린과 음성으로 상태를 안내하는 것을 최종 목표로 한다. 실외 배송 로봇과 달리 (1) GPS를 쓸 수 없는 실내 환경, (2) 정형화되지 않은 자연어 목적지 표현, (3) 일반인 이용자를 대상으로 하는 상호작용이라는 세 가지 제약 위에서 목표가 성립해야 한다.

#### 1.2 하위 문제 drill-down

**문제 A. 로봇이 "사람의 말"을 목적지로 바꾸지 못한다**
- A-1. 잡음·발화 스타일이 제각각인 음성을 안정적으로 텍스트화해야 함 (STT)
- A-2. "화장실 어디예요?" 같은 비정형 발화를 고정된 장소명·좌표에 매핑해야 함 (자연어 → 좌표)
- A-3. 특정 장소가 아니라 "화장실"·"카페"처럼 후보가 여러 곳인 요청은 로봇이 임의로 정할지, 사용자에게 물을지 정책이 필요
- A-4. STT는 음성인식 오류(발음이 비슷한 단어로 오인식)를 포함할 수 있어, 목적지 해석 단계에서 이 오류까지 보정해야 함

**문제 B. 실내에는 GPS가 없어 로봇이 "자기 위치"를 모른다**
- B-1. ECC 실내 지도 자체가 없음 → SLAM으로 지도 제작 필요
- B-2. 지도가 있어도 그 위에서 로봇의 현재 위치 추정(localization)이 부정확하면 무의미
- B-3. 목적지 좌표 기준(장소 DB)이 지도 좌표계와 어긋나면 안내 자체가 틀어짐

**문제 C. 지도와 목적지가 있어도 "안전하게" 그 경로로 못 가면 소용없음**
- C-1. Jetson Orin Nano의 제한된 연산 자원 안에서 동작하는 경로계획기 선정
- C-2. 사람이 오가는 동적 장애물 환경에서 충돌 없이 회피
- C-3. 실내 안내 로봇 특성상 "센티미터 단위 정밀 정지"가 오히려 과한 요구일 수 있음 → 현실적 기준 필요

**문제 D. 로봇이 무엇을 하는지 사용자가 알 수 없으면 신뢰할 수 없다**
- D-1. 음성 인식 결과를 사용자가 확인/취소할 수 있어야 함 (오인식 대응)
- D-2. 이동 중 "지금 어디쯤 왔는지"를 직관적으로 보여줘야 함
- D-3. 목적지 도착·오류 등 상태 변화를 화면과 음성으로 동시에 전달해야 함
- D-4. 목적지명처럼 매번 달라지는 문장까지 음성으로 자연스럽게 말해야 함 (고정 녹음 음성의 한계)

**문제 E. 세 사람이 각자 만든 모듈이 하나의 로봇으로 합쳐져야 한다**
- E-1. 모듈 간 토픽/메시지 계약이 없으면 통합 시점에 인터페이스 충돌 발생
- E-2. 응대 중이 아닐 때 로봇이 그냥 서 있을지, 다른 동작(배회)을 할지 상태 관리 필요
- E-3. 서로 다른 담당자가 만든 두 모듈이 같은 자원(Nav2 목표)을 동시에 요청하면 경합이 생김
- E-4. 문서와 코드가 어긋나면(구현은 바뀌었는데 문서가 안 바뀌면) 팀 전체가 잘못된 전제로 작업하게 됨

**문제 F. 개발 환경(시뮬레이터/CPU 서버)과 실제 로봇(Jetson) 사이의 간극**
- F-1. 현장 주행에서 문제가 나면 원인이 소프트웨어인지 하드웨어인지 즉시 분리하기 어려움
- F-2. 개발은 CPU 서버에서 하지만 최종 동작 검증은 Jetson Orin Nano 실기에서만 가능
- F-3. 이 Jetson(arm64) 환경엔 표준 시뮬레이션 도구 일부가 아예 배포되지 않아, 표준 워크플로를 그대로 쓸 수 없음

---

### 2. 해결방안

#### 2.1 시스템 아키텍처

| 구분 | 내용 |
|---|---|
| 베이스 | TurtleBot3 Waffle [4] |
| 컴퓨트 | NVIDIA Jetson Orin Nano [7] (기존 Raspberry Pi 대비 온보드 LLM/STT/TTS 호출 및 Nav2 연산 여유 확보 목적으로 교체) |
| 센서 | LiDAR(ld08/coin_d4), ReSpeaker 마이크 어레이(카드 0), 스피커(HDMI 오디오), 터치스크린(Waveshare 8DP-CAPLCD, 1280×800) |
| OS/미들웨어 | Ubuntu 22.04 / ROS 2 Humble [1] |
| SLAM | Google Cartographer [3] |
| Navigation | Nav2 [2] — AMCL(localization), Planner/Controller/BT Navigator |
| 음성인식(STT) | faster-whisper (Whisper small 모델), 로컬(온디바이스) 추론 |
| 자연어 목적지 해석 | Google Gemini API [6] structured output — `gemini-3.5-flash-lite` |
| 음성합성(TTS) | Google Gemini TTS (Interactions API) — `gemini-3.1-flash-tts-preview` |
| UI 프레임워크 | PyQt5 |
| 시뮬레이터 | Ignition Gazebo Fortress [5] (arm64 환경에 Gazebo Classic 미지원으로 채택) |

의존성 방침으로 `mov_*` 패키지는 공식 ROS 2 Humble apt 패키지에만 의존하고, 벤더 소스(`turtlebot3_ws`)는 참고용으로만 두어 빌드/런타임 의존성에서 제외했다. 이는 팀 3인이 각자 패키지를 독립적으로 빌드·배포할 수 있게 하기 위한 결정이다.

> **참고**: 초기 아키텍처 설계(`ARCHITECTURE.md`)에는 STT를 "온디바이스 또는 Gemini API" 중 미정으로 남겨두었으나, 실제 구현 단계에서 **네트워크 지연 없이 즉시 반응해야 하는 음성 인식 특성상 온디바이스 Whisper**로 확정했다(2.4.1절). 반대로 목적지 해석·TTS는 결정론적 매칭이 어려운 자연어 이해·음성 합성 영역이라 클라우드 LLM(Gemini)을 그대로 채택했다 — 즉 "실시간성이 중요한 인식"과 "이해·생성이 필요한 영역"을 구분해 온디바이스/클라우드를 나눠 배치한 것이 실제 설계의 핵심 판단이다.

#### 2.2 노드 구성 및 담당

| 패키지 | 담당 | 역할 |
|---|---|---|
| `mov_interfaces` | 공동 | 공용 msg 정의 (`SttResult`, `DestResult`, `NavResult`, `DestChoices`) |
| `mov_stt` | 곽 | 음성 → 텍스트 (VAD + faster-whisper) |
| `mov_ui` | 곽 | 터치스크린 UI, 상태 화면 전환 (PyQt5) |
| `mov_tts` | 곽 (인프라는 최가 선구현) | 텍스트 → 음성 (Gemini TTS 실시간 합성) |
| `mov_dest_resolver` | 배 | 자연어 → 좌표 매핑 (Gemini structured output + 랜드마크 DB) |
| `mov_navigation` | 최 | Nav2 연동, URDF/월드 등 시뮬레이터 자산 |
| `mov_fsm` | 최 | 응대 대기 중 배회, Nav2 goal 경합 관리 |

#### 2.3 노드 통신 구조 (전체 개요)

```
1. mov_ui --(/stt/start_listening)--> mov_stt, mov_fsm(배회 일시정지)
2. mov_stt --(/stt/listening_started)--> mov_ui   [마이크 실제로 열린 시점]
3. mov_stt --(/stt/result)--> mov_ui               [CONFIRMING 화면]
4. mov_ui --(/stt/confirmed, 사용자 확인 시에만)--> mov_dest_resolver
5. mov_dest_resolver --(/dest_resolver/choices, 후보 2개 이상)--> mov_ui  [CHOOSING 화면]
   mov_ui --(/dest_resolver/choice_selected)--> mov_dest_resolver
6. mov_dest_resolver --(/dest_resolver/result)--> mov_ui, mov_fsm
7. mov_dest_resolver <--(/amcl_pose)-- Nav2/AMCL   [최근접 계산용 현재 위치]
8. mov_dest_resolver --(NavigateToPose action)--> Nav2
9. mov_dest_resolver <--(feedback: distance_remaining)-- Nav2
   mov_dest_resolver --(/navigation/distance_remaining)--> mov_ui
10. mov_dest_resolver --(/navigation/result)--> mov_ui, mov_fsm
11. mov_ui --(/navigation/cancel)--> mov_dest_resolver
12. mov_ui --(/tts/speak)--> mov_tts --> 스피커(Gemini TTS 합성 후 aplay 재생)
13. mov_fsm --(NavigateToPose action, 별도 ActionClient)--> Nav2   [배회용, 7~10과 별개 goal]
```

세부 토픽·메시지 정의는 `docs/INTERFACES.md`를 3인 공동 소유 계약 문서로 관리하며, 변경 시 나머지 2인의 리뷰를 거친다. **현재 구조의 특징**은 `mov_fsm`이 신설된 이후에도 `mov_ui`↔`mov_stt`↔`mov_dest_resolver` 사이의 기존 직접 토픽 체인을 그대로 유지하고, `mov_fsm`은 그 위에 배회 행동만 구독 전용으로 얹은 것이다 — 중앙 허브로 전체를 재배선하는 것은 의도적으로 범위 밖으로 두었다(이미 안정 동작하는 체인을 건드리는 리스크보다, 얇게 얹는 쪽이 통합 리스크가 작다는 판단).

#### 2.4 모듈별 상세 구현

##### 2.4.1 `mov_stt` — 음성인식

**파이프라인**: 마이크 스트림(ReSpeaker, ALSA 카드 0, 16kHz 모노) → `webrtcvad` 기반 VAD(Voice Activity Detection)로 발화 구간만 절단 → `faster-whisper`(Whisper small 모델)로 텍스트 변환 → `/stt/result` 발행.

| 파라미터 | 값 | 의미 |
|---|---|---|
| SAMPLE_RATE | 16000 Hz | |
| FRAME_MS / FRAME_SAMPLES | 30ms / 480샘플 | VAD 프레임 단위 |
| MAX_WAIT_FOR_SPEECH_SEC | 5.0초 | 트리거 후 이 시간 안에 말이 시작 안 되면 "무음 감지"로 실패 처리 |
| SILENCE_TO_STOP_SEC | 0.9초 | 발화 시작 후 이만큼 연속 무음이면 발화 종료로 판단(기존 1.2초에서 단축) |
| MAX_RECORDING_SEC | 15.0초 | 안전장치: 최대 녹음 길이 |
| VAD 민감도 | `webrtcvad.Vad(1)` | 0~3 중 1 (무음 판정 엄격도) |
| Whisper 모델 | small, `beam_size=1`(그리디) | beam_size 기본값(5)은 CPU 추론에서 체감 지연 유발 → 속도 우선, 정확도는 CONFIRMING 화면의 사용자 확인으로 보완 |
| 언어 | 자동 감지 (`language=None`) | 초기엔 `'ko'` 고정이었으나, 영어 사용자 지원을 위해 Whisper 자체 언어 감지로 전환 |
| 디바이스 | CUDA 우선, 실패 시 CPU(`int8`) 폴백 | 이 Jetson의 `ctranslate2`가 CUDA 없이 빌드돼 있어 실제로는 항상 CPU로 동작(코드상 폴백 로직은 유지) |

**설계 상 주의점 2가지**(코드 주석으로 명시적으로 남겨진 실제 버그 회피 사례):
1. *구독을 모델 로딩보다 먼저 생성*: 반대 순서면 Whisper 모델 로딩 중 들어온 트리거가 구독 자체가 없어 조용히 유실되는 버그가 있었음 — 순서를 바꿔 해결.
2. *`/stt/listening_started` 신호 분리*: UI가 트리거 발행 즉시 "듣고 있어요" 화면으로 전환하면, 마이크 스트림이 실제로 열리기 전에 화면만 먼저 바뀌는 문제가 있어, 마이크가 실제로 열린 시점에만 별도 토픽으로 신호하도록 분리.

##### 2.4.2 `mov_dest_resolver` — 목적지 해석 (LLM 기반 NLU + 결정론적 좌표 매칭)

**핵심 설계 원칙**: LLM은 좌표를 직접 생성하지 않는다. LLM(Gemini)은 `target_type`/`place_name`/`category`/`wants_nearest`라는 **구조화된 의도(intent)만** 추출하고, 실제 좌표는 항상 결정론적 코드가 `landmarks.csv`에서 정확히 조회한다 — LLM이 좌표를 직접 생성하게 하면 할루시네이션(존재하지 않는 좌표 생성) 위험이 있기 때문이다.

**할루시네이션 방지 장치**: Gemini의 `response_schema`에서 `place_name`/`category` 필드를 **DB에 실재하는 값만 담긴 enum**으로 제약한다. 그래도 한 번 더 방어적으로 "DB에 실제로 있는지" 코드에서 재확인한다(이중 방어). 참고로 enum에는 빈 문자열을 못 넣는 Gemini 스키마 제약이 있어 `"NONE"` 센티널 값으로 "해당 없음"을 표현한다.

**분류 로직 (프롬프트 규칙 요약)**:
1. 발화가 목록의 특정 장소를 가리키면 `target_type="named_place"` — 이름 직접 언급뿐 아니라, `landmarks.csv`의 `desc`(메뉴/특징) 컬럼만으로 장소 하나를 특정할 수 있는 경우도 포함 (예: "쌀국수 먹고 싶어" → 포포420). desc가 여러 장소에 겹치면 매칭하지 않고 unsupported 처리.
2. 발화가 카테고리(화장실, 카페 등)를 가리키면 `target_type="category"`, 최근접을 명시했는지(`wants_nearest`)도 같이 추출.
3. 목록에 없거나 목적지와 무관한 발화(잡담 등)는 `target_type="unsupported"`.
4. STT 오인식 보정: 프롬프트에 "음성인식 결과라 발음이 비슷한 단어로 잘못 인식됐을 수 있다"는 지시를 포함해, LLM이 문맥상 자연스러운 의도로 먼저 보정한 뒤 판단하게 함 (문제 A-4 대응).

**카테고리 후보 처리 정책** (문제 A-3에 대한 답):

| 상황 | 처리 |
|---|---|
| 후보 1개 | 바로 확정, `/dest_resolver/result` 발행 |
| 후보 2개 이상, 카테고리가 화장실/엘리베이터(`AUTO_NEAREST_CATEGORIES`) | 위치(`/amcl_pose`)가 있으면 최근접 하나로 자동 확정, `DestResult.category`에 카테고리명을 채워 TTS가 "동1 화장실" 대신 "가까운 화장실"로 일반화해 말하게 함 |
| 후보 2개 이상, 사용자가 "제일/가장 가까운"을 명시(`wants_nearest`) | 위치가 있으면 최근접 하나로 자동 확정 |
| 후보 2개 이상, 그 외(카페·식당 등 브랜드/메뉴 선호 가능성이 있는 카테고리) | 확정하지 않고 후보 전체를 `/dest_resolver/choices`로 UI에 전달 → 사용자가 직접 선택 |

이 정책은 "로봇이 임의로 아무 카페나 데려가면 '스타벅스 말고 다른 카페' 같은 선호/제외가 섞인 발화에서 틀리기 쉽다"는 판단에서 나왔고, 반대로 화장실·엘리베이터는 "어느 후보든 사용자 목적(용변/이동)에 차이가 없다"는 판단에서 예외적으로 자동화했다 — 즉 카테고리 성격에 따라 자동화 여부를 다르게 적용한 것이 이 모듈의 핵심 설계 지점이다.

**LLM 모델 선정 (실측 벤치마크)**:

| 모델 | 평균 응답 시간 | 비고 |
|---|---|---|
| `gemini-3.6-flash` (플래그십) | 5.1초/건 | 음성 인터랙션엔 지연이 너무 큼 |
| `gemini-3.5-flash-lite` (채택) | 0.94초/건 | 약 5배 빠름, 고정된 소규모 목록 분류 작업이라 정확도 손실 없음 확인 |

모델명은 `"latest"` 별칭 대신 특정 버전으로 고정 — 구글 측의 조용한 모델 교체로 로봇 동작이 예고 없이 바뀌는 것을 방지하기 위함(재현성).

**Nav2 연동**: `dest_resolver_node`가 `NavigateToPose` 액션 클라이언트를 직접 들고 있다가, 목적지가 확정되면 `map` 프레임 기준 좌표로 goal을 전송한다(방향값은 랜드마크 DB에 없어 단위 쿼터니언 고정). 액션 피드백의 `distance_remaining`을 `/navigation/distance_remaining`으로 UI에 중계하고, 최종 결과(성공/실패/취소)는 `/navigation/result`로 발행한다. 또한 `/amcl_pose`를 구독해 로봇의 최신 위치를 들고 있다가 `resolve()` 호출 시 넘겨줌으로써 "제일 가까운 X" 요청의 최근접 계산을 가능하게 한다 — 이 위치 연동은 실기에 Nav2(AMCL)가 붙은 뒤(2026-09-01)에야 실질적으로 동작하게 됐다.

##### 2.4.3 `mov_fsm` — 배회(patrol) 상태 관리

**요구사항**: 로봇이 응대하지 않는 시간에 가만히 서 있지 않고 `landmarks.csv`의 지점을 랜덤하게 순회하다가, 사용자가 말하기 버튼을 누르면 즉시 멈추고, 실제 안내(도착/실패/취소) 또는 목적지 해석 실패가 끝나면 배회를 재개한다.

**상태**: `WANDERING`(배회 중) / `PAUSED`(응대 중, 배회 정지). 별도 FSM 상태 토픽으로 발행하지는 않고, 노드 내부 boolean 플래그(`_paused`)로 관리한다.

**Nav2 goal 경합 방지 설계**: `mov_dest_resolver`와 `mov_fsm`이 각자 독립적인 `NavigateToPose` ActionClient를 갖는다. 두 노드가 동시에 활성 goal을 갖는 경합을 막기 위해, `PAUSED` 상태를 "말하기 버튼을 누른 시점"부터 "실제 주행 결과(`/navigation/result`) 또는 목적지 해석 실패(`/dest_resolver/result`, success=false)"까지로 정의하고, 이 구간 동안은 배회 goal을 절대 새로 보내지 않으며 진행 중이던 배회 goal은 즉시 취소한다.

**초기 위치 게이트**: Nav2 파라미터(`set_initial_pose: false`)상 AMCL은 부팅 직후 `(0,0,0)` 기본값 기준으로만 서 있어, 사용자가 RViz "2D Pose Estimate"로 실제 위치를 찍기 전엔 그 값이 실제 위치와 무관하다. 이 상태에서 배회를 시작하면 엉뚱한 좌표로 이동을 시도하므로, `/initialpose`가 최소 한 번 들어오기 전까지는 배회를 시작하지 않도록 게이트를 걸었다 — "맨 처음 1회 수동 위치 지정 → 이후 자동 배회"가 코드로 보장된다.

**안전 타임아웃**: CONFIRMING 화면에서 사용자가 확인도 취소도 아닌 경로로 이탈하는 경우처럼, `mov_fsm`이 감지할 수 있는 토픽이 발행되지 않는 경로가 있을 수 있다. 이런 경우에도 무한정 멈춰있지 않도록 `RESUME_TIMEOUT_SEC=60`초 뒤엔 무조건 배회를 재개하는 안전장치를 두었다.

**실제 발견·수정된 버그 사례**: 초기 구현에서는 위 안전 타이머가 `/dest_resolver/result` 성공(=실제 주행 시작) 시점에 취소되지 않고 방치되어 있었다. 그 결과 "말하기 → STT → 확인 → 목적지 해석 → 실제 주행"까지의 총 소요 시간이 60초를 넘기면(건물을 가로지르는 실제 이동에서는 흔함), 안전 타이머가 **주행 도중**에 발화해 배회 goal을 새로 전송했고, Nav2가 이를 진행 중이던 안내 goal에 대해 preempt(취소)해버려 사용자 화면에 "주행이 취소됨" 오류가 뜨는 버그로 이어졌다. `on_dest_result(success=True)` 시점에 안전 타이머를 명시적으로 취소하도록 수정해, 실제 주행이 시작된 뒤에는 안전 타이머가 아니라 `/navigation/result`(모든 경우에 반드시 발행됨)로만 재개 여부를 판단하도록 고쳤다. (실기 통합 테스트 중 발견 → 원인 분석 → 코드 수정까지 이어진 실제 디버깅 사례.)

##### 2.4.4 `mov_tts` — 실시간 음성 합성

**API 특이사항**: Gemini TTS는 다른 모듈이 쓰는 `client.models.generate_content`가 아니라 `client.interactions.create`(Interactions API)로 호출해야 한다. 또한 `generation_config.speech_config`는 dict가 아니라 **리스트**로 넘겨야 한다(`[{"voice": "Kore"}]`) — dict로 넘기면 400 에러가 발생함을 실제 API 호출로 확인했다.

**오디오 처리**: 응답의 `output_audio`는 24kHz mono 16bit PCM을 base64로 담고 있어, 이를 WAV 컨테이너로 감싸 `aplay`(ALSA CLI)로 재생한다 — 별도 오디오 라이브러리 의존성을 추가하지 않았다.

**캐싱 (실기 지연 문제 대응)**: 실기 end-to-end 테스트에서 발화당 API 왕복이 6~8초(가끔 그 이상) 걸려 체감 지연이 컸다. 실제 발화 문구는 "도착했습니다"(완전 고정) + "OO(로/으로) 안내를 시작합니다"(장소명만 바뀌는 템플릿, 후보는 `landmarks.csv` 수십 개뿐)로 사실상 종류가 유한하다는 점에 착안해, (모델, 보이스, 텍스트) 조합을 SHA-256 해시 키로 삼아 합성 결과 WAV를 로컬 디렉터리(`TTS_CACHE_DIR`)에 영구 캐싱했다. 같은 문장이 다시 들어오면 API 호출 없이 캐시 파일을 바로 재생해 지연이 거의 사라진다. 캐시 파일은 임시 경로에 완성 후 `os.replace`로 원자적으로 최종 위치에 옮겨, 합성 도중 실패해도 손상된 파일이 캐시로 남지 않게 했다.

**오디오 출력 장치**: 로봇에 ALSA 카드가 여러 개 잡혀(ReSpeaker, Jetson 내장 HDMI 등) 기본 장치가 의도한 스피커가 아닐 수 있다. 실기 테스트로 `plughw:1,3`(카드 1 = Jetson Orin Nano HDA, 디바이스 3 = HDMI 0)이 실제 디스플레이 출력 장치임을 확인했다.

##### 2.4.5 `mov_ui` — 터치스크린 UI

**FSM-화면 매핑**: `QStackedWidget`에 7개 상태(`IDLE`, `LISTENING`, `CONFIRMING`, `CHOOSING`, `NAVIGATING`, `ARRIVED`, `ERROR`)를 각각 페이지로 등록하고, `set_state(state)` 한 번으로 화면을 전환한다. 현재는 `mov_fsm`이 상태 토픽을 발행하지 않으므로, 어떤 이벤트가 오면 어느 화면으로 전환할지의 판단 로직 자체를 `ui_node.py`가 임시로 담당하고 있다(향후 `mov_fsm`이 상태 토픽을 발행하게 되면 `ui_node`는 구독→`set_state()` 호출만 남기도록 리팩터링 예정).

**PyQt5 + rclpy 통합 패턴**: 별도 스레드를 쓰지 않고, `QTimer`가 50ms 주기로 `rclpy.spin_once(node, timeout_sec=0)`를 폴링 호출한다. 이 패턴 덕분에 모든 위젯 조작이 항상 Qt 메인 스레드에서만 일어나 스레드 안전성 문제를 원천적으로 피한다.

**진행률(%) 계산**: Nav2 액션 피드백은 "남은 거리(`distance_remaining`, meter)"만 주고 총 거리는 주지 않는다. UI는 이번 주행 중 관측된 `distance_remaining`의 **최댓값**을 "총 거리"로 간주하고, `퍼센트 = (1 - remaining/총거리) × 100`으로 환산한다. 첫 피드백이 보통 최댓값이지만 리플래닝으로 일시적으로 늘어날 수도 있어 매 콜백마다 최댓값을 갱신한다.

**진행 표시 UI (`RouteTrack`)**: 초기엔 출발/도착 위치에 고정 원(●) 두 개만 표시했으나, 도착지 표시는 작은 점 하나만 남기고 대신 마스코트 이미지가 진행률(%)만큼 트랙을 따라 좌→우로 이동하는 방식으로 변경했다(사용자 요청 반영).

**조사(로/으로) 자동 선택**: 목적지명 뒤에 붙는 한국어 조사를 마지막 한글 음절의 종성(받침) 유무로 자동 판단한다 — 받침이 없거나 받침이 'ㄹ'이면 '로', 그 외엔 '으로'. "아트하우스 모모 (영화관)"처럼 끝에 괄호·공백이 붙는 이름도 있어 문자열 끝에서부터 거슬러 올라가며 실제 마지막 한글 음절을 탐색한다. 한글 음절이 없는 이름(숫자/영문뿐)은 '으로'로 기본 처리한다. 이 로직은 `landmarks.csv`의 36개 항목 전부(괄호·영문 병기 포함)에 대해 검증했다.

**다국어(i18n) 지원**: 화면 우상단 언어 토글(한국어/EN) 버튼으로 UI 텍스트와 TTS 발화 문구(영어는 "Starting navigation to the nearest X." 형태로 조사 없이 구성) 모두 전환된다.

**CONFIRMING 취소 경쟁 조건 처리**: LISTENING 화면에서 취소를 누르면 IDLE로 돌아가지만, `mov_stt`는 아직 취소를 받는 토픽이 없어 마이크가 계속 듣고 있다가 뒤늦게 `/stt/result`를 보내올 수 있다. 이 경우 사용자가 이미 IDLE로 나갔는데 갑자기 CONFIRMING/ERROR로 튕기는 문제가 생기므로, 취소 이후 도착하는 결과 하나를 무시하는 플래그(`_listening_cancelled`)를 두었다.

##### 2.4.6 `mov_navigation` — Nav2 연동 및 Ignition Gazebo 시뮬레이터

**시뮬레이터 채택 배경**: 이 Jetson arm64 환경에는 Gazebo Classic(`gazebo11`, `ros-humble-gazebo-ros-pkgs`, `ros-humble-turtlebot3-gazebo`)이 apt 저장소에 전혀 없다. 대신 **Ignition Gazebo Fortress**(`ign gazebo`, 6.18.0)를 사용하되, 표준 `ros_gz_sim` 스폰 유틸도 humble+arm64 조합에서는 빌드팜 공백으로 존재하지 않아, `ign service`(EntityFactory)로 직접 스폰하고 `ros_gz_bridge`의 `parameter_bridge`로 토픽을 손수 브리징하는 방식을 채택했다.

**`map_to_walls_world.py` — 지도 → 시뮬레이션 월드 변환 알고리즘**:
1. `<map>.pgm`을 `<map>.yaml`의 `negate`/`occupied_thresh` 기준으로 occupancy mask로 변환
2. `cv2.dilate`로 인접한 벽 조각을 먼저 병합 (성능 문제 대응, 아래 참고)
3. `cv2.findContours` + `approxPolyDP`로 컨투어 추출/단순화
4. shapely로 폴리곤 보정: `buffer(0)`(자기교차 복구) → **모든 폴리곤을 convex hull로 강제 대체**(triangulation 실패 방지) → **CCW(반시계) 방향으로 강제 정렬**(라이다 인식 문제 방지)
5. 각 폴리곤을 SDF `<polyline>` extrusion으로 출력(높이 1m, 별도 mesh 불필요)

**디버깅 기록 (문제 → 원인 → 해결)**:

| 문제 | 증상 | 원인 | 해결 |
|---|---|---|---|
| 성능 저하 | real_time_factor 0.09 (10배 느림) | ECC 실측 맵(294m×208m) 전체를 픽셀 단위 그대로 압출하면 1,552개 개별 충돌 형상 생성 — 형상 개수 자체가 병목(라이다 렌더링과는 무관, 빈 월드에서 라이다만 켜면 정상) | dilate로 인접 벽 병합, 226개로 축소 → real_time_factor 1.0 회복 |
| Triangulation 실패 | `Unable to extrude mesh` 에러 | Ignition의 polyline 압출기가 오목한(concave) 폴리곤에서 자주 실패, `buffer(0)`으로 수학적으로 유효해도 실패하는 경우 존재(면적비 98% 이상 거의-convex 도형도 실패) | 모든 폴리곤을 convex hull로 강제 치환 (1,552개 중 54개 실패 → 226개 중 1개만 실패, 무시 가능) |
| 라이다가 벽을 전혀 못 잡음 | `/scan`이 전부 `.inf` | 생성된 폴리곤이 전부 시계방향(CW)으로 감겨 있어, 압출된 벽 옆면의 법선이 안쪽을 향함 → back-face culling으로 `gpu_lidar`의 depth 렌더 패스에서 안 보임(일반 카메라/GUI 렌더링에서는 문제없이 보여서 원인 특정에 시간 소요) | shapely `orient(sign=1.0)`로 모든 폴리곤을 CCW로 강제 통일 |
| 반복적 세그폴트 | gazebo 프로세스가 조용히 사라짐 | `$DISPLAY` 환경변수가 비어있으면 Ogre2 렌더 경로가 headless 모드에서도 더미 렌더 컨텍스트조차 생성 못 함(실제 GPU 렌더링과 무관하게 X 디스플레이 자체가 필요) | `export DISPLAY=:1` (호스트의 실제 X 디스플레이 번호) |
| CPU 레이캐스팅 미지원 | `Sensor type LIDAR not supported` | Ignition Fortress(6.18)는 `type="lidar"` 미지원, `gpu_lidar`만 지원 | `gpu_lidar` 사용(GPU 없이도 소프트웨어 렌더링(ogre2/llvmpipe)으로 정상 동작 확인) |

**AMCL 연동 디버깅**: `sim_localization.launch.py`로 map_server+AMCL+lifecycle_manager를 구동하는 과정에서 "`/amcl_pose`가 완전히 조용함" 문제가 발생했다. 원인은 (1) 라이다 프레임에 대한 TF 자체가 없었던 문제 → `static_transform_publisher`로 고정 TF 추가, (2) `robot_localization`(EKF) 노드가 `/clock` 구독 방식 때문에 스캔 타임스탬프를 따라가지 못해 TF 버퍼가 계속 가득 차던 문제 → EKF를 제외하고 `/odom`을 직접 구독해 TF를 발행하는 간단한 브로드캐스터(`odom_to_tf.py`)로 대체해 해결했다. (IMU 융합(EKF)은 이 기본 파이프라인 검증 후 재도입 예정으로 보류.)

**알려진 한계**: Ignition이 동적 스폰(`ign service create`) 엔티티의 pose를 안정적으로 브로드캐스트하지 않아, AMCL 추정치와 실제(ground-truth) 위치를 자동으로 비교하는 기능은 아직 구현하지 못했다(3가지 방법 모두 시도 후 실패 확인). 현재는 GUI 육안 확인으로 대체하며, 근본 해결책은 로봇을 동적 스폰 대신 world SDF에 정적으로 `<include>`하는 방식으로의 전환이다.

##### 2.4.7 `mov_interfaces` — 커스텀 메시지 정의

```
SttResult.msg
  bool success          # 음성 인식 자체의 성패 (무음/API에러 등)
  string text
  string error_message  # success=false일 때만

DestResult.msg
  bool success
  string place_name      # 매칭된 정식 장소명
  string error_message   # 실패 사유
  string category         # 비어있지 않으면 자동 최근접 확정(화장실/엘리베이터)이었다는 신호

NavResult.msg
  bool success
  string place_name
  string error_message   # "주행 실패" | "주행 취소됨" 등

DestChoices.msg
  string category         # 사용자가 말한 카테고리
  string[] place_names    # 후보 장소명 전체 (2개 이상일 때만 발행)
```

#### 2.5 FSM 상태 정의 (`mov_ui`)

| 상태 | 의미 | 진입 조건 | 다음 상태 |
|---|---|---|---|
| IDLE | 대기(배회 가능) | 부팅 완료 / 이전 상호작용 종료 | LISTENING |
| LISTENING | 마이크로 발화 수신 중 | `/stt/listening_started` 수신 | CONFIRMING / ERROR / (취소 시)IDLE |
| CONFIRMING | STT 결과 확인 대기 | `/stt/result`(success=true) 수신 | (확인)해석 대기 유지 → NAVIGATING/CHOOSING/ERROR / (취소)IDLE |
| CHOOSING | 카테고리 후보 선택 대기 | `/dest_resolver/choices` 수신 | NAVIGATING(선택 후 결과 대기) / ERROR |
| NAVIGATING | Nav2 주행 중 | `/dest_resolver/result`(success=true) 수신 | ARRIVED / ERROR / (취소)IDLE |
| ARRIVED | 도착 안내 | `/navigation/result`(success=true) 수신 | IDLE |
| ERROR | 오류 안내 | 각 단계 실패 시 | IDLE(재시도) |

#### 2.6 검증 전략 — 단계적 격리 검증

문제 F(개발-실기 간극)에 대한 해결책으로, 실기 단독 검증 대신 **시뮬레이터를 통한 소프트웨어/하드웨어 원인 분리** 전략을 채택했다. 현장 주행에서 localization 문제가 발견되었을 때, 이것이 Nav2/AMCL 설정 문제인지 라이다·오도메트리 등 하드웨어 문제인지 실기에서는 구분이 어려웠기 때문에, ECC 실측 맵을 그대로 Ignition Gazebo로 옮겨 소프트웨어 스택만 독립적으로 검증할 수 있는 환경을 별도로 구축했다.

로드맵은 Phase 0(규칙설계) → Phase 1(시뮬레이터 스켈레톤) → Phase 2(실기 테스트맵 스켈레톤) → Phase 3(ECC 실측 SLAM) → Phase 4(3개 트랙 병렬 실구현) → Phase 5(통합·Jetson 포팅) → Phase 6(실전 테스트)의 7단계로 구성되며, Phase 하나를 세션(작업 단위) 하나로 관리해 진행 상황을 문서로 추적한다.

---

### 3. 결론

#### 3.1 예상 개발 결과물

- ECC 실내 지도 및 36개 실측 랜드마크 좌표 DB(카테고리 라벨 포함 — 엘리베이터 7개, 화장실 5개, 식당·카페·상점 등 다수)
- 음성 질의 → 목적지 해석 → Nav2 자율주행 → 도착 안내까지의 end-to-end 파이프라인
- 터치스크린 기반 7단계 상태 UI(IDLE/LISTENING/CONFIRMING/CHOOSING/NAVIGATING/ARRIVED/ERROR), 한국어/영어 다국어 지원
- 응대 대기 시간에 정적으로 서 있지 않고 랜드마크 사이를 배회하다가 호출에 응답하는 동작

#### 3.2 서비스 시나리오

```
1. [배회 중인 로봇] 사용자가 말하기 버튼 터치
   → mov_ui: /stt/start_listening 발행 (mov_fsm: 배회 즉시 일시정지)
2. mov_stt: 마이크 오픈 → /stt/listening_started (UI: LISTENING 화면)
3. 사용자: "화장실 어디예요?"
4. mov_stt: VAD로 발화 구간 검출 → Whisper 변환 → /stt/result (UI: CONFIRMING 화면, 텍스트 표시)
5. 사용자: 확인 버튼 터치
   → mov_ui: /stt/confirmed 발행
6. mov_dest_resolver: Gemini로 "화장실"(category) 분류
   → AUTO_NEAREST_CATEGORIES 대상 + /amcl_pose 위치 보유
   → 화장실 5곳 중 최근접 1곳으로 자동 확정 (사용자에게 다시 묻지 않음)
   → /dest_resolver/result 발행, Nav2에 NavigateToPose goal 전송
7. mov_ui: NAVIGATING 화면 전환, "가까운 화장실로 안내를 시작합니다" TTS 발행
   → mov_tts: Gemini TTS 합성(또는 캐시 재생) → 스피커 출력
8. 주행 중: Nav2 피드백(distance_remaining) → mov_ui 진행률(%) 갱신, 마스코트 이동
9. 도착: Nav2 결과 성공 → /navigation/result
   → mov_ui: ARRIVED 화면, "도착했습니다" TTS
   → mov_fsm: 배회 재개
```

#### 3.3 활용 기술 배치

| 계층 | 기술 | 배치 위치 |
|---|---|---|
| 인지 | webrtcvad + faster-whisper(Whisper small) [8][9] | Jetson 온보드(로컬 추론) |
| 인지 | Gemini API structured output(NLU) [6] | Jetson → 클라우드 API 호출 |
| 인지 | Cartographer SLAM [3] | Jetson (맵 제작 시) |
| 의사결정 | Nav2 (AMCL, Planner, Controller, BT Navigator) [2] | Jetson 온보드 |
| 표현 | Gemini TTS(Interactions API, `gemini-3.1-flash-tts-preview`) [6] | Jetson → 클라우드 API, 로컬 캐시 + ALSA 재생 |
| 표현 | PyQt5 터치스크린 UI [10] | Jetson 온보드 |
| 검증 | Ignition Gazebo Fortress [5] | 개발 서버(CPU) — 실기 배포 전 격리 검증용 |

#### 3.4 초기 단계 실험 결과

**(1) 시뮬레이터 구축 — 성능/정확도 검증**

| 지표 | 최적화 전 | 최적화 후 |
|---|---|---|
| 충돌 형상 개수 | 1,552개 | 226개 |
| real_time_factor | 0.09 | 1.0 |
| Triangulation 실패 형상 수 | 54개 | 1개(무시 가능 수준) |

폴리곤 개수가 벽 디테일보다 시뮬레이션 성능에 더 큰 영향을 준다는 정량적 결론을 얻었다.

**(2) AMCL localization 검증**

`sim_localization.launch.py`(map_server + AMCL + lifecycle_manager)로 실기와 동일한 Nav2 파라미터를 시뮬레이터에서 재사용해 AMCL 안정 동작을 확인했다. 다만 Ignition의 동적 스폰 엔티티 pose 브로드캐스트 제약으로 ground-truth 자동 비교는 아직 미구현이며, 현재는 GUI 육안 확인으로 대체하고 있다.

**(3) 실기 Nav2 통합 검증**

ECC 실측 맵 기준으로 `turtlebot3_bringup` + `nav2_bringup`을 실기에서 구동해 Nav2 전체 스택(AMCL/Planner/Controller/BT Navigator)의 정상 동작을 확인했다. 이를 계기로 이미 완성돼 있던 소프트웨어 체인을 실제로 연결하는 `full_system.launch.py`를 구성했다. 실내 안내 로봇 특성상 정밀 정지가 불필요하다는 판단에 따라 목표 도달 허용 오차(`xy_goal_tolerance`)를 0.25m에서 1.0m로 완화했다.

**(4) 목적지 해석(NLU) 검증**

36개 실측 랜드마크에 대해 Gemini API 기반 자연어 → 좌표 매핑을 실제 API 호출로 검증했다. 모델 벤치마크 결과 `gemini-3.5-flash-lite`(0.94초/건)가 플래그십 모델(`gemini-3.6-flash`, 5.1초/건) 대비 약 5배 빠르면서 정확도 손실이 없어 최종 채택했다. 단일 후보/최근접+위치 있음/최근접+위치 없음/최근접 미요청+위치 있음 등 4가지 조합 전부 실제 API 테스트로 검증을 통과했다.

**(5) TTS 합성 검증**

Gemini TTS(Interactions API)로 한국어 문장의 실시간 합성 및 ALSA(`aplay`) 재생을 확인했다. 캐싱 도입 전 발화당 6~8초였던 지연을, 유한한 템플릿 문구를 캐싱하는 방식으로 재요청 시 즉시 재생 수준까지 줄였다. 조사(로/으로) 자동 선택 로직을 랜드마크 DB 36개 항목(괄호·영문 병기 포함) 전체에 대해 검증했다.

**(6) 통합 과정에서 발견·수정된 버그**

| 버그 | 증상 | 원인 | 수정 |
|---|---|---|---|
| mov_fsm 안전 타이머 미취소 | 실제 주행 중 갑자기 "주행이 취소됨" 오류 | 안전 타이머가 실제 주행 성공 시점에 취소되지 않아, 주행이 60초를 넘기면 배회 goal이 새로 전송되어 Nav2가 안내 goal을 preempt | `on_dest_result(success=True)`에서 타이머 명시적 취소 |
| STT 구독 생성 순서 | 모델 로딩 중 들어온 트리거 유실 | 모델 로딩 후 구독 생성 시 로딩 중 트리거를 받을 구독 자체가 없음 | 구독을 모델 로딩 전에 생성 |
| UI 화면 전환 타이밍 | 마이크가 실제로 열리기 전에 "듣고 있어요" 화면 표시 | 트리거 발행 시점에 즉시 화면 전환 | `/stt/listening_started`(마이크 실제 오픈 시점) 신호 분리 |
| 라이다 전체 무반응(`.inf`) | 시뮬레이터에서 벽을 전혀 인식 못 함 | 압출 폴리곤이 시계방향으로 감겨 벽 옆면 법선이 안쪽을 향함(back-face culling) | 폴리곤을 CCW로 강제 정렬 |

---

### 4. 기대효과

#### 4.1 초기 설계 대비 발전된 사항

원본 제안서 문서는 본 보고서 작성 시점에 별도로 대조하지 않았으나, 프로젝트 진행 중 초기 설계에서 아래와 같이 구체화·발전된 지점들이 문서와 코드로 기록되어 있다.

| 항목 | 초기 계획 | 현재 | 변경 원인 |
|---|---|---|---|
| STT 방식 | 온디바이스 또는 Gemini API 중 미정 | 온디바이스 Whisper(faster-whisper) + VAD 확정 | 음성 인식은 네트워크 왕복 지연을 감당하기 어려운 실시간성이 필요한 영역이라 로컬 추론으로 확정 |
| 음성 출력 | 사전 녹음 mp3 재생(룰베이스), 별도 패키지 없이 UI가 흡수 | `mov_tts` 패키지 재신설, Gemini TTS로 임의 텍스트 실시간 합성 + 로컬 캐싱 | 목적지명처럼 매번 달라지는 문장은 고정 mp3로 표현 불가능하다는 한계 확인, 이후 API 지연 문제는 캐싱으로 재해결 |
| 카테고리 목적지 처리 | 현재 위치 기준 최근접 좌표로 로봇이 자동 결정 | 후보가 여럿이면 사용자에게 모두 보여주고 직접 선택(단, 화장실·엘리베이터는 예외적으로 자동 최근접) | 로봇이 임의로 고르면 사용자 의도(브랜드 선호 등)와 어긋날 수 있다는 판단, 이후 목적 차이가 없는 카테고리만 다시 자동화 |
| 대기 중 동작 | 로드맵상 "전체 동작 FSM" 수준으로만 계획, 세부 미정 | `mov_fsm` 신설 — 응대하지 않는 시간엔 랜드마크 사이를 배회하다 호출 시 정지, Nav2 goal 경합 방지 설계까지 구현 | 대기 로봇이 그냥 서 있지 않고 실제 안내 로봇처럼 동작해야 한다는 요구 구체화 |
| 검증 환경 | 실기 우선 검증 | 실기 문제 발견 시 Ignition Gazebo 시뮬레이터로 소프트웨어/하드웨어 원인 분리 후 재검증 | 현장 localization 문제의 원인 특정이 실기 단독으로는 어려웠음 |
| 목표 도달 기준 | 표준 Nav2 기본값(0.25m) | 1.0m로 완화 | 실내 안내 로봇에 센티미터 단위 정밀 정지가 불필요하다는 현실적 판단 |

#### 4.2 기대효과

- **정량적**: 36개 실측 랜드마크 기준 목적지 해석 검증 완료, LLM 모델 벤치마크로 응답 지연 약 5배 단축(5.1초→0.94초), TTS 캐싱으로 반복 발화 지연 사실상 제거, 시뮬레이터 최적화로 real_time_factor 0.09→1.0 확보, Nav2 목표 허용 오차 현실화로 도착 판정 실패율 감소
- **정성적**: 화면·음성 이중 채널 안내로 시각/청각 접근성을 모두 고려한 안내 경험 제공, 응대 대기 중 배회 동작으로 로봇의 존재감·상호작용 유도 효과 기대, 한/영 다국어 지원으로 외국인 방문객도 이용 가능
- **팀 프로세스 측면**: `INTERFACES.md`를 3인 공동 소유 계약 문서로 관리하고 변경 이력을 draft 형태로 남기는 방식이, 서로 다른 담당자가 만든 모듈(예: 최가 배 담당 `mov_dest_resolver`에 위치 연동을 추가한 사례, 배가 최 담당 `mov_fsm`의 버그를 실기 테스트 중 발견한 사례)도 충돌 없이 통합·교차검증되게 하는 실질적 효과를 보였다.

---

## III. 참고 문헌

[1] Open Robotics, "ROS 2 Documentation: Humble," https://docs.ros.org/en/humble/

[2] Open Navigation, "Nav2 Documentation," https://docs.nav2.org/

[3] Google, "Cartographer ROS Integration Documentation," https://google-cartographer-ros.readthedocs.io/

[4] ROBOTIS, "TurtleBot3 e-Manual," https://emanual.robotis.com/docs/en/platform/turtlebot3/overview/

[5] Open Robotics, "Gazebo (Ignition Fortress) Documentation," https://gazebosim.org/docs/fortress

[6] Google, "Gemini API Documentation," https://ai.google.dev/gemini-api/docs

[7] NVIDIA, "Jetson Orin Nano Developer Kit," https://developer.nvidia.com/embedded/jetson-orin

[8] SYSTRAN, "faster-whisper: Fast inference engine for Whisper models," https://github.com/SYSTRAN/faster-whisper

[9] WebRTC Project, "WebRTC Voice Activity Detector (webrtcvad)," https://webrtc.org/

[10] Riverbank Computing, "PyQt5 Reference Guide," https://www.riverbankcomputing.com/static/Docs/PyQt5/
