# Roadmap

전체 구현 순서. 각 Phase는 Step 단위로 세분화되어 있다. **Phase 하나가 보통 세션(채팅) 하나의 단위**이고, 그 안의 Step들은 같은 세션에서 순서대로 처리한다 — [PROMPTING_GUIDE.md](PROMPTING_GUIDE.md) 참고. 완료된 Step은 체크하고, 끝날 때마다 이 문서를 갱신한다.

## Phase 0 — 규칙설계 (공통)

- [x] Step 1. 문서화 인프라 구축 — 저장소 이름/구조 정리, `CLAUDE.md` 및 `docs/`(ARCHITECTURE·INTERFACES·ROADMAP·TEAM·GIT_WORKFLOW·PROMPTING_GUIDE) 작성, 패키지 CLAUDE.md 템플릿 준비
- [ ] Step 2. 입출력 인터페이스 규칙 + 로봇 상태 FSM + 노드 통신 구조 정하기 (좌표계 규약, 토픽/서비스/액션 계약 → [INTERFACES.md](INTERFACES.md), FSM과 노드 다이어그램 → [ARCHITECTURE.md](ARCHITECTURE.md))

## Phase 1 — 워킹 스켈레톤 · 시뮬레이터

> **2026-08-28 변경**: 테스트맵 대신 ECC 실측 맵(`slam/slam_frommap/out3/real.pgm`+`real.yaml`, Phase 3 산출물)을 그대로 사용하는 것으로 방향 전환. 현장 주행 테스트에서 localization 문제가 발견되어, Nav2/AMCL 설정 문제인지 하드웨어 문제인지 시뮬레이터에서 먼저 격리 검증하기 위함(전체 맵 압출로 진행, 부분 크롭 아님). 배경/이유는 `SESSION_LOG.md` 9번 항목 참고.

- [x] Step 1. ECC 실측 맵(real.pgm) → Gazebo world 변환(occupancy grid 압출) + TurtleBot3 스폰, 실제 라이다 스펙에 맞춘 센서 plugin 설정 — `mov_navigation/scripts/map_to_walls_world.py`로 226개 collision shape 생성, real_time_factor 1.0 확인 (2026-08-29). 라이다 range/샘플은 표준 LDS-01 참고값 그대로라 실기 센서(ld08/coin_d4)와 다르면 추후 보정 필요
- [ ] Step 2. 위 맵 기반 가짜 좌표(목적지) 지정
- [ ] Step 3. 가짜 입출력으로 전체 노드 연결 (각 `mov_*` 스텁 구현)
- [ ] Step 4. 시뮬레이터 기반 end2end 동작 확인 — ground-truth pose 대비 AMCL 오차 비교로 localization 문제 원인 분리. **AMCL 자체는 안정 동작 확인(2026-08-29, `launch/sim_localization.launch.py`)했으나, 자동 ground-truth 비교는 Ignition의 동적 스폰 엔티티 pose 브로드캐스트 문제로 막힘 — 상세 [GAZEBO.md](GAZEBO.md) 참고. 지금은 GUI 육안 확인으로 대체 중, 정적 include 전환이 근본 해결책**

## Phase 2 — 워킹 스켈레톤 · 실기 (테스트맵)

- [x] Step 1. 테스트맵 SLAM 지도 제작 완료 (실제 주행으로 생성)
- [ ] Step 2. 위 지도 위에서 가짜 좌표 기준 실제 로봇 end2end 동작 확인

## Phase 3 — ECC 실측 SLAM 매핑

- [x] Step 1. ECC 실내 전체 주행 (팀 공동 작업) — 완료, `slam/slam_frommap/out3/real.pgm` 확보
- [ ] Step 2. ECC 맵 생성 및 localization 정확도 검증 — 맵 생성 자체는 완료했으나 현장 주행 테스트에서 localization 문제 발견(2026-08-28) → Phase 1을 이 맵 기반으로 먼저 진행해 원인(소프트웨어 vs 하드웨어) 격리 중
- [ ] Step 3. Phase 1/2 스켈레톤의 가짜 좌표를 ECC 실제 좌표로 교체

## Phase 4 — 병렬 실구현

### 4-A. 배 — SLAM / 랜드마크 DB / LLM 연동
- [ ] Step 1. ECC 맵 기준 localization 정확도 튜닝
- [x] Step 2. 맵 기반 장소 좌표 DB 구축 — `slam/slam_frommap/out3/landmarks.csv`(36개 실측)를 `mov_dest_resolver`가 직접 읽음
- [x] Step 2-1. 맵/좌표DB 내부 패키지화(2026-09-03) — `mov_slam` 패키지 신설(ARCHITECTURE.md/TEAM.md에 계획만
      돼 있던 것을 실제 생성), `maps/mapjh.{yaml,pgm}`·`landmarks/landmarks.csv`를 `share/mov_slam/`로 설치.
      `mov_fsm`/`mov_dest_resolver`/`mov_navigation`의 `/workspace/slam/slam_frommap/...` 절대경로
      하드코딩 4곳을 `get_package_share_directory('mov_slam')` 기반으로 교체. 원본 SLAM 작업 디렉토리
      (`/workspace/slam/slam_frommap`, out/out2/out3+backup+검증이미지)는 그대로 두고 최종본만 승격하는
      흐름으로 정리. 함께 RViz 설정도 내부화(`mov_navigation/rviz/ecc_default_view.rviz`, stock
      `nav2_default_view.rviz`를 시드로 시작 — 곽/최 리뷰 후 원하는 대로 Save Config As로 갱신 필요)
- [x] Step 3. 자연어 → 고정 장소이름·좌표 매핑 LLM 프롬프트/스크립트 작성 — `mov_dest_resolver` 패키지, Gemini API(`gemini-3.5-flash-lite`)로 구현·검증 완료(2026-08-29). `category`(예: 화장실) 인식은 되지만 최근접 계산은 Step 4로 남음
- [x] Step 4. 카테고리 목적지 처리 (2026-08-30, 설계 변경 — 원래 계획했던 "현재 위치 기준
      최근접 좌표 매핑" 대신, 후보가 여럿이면 로봇이 임의로 고르지 않고 사용자에게 전부
      보여주고 직접 고르게 하는 방식으로 확정. 위치 정보가 필요 없어져 `/amcl_pose` 연동
      의존성도 사라짐). `landmarks.csv`에 category 컬럼 추가, `resolve()`가 후보 1개면
      바로 확정·2개 이상이면 `/dest_resolver/choices`로 UI에 물어봄, UI의 새 CHOOSING
      화면에서 탭하면 `/dest_resolver/choice_selected`로 최종 확정. 실제 API 테스트 통과

### 4-B. 최 — 네비게이션 / 시스템 통합 / 하드웨어
- [ ] Step 1. 동적 장애물 환경에서 안정적으로 동작하는 Navigator 선정
- [ ] Step 2. 젯슨 오린 나노 제약 내 Planner 성능 비교 (Nav2 기본 vs 대회 우승 Planner 등)
- [x] Step 3. 전체 시스템 통합 관리 (FSM, 노드 간 연동 유지보수) — `mov_fsm` 패키지 신설(2026-09-01,
      유휴 시 랜드마크 배회 → 말하기 버튼으로 정지 → 안내 종료 후 재개, `/initialpose` 수신 전
      배회 시작 안 하는 게이트 포함), `launch/full_system.launch.py`로 실기 전체 진입점 통합.
      상세는 `SESSION_LOG.md` 10번 항목
- [ ] Step 4. 하드웨어 디자인 및 배치

### 4-C. 곽 — STT / 터치스크린 / 음성출력
- [x] Step 1. 마이크 구동 테스트 — ReSpeaker 실기 연동 완료, USB 허브 경유 시 오디오 장치 번호
      변경·무한 대기 등 안정성 버그 수정(2026-09-03, `SESSION_LOG.md` 13번 항목)
- [x] Step 2. STT 안정화 (온디바이스 Whisper) — 실기 하드닝 진행 중, 위 13번 항목 참고
- [x] Step 3. 터치스크린 UI 설계 및 토픽 메시지 연결 — IDLE/LISTENING/CONFIRMING/CHOOSING/
      NAVIGATING(진행률 표시)/ARRIVED/ERROR 전 화면 구현, 한/영 다국어 지원. 토픽 계약은
      [INTERFACES.md](INTERFACES.md) 참고
- [x] Step 4. 음성출력 — 계획했던 상태별 mp3 사전녹음 대신 `mov_tts` 신설(2026-09-02)로 Gemini TTS
      실시간 합성 방식 채택. 목적지 해석 성공 시 안내 시작 문구, 도착 시 완료 문구 발행

## Phase 5 — 통합 & 젯슨 포팅

- [ ] Step 1. ECC 맵 위에서 각 파트 실구현 통합 e2e
- [ ] Step 2. 젯슨 오린 나노 보드로 이식, 동일 시나리오 재현

## Phase 6 — 실전 테스트

- [ ] Step 1. ECC 현장 실전 테스트 / 데모
