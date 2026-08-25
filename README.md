# ecc-guide-robot
ECC(이화캠퍼스콤플렉스) 실내에서 목적지를 음성으로 물어보면 길을 안내하는자율주행 로봇 프로젝트입니다.
사용자가 말로 목적지를 말하면(STT) 로봇이 지도 상의 좌표를 찾아 자율주행(Nav2)으로 안내하고, 상태를 터치스크린과 음성(TTS)으로 알려줍니다.
Team **MovEdge**
## Tech Stack
- ROS 2 Humble / Ubuntu 22.04
- TurtleBot3 Waffle (Raspberry Pi → Jetson Orin Nano 교체)
- SLAM (Cartographer), Nav2
- STT / LLM 기반 좌표 매핑 / TTS
## Docs
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 시스템 구조, 노드/패키지구성
- [docs/INTERFACES.md](docs/INTERFACES.md) — 노드 간 통신 계약 (토픽/서비스/액션/FSM)
- [docs/ROADMAP.md](docs/ROADMAP.md) — 구현 순서 및 진행 상황
- [docs/TEAM.md](docs/TEAM.md) — 팀원별 담당 파트
- [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) — 브랜치/커밋/PR 규칙
- [docs/PROMPTING_GUIDE.md](docs/PROMPTING_GUIDE.md) — Phase별 Claude Code 프롬프트 예시
- [CLAUDE.md](CLAUDE.md) — Claude Code 작업 규칙
