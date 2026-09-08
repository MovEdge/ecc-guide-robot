# ecc-guide-robot
ECC(이화캠퍼스콤플렉스) 실내에서 목적지를 음성으로 물어보면 길을 안내하는자율주행 로봇 프로젝트입니다.
사용자가 말로 목적지를 말하면(STT) 로봇이 지도 상의 좌표를 찾아 자율주행(Nav2)으로 안내하고, 상태를 터치스크린과 음성(TTS)으로 알려줍니다.
Team **MovEdge**

## 현재 상태

`mov_ui → mov_stt → mov_dest_resolver → Nav2 → mov_ui/mov_tts` end-to-end 체인이 시뮬레이터·실기 모두에서 동작합니다.

- 음성으로 목적지 요청 → STT 인식 결과를 화면에서 확인/취소
- 목적지가 하나면 바로 확정, "화장실"처럼 카테고리 후보가 여럿이면 화면에서 직접 선택(화장실·엘리베이터는 최근접으로 자동 확정)
- Nav2 자율주행 + 진행률(%) 표시, 취소 가능
- 이동 시작/도착을 음성(TTS)으로 안내
- 목적지가 없을 때는 랜드마크 사이를 배회하다가 사용자가 부르면 정지(`mov_fsm`)
- 터치스크린 UI 한/영 다국어 지원
- Ignition Gazebo 기반 시뮬레이터로 실측 맵 위에서 사전 검증

자세한 진행 상황은 [docs/ROADMAP.md](docs/ROADMAP.md), 배경/의사결정은 [docs/SESSION_LOG.md](docs/SESSION_LOG.md) 참고.

## Tech Stack
- ROS 2 Humble / Ubuntu 22.04, Jetson Orin Nano
- TurtleBot3 Waffle (Raspberry Pi → Jetson Orin Nano 교체)
- SLAM (Cartographer 기반 매핑), Nav2
- STT / Gemini API 기반 목적지 해석 / Gemini TTS
- Ignition Gazebo Fortress (시뮬레이터)

## Packages (`src/`)

| 패키지 | 담당 | 역할 |
|---|---|---|
| `mov_interfaces` | 공동 | 노드 간 공용 메시지 정의 |
| `mov_stt` | 곽 | 음성 인식 |
| `mov_ui` | 곽 | 터치스크린 UI (한/영) |
| `mov_tts` | 곽 | 음성 안내(Gemini TTS) |
| `mov_navigation` | 최 | Nav2 연동, 시뮬레이터/실기 launch·world |
| `mov_fsm` | 최 | 전체 상태 관리, 유휴 배회 |
| `mov_slam` | 배 | 맵/랜드마크 좌표 DB |
| `mov_dest_resolver` | 배 | 자연어 → 목적지 해석(LLM) |

## Docs
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 시스템 구조, 노드/패키지구성
- [docs/INTERFACES.md](docs/INTERFACES.md) — 노드 간 통신 계약 (토픽/서비스/액션/FSM)
- [docs/ROADMAP.md](docs/ROADMAP.md) — 구현 순서 및 진행 상황
- [docs/TEAM.md](docs/TEAM.md) — 팀원별 담당 파트
- [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) — 브랜치/커밋/PR 규칙
- [docs/PROMPTING_GUIDE.md](docs/PROMPTING_GUIDE.md) — Phase별 Claude Code 프롬프트 예시
- [docs/GAZEBO.md](docs/GAZEBO.md) — Ignition Gazebo 시뮬레이터 구축/실행 방법, 디버깅 기록
- [docs/REPORT.md](docs/REPORT.md) — 중간보고서
- [CLAUDE.md](CLAUDE.md) — Claude Code 작업 규칙
