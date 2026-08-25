# Architecture

## 개요

ECC(이화캠퍼스콤플렉스) 실내에서 음성으로 목적지를 물으면 자율주행으로 안내하는 로봇. 사용자가 말한 목적지를 STT → LLM으로 지도상의 좌표에 매핑하고, Nav2로 주행하며, 터치스크린/음성으로 상태를 안내한다.

## 하드웨어 구성

- 베이스: TurtleBot3 Waffle
- 컴퓨트: Jetson Orin Nano (기존 Raspberry Pi에서 교체)
- LiDAR: TBD — `turtlebot3_ws`에 `ld08_driver`, `coin_d4_driver` 두 드라이버 소스가 참고용으로 있음, 최종 채택 센서는 Phase 0~1에서 확정
- 마이크 (STT 입력), 스피커 (TTS 출력), 터치스크린 (상태 표시/상호작용)

## 소프트웨어 스택 & 의존성 방침

- ROS 2 Humble / Ubuntu 22.04
- `mov_*` 패키지는 공식 ROS 2 Humble 배포 패키지(`navigation2`, TurtleBot3가 공식 제공하는 apt 패키지 등)에 의존한다. rosdep/apt로 설치 가능한 것은 apt로 설치하고, 소스를 직접 vendor하지 않는다.
- **`turtlebot3_ws`(turtlebot3, ld08_driver, coin_d4_driver 소스 클론)는 참고용일 뿐, 빌드/런타임 의존성이 아니다.** overlay workspace로 source하지 않는다. 로직이 필요하면 코드를 읽고 참고해서 `mov_*` 패키지 안에 직접 구현한다.
- 예외: LiDAR 드라이버처럼 공식 apt 패키지로 제공되지 않는 하드웨어 드라이버는 필요 시 별도로 자체 작성하거나 빌드해야 할 수 있음 — Phase 0~1에서 실제로 apt 설치가 가능한지 확인 후 결정.
- SLAM: Cartographer (`turtlebot3_ws/src/turtlebot3/turtlebot3_cartographer` 소스는 설정 참고용)
- Navigation: Nav2 (기본 Planner 또는 대체 Planner, [ROADMAP.md](ROADMAP.md) Phase 4-B에서 비교)
- STT: 온디바이스 또는 Gemini API
- 좌표 매핑: LLM API (자연어 → 장소 좌표)
- TTS: 사전 녹음 mp3 재생

## 패키지 구조 (계획)

| 패키지 | 담당 | 역할 |
|---|---|---|
| `mov_interfaces` | 공동 | 공용 msg/srv/action 정의 |
| `mov_fsm` | 최 | 전체 동작 FSM |
| `mov_navigation` | 최 | 경로 계획 및 이동 (Nav2 연동) |
| `mov_slam` | 배 | SLAM 및 지도 생성, localization |
| `mov_dest_resolver` | 배 | 자연어 목적지 → 좌표 (좌표 DB + LLM NLU) |
| `mov_stt` | 곽 | 음성 → 텍스트 |
| `mov_tts` | 곽 | 텍스트 → 음성 |
| `mov_ui` | 곽 | 터치스크린 UI |

각 패키지가 생성되면 패키지 폴더에 자체 `CLAUDE.md`를 두어, 그 안에서 작업할 때 담당자·인터페이스·현재 상태가 자동으로 로드되게 한다.

## 노드 다이어그램

_Phase 0에서 확정 후 이 섹션에 다이어그램/설명 추가 예정._

## FSM (로봇 상태)

_Phase 0에서 확정 후 이 섹션에 상태 목록과 전이 조건 추가 예정. 확정되면 [INTERFACES.md](INTERFACES.md)에도 상태값을 반영._
