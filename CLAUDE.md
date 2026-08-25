# ECC Guide Robot

ECC 실내 음성 안내 자율주행 로봇. ROS 2 Humble / Ubuntu 22.04 / TurtleBot3 Waffle / Jetson Orin Nano. Team MovEdge (곽/최/배).

## 문서 지도

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 시스템 구조, 하드웨어, 패키지 구성, 노드 다이어그램
- [docs/INTERFACES.md](docs/INTERFACES.md) — 노드 간 통신 계약 (아래 항상 로드됨)
- [docs/ROADMAP.md](docs/ROADMAP.md) — 구현 순서, Phase별 진행 상황
- [docs/TEAM.md](docs/TEAM.md) — 팀원별 담당 파트, 패키지 소유권
- [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) — 브랜치/커밋/PR 규칙
- [docs/PROMPTING_GUIDE.md](docs/PROMPTING_GUIDE.md) — Phase별 Claude Code 프롬프트 예시

패키지가 생성되면 [docs/templates/PACKAGE_CLAUDE_TEMPLATE.md](docs/templates/PACKAGE_CLAUDE_TEMPLATE.md)를 `src/<패키지명>/CLAUDE.md`로 복사해 채운다 (담당자·로컬 인터페이스·현재 상태). 그 폴더에서 작업할 때는 이 루트 문서와 함께 자동으로 로드된다.

## 핵심 규칙

- 새 기능 구현 전 아래 [INTERFACES.md](docs/INTERFACES.md) 계약을 확인한다. 토픽/메시지/FSM 상태를 임의로 바꾸지 않는다 — 바꿔야 하면 먼저 사용자에게 확인하고 문서부터 갱신한다.
- 담당 외 패키지([TEAM.md](docs/TEAM.md) 기준)를 수정해야 하면 먼저 이유를 확인받는다.
- 커밋은 `type(scope): 한글 설명` 형식 (예: `feat(nav): 동적 장애물 회피 로직 추가`). 자세한 규칙은 [GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) 참고.
- `main` 직접 push 금지, PR로만 병합.
- `turtlebot3_ws`(벤더 소스)는 참고용일 뿐 빌드/런타임 의존성이 아니다 — overlay로 source하지 않고, 공식 apt 패키지에 의존하거나 직접 구현한다. 자세한 내용은 [ARCHITECTURE.md](docs/ARCHITECTURE.md) 참고.
- `build/`, `install/`, `log/`는 커밋하지 않는다 (`.gitignore`에 등록됨).
- 작업으로 [ROADMAP.md](docs/ROADMAP.md) 항목이 끝났으면 체크박스를 갱신한다.
- 이 CPU 서버는 협업 코드 구현용이며, 실제 동작은 GitHub push 또는 워크스페이스 전송을 통해 Jetson Orin Nano 보드에서 검증한다. 하드웨어 종속적인 코드(센서 드라이버 등)는 실제 로봇 없이 동작 확인이 불가능할 수 있음을 감안한다.

## 항상 참조하는 계약 문서

@docs/INTERFACES.md
