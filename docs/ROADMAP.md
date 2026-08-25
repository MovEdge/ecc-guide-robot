# Roadmap

전체 구현 순서. 각 Phase는 Step 단위로 세분화되어 있다. **Phase 하나가 보통 세션(채팅) 하나의 단위**이고, 그 안의 Step들은 같은 세션에서 순서대로 처리한다 — [PROMPTING_GUIDE.md](PROMPTING_GUIDE.md) 참고. 완료된 Step은 체크하고, 끝날 때마다 이 문서를 갱신한다.

## Phase 0 — 규칙설계 (공통)

- [x] Step 1. 문서화 인프라 구축 — 저장소 이름/구조 정리, `CLAUDE.md` 및 `docs/`(ARCHITECTURE·INTERFACES·ROADMAP·TEAM·GIT_WORKFLOW·PROMPTING_GUIDE) 작성, 패키지 CLAUDE.md 템플릿 준비
- [ ] Step 2. 입출력 인터페이스 규칙 + 로봇 상태 FSM + 노드 통신 구조 정하기 (좌표계 규약, 토픽/서비스/액션 계약 → [INTERFACES.md](INTERFACES.md), FSM과 노드 다이어그램 → [ARCHITECTURE.md](ARCHITECTURE.md))

## Phase 1 — 워킹 스켈레톤 · 시뮬레이터

- [ ] Step 1. 테스트맵 기반 가짜 좌표(목적지) 지정
- [ ] Step 2. 가짜 입출력으로 전체 노드 연결 (각 `mov_*` 스텁 구현)
- [ ] Step 3. 시뮬레이터 기반 end2end 동작 확인

## Phase 2 — 워킹 스켈레톤 · 실기 (테스트맵)

- [x] Step 1. 테스트맵 SLAM 지도 제작 완료 (실제 주행으로 생성)
- [ ] Step 2. 위 지도 위에서 가짜 좌표 기준 실제 로봇 end2end 동작 확인

## Phase 3 — ECC 실측 SLAM 매핑

- [ ] Step 1. ECC 실내 전체 주행 (팀 공동 작업)
- [ ] Step 2. ECC 맵 생성 및 localization 정확도 검증
- [ ] Step 3. Phase 1/2 스켈레톤의 가짜 좌표를 ECC 실제 좌표로 교체

## Phase 4 — 병렬 실구현

### 4-A. 배 — SLAM / 랜드마크 DB / LLM 연동
- [ ] Step 1. ECC 맵 기준 localization 정확도 튜닝
- [ ] Step 2. 맵 기반 장소 좌표 DB 구축
- [ ] Step 3. 자연어 → 고정 장소이름·좌표 매핑 LLM 프롬프트/스크립트 작성
- [ ] Step 4. 상대좌표 처리 로직 (현재 위치 기준 최근접 좌표 매핑)

### 4-B. 최 — 네비게이션 / 시스템 통합 / 하드웨어
- [ ] Step 1. 동적 장애물 환경에서 안정적으로 동작하는 Navigator 선정
- [ ] Step 2. 젯슨 오린 나노 제약 내 Planner 성능 비교 (Nav2 기본 vs 대회 우승 Planner 등)
- [ ] Step 3. 전체 시스템 통합 관리 (FSM, 노드 간 연동 유지보수)
- [ ] Step 4. 하드웨어 디자인 및 배치

### 4-C. 곽 — STT / 터치스크린 / 음성출력
- [ ] Step 1. 마이크 구동 테스트
- [ ] Step 2. STT 안정화 (온디바이스 또는 Gemini API)
- [ ] Step 3. 터치스크린 UI 설계 및 토픽 메시지 연결 (상태판, 말하기 버튼, 파형 애니메이션, 이동중 화면, 도착 화면)
- [ ] Step 4. 음성출력 (상태별 mp3 재생)

## Phase 5 — 통합 & 젯슨 포팅

- [ ] Step 1. ECC 맵 위에서 각 파트 실구현 통합 e2e
- [ ] Step 2. 젯슨 오린 나노 보드로 이식, 동일 시나리오 재현

## Phase 6 — 실전 테스트

- [ ] Step 1. ECC 현장 실전 테스트 / 데모
