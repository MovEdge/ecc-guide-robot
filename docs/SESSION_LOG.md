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
