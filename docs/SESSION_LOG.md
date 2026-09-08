# Session Log — Phase 0

이 문서는 Phase 0 진행 중 나눈 대화를 정리한 **결정 기록(decision log)**이다. `ARCHITECTURE.md`/`INTERFACES.md`/`ROADMAP.md` 등은 "지금 결정된 것"만 담지만, 여기는 **왜 그렇게 정했는지, 어떤 대안을 검토하고 버렸는지**까지 남긴다 — 나중에 같은 논의를 반복하지 않기 위한 용도. 팀원 온보딩이나 "왜 이렇게 했더라?" 싶을 때 참고.

---

## 1. 문서화 인프라 설계

**문제의식**: 매번 프롬프트에 프로젝트 배경을 자세히 안 써도 Claude Code가 알아서 맥락을 잡게 하고 싶다.

**결정**: 문서를 용도별로 분리하고, Claude Code가 세션마다 자동으로 읽는 `CLAUDE.md`(루트)에서 나머지 문서로 링크를 건다.

| 문서 | 역할 |
|---|---|
| `CLAUDE.md` (루트) | 세션마다 자동 로드. 핵심 규칙 + 문서 지도. `@docs/INTERFACES.md`는 항상 강제 로드 |
| `docs/ARCHITECTURE.md` | 시스템 기술 설명, 하드웨어, 패키지 구조, 노드 다이어그램 |
| `docs/INTERFACES.md` | 노드 간 통신 계약(토픽/서비스/액션/FSM) — 변경 시 전원 리뷰 필요한 "계약 문서" |
| `docs/ROADMAP.md` | Phase/Step별 구현 순서, 체크박스로 진행 추적 |
| `docs/TEAM.md` | 팀원별 담당 패키지, 소유권 규칙 |
| `docs/GIT_WORKFLOW.md` | 브랜치/커밋/PR 규칙 |
| `docs/PROMPTING_GUIDE.md` | Phase별 Claude Code 프롬프트 예시 |
| `docs/templates/PACKAGE_CLAUDE_TEMPLATE.md` | 패키지 생성 시 복사해서 쓰는 개별 `CLAUDE.md` 틀 |

패키지별로도 자체 `CLAUDE.md`를 두어, 그 폴더에서 작업할 때 루트 문서와 함께 자동 로드되게 한다.

---

## 2. 저장소/브랜드 정리

- 팀명은 **MovEdge**, 레포는 원래 `ecc-delivery-robot`(배송로봇 아이디어의 잔재)이었으나 현재 컨셉은 **음성 안내 로봇**이라 **`ecc-guide-robot`**으로 개명 (사용자가 로컬/원격 직접 변경 완료, GitHub 상 실제 리포명은 추후 변경 예정).
- ROS2 패키지 프리픽스는 `movedge_` 대신 **`mov_`**로 (장소보다 팀 브랜드 중심, 포트폴리오 시 다른 장소로 확장해도 자연스럽도록).
- Git 전략: **GitHub Flow** (main + 기능별 브랜치 + PR).
- 커밋 컨벤션: **Conventional Commits + 한글 설명** (`feat(nav): 동적 장애물 회피 로직 추가`).
- PR 규칙: **main 병합은 PR 필수**, 단 본인 담당 패키지만 건드리면 자가승인 가능. `mov_interfaces` 변경이나 타인 패키지 수정은 관련자 승인 필요.

---

## 3. 로드맵 설계

세 가지 버전을 비교했다:
- **순차형**: Phase 0~6을 한 줄로. 이해하기 쉽지만 ECC 매핑이 병렬 실구현을 막는 블로커가 됨.
- **트랙 분리형**: 지도(SLAM) 트랙과 소프트웨어(스켈레톤) 트랙을 분리, ECC 맵 나올 때까지 아무도 안 놀게.
- **마일스톤형**: Phase 대신 "완료 조건" 체크포인트 중심.

**최종 선택**: 순차형 + 4번(병렬 실구현)만 파트별(4-A/B/C)로 분해. 이후 각 Phase를 다시 **Step 1, 2, ...**로 세분화 (지금까지 한 문서화 작업 자체가 Phase 0 Step 1로 소급 체크됨).

**세션 단위 원칙**: **Phase 하나 = 세션(채팅) 하나**. 그 안의 Step들은 같은 세션에서 순서대로 처리. (`PROMPTING_GUIDE.md`에 Phase별 예시 프롬프트 정리됨 — "바로 구현해줘" 대신 "먼저 계획 제시 → 승인 → 하나씩 같이 진행" 패턴으로 작성.)

---

## 4. 패키지 구조 & 명명

**팀 구성**
| 팀원 | 담당 |
|---|---|
| 곽 | STT, 터치스크린 UI, 음성출력 |
| 최 | 네비게이션, 전체 시스템 통합/FSM, 하드웨어 디자인 |
| 배 | SLAM/맵, 랜드마크 좌표 DB, LLM API 연동 |

**패키지 명명 변천**
- `mov_system` → **`mov_fsm`** (역할을 FSM으로 명확히)
- `mov_landmark_llm` → **`mov_dest_resolver`** — "llm"이 이름에 박히면 구현 기술이 바뀔 때 이름이 안 맞아짐. 역할(목적지 해석) 중심으로 개명.
- **`mov_tts` 제거** — 룰베이스 mp3 재생 정도라 별도 패키지 없이 `mov_ui`가 흡수하기로 결정 (⚠️ 이 결정이 `TEAM.md`/`ARCHITECTURE.md`에는 아직 반영 안 됨 — 문서 캐치업 필요).

**최종 패키지 7개**: `mov_interfaces`, `mov_fsm`, `mov_navigation`, `mov_slam`, `mov_dest_resolver`, `mov_stt`, `mov_ui`

**turtlebot3_ws 관계**: 벤더 소스(turtlebot3, ld08_driver, coin_d4_driver)는 **참고용일 뿐 빌드/런타임 의존성이 아님**. `mov_*`는 공식 ROS2 apt 패키지에 의존하거나 직접 구현.

---

## 5. 인터페이스/아키텍처 설계 논의

**좌표계**: ROS2/Nav2 표준 그대로 (`map`/`base_link`/`odom`, meter/radian). 랜드마크 DB는 `map` 프레임 절대좌표로 저장 — ECC 맵 교체 시 원점이 바뀜에 유의.

**FSM: 중앙집중 vs 탈중앙화 논쟁**
- 사용자가 "FSM 없이 각 노드가 `/system/status`만 발행/구독하면 되지 않냐"고 제안.
- 검토 결과: 상태 *브로드캐스트*는 분산해도 되지만, **cancel/retry처럼 여러 단계에 걸친 로직**은 어딘가 한 곳에 있어야 함 — 안 그러면 3명이 각자 자기 패키지에 같은 로직(취소 판단)을 중복 구현하게 됨.
- **최종 결정**: `mov_fsm`은 유지하되, **1차 구현은 정순서(성공 경로)만** 처리 — cancel/retry/error 역방향 전이는 나중에 확장. 지금은 UI↔FSM↔{STT, dest_resolver, Nav2} 허브 구조를 기본 골격으로만 잡음.

**목적지 해석 로직 (`mov_dest_resolver`) — RAG 필요한가?**
- 질의 유형 두 가지: (1) 특정 장소명("스타벅스") — 목록이 작아 RAG 없이 LLM 프롬프트에 전체 목록 주고 매칭하면 충분. (2) 카테고리 최근접("가장 가까운 화장실") — 이건 검색/생성 문제가 아니라 **기하 계산 문제**. LLM은 카테고리만 추출하고, 실제 최근접 계산은 결정론적 코드가 담당 (LLM에 거리 계산 맡기면 할루시네이션 위험).
- **결론**: RAG 불필요. 2단계 구조(NLU로 intent/place_name/category 추출 → 결정론적 코드로 매칭 or 최근접 계산)로 충분.

**STT 결과가 왜 커스텀 메시지여야 하는가 — "성공"의 주체 구분**
사용자 질문: STT 자신이 뭘 근거로 성공/실패를 판단하나?
- **STT가 판단 가능**: 음향적 실패 (무음, API 에러) — 엔진이 이미 아는 정보를 구조화하는 것뿐.
- **STT가 판단하면 안 됨**: 의미적 타당성("이게 유효한 목적지인가") — 이건 `mov_dest_resolver`의 `success`/`error_message` 몫.
- **둘 다 아님**: 최종 사용자 확인 — `CONFIRMING` 상태에서 사람이 직접 판단, boolean으로 표현할 문제가 아님.
- `SttResult.msg`의 `success`는 **1번 의미로만 한정** — `.msg` 파일에 주석으로 범위 명시함.

---

## 6. 개발 환경 셋업

- ROS2 Humble이 이미 `/opt/ros/humble`에 설치돼 있고 `~/.bashrc`에도 소싱돼 있었음 (기존 turtlebot3_ws 빌드 이력으로 확인).
- 빠져 있던 `rosdep` 설치 (`sudo apt install python3-rosdep && sudo rosdep init && rosdep update`).
- `~/.bashrc`에 워크스페이스 단축 명령 추가 (사용자가 이름을 최종적으로 짧게 변경):
  - `cb` — 어디서든 `colcon build --symlink-install` + 현재 셸 재소싱
  - `ss` — 재소싱만
  - `bashrc` — `.bashrc` 반영
  - 새 터미널 열면 `ecc-guide-robot`이 빌드돼 있을 때 자동 소싱

---

## 7. 실습 진행 상황 — 패키지 스켈레톤

FSM의 취소/재시도/에러 분기는 잠시 미뤄두고, **정순서 체인만** 손으로 직접 구현하며 학습 중 (Claude는 설명만, 코드는 사용자가 직접 작성 — `mov_interfaces`부터는 일부 요청으로 Claude가 대신 작성).

체인: `mov_ui → mov_stt → mov_dest_resolver → Nav2 → mov_ui` (지금은 FSM 허브 없이 노드가 서로 토픽을 직접 구독하는 체인 방식으로 우선 진행)

| 패키지 | 상태 | 배운 개념 |
|---|---|---|
| `mov_ui` | ✅ 완료, 빌드/실행 검증됨 | Publisher, 타이머 콜백, `entry_points` 등록 |
| `mov_stt` | ✅ 완료, 빌드/실행 검증됨 | Subscriber (+ "self에 저장 안 하면 GC됨" 함정) |
| `mov_interfaces` | ✅ 완료, 빌드/검증됨 | `ament_cmake` + `rosidl_generate_interfaces`로 커스텀 메시지(`SttResult.msg`) 정의, `package.xml`의 `build_depend`/`exec_depend` 구분 |
| `mov_dest_resolver` | 🔄 진행 중 | Action Client (`ActionClient`, `send_goal_async`, `goal_response_callback` → `get_result_callback` 콜백 체인). Nav2 없이는 `wait_for_server()`에서 대기하는 게 정상 |
| `mov_fsm` | ⏳ 예정 | 오케스트레이션, 정순서만 |
| `mov_navigation`/`mov_slam` | ⏳ 예정 | 설정 위주 (Nav2/Cartographer 파라미터) |

각 단계 코드는 실제로 `colcon build` + `ros2 run` + `ros2 topic echo`로 빌드·실행 검증까지 거쳤음.

---

## 8. 남은 작업

1. `mov_dest_resolver` 완성 (Action Client 코드 마무리)
2. `mov_fsm` 스텁 (오케스트레이션, 정순서만)
3. `mov_navigation`/`mov_slam` 역할 정리
4. **문서 캐치업**: 지금까지 코드/대화로 확정된 것들을 `INTERFACES.md`(FSM 상태, 토픽/서비스/액션 계약, `SttResult.msg` 기록) · `ARCHITECTURE.md`(노드 다이어그램) · `TEAM.md`(`mov_tts` 제거)에 반영
5. Phase 0 Step 2 체크 → Phase 1(워킹 스켈레톤 · 시뮬레이터)으로 진행

관련 파일 위치는 전부 `docs/` 아래 (`ARCHITECTURE.md`, `INTERFACES.md`, `ROADMAP.md`, `TEAM.md`, `GIT_WORKFLOW.md`, `PROMPTING_GUIDE.md`), 패키지 코드는 `src/mov_*/`.

---

## 9. Phase 3 실측 테스트 중 localization 문제 발견 → 시뮬레이터 우선 검증으로 전환 (2026-08-28)

**상황**: ECC 실내 전체 주행으로 실측 맵(`slam/slam_frommap/out3/real.pgm`, `real.yaml`)을 확보한 뒤 현장에서 주행 테스트를 진행했으나, localization에서 문제가 발견됨.

**문제**: 원인이 Nav2/AMCL 파라미터·맵 품질 때문인지, 하드웨어(라이다 마운트, 오도메트리 드리프트 등) 때문인지 실기 위에서는 구분하기 어려움 — 변수가 뒤섞여 있어 반복 실험 비용이 큼.

**결정**: 이 실측 맵(real.pgm)을 그대로 Gazebo world로 압출해서, 시뮬레이터 상에서 전체 노드 체인(`mov_ui → mov_stt → mov_dest_resolver → Nav2 → mov_ui`)을 먼저 end2end로 검증하기로 함. Gazebo의 ground-truth pose와 AMCL 추정치를 비교해서, 시뮬레이터에서도 오차가 크면 Nav2/AMCL·맵 쪽 문제, 시뮬레이터에서는 깨끗하면 하드웨어/센서 쪽 문제로 원인을 격리할 수 있음.

**맵 범위**: 문제가 재현되는 위치가 아직 특정되지 않아, 부분 크롭 대신 real.pgm 전체를 압출하기로 함. Jetson Orin Nano 실시간 성능이 부족해지면 그때 압출 파라미터(폴리곤 단순화, headless 실행 등)로 최적화하는 순서로 진행.

**진행 방식**: 이 결정에 대한 설계(월드 변환 방식, 센서 스펙 매칭, localization 검증 방법)는 Claude가 설명하고, 실제 구현(world 변환, launch 파일, Nav2 설정)은 사용자(최, 본인 담당 트랙)가 직접 진행 — 학습 목적의 mentor 모드 적용. **단, "팀이 바쁘다"는 요청으로 이후 실제 파일 작성/디버깅은 Claude가 직접 수행하는 방식으로 전환함(2026-08-29).**

**Gazebo 시뮬레이터 구축 완료, 디버깅 기록 (2026-08-29)**:
- `mov_navigation` 패키지 신설. `urdf/turtlebot3_waffle_sim.urdf`(turtlebot3_description 지오메트리 + DiffDrive/gpu_lidar 플러그인 수동 추가, `turtlebot3_description`엔 gazebo 태그가 아예 없었음), `scripts/map_to_walls_world.py`(occupancy grid → Gazebo world 변환), `scripts/run_sim.sh`(월드+스폰+브리지 원샷 실행)
- **Gazebo Classic 대신 Ignition Gazebo Fortress(`ign gazebo`) 채택** — 이 Jetson arm64 저장소엔 `gazebo11`/`ros-humble-turtlebot3-gazebo`/`ros-humble-ros-gz-sim`이 전부 없음(iron/rolling엔 있는데 humble+arm64만 빌드팜 공백). `ros_gz_sim` 없이 `ign service`(EntityFactory) 직접 호출로 스폰, `ros_gz_bridge`의 `parameter_bridge`로 토픽 브리징
- **벽 압출 성능 문제**: real.pgm 전체(294m×208m) 픽셀 단위 압출 시 1552개 개별 collision shape → real_time_factor 0.09(10배 느림). `cv2.dilate`로 인접 벽 조각을 먼저 병합한 뒤 컨투어 추출하는 방식으로 226개까지 줄여서 real_time_factor 1.0 회복
- **Triangulation 실패**: Ignition의 polyline 압출기가 오목한(concave) 폴리곤에서 자주 실패(`Unable to extrude mesh`) — shapely `buffer(0)` 자기교차 복구만으론 부족했고, **모든 폴리곤을 convex hull로 대체**하는 것으로 해결(1552개 중 54개 실패 → 226개 중 1개만 실패, 무시 가능한 수준)
- **라이다가 벽을 전혀 못 잡는 문제(`/scan` 전부 `.inf`)**: 스폰 위치·범위 문제가 아니었고, Ignition 공식 예제 world로 렌더링 환경 자체는 정상 작동함을 확인, 박스 같은 일반 primitive는 동적 스폰 로봇도 잘 감지함을 확인 → **원인은 우리 폴리곤이 전부 시계방향(CW)으로 감겨있어서 압출된 벽 옆면의 법선이 안쪽을 향했고, back-face culling 때문에 gpu_lidar의 depth 렌더 패스에서 안 보였던 것**. shapely `orient(sign=1.0)`로 전부 반시계(CCW) 방향으로 강제 통일해서 해결
- 스폰 위치는 여전히 임의값(자유공간 아무 곳) — 실제 로봇이 실측 주행을 시작했던 지점과는 무관, 나중에 알게 되면 교체 필요

**Why**: 실기에서 하드웨어 문제와 소프트웨어 문제를 뒤섞은 채로 계속 튜닝하면 원인 파악이 어려움 — 시뮬레이터로 변수를 하나 줄이는 게 더 빠르고 확실함.

**진행 중 발견 (2026-08-29)**: 이 Jetson arm64 저장소엔 **Gazebo Classic이 아예 없고** (`gazebo11`/`ros-humble-gazebo-ros-pkgs`/`ros-humble-turtlebot3-gazebo` 전부 미존재), 대신 **Ignition Gazebo Fortress(`ign gazebo` 6.18.0)** + `ros_gz_bridge`/`ros_gz_image`/`ros_gz_interfaces`가 설치돼 있음. 다만 `ros-humble-ros-gz-sim`과 `ros-humble-ros-gz` 메타패키지는 humble+arm64 조합에서 빌드팜 공백으로 안 올라와 있어(iron/rolling엔 있음) — 표준 `ros_gz_sim` 스폰 launch 유틸을 못 씀. **결정**: 소스 빌드 대신 `ign service`(EntityFactory) 직접 호출로 스폰 + `ros_gz_bridge`의 `parameter_bridge`로 토픽 브리징을 손으로 구성하는 방식 채택.

또한 `ros-humble-turtlebot3-description`의 URDF(`turtlebot3_waffle.urdf` 등)에는 **Gazebo 관련 태그가 전혀 없음** (공식 `turtlebot3_gazebo` 패키지가 따로 그 역할을 하는데, 그 패키지 자체가 이 저장소에 없음) — 그래서 `mov_navigation/urdf/turtlebot3_waffle_sim.urdf`에 지오메트리는 그대로 복사하고 DiffDrive/gpu_lidar 플러그인을 새로 추가해서 만듦. 바퀴 간격(0.288m)·반지름(0.033m)은 원본 URDF의 joint origin/collision에서 실측.

**진행 방식 변경**: 원래 [[feedback-mentor-mode]]대로 설계만 안내하고 사용자가 직접 구현하는 방식으로 시작했으나, "팀이 바쁘다"는 사용자 요청으로 이 시뮬레이터 셋업 작업은 Claude가 직접 파일을 작성하고 설명하는 방식으로 전환함 (2026-08-29). `mov_navigation` 패키지(ament_cmake)를 새로 만들어 `urdf/`, `worlds/`에 시뮬레이션 자산을 두는 구조로 시작.

---

## 10. 실기 Nav2 검증 완료 → end-to-end 연결, 배회(mov_fsm) 신설, 최근접 위치 연동 (2026-09-01)

**상황**: ECC 실측 맵을 다시 딴 `mapjh.pgm`/`mapjh.yaml`로 실기에서 `turtlebot3_bringup robot.launch.py`
+ `nav2_bringup bringup_launch.py`를 수동으로 띄워보니 Nav2가 정상 동작함을 확인. 그동안 막혀있던
마지막 조각(Nav2 풀스택 부재)이 풀려서, 이미 완성돼 있던 소프트웨어 체인(mov_ui↔mov_stt↔
mov_dest_resolver↔Nav2 ActionClient)과 합쳐 실사용자용 end-to-end를 구성.

**launch 구조**:
- `src/mov_navigation/launch/real_bringup.launch.py` (신규) — 위 두 수동 커맨드를 하나로. 하드웨어
  안정화 시간을 벌기 위해 Nav2를 5초 지연 시작.
- `launch/full_system.launch.py` (신규) — `real_bringup.launch.py` + `launch/app.launch.py`를 합친
  최종 진입점.
- `src/mov_navigation/scripts/run_full_real.sh` + `cleanup_real.sh` (신규) — `run_full_sim.sh`/
  `cleanup_sim.sh`와 동일 패턴. 실기 버전도 터미널 종료 시 프로세스 트리가 안 죽는 동일한 위험이
  있어(cleanup_sim.sh 참고) 예방적으로 같이 만듦.
- 로봇 시작 위치(AMCL 초기 pose)는 아직 자동화 안 함 — `set_initial_pose: false`라 부팅마다 RViz
  "2D Pose Estimate"로 수동 지정 필요. 사용자가 "맨 처음에만 RViz로 찍고 그 이후엔 자동"을
  원한다고 확인함 — 즉 초기 pose 수동 지정은 의도된 동작(자동화 대상 아님).

**mov_fsm 신설 (ROADMAP Phase 4-B Step 3, 최 담당)**: "도착 후 가만히 있지 말고, 필요하면 랜덤하게
돌아다니다가 사용자가 부르면 멈춘다"는 요구사항 반영.
- 기존 mov_ui/mov_stt/mov_dest_resolver 직접 토픽 체인은 안 건드림(중앙 허브로의 재배선은 범위
  밖 — #7의 "정순서만" 결정 유지). `mov_fsm`은 기존 토픽(`/stt/start_listening`,
  `/dest_resolver/result`, `/navigation/result`)을 추가로 구독만 해서 그 위에 배회 행동만 얹음.
- Nav2 goal 경합 방지: `dest_resolver_node`와 `mov_fsm`이 각자 별도 `navigate_to_pose`
  ActionClient를 갖되, PAUSED 상태가 "말하기 버튼 시점"부터 "실제 주행 결과 또는 목적지 해석
  실패"까지 걸쳐 있게 설계해서 두 노드가 동시에 활성 goal을 가질 일이 없게 함.
- 안전장치: CONFIRMING 화면에서 확인도 취소도 아닌 경로로 빠져나가는 경우처럼(INTERFACES.md
  기준 그 경로엔 발행 토픽이 없음) FSM이 못 보는 채로 상호작용이 끝날 수 있어, 60초 타임아웃
  뒤엔 무조건 배회 재개하는 안전장치를 넣음.
- 배회 목표는 `landmarks.csv`에서 랜덤 선택. `mov_dest_resolver.resolver_core.load_landmarks()`를
  재사용하지 않고 `mov_fsm/landmarks.py`에 이름/좌표만 읽는 최소 로더를 따로 둠 — google-genai
  의존성 없이 배 담당 패키지 내부 구현에 결합되지 않게 하기 위함.
- 실기에서 배회 동작 자체는 아직 미검증(코드/빌드/import만 확인).
- **초기 위치 게이트 추가(같은 날, 사용자 질문으로 발견)** — 최초 버전은 노드 시작 즉시
  배회를 시작해서, `full_system.launch.py`로 한 번에 띄우면 사용자가 RViz로 초기 위치를
  찍기도 전에(AMCL이 `initial_pose: {x:0,y:0,yaw:0}` 기본값 상태일 때) 엉뚱한 좌표로
  이동을 시도할 수 있는 버그였음. `/initialpose`(RViz "2D Pose Estimate" 발행 토픽)를
  구독해서 최소 한 번 들어오기 전까지는 배회를 시작하지 않도록 게이트 추가 — "맨 처음
  1회 수동 위치 지정 → 그 이후 자동 배회"가 이제 코드로 보장됨.

**최근접 위치("가장 가까운 화장실/엘리베이터") 연동**: `resolver_core.resolve()`는 8/30부터 이미
`current_x`/`current_y`를 받게 설계돼 있었으나 `dest_resolver_node.py`가 계속 위치 없이 호출해서
실질적으로 항상 후보 나열로 귀결됐음(Nav2/AMCL이 어디에도 안 떠 있었으니 위치 소스가 없었음).
이번에 Nav2가 실기에 붙은 김에 `dest_resolver_node.py`가 `/amcl_pose`를 구독해 최신 위치를 들고
있다가 `resolve()` 호출 시 넘기도록 고침. `landmarks.csv`에 화장실 5개/엘리베이터 7개 후보가 이미
있어 "제일 가까운 화장실" 같은 발화가 이제 실제로 최근접 계산으로 이어짐. **mov_dest_resolver는
배 담당 패키지 — 곽/배 리뷰 전.**

**Nav2 tolerance 조정**: `controller_server.goal_checker.xy_goal_tolerance`를 0.25m → 1.0m로 완화
(사용자 요청, "현실 기준"). 실내 AMCL 오차/좁은 통로에서 0.25m는 너무 빡빡해서 도착 판정이 잘 안
나던 문제 — 안내 로봇 특성상 센티미터 단위 정밀 정지가 필요 없어서 1m로 완화.

**진행 방식**: SESSION_LOG #9에서 "팀이 바쁘다"는 이유로 이미 mentor 모드에서 Claude 직접 구현
방식으로 전환된 상태를 유지 — 이번 세션도 설계는 Claude가 제안하고 사용자가 확인/방향 결정 후
Claude가 코드까지 작성함.

**Why**: 계속 미뤄지던 "실제 사용자가 쓸 수 있는 하나의 진입점"을 Nav2 검증 완료를 계기로 완성.
mov_fsm은 로드맵상 계획돼 있었지만(1차 구현은 정순서만) 계속 스텁도 없던 상태였는데, "배회"
요구사항이 그 첫 실질적 구현 계기가 됨.

**How to apply**: 다음 검증은 실기에서 `real_bringup.launch.py` 단독 → `full_system.launch.py`
순서로. `mov_dest_resolver` 변경은 배 리뷰 후 반영. `docs/ROADMAP.md`는 아직 안 건드림 — 실기
검증 끝나면 Phase 5 Step 1(통합 e2e) 체크 여부 판단할 것.

---

## 11. mov_fsm(배회) 비활성화 상태 — 문서 미기록 발견 (2026-09-02)

**상황**: end-to-end 실기 테스트 준비 중 정적 점검 과정에서, `launch/app.launch.py`의 주석에
`mov_fsm` Node 블록이 현재 빠져있다는 사실을 발견함. 이 변경은 SESSION_LOG.md #10(mov_fsm
신설 기록) 이후에 일어난 것으로 보이나, 어디에도(ROADMAP.md/SESSION_LOG.md) 기록되지 않은 채
코드에만 반영돼 있었음 — 문서가 코드를 못 따라간 사례.

**사실(코드로 확인됨)**: `app.launch.py`에는 현재 `mov_stt`/`mov_dest_resolver`/`mov_ui` 3개
Node만 있고 `mov_fsm`은 빠져 있음. 패키지 자체(`src/mov_fsm/`)는 그대로 남아있고 빌드도 돼
있음 — launch에서만 제외된 상태.

**원인(추정, 미검증)**: 코드 주석에는 "`mapjh.pgm`의 중앙 복도가 지도상 unknown(선큰가든
no-go 구역)으로 비어있어서 배회 목표 선정이 계속 planning 실패를 반복했기 때문"이라고 적혀
있음. **단, 이 인과관계는 실제로 로그/재현으로 검증된 것이 아니라 추정임** — 다른 원인(예:
초기 위치 게이트, Nav2 파라미터, 특정 랜드마크 좌표 자체의 접근 불가 등)일 가능성도 배제할
수 없음. 다시 켜기 전에 실제 실패 로그로 이 가설부터 확인할 것.

**Why**: 원인을 검증된 사실처럼 기록해두면 나중에 이 이슈를 다시 여는 사람이 잘못된 가설을
전제로 삼고 엉뚱한 곳을 고칠 위험이 있음 — 그래서 "무엇을 껐는지"(사실)와 "왜 껐다고
추정하는지"(가설)를 분리해서 남김.

**How to apply**: `mov_fsm`을 다시 켤 때는 (1) 실제 planning 실패 로그를 먼저 재현/확인,
(2) 위 가설(중앙 복도 unknown 구역)이 맞는지부터 검증, (3) 맞다면 지도의 해당 구역 처리
방식(`GAZEBO.md`의 `map_to_walls_world.py` 관련 unknown 처리 로직 참고) 또는 배회 목표 후보
선정 로직(`mov_fsm/landmarks.py`)에서 no-go 구역 필터링을 검토. `docs/ROADMAP.md` Phase
4-B Step 3는 "1차 구현" 기준으로는 체크 유지 — 이번 비활성화는 그 이후의 별도 이슈로 취급.

---

## 11. mov_tts 재도입 — Gemini TTS로 실시간 음성 합성 (2026-09-02)

**상황**: 원래 Phase 0 설계 당시 `mov_tts`가 있었으나, "룰베이스 mp3 재생 정도"라는 이유로
별도 패키지 없이 `mov_ui`가 흡수하기로 결정했었음(#3 근처, TEAM.md에서 `mov_tts` 제거).
실제로는 그 결정 이후 `mov_ui`에 오디오 재생 코드가 전혀 구현되지 않은 채 방치돼 있었음
(`ui_node.py`/`main_window.py`에 mp3/audio 관련 코드 전무, 코드로 재확인함).

**결정**: 목적지명처럼 매번 달라지는 문장("OO로 안내를 시작합니다")을 말하려면 고정 mp3로는
부족하다는 이유로, Gemini TTS API로 임의 텍스트를 그때그때 합성하는 방식으로 `mov_tts`를
별도 패키지로 재도입.

**API 확인**: Gemini TTS는 텍스트 분류에 쓰던 `client.models.generate_content`가 아니라
**`client.interactions.create`(Interactions API, google-genai 2.20.0 기준 존재 확인)**로 호출.
`generation_config.speech_config`는 dict가 아니라 **리스트**로 넘겨야 함(`[{"voice": "Kore"}]`)
— dict로 넘기면 400 에러, 실제 API 호출로 두 형태 다 테스트해서 확인함. 모델은
`gemini-3.1-flash-tts-preview`. 응답의 `output_audio`는 24kHz mono 16bit PCM을 base64로
담고 있어서 WAV로 감싸 `aplay`(ALSA CLI, 이미 설치돼 있음)로 재생 — 별도 오디오 라이브러리
의존성 추가 안 함. 한국어 문장("화장실로 안내를 시작합니다.")으로 실제 합성 성공 확인.

**인터페이스**: `/tts/speak`(신규, `std_msgs/String`) 하나만 추가. 노드 자체(구독→합성→재생)만
구현했고, **어느 노드가 언제 무슨 문구를 발행할지는 의도적으로 안 정함** — UX 문구/타이밍
결정이라 곽 담당(`mov_tts`는 TEAM.md상 원래도 곽 담당 트랙)으로 남겨둠. 지금은
`ros2 topic pub`으로 수동 테스트만 가능.

**진행 방식**: `mov_dest_resolver`(배 담당) 건드릴 때와 동일하게, 이것도 곽 담당 패키지를
최가 먼저 인프라만 구현한 것 — TEAM.md 규칙상 PR 전에 곽에게 알릴 것.

**Why**: 사용자가 원래 설계에 있던 TTS를 다시 요청 — 이번엔 룰베이스가 아니라 dest_resolver와
같은 패턴(Gemini API, `.env`의 `GEMINI_API_KEY` 재사용)으로 구현.

**추가(같은 날)**: 사용자가 정확한 트리거 두 개를 지정 — 목적지 안내 시작 시 "OO로 안내를
시작합니다"(목적지명 동적 삽입), 도착 시 "도착했습니다". `mov_ui`의 `on_dest_result`(성공)/
`on_nav_result`(성공)에 `/tts/speak` 발행을 추가해서 바로 와이어링함 — 조사(로/으로)는 마지막
한글 음절 받침 유무로 자동 선택하는 헬퍼(`_destination_particle`)를 넣어서 `landmarks.csv`
36개 전부(괄호/영문 섞인 이름 포함) 정상 처리되는지 확인. 소리 출력은 로봇에 붙은
디스플레이(HDMI 오디오)로 나가야 한다고 확인받아서, `tts_node`에 `TTS_AUDIO_DEVICE` 환경변수로
ALSA 장치를 지정할 수 있게 추가함(정확한 카드 번호는 아직 실기에서 확인 안 됨).

**How to apply**: 곽이 `mov_ui`의 이 임시 문구/트리거를 검토·확정. 스피커로 쓸 정확한 ALSA 카드(로봇에 여러 출력 장치 존재 —
`aplay -l` 참고)도 실기에서 확인 필요.

---

## 12. mov_tts 캐싱 + 랜드마크 전체 사전 합성 (2026-09-03)

**상황**: 실기 TTS 테스트 중 발화당 API 왕복이 6~8초(가끔 그 이상)로 체감 지연이 컸음. 반면
실제 발화 문구는 "도착했습니다"(고정) + "OO(로/으로) 안내를 시작합니다"(장소명만 바뀌는
템플릿, 후보는 `landmarks.csv` 36개뿐)라 사실상 종류가 유한함.

**결정**: (모델, 보이스, 텍스트) 조합을 키로 합성 결과 WAV를 `TTS_CACHE_DIR`(기본
`~/.cache/mov_tts`)에 영구 캐싱하도록 `tts_node.py` 수정. 같은 문장 재요청 시 API 호출 없이
캐시 파일 바로 재생. 캐시 파일은 임시 경로에 완성한 뒤 `os.replace`로 원자적으로 옮겨서,
합성 도중 실패해도 캐시 자리에 손상된 파일이 안 남게 함. 캐싱/합성 로직은 `ensure_cached()`/
`cache_path()`로 모듈 함수화해서, `TtsNode.on_speak`과 별도 예열 스크립트가 같은 로직을
공유하게 함(둘이 캐시 키 계산 방식이 어긋나는 걸 방지).

**예열 스크립트**: `src/mov_tts/scripts/prewarm_cache.py` 추가. 문구를 직접 재구현하지 않고
`mov_ui.ui_node._build_navigating_speech`/`_build_arrived_speech`(다른 세션에서 추가된 영어
i18n 로직 포함)를 그대로 import해서 써서, 실제 런타임이 만드는 문구와 100% 일치하도록 함.
화장실/엘리베이터는 `AUTO_NEAREST_CATEGORIES`라 카테고리명으로만 말하므로(개별 랜드마크
무관) 실질 54개 문구(장소 24개×2언어 + 카테고리 2개×2언어 + "도착했습니다"×2언어)로 수렴,
전부 캐싱 완료(2026-09-03 실행 완료 확인). `gemini-3.1-flash-tts`가 분당 10건 쿼터라 동시
요청 5개로 처음 돌렸을 때 429(rate limit) 에러가 실제로 발생함을 확인 — 순차 처리 +
API 에러 메시지의 "retry in Ns" 안내를 그대로 따르는 재시도로 재구현해서 54개 전부 성공시킴.

**Why**: 사용자가 "랜드마크들에 대해 캐싱이 되게끔 미리 돌려두고 싶다(한국어/영어 둘 다)"고
요청. 캐싱 자체는 그 전 세션에서 이미 사용자 승인받아 구현된 상태였고, 이번엔 그 캐시를
실사용 전에 다 채워두는 운영 스크립트를 추가한 것.

**How to apply**: `landmarks.csv`가 바뀌면(장소 추가/삭제) `prewarm_cache.py` 재실행해서
캐시 갱신 필요. `mov_tts`는 곽 담당 패키지라 이 변경들 곽 리뷰 필요 — 아직 안 받음.

---

## 13. 실기 안정성 버그 3종(마이크/UI/Whisper) + USB 허브로 인한 오디오 장치 번호 변경 (2026-09-03)

**상황**: 실기 end-to-end 반복 테스트 중 "말하기 취소 후 재시도해도 다음 화면으로 안 넘어감",
"말을 했는데도 인식 결과가 안 나오거나 빈 문자열로 나옴", "젯슨이 테스트 도중 반복적으로
재부팅됨"이 겹쳐서 나타남. 아래는 각각 확인된 사실과, 아직 확인되지 않은 추정을 분리해서
기록한다 — 특히 마지막 재부팅 원인은 **추정이며 실측으로 검증되지 않았음**에 주의.

### 13-1. 마이크 캡처 무한 대기 (확인됨)

`mov_stt/stt_node.py`가 `sounddevice.RawInputStream.read()`를 타임아웃 없이 블로킹 호출하고
있었음. 실기에서 이 호출이 멈추는 걸 재현 확인함(로그상 "STT 트리거 수신, 녹음 시작" 이후
`STT Node`가 이후 트리거를 전혀 처리하지 못하고, `ros2 launch`가 Ctrl+C에 반응 못 해 SIGKILL로
강제 종료해야 했음 — `launch.log`에 SIGINT→SIGTERM→SIGKILL 에스컬레이션 기록 남음). ROS2
단일 스레드 executor 특성상 이 콜백이 안 끝나면 이후 모든 "말하기" 트리거가 큐에 쌓인 채
영원히 처리 안 됨(UI 취소 버튼도 화면만 바꿀 뿐 이 상태를 못 끊음).

**수정**: 캡처를 `subprocess`(`arecord`)로 옮기고, `select()` 기반으로 프레임(30ms)당 읽기
타임아웃(3초)을 걸었음. 멈추면 프로세스를 `kill()`하는데, `kill()`을 보내도 커널 레벨(D-state)에서
안 죽을 수 있어(실기에서 SIGKILL 후에도 프로세스가 바로 안 사라지는 걸 확인함) `proc.wait()`에도
타임아웃(5초)을 걸어, 최악의 경우도 콜백이 반드시 끝나게 함(좀비로 남을 순 있음).

### 13-2. `mov_ui` SIGABRT 크래시 (원인은 추정)

**확인된 사실**: `ui_node` 프로세스가 실기 테스트 중 exit code -6(SIGABRT)으로 죽는 걸
`launch.log`에서 확인함.

**원인(추정, 미검증)**: PyQt5(5.5+)는 슬롯(여기선 `QTimer`→`rclpy.spin_once()`로 실행되는
ROS 콜백 전부 포함) 안에서 처리 안 된 Python 예외가 발생하면, `sys.excepthook`이 따로
설정돼 있지 않은 한 프로세스 전체를 abort시키는 것으로 알려져 있음 — exit code -6은 이 패턴과
일치함. 다만 **실제로 어떤 예외가 어느 코드 경로에서 발생했는지는 확인하지 못함** —
`ui_node`는 `output="screen"`이라 터미널에만 출력되고 로그 파일로 안 남아서, 크래시 순간의
실제 트레이스백을 확보하지 못했음. 즉 "PyQt5의 이 알려진 동작 때문"이라는 건 exit code가
들어맞는 정황 증거이지, 트레이스백으로 확인된 사실이 아님.

**수정**: `mov_ui/ui_node.py`의 `main()`에 `sys.excepthook`을 설치해서, 처리 안 된 예외가
나도 로그만 남기고 프로세스는 계속 돌게 함. 이 수정은 "무슨 예외인지"와 무관하게 증상(UI
전체 크래시)은 막지만, 근본 원인이 된 예외 자체를 고친 것은 아님 — 재발 시 이번엔
`sys.excepthook`이 실제 트레이스백을 로그에 남길 것.

### 13-3. Whisper 전사(`_transcribe`) 무제한 대기 (확인됨)

마이크 캡처 쪽을 고친 뒤에도 "말은 했는데 화면이 안 넘어감" 증상이 재현됨. 실측으로 원인을
추적한 결과 `_transcribe()`(Whisper CPU 추론) 자체엔 타임아웃이 없어서, 특정 오디오(VAD가
배경 소음을 발화로 오탐지해 녹음된, 실제로는 사람 말이 아닌 오디오)에서 **234초**까지 걸리는
걸 직접 재현 확인함(프로세스가 죽지 않고 지속적으로 CPU를 쓰며 234초 후 빈 문자열 결과를
발행함).

**수정**: `_transcribe` 호출을 `ThreadPoolExecutor`에 던지고 타임아웃을 건 뒤, 넘으면 포기하고
실패 결과를 발행하도록 함. ctranslate2 네이티브 호출이라 스레드 자체는 강제 종료할 방법이
없어서, 포기된 스레드는 백그라운드에서 계속 CPU를 쓰며 도는 채로 둠(13-4 참고). 타임아웃을
처음 20초로 잡았다가, 실기에서 정상적으로 성공한 케이스가 25.6초 걸린 적이 있는 걸 사용자가
제공한 로그에서 확인해서 **40초로 상향**함 — 20초는 정상 케이스까지 실패로 처리하는 문제가
있었음.

### 13-4. Whisper CPU 스레드 미제한 + 재부팅 (인과관계는 추정, 미검증)

**확인된 사실**: 실기 테스트 도중 load average가 6코어 기기에서 **52**까지 치솟은 걸
확인했고, 그 직후 젯슨이 재부팅됨(호스트 uptime으로 확인). 사용자에 따르면 이런 재부팅이
이번 세션 동안 반복됐음. 로그상 여러 번의 느린 Whisper 전사(13-3)가 짧은 시간에 겹쳐 발생한
정황이 있었음.

**원인(추정, 미검증)**: `faster-whisper`/`ctranslate2`는 `cpu_threads` 기본값(0)일 때 추론
한 번에 사용 가능한 코어를 거의 다 쓰는 것으로 알려져 있음. 13-3에서 타임아웃 시 스레드를
"포기"(강제 종료 아님)하는 방식으로 고쳤기 때문에, 느린 전사가 여러 번 겹치면(포기된 것 +
새로 시작한 것) 코어 6개짜리 기기에서 스레드 여러 개가 코어를 두고 경쟁해서 load average가
비정상적으로 치솟을 수 있다는 게 추정 근거임. **다만 재부팅 발생 시점에 실제로 어떤 스레드가
몇 개나 떠 있었는지, CPU가 정확히 어떻게 나뉘어 쓰였는지는 직접 측정하지 못했고, 재부팅이
전압 강하(브라운아웃) 때문인지 다른 이유(열 문제 등) 때문인지도 확인하지 못했음** — 시간상
상관관계와 일반적으로 알려진 메커니즘에 기반한 추정.

**수정**: `WhisperModel` 생성 시 `cpu_threads=2`로 명시 제한하고, 전사용 `ThreadPoolExecutor`의
`max_workers`도 4→2로 낮춤. 이 추정이 100% 정확하지 않더라도, ctranslate2 기본 동작이
무제한으로 코어를 쓸 수 있다는 것 자체는 확인된 사실이라 이 수정은 재부팅 원인 여부와
무관하게 유효한 안전장치임.

### 13-5. USB 허브 연결 후 ALSA 카드 번호 변경 (확인됨)

**상황**: 사용자가 ReSpeaker 마이크를 젯슨 USB 포트 직결에서 USB 허브 경유로 배선을 바꿈.

**확인된 사실**: `arecord -l`/`cat /proc/asound/cards`로 확인한 결과 ReSpeaker의 카드 번호가
0→3으로, 다른 장치(정체불명의 "Jieli Technology USB Composite Device")가 card 0을 차지하게
바뀌었음. 디스플레이 오디오(HDA)도 card 1→2로 밀림(`aplay -l`로 확인). `mov_stt`/`mov_tts`
코드가 카드 번호를 숫자로 고정(`plughw:0,0`, `plughw:1,3`)해두고 있어서, 이 변경 이후
ReSpeaker가 아니라 허브의 다른 장치를 잡아 녹음하고 있었음 — VAD는 그 신호에도 반응해서
녹음은 진행됐지만, Whisper엔 사람 음성이 아니어서 빈 결과/이상한 결과로 이어졌던 것으로
보임(이 인과관계는 카드 번호 수정 후 정상 인식되는 걸 확인한 것으로 뒷받침되지만, 수정 전
캡처된 오디오 자체를 직접 청취/분석해서 "허브의 다른 장치 신호였다"를 직접 증명하지는
않았음 — 카드 번호 불일치라는 사실과, 수정 후 정상 동작한다는 사실로부터의 추론임).

**수정**: `STT_AUDIO_DEVICE`/`TTS_AUDIO_DEVICE` 기본값을 카드 번호(`hw:N,M`) 대신 카드 이름
(`plughw:CARD=ArrayUAC10,DEV=0`, `plughw:CARD=HDA,DEV=3`) 기반으로 변경 — USB 재열거 순서가
바뀌어도 카드 이름은 드라이버가 고정 부여해서 안 바뀜. 수정 후 실기에서 사용자가 정상 인식
확인함("확인했어. 되네.").

**Why**: 이 항목 전체 — 사용자가 실기에서 반복 재현한 문제를 세션 동안 하나씩 진단/수정한
기록. 특히 13-2, 13-4는 근본 원인을 완전히 확인하지 못한 채 증상 대응 수정만 반영된
상태라는 걸 명시적으로 남긴다 — 나중에 같은 증상이 재발하면 "이미 고친 버그가 재발한 것"이
아니라 "가설이 틀렸을 가능성"부터 의심할 것.

**How to apply**: `mov_stt`/`mov_ui`는 곽 담당 패키지라 이 변경들 곽 리뷰 필요 — 아직 안 받음.
재부팅이 계속되면 (1) USB 허브를 유전원(powered) 허브로 바꾸거나 마이크를 젯슨에 직결,
(2) 재부팅 시점에 `dmesg`/전원 관련 커널 로그를 실제로 확보해서 13-4의 추정을 검증할 것.

---

## 14. `cleanup_real.sh`가 컴포저블 Nav2 컨테이너를 못 잡던 버그 (2026-09-03)

**상황**: `run_full_real.sh`로 재실행했더니 RViz에 맵이 안 보임(전에는 계속 보였음).

**확인된 사실**: `nav2_container`(`component_container_isolated` 프로세스)가 **두 개** 동시에
떠 있었음 — 이전 실행의 것이 안 죽고 남아있었음. `map_server`/`amcl`이 중복 실행되면서 토픽이
꼬여 RViz가 맵을 못 받은 것으로 보임(중복 프로세스를 정리하니 맵이 다시 보이는 것으로 확인).

**원인**: `mov_navigation/scripts/cleanup_real.sh`의 kill 패턴(`nav2_map_server/map_server`,
`nav2_amcl/amcl` 등)이 각 서버가 **독립 실행 파일**이라고 가정하고 있었는데, 실제
`nav2_bringup`은 기본적으로 composition을 써서 `map_server`/`amcl`/`controller_server` 등이
전부 `component_container_isolated`라는 프로세스 하나에 플러그인으로 로드됨 — 이 프로세스의
실제 커맨드라인엔 "map_server" 같은 문자열이 안 나타나서 기존 패턴이 절대 매치되지 않았고,
그 결과 재실행할 때마다 이 컨테이너가 orphan으로 계속 쌓이는 구조였음. 같은 이유로
`mov_tts/tts_node`도 kill 패턴에 빠져 있어서 중복 재생 문제로 이어질 수 있었음.

**수정**: `component_container_isolated`와 `mov_tts/tts_node` 패턴을 kill 목록에 추가.

**Why**: `cleanup_real.sh` 자체의 주석에 이미 "Ctrl+C가 전체 프로세스 트리에 전파 안 돼서
orphan이 남는다"는 배경이 적혀 있었음(스크립트를 만들게 된 원래 이유) — 이번 건 그 스크립트
자체의 매칭 패턴이 nav2_bringup의 composition 기본 동작과 안 맞았던, 별도의 새 버그.

**How to apply**: `mov_navigation`은 최 담당 패키지라 이 변경 최 리뷰 필요 — 아직 안 받음.
Nav2 kill 패턴에 새 서버(예: 새 lifecycle 노드)가 추가되면, composition을 쓰는지 먼저 확인하고
독립 실행 파일 이름이 아니라 `component_container_isolated`로 잡히는지부터 볼 것.
